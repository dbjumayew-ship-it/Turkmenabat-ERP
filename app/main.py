import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path

import jwt
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine, get_db
from .models import (
    AuditLog, DashboardMetric, Purchase, PurchaseItem, RawMaterial,
    RawMaterialMovement, RecipeItem, Product, Supplier, User,
    ProductionBatch, ProductionConsumption, FinishedGoodsMovement,
    ProductionEvent, QualityControlRecord
)
from .security import create_token, decode_token, hash_password, verify_password

BASE_DIR = Path(__file__).resolve().parent
COOKIE_SECURE = os.getenv("COOKIE_SECURE", "false").lower() == "true"

def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        username = os.getenv("ADMIN_USERNAME", "director")
        password = os.getenv("ADMIN_PASSWORD", "ChangeMe123!")
        full_name = os.getenv("ADMIN_FULL_NAME", "Director")
        user = db.query(User).filter(User.username == username).first()
        if not user:
            db.add(User(username=username, full_name=full_name,
                        password_hash=hash_password(password),
                        role="director", is_active=True))
        if db.query(DashboardMetric).count() == 0:
            db.add_all([
                DashboardMetric(metric_key="raw_stock", metric_label="Сырьё на складе", value=0, unit="ед.", sort_order=1),
                DashboardMetric(metric_key="finished_stock", metric_label="Готовая продукция", value=0, unit="бут.", sort_order=2),
                DashboardMetric(metric_key="production_today", metric_label="Произведено сегодня", value=0, unit="бут.", sort_order=3),
                DashboardMetric(metric_key="sales_month", metric_label="Продажи за месяц", value=0, unit="TMT", sort_order=4),
            ])
        db.commit()
    finally:
        db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    seed()
    yield

app = FastAPI(title="Türkmenabat ERP API", version="0.3.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")

def current_user(request: Request, db: Session = Depends(get_db)) -> User:
    token = request.cookies.get("erp_token")
    auth = request.headers.get("Authorization", "")
    if not token and auth.startswith("Bearer "):
        token = auth[7:]
    if not token:
        raise HTTPException(401)
    try:
        payload = decode_token(token)
    except jwt.PyJWTError:
        raise HTTPException(401)
    user = db.query(User).filter(User.username == payload.get("sub")).first()
    if not user or not user.is_active:
        raise HTTPException(401)
    return user

def stock_for_material(db: Session, material_id: int) -> Decimal:
    total = db.query(
        func.coalesce(func.sum(case(
            (RawMaterialMovement.movement_type == "receipt", RawMaterialMovement.quantity),
            else_=-RawMaterialMovement.quantity,
        )), 0)
    ).filter(RawMaterialMovement.material_id == material_id).scalar()
    return Decimal(total or 0)

def safe_decimal(value: str, allow_zero: bool = False) -> Decimal:
    try:
        number = Decimal((value or "0").replace(",", "."))
        if number < 0 or (not allow_zero and number == 0):
            raise ValueError
        return number
    except Exception:
        raise HTTPException(400, "Неверное числовое значение")

@app.get("/api/health")
def health():
    return {"status": "ok", "version": "0.3.0"}

@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/web/login")
def web_login(username: str = Form(...), password: str = Form(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == username).first()
    if not user or not verify_password(password, user.password_hash):
        return RedirectResponse("/?error=1", 303)
    response = RedirectResponse("/dashboard", 303)
    response.set_cookie("erp_token", create_token(user.username, user.role),
                        httponly=True, secure=COOKIE_SECURE, samesite="lax", max_age=43200)
    db.add(AuditLog(username=user.username, action="login", details="Web login"))
    db.commit()
    return response

@app.get("/dashboard", response_class=HTMLResponse)
def dashboard(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    raw_total = db.query(func.coalesce(func.sum(case(
        (RawMaterialMovement.movement_type == "receipt", RawMaterialMovement.quantity),
        else_=-RawMaterialMovement.quantity,
    )), 0)).scalar()
    metrics = db.query(DashboardMetric).order_by(DashboardMetric.sort_order).all()
    display_metrics = [{"label": x.metric_label,
                        "value": Decimal(raw_total or 0) if x.metric_key == "raw_stock" else x.value,
                        "unit": x.unit} for x in metrics]
    return templates.TemplateResponse("dashboard.html",
        {"request": request, "user": user, "metrics": display_metrics})

@app.get("/warehouse/raw-materials", response_class=HTMLResponse)
def raw_materials_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    materials = db.query(RawMaterial).filter(RawMaterial.is_active == True).order_by(RawMaterial.name).all()
    rows = [{"material": m, "stock": stock_for_material(db, m.id)} for m in materials]
    movements = db.query(RawMaterialMovement).order_by(RawMaterialMovement.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("raw_materials.html", {
        "request": request, "user": user, "rows": rows, "materials": materials,
        "movements": movements, "error": request.query_params.get("error"),
        "success": request.query_params.get("success")
    })

@app.post("/warehouse/raw-materials/create")
def create_raw_material(request: Request, code: str = Form(...), name: str = Form(...),
                        unit: str = Form(...), minimum_stock: str = Form("0"),
                        db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    code, name = code.strip().upper(), name.strip()
    if not code or not name:
        return RedirectResponse("/warehouse/raw-materials?error=Заполните код и название", 303)
    if db.query(RawMaterial).filter(RawMaterial.code == code).first():
        return RedirectResponse("/warehouse/raw-materials?error=Такой код уже существует", 303)
    minimum = safe_decimal(minimum_stock, allow_zero=True)
    db.add(RawMaterial(code=code, name=name, unit=unit.strip() or "кг", minimum_stock=minimum))
    db.add(AuditLog(username=user.username, action="raw_material_create", details=f"{code} — {name}"))
    db.commit()
    return RedirectResponse("/warehouse/raw-materials?success=Сырьё добавлено", 303)

@app.post("/warehouse/raw-materials/movement")
def create_movement(request: Request, material_id: int = Form(...), movement_type: str = Form(...),
                    quantity: str = Form(...), unit_price: str = Form("0"),
                    supplier_or_destination: str = Form(""), document_number: str = Form(""),
                    note: str = Form(""), db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    material = db.get(RawMaterial, material_id)
    if not material:
        return RedirectResponse("/warehouse/raw-materials?error=Сырьё не найдено", 303)
    if movement_type not in {"receipt", "issue"}:
        return RedirectResponse("/warehouse/raw-materials?error=Неверный тип операции", 303)
    qty, price = safe_decimal(quantity), safe_decimal(unit_price, allow_zero=True)
    if movement_type == "issue" and qty > stock_for_material(db, material.id):
        return RedirectResponse("/warehouse/raw-materials?error=Недостаточно остатка", 303)
    db.add(RawMaterialMovement(
        material_id=material.id, movement_type=movement_type, quantity=qty, unit_price=price,
        supplier_or_destination=supplier_or_destination.strip(),
        document_number=document_number.strip(), note=note.strip(), created_by=user.username
    ))
    db.add(AuditLog(username=user.username, action=f"raw_material_{movement_type}",
                    details=f"{material.code}: {qty} {material.unit}"))
    db.commit()
    return RedirectResponse("/warehouse/raw-materials?success=Операция сохранена", 303)

@app.get("/suppliers", response_class=HTMLResponse)
def suppliers_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()
    return templates.TemplateResponse("suppliers.html", {
        "request": request, "user": user, "suppliers": suppliers,
        "error": request.query_params.get("error"), "success": request.query_params.get("success")
    })

@app.post("/suppliers/create")
def create_supplier(request: Request, code: str = Form(...), name: str = Form(...),
                    contact_person: str = Form(""), phone: str = Form(""),
                    email: str = Form(""), address: str = Form(""),
                    tax_number: str = Form(""), currency: str = Form("TMT"),
                    db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    code, name = code.strip().upper(), name.strip()
    if not code or not name:
        return RedirectResponse("/suppliers?error=Заполните код и название", 303)
    if db.query(Supplier).filter(Supplier.code == code).first():
        return RedirectResponse("/suppliers?error=Такой код уже существует", 303)
    supplier = Supplier(code=code, name=name, contact_person=contact_person.strip(),
                        phone=phone.strip(), email=email.strip(), address=address.strip(),
                        tax_number=tax_number.strip(), currency=currency.strip().upper() or "TMT")
    db.add(supplier)
    db.add(AuditLog(username=user.username, action="supplier_create", details=f"{code} — {name}"))
    db.commit()
    return RedirectResponse("/suppliers?success=Поставщик добавлен", 303)

@app.get("/purchases", response_class=HTMLResponse)
def purchases_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    suppliers = db.query(Supplier).filter(Supplier.is_active == True).order_by(Supplier.name).all()
    materials = db.query(RawMaterial).filter(RawMaterial.is_active == True).order_by(RawMaterial.name).all()
    purchases = db.query(Purchase).order_by(Purchase.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("purchases.html", {
        "request": request, "user": user, "suppliers": suppliers, "materials": materials,
        "purchases": purchases, "error": request.query_params.get("error"),
        "success": request.query_params.get("success")
    })

@app.post("/purchases/create")
def create_purchase(request: Request, document_number: str = Form(...),
                    supplier_id: int = Form(...), material_id: int = Form(...),
                    quantity: str = Form(...), unit_price: str = Form(...),
                    invoice_number: str = Form(""), currency: str = Form("TMT"),
                    note: str = Form(""), db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)
    document_number = document_number.strip().upper()
    supplier = db.get(Supplier, supplier_id)
    material = db.get(RawMaterial, material_id)
    if not supplier or not material:
        return RedirectResponse("/purchases?error=Поставщик или сырьё не найдено", 303)
    if db.query(Purchase).filter(Purchase.document_number == document_number).first():
        return RedirectResponse("/purchases?error=Такой номер закупки уже существует", 303)
    qty, price = safe_decimal(quantity), safe_decimal(unit_price, allow_zero=True)
    purchase = Purchase(document_number=document_number, supplier_id=supplier.id,
                        invoice_number=invoice_number.strip(), currency=currency.strip().upper() or "TMT",
                        note=note.strip(), created_by=user.username, status="posted")
    purchase.items.append(PurchaseItem(material_id=material.id, quantity=qty, unit_price=price))
    db.add(purchase)
    db.add(RawMaterialMovement(
        material_id=material.id, movement_type="receipt", quantity=qty, unit_price=price,
        supplier_or_destination=supplier.name, document_number=document_number,
        note=f"Закупка {document_number}. {note}".strip(), created_by=user.username
    ))
    db.add(AuditLog(username=user.username, action="purchase_post",
                    details=f"{document_number}: {material.code}, {qty} {material.unit}"))
    db.commit()
    return RedirectResponse("/purchases?success=Закупка проведена, склад обновлён", 303)

@app.get("/logout")
def logout():
    response = RedirectResponse("/", 303)
    response.delete_cookie("erp_token")
    return response


@app.get("/recipes", response_class=HTMLResponse)
def recipes_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    products = db.query(Product).filter(Product.is_active == True).order_by(Product.name).all()
    materials = db.query(RawMaterial).filter(RawMaterial.is_active == True).order_by(RawMaterial.name).all()

    recipe_rows = []
    for product in products:
        total_items = len(product.recipe_items)
        recipe_rows.append({
            "product": product,
            "items_count": total_items,
            "items": sorted(product.recipe_items, key=lambda x: x.material.name.lower())
        })

    return templates.TemplateResponse("recipes.html", {
        "request": request,
        "user": user,
        "recipe_rows": recipe_rows,
        "products": products,
        "materials": materials,
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })

@app.post("/recipes/products/create")
def create_product(
    request: Request,
    code: str = Form(...),
    name: str = Form(...),
    volume_liters: str = Form("0.33"),
    output_unit: str = Form("бут."),
    base_batch_quantity: str = Form("1000"),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    code = code.strip().upper()
    name = name.strip()
    if not code or not name:
        return RedirectResponse("/recipes?error=Заполните код и название продукта", 303)

    if db.query(Product).filter(Product.code == code).first():
        return RedirectResponse("/recipes?error=Такой код продукта уже существует", 303)

    volume = safe_decimal(volume_liters)
    batch = safe_decimal(base_batch_quantity)

    product = Product(
        code=code,
        name=name,
        volume_liters=volume,
        output_unit=output_unit.strip() or "бут.",
        base_batch_quantity=batch,
    )
    db.add(product)
    db.add(AuditLog(
        username=user.username,
        action="product_create",
        details=f"{code} — {name}; базовая партия {batch}"
    ))
    db.commit()
    return RedirectResponse("/recipes?success=Продукт создан", 303)

@app.post("/recipes/items/create")
def create_recipe_item(
    request: Request,
    product_id: int = Form(...),
    material_id: int = Form(...),
    quantity: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    product = db.get(Product, product_id)
    material = db.get(RawMaterial, material_id)
    if not product or not material:
        return RedirectResponse("/recipes?error=Продукт или сырьё не найдено", 303)

    qty = safe_decimal(quantity)

    existing = db.query(RecipeItem).filter(
        RecipeItem.product_id == product.id,
        RecipeItem.material_id == material.id,
    ).first()

    if existing:
        existing.quantity = qty
        existing.note = note.strip()
        action = "recipe_item_update"
    else:
        db.add(RecipeItem(
            product_id=product.id,
            material_id=material.id,
            quantity=qty,
            note=note.strip(),
        ))
        action = "recipe_item_create"

    db.add(AuditLog(
        username=user.username,
        action=action,
        details=f"{product.code}: {material.code} = {qty} {material.unit}"
    ))
    db.commit()
    return RedirectResponse("/recipes?success=Рецептура сохранена", 303)

@app.post("/recipes/items/delete")
def delete_recipe_item(
    request: Request,
    item_id: int = Form(...),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    item = db.get(RecipeItem, item_id)
    if not item:
        return RedirectResponse("/recipes?error=Строка рецептуры не найдена", 303)

    details = f"{item.product.code}: удалено {item.material.code}"
    db.delete(item)
    db.add(AuditLog(
        username=user.username,
        action="recipe_item_delete",
        details=details
    ))
    db.commit()
    return RedirectResponse("/recipes?success=Компонент удалён", 303)


def finished_stock_for_product(db: Session, product_id: int) -> Decimal:
    total = db.query(
        func.coalesce(func.sum(case(
            (FinishedGoodsMovement.movement_type == "receipt", FinishedGoodsMovement.quantity),
            else_=-FinishedGoodsMovement.quantity,
        )), 0)
    ).filter(FinishedGoodsMovement.product_id == product_id).scalar()
    return Decimal(total or 0)

@app.get("/production", response_class=HTMLResponse)
def production_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.name)
        .all()
    )
    batches = (
        db.query(ProductionBatch)
        .order_by(ProductionBatch.created_at.desc())
        .limit(50)
        .all()
    )

    product_rows = []
    for product in products:
        shortages = []
        for item in product.recipe_items:
            available = stock_for_material(db, item.material_id)
            shortages.append({
                "material": item.material,
                "available": available,
                "required_for_base": item.quantity,
            })
        product_rows.append({
            "product": product,
            "finished_stock": finished_stock_for_product(db, product.id),
            "materials": shortages,
        })

    return templates.TemplateResponse("production.html", {
        "request": request,
        "user": user,
        "products": products,
        "product_rows": product_rows,
        "batches": batches,
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })

@app.post("/production/create")
def create_production_batch(
    request: Request,
    batch_number: str = Form(...),
    product_id: int = Form(...),
    output_quantity: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    batch_number = batch_number.strip().upper()
    if not batch_number:
        return RedirectResponse("/production?error=Укажите номер производственной партии", 303)

    if db.query(ProductionBatch).filter(
        ProductionBatch.batch_number == batch_number
    ).first():
        return RedirectResponse("/production?error=Такой номер партии уже существует", 303)

    product = db.get(Product, product_id)
    if not product:
        return RedirectResponse("/production?error=Продукт не найден", 303)

    if not product.recipe_items:
        return RedirectResponse(
            "/production?error=Для продукта не создана рецептура", 303
        )

    output_qty = safe_decimal(output_quantity)
    base_qty = Decimal(product.base_batch_quantity)
    if base_qty <= 0:
        return RedirectResponse(
            "/production?error=У продукта неверно указана базовая партия", 303
        )

    multiplier = output_qty / base_qty
    required_rows = []
    shortage_messages = []

    for item in product.recipe_items:
        required = (Decimal(item.quantity) * multiplier).quantize(Decimal("0.0001"))
        available = stock_for_material(db, item.material_id)
        required_rows.append((item, required, available))
        if required > available:
            shortage = required - available
            shortage_messages.append(
                f"{item.material.name}: не хватает {shortage} {item.material.unit}"
            )

    if shortage_messages:
        message = "; ".join(shortage_messages)
        return RedirectResponse(f"/production?error={message}", 303)

    try:
        batch = ProductionBatch(
            batch_number=batch_number,
            product_id=product.id,
            output_quantity=output_qty,
            status="posted",
            note=note.strip(),
            created_by=user.username,
        )
        db.add(batch)
        db.flush()

        for item, required, _available in required_rows:
            db.add(ProductionConsumption(
                production_batch_id=batch.id,
                material_id=item.material_id,
                required_quantity=required,
            ))
            db.add(RawMaterialMovement(
                material_id=item.material_id,
                movement_type="issue",
                quantity=required,
                unit_price=0,
                supplier_or_destination=f"Производство: {product.name}",
                document_number=batch_number,
                note=f"Автоматическое списание по партии {batch_number}",
                created_by=user.username,
            ))

        db.add(FinishedGoodsMovement(
            product_id=product.id,
            movement_type="receipt",
            quantity=output_qty,
            document_number=batch_number,
            destination_or_customer="Склад готовой продукции",
            note=f"Выпуск по производственной партии {batch_number}",
            created_by=user.username,
        ))

        db.add(AuditLog(
            username=user.username,
            action="production_post",
            details=f"{batch_number}: {product.code}, выпуск {output_qty} {product.output_unit}",
        ))
        db.commit()
    except Exception:
        db.rollback()
        raise

    return RedirectResponse(
        "/production?success=Производственная партия проведена, сырьё списано, продукция оприходована",
        303,
    )

@app.get("/finished-goods", response_class=HTMLResponse)
def finished_goods_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.name)
        .all()
    )
    rows = [
        {"product": product, "stock": finished_stock_for_product(db, product.id)}
        for product in products
    ]
    movements = (
        db.query(FinishedGoodsMovement)
        .order_by(FinishedGoodsMovement.created_at.desc())
        .limit(100)
        .all()
    )

    return templates.TemplateResponse("finished_goods.html", {
        "request": request,
        "user": user,
        "rows": rows,
        "movements": movements,
    })


PRODUCTION_EVENT_LABELS = {
    "defect": "Брак производства",
    "finished_writeoff": "Списание готовой продукции",
    "raw_loss": "Потеря сырья",
    "rework": "Передача в переработку",
}

FINISHED_REASONS = [
    "Разбитая бутылка",
    "Неправильная крышка",
    "Повреждённая этикетка",
    "Неправильный уровень наполнения",
    "Утечка",
    "Грязная бутылка",
    "Повреждение упаковки",
    "Истёк срок годности",
    "Повреждение при хранении",
    "Повреждение при погрузке",
    "Лабораторный образец",
    "Другое",
]

RAW_LOSS_REASONS = [
    "Испарение",
    "Пролив",
    "Потери при запуске линии",
    "Остаток в трубопроводе",
    "Промывка оборудования / CIP",
    "Лабораторный образец",
    "Повреждение тары",
    "Другое",
]

@app.get("/production/control", response_class=HTMLResponse)
def production_control_page(request: Request, db: Session = Depends(get_db)):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    products = (
        db.query(Product)
        .filter(Product.is_active == True)
        .order_by(Product.name)
        .all()
    )
    materials = (
        db.query(RawMaterial)
        .filter(RawMaterial.is_active == True)
        .order_by(RawMaterial.name)
        .all()
    )
    batches = (
        db.query(ProductionBatch)
        .order_by(ProductionBatch.created_at.desc())
        .limit(100)
        .all()
    )
    events = (
        db.query(ProductionEvent)
        .order_by(ProductionEvent.created_at.desc())
        .limit(100)
        .all()
    )
    quality_records = (
        db.query(QualityControlRecord)
        .order_by(QualityControlRecord.created_at.desc())
        .limit(100)
        .all()
    )

    total_produced = db.query(
        func.coalesce(func.sum(ProductionBatch.output_quantity), 0)
    ).scalar()

    defect_total = db.query(
        func.coalesce(func.sum(ProductionEvent.quantity), 0)
    ).filter(ProductionEvent.event_type == "defect").scalar()

    writeoff_total = db.query(
        func.coalesce(func.sum(ProductionEvent.quantity), 0)
    ).filter(ProductionEvent.event_type == "finished_writeoff").scalar()

    rework_total = db.query(
        func.coalesce(func.sum(ProductionEvent.quantity), 0)
    ).filter(ProductionEvent.event_type == "rework").scalar()

    produced_decimal = Decimal(total_produced or 0)
    defect_decimal = Decimal(defect_total or 0)
    efficiency = Decimal("100.00")
    if produced_decimal > 0:
        efficiency = (
            (produced_decimal - defect_decimal) / produced_decimal * Decimal("100")
        ).quantize(Decimal("0.01"))

    return templates.TemplateResponse("production_control.html", {
        "request": request,
        "user": user,
        "products": products,
        "materials": materials,
        "batches": batches,
        "events": events,
        "quality_records": quality_records,
        "event_labels": PRODUCTION_EVENT_LABELS,
        "finished_reasons": FINISHED_REASONS,
        "raw_loss_reasons": RAW_LOSS_REASONS,
        "stats": {
            "produced": produced_decimal,
            "defect": defect_decimal,
            "writeoff": Decimal(writeoff_total or 0),
            "rework": Decimal(rework_total or 0),
            "efficiency": efficiency,
        },
        "error": request.query_params.get("error"),
        "success": request.query_params.get("success"),
    })

@app.post("/production/events/create")
def create_production_event(
    request: Request,
    document_number: str = Form(...),
    event_type: str = Form(...),
    quantity: str = Form(...),
    reason: str = Form(...),
    product_id: int | None = Form(None),
    material_id: int | None = Form(None),
    production_batch_id: int | None = Form(None),
    responsible_person: str = Form(""),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    document_number = document_number.strip().upper()
    if event_type not in PRODUCTION_EVENT_LABELS:
        return RedirectResponse("/production/control?error=Неверный тип операции", 303)

    if db.query(ProductionEvent).filter(
        ProductionEvent.document_number == document_number
    ).first():
        return RedirectResponse(
            "/production/control?error=Документ с таким номером уже существует", 303
        )

    qty = safe_decimal(quantity)
    product = db.get(Product, product_id) if product_id else None
    material = db.get(RawMaterial, material_id) if material_id else None
    batch = db.get(ProductionBatch, production_batch_id) if production_batch_id else None

    finished_event = event_type in {"defect", "finished_writeoff", "rework"}
    raw_event = event_type == "raw_loss"

    if finished_event:
        if not product:
            return RedirectResponse(
                "/production/control?error=Выберите готовый продукт", 303
            )
        available = finished_stock_for_product(db, product.id)
        if qty > available:
            return RedirectResponse(
                "/production/control?error=Недостаточно готовой продукции на складе", 303
            )

    if raw_event:
        if not material:
            return RedirectResponse(
                "/production/control?error=Выберите сырьё", 303
            )
        available = stock_for_material(db, material.id)
        if qty > available:
            return RedirectResponse(
                "/production/control?error=Недостаточно сырья на складе", 303
            )

    event = ProductionEvent(
        document_number=document_number,
        event_type=event_type,
        product_id=product.id if product else None,
        material_id=material.id if material else None,
        production_batch_id=batch.id if batch else None,
        quantity=qty,
        reason=reason.strip(),
        responsible_person=responsible_person.strip(),
        note=note.strip(),
        created_by=user.username,
    )
    db.add(event)

    if finished_event:
        db.add(FinishedGoodsMovement(
            product_id=product.id,
            movement_type="issue",
            quantity=qty,
            document_number=document_number,
            destination_or_customer=PRODUCTION_EVENT_LABELS[event_type],
            note=f"{reason}. {note}".strip(),
            created_by=user.username,
        ))

    if raw_event:
        db.add(RawMaterialMovement(
            material_id=material.id,
            movement_type="issue",
            quantity=qty,
            unit_price=0,
            supplier_or_destination="Производственные потери",
            document_number=document_number,
            note=f"{reason}. {note}".strip(),
            created_by=user.username,
        ))

    db.add(AuditLog(
        username=user.username,
        action=f"production_{event_type}",
        details=(
            f"{document_number}: {PRODUCTION_EVENT_LABELS[event_type]}, "
            f"{qty}, причина: {reason}"
        ),
    ))
    db.commit()
    return RedirectResponse(
        "/production/control?success=Операция проведена и остатки обновлены", 303
    )

@app.post("/production/quality/create")
def create_quality_control(
    request: Request,
    document_number: str = Form(...),
    production_batch_id: int = Form(...),
    strength_percent: str = Form(""),
    co2_value: str = Form(""),
    color_result: str = Form(""),
    smell_result: str = Form(""),
    taste_result: str = Form(""),
    status: str = Form(...),
    checked_by: str = Form(...),
    note: str = Form(""),
    db: Session = Depends(get_db),
):
    try:
        user = current_user(request, db)
    except HTTPException:
        return RedirectResponse("/", 303)

    document_number = document_number.strip().upper()
    if status not in {"approved", "rejected", "conditional"}:
        return RedirectResponse(
            "/production/control?error=Неверный статус контроля качества", 303
        )

    if db.query(QualityControlRecord).filter(
        QualityControlRecord.document_number == document_number
    ).first():
        return RedirectResponse(
            "/production/control?error=Документ контроля уже существует", 303
        )

    batch = db.get(ProductionBatch, production_batch_id)
    if not batch:
        return RedirectResponse(
            "/production/control?error=Производственная партия не найдена", 303
        )

    strength = safe_decimal(strength_percent, allow_zero=True) if strength_percent.strip() else None
    co2 = safe_decimal(co2_value, allow_zero=True) if co2_value.strip() else None

    record = QualityControlRecord(
        document_number=document_number,
        production_batch_id=batch.id,
        strength_percent=strength,
        co2_value=co2,
        color_result=color_result.strip(),
        smell_result=smell_result.strip(),
        taste_result=taste_result.strip(),
        status=status,
        checked_by=checked_by.strip(),
        note=note.strip(),
        created_by=user.username,
    )
    db.add(record)
    db.add(AuditLog(
        username=user.username,
        action="quality_control_create",
        details=f"{document_number}: партия {batch.batch_number}, статус {status}",
    ))
    db.commit()
    return RedirectResponse(
        "/production/control?success=Контроль качества сохранён", 303
    )
