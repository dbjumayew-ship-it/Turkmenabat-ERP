import os
from contextlib import asynccontextmanager
from decimal import Decimal
from pathlib import Path
import jwt
from fastapi import Depends,FastAPI,Form,HTTPException,Request
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import case,func
from sqlalchemy.orm import Session
from .database import Base,SessionLocal,engine,get_db
from .models import User,AuditLog,DashboardMetric,RawMaterial,RawMaterialMovement
from .security import hash_password,verify_password,create_token,decode_token
BASE=Path(__file__).resolve().parent
COOKIE_SECURE=os.getenv("COOKIE_SECURE","false").lower()=="true"
def seed():
    Base.metadata.create_all(bind=engine); db=SessionLocal()
    try:
        u=os.getenv("ADMIN_USERNAME","director"); p=os.getenv("ADMIN_PASSWORD","ChangeMe123!"); n=os.getenv("ADMIN_FULL_NAME","Director")
        user=db.query(User).filter_by(username=u).first()
        if not user: db.add(User(username=u,full_name=n,password_hash=hash_password(p),role="director",is_active=True))
        if db.query(DashboardMetric).count()==0:
            db.add_all([DashboardMetric(metric_key="raw_stock",metric_label="Сырьё на складе",value=0,unit="ед.",sort_order=1),DashboardMetric(metric_key="finished_stock",metric_label="Готовая продукция",value=0,unit="бут.",sort_order=2),DashboardMetric(metric_key="production_today",metric_label="Произведено сегодня",value=0,unit="бут.",sort_order=3),DashboardMetric(metric_key="sales_month",metric_label="Продажи за месяц",value=0,unit="TMT",sort_order=4)])
        db.commit()
    finally: db.close()
@asynccontextmanager
async def lifespan(app): seed(); yield
app=FastAPI(title="Turkmenabat ERP API",version="0.2.0",lifespan=lifespan)
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
templates=Jinja2Templates(directory=BASE/"templates")
def current(request:Request,db:Session):
    t=request.cookies.get("erp_token")
    if not t: raise HTTPException(401)
    try: payload=decode_token(t)
    except jwt.PyJWTError: raise HTTPException(401)
    u=db.query(User).filter_by(username=payload.get("sub")).first()
    if not u or not u.is_active: raise HTTPException(401)
    return u
def stock(db,mid):
    v=db.query(func.coalesce(func.sum(case((RawMaterialMovement.movement_type=="receipt",RawMaterialMovement.quantity),else_=-RawMaterialMovement.quantity)),0)).filter(RawMaterialMovement.material_id==mid).scalar()
    return Decimal(v or 0)
@app.get("/api/health")
def health(): return {"status":"ok","version":"0.2.0"}
@app.get("/",response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse("login.html",{"request":request})
@app.post("/web/login")
def login(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=username).first()
    if not u or not verify_password(password,u.password_hash): return RedirectResponse("/?error=1",303)
    r=RedirectResponse("/dashboard",303); r.set_cookie("erp_token",create_token(u.username,u.role),httponly=True,secure=COOKIE_SECURE,samesite="lax",max_age=43200); return r
@app.get("/dashboard",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
    try:u=current(request,db)
    except HTTPException:return RedirectResponse("/",303)
    total=db.query(func.coalesce(func.sum(case((RawMaterialMovement.movement_type=="receipt",RawMaterialMovement.quantity),else_=-RawMaterialMovement.quantity)),0)).scalar()
    ms=db.query(DashboardMetric).order_by(DashboardMetric.sort_order).all(); arr=[]
    for m in ms: arr.append({"label":m.metric_label,"value":Decimal(total or 0) if m.metric_key=="raw_stock" else m.value,"unit":m.unit})
    return templates.TemplateResponse("dashboard.html",{"request":request,"user":u,"metrics":arr})
@app.get("/warehouse/raw-materials",response_class=HTMLResponse)
def warehouse(request:Request,db:Session=Depends(get_db)):
    try:u=current(request,db)
    except HTTPException:return RedirectResponse("/",303)
    mats=db.query(RawMaterial).filter_by(is_active=True).order_by(RawMaterial.name).all(); rows=[{"material":m,"stock":stock(db,m.id)} for m in mats]
    moves=db.query(RawMaterialMovement).order_by(RawMaterialMovement.created_at.desc()).limit(50).all()
    return templates.TemplateResponse("raw_materials.html",{"request":request,"user":u,"materials":mats,"rows":rows,"movements":moves,"error":request.query_params.get("error"),"success":request.query_params.get("success")})
@app.post("/warehouse/raw-materials/create")
def create_material(request:Request,code:str=Form(...),name:str=Form(...),unit:str=Form(...),minimum_stock:str=Form("0"),db:Session=Depends(get_db)):
    try:u=current(request,db)
    except HTTPException:return RedirectResponse("/",303)
    code=code.strip().upper(); name=name.strip()
    if db.query(RawMaterial).filter_by(code=code).first(): return RedirectResponse("/warehouse/raw-materials?error=Такой код уже существует",303)
    try: minimum=Decimal(minimum_stock.replace(",","."))
    except: return RedirectResponse("/warehouse/raw-materials?error=Неверный минимальный остаток",303)
    db.add(RawMaterial(code=code,name=name,unit=unit,minimum_stock=minimum)); db.add(AuditLog(username=u.username,action="raw_material_create",details=f"{code} — {name}")); db.commit()
    return RedirectResponse("/warehouse/raw-materials?success=Сырьё добавлено",303)
@app.post("/warehouse/raw-materials/movement")
def movement(request:Request,material_id:int=Form(...),movement_type:str=Form(...),quantity:str=Form(...),unit_price:str=Form("0"),supplier_or_destination:str=Form(""),document_number:str=Form(""),note:str=Form(""),db:Session=Depends(get_db)):
    try:u=current(request,db)
    except HTTPException:return RedirectResponse("/",303)
    m=db.get(RawMaterial,material_id)
    if not m:return RedirectResponse("/warehouse/raw-materials?error=Сырьё не найдено",303)
    try:q=Decimal(quantity.replace(",",".")); price=Decimal(unit_price.replace(",","."))
    except:return RedirectResponse("/warehouse/raw-materials?error=Проверьте количество и цену",303)
    if q<=0:return RedirectResponse("/warehouse/raw-materials?error=Количество должно быть больше нуля",303)
    if movement_type=="issue" and q>stock(db,m.id): return RedirectResponse(f"/warehouse/raw-materials?error=Недостаточно остатка. Доступно {stock(db,m.id)} {m.unit}",303)
    db.add(RawMaterialMovement(material_id=m.id,movement_type=movement_type,quantity=q,unit_price=price,supplier_or_destination=supplier_or_destination,document_number=document_number,note=note,created_by=u.username)); db.add(AuditLog(username=u.username,action=f"raw_material_{movement_type}",details=f"{m.code}: {q} {m.unit}")); db.commit()
    return RedirectResponse("/warehouse/raw-materials?success=Операция сохранена",303)
@app.get("/logout")
def logout():
    r=RedirectResponse("/",303); r.delete_cookie("erp_token"); return r
