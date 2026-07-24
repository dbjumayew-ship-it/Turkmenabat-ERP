from datetime import datetime
from decimal import Decimal
from sqlalchemy import String, Boolean, DateTime, Integer, Numeric, ForeignKey, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from .database import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    full_name: Mapped[str] = mapped_column(String(150))
    password_hash: Mapped[str] = mapped_column(String(300))
    role: Mapped[str] = mapped_column(String(40), default="director")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(80))
    action: Mapped[str] = mapped_column(String(120))
    details: Mapped[str] = mapped_column(String(500), default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class DashboardMetric(Base):
    __tablename__ = "dashboard_metrics"
    id: Mapped[int] = mapped_column(primary_key=True)
    metric_key: Mapped[str] = mapped_column(String(80), unique=True)
    metric_label: Mapped[str] = mapped_column(String(120))
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    unit: Mapped[str] = mapped_column(String(30), default="")
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

class Supplier(Base):
    __tablename__ = "suppliers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    contact_person: Mapped[str] = mapped_column(String(140), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(140), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    tax_number: Mapped[str] = mapped_column(String(80), default="")
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    purchases: Mapped[list["Purchase"]] = relationship(back_populates="supplier")

class RawMaterial(Base):
    __tablename__ = "raw_materials"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    unit: Mapped[str] = mapped_column(String(20), default="кг")
    minimum_stock: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    movements: Mapped[list["RawMaterialMovement"]] = relationship(back_populates="material")

class Purchase(Base):
    __tablename__ = "purchases"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    supplier_id: Mapped[int] = mapped_column(ForeignKey("suppliers.id"), index=True)
    invoice_number: Mapped[str] = mapped_column(String(80), default="")
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    status: Mapped[str] = mapped_column(String(20), default="posted")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    supplier: Mapped[Supplier] = relationship(back_populates="purchases")
    items: Mapped[list["PurchaseItem"]] = relationship(back_populates="purchase", cascade="all, delete-orphan")

class PurchaseItem(Base):
    __tablename__ = "purchase_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    purchase_id: Mapped[int] = mapped_column(ForeignKey("purchases.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    purchase: Mapped[Purchase] = relationship(back_populates="items")
    material: Mapped[RawMaterial] = relationship()

class RawMaterialMovement(Base):
    __tablename__ = "raw_material_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    supplier_or_destination: Mapped[str] = mapped_column(String(200), default="")
    document_number: Mapped[str] = mapped_column(String(80), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    material: Mapped[RawMaterial] = relationship(back_populates="movements")


class Product(Base):
    __tablename__ = "products"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    volume_liters: Mapped[Decimal] = mapped_column(Numeric(10, 3), default=0.33)
    output_unit: Mapped[str] = mapped_column(String(20), default="бут.")
    base_batch_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3), default=1000)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    recipe_items: Mapped[list["RecipeItem"]] = relationship(
        back_populates="product", cascade="all, delete-orphan"
    )

class RecipeItem(Base):
    __tablename__ = "recipe_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    note: Mapped[str] = mapped_column(String(300), default="")
    product: Mapped[Product] = relationship(back_populates="recipe_items")
    material: Mapped[RawMaterial] = relationship()


class ProductionBatch(Base):
    __tablename__ = "production_batches"
    id: Mapped[int] = mapped_column(primary_key=True)
    batch_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    output_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    status: Mapped[str] = mapped_column(String(20), default="posted")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    product: Mapped[Product] = relationship()
    consumptions: Mapped[list["ProductionConsumption"]] = relationship(
        back_populates="batch", cascade="all, delete-orphan"
    )

class ProductionConsumption(Base):
    __tablename__ = "production_consumptions"
    id: Mapped[int] = mapped_column(primary_key=True)
    production_batch_id: Mapped[int] = mapped_column(
        ForeignKey("production_batches.id"), index=True
    )
    material_id: Mapped[int] = mapped_column(ForeignKey("raw_materials.id"), index=True)
    required_quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    batch: Mapped[ProductionBatch] = relationship(back_populates="consumptions")
    material: Mapped[RawMaterial] = relationship()

class FinishedGoodsMovement(Base):
    __tablename__ = "finished_goods_movements"
    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    movement_type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    document_number: Mapped[str] = mapped_column(String(80), default="")
    destination_or_customer: Mapped[str] = mapped_column(String(200), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    product: Mapped[Product] = relationship()


class ProductionEvent(Base):
    __tablename__ = "production_events"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    event_type: Mapped[str] = mapped_column(String(30), index=True)
    product_id: Mapped[int | None] = mapped_column(
        ForeignKey("products.id"), nullable=True, index=True
    )
    material_id: Mapped[int | None] = mapped_column(
        ForeignKey("raw_materials.id"), nullable=True, index=True
    )
    production_batch_id: Mapped[int | None] = mapped_column(
        ForeignKey("production_batches.id"), nullable=True, index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 4))
    reason: Mapped[str] = mapped_column(String(120))
    responsible_person: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    product: Mapped[Product | None] = relationship()
    material: Mapped[RawMaterial | None] = relationship()
    production_batch: Mapped[ProductionBatch | None] = relationship()

class QualityControlRecord(Base):
    __tablename__ = "quality_control_records"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    production_batch_id: Mapped[int] = mapped_column(
        ForeignKey("production_batches.id"), index=True
    )
    strength_percent: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3), nullable=True
    )
    co2_value: Mapped[Decimal | None] = mapped_column(
        Numeric(8, 3), nullable=True
    )
    color_result: Mapped[str] = mapped_column(String(60), default="")
    smell_result: Mapped[str] = mapped_column(String(60), default="")
    taste_result: Mapped[str] = mapped_column(String(60), default="")
    status: Mapped[str] = mapped_column(String(20), default="approved")
    checked_by: Mapped[str] = mapped_column(String(160))
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    production_batch: Mapped[ProductionBatch] = relationship()


class Customer(Base):
    __tablename__ = "customers"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(180), index=True)
    customer_type: Mapped[str] = mapped_column(String(30), default="shop")
    contact_person: Mapped[str] = mapped_column(String(140), default="")
    phone: Mapped[str] = mapped_column(String(60), default="")
    email: Mapped[str] = mapped_column(String(140), default="")
    address: Mapped[str] = mapped_column(String(300), default="")
    tax_number: Mapped[str] = mapped_column(String(80), default="")
    credit_limit: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    sales: Mapped[list["Sale"]] = relationship(back_populates="customer")
    payments: Mapped[list["CustomerPayment"]] = relationship(back_populates="customer")

class Sale(Base):
    __tablename__ = "sales"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    payment_type: Mapped[str] = mapped_column(String(20), default="credit")
    status: Mapped[str] = mapped_column(String(20), default="posted")
    delivery_address: Mapped[str] = mapped_column(String(300), default="")
    vehicle_number: Mapped[str] = mapped_column(String(80), default="")
    driver_name: Mapped[str] = mapped_column(String(160), default="")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    customer: Mapped[Customer] = relationship(back_populates="sales")
    items: Mapped[list["SaleItem"]] = relationship(
        back_populates="sale", cascade="all, delete-orphan"
    )

class SaleItem(Base):
    __tablename__ = "sale_items"
    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(ForeignKey("sales.id"), index=True)
    product_id: Mapped[int] = mapped_column(ForeignKey("products.id"), index=True)
    quantity: Mapped[Decimal] = mapped_column(Numeric(14, 3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    sale: Mapped[Sale] = relationship(back_populates="items")
    product: Mapped[Product] = relationship()

class CustomerPayment(Base):
    __tablename__ = "customer_payments"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    customer_id: Mapped[int] = mapped_column(ForeignKey("customers.id"), index=True)
    sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id"), nullable=True, index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    payment_method: Mapped[str] = mapped_column(String(30), default="cash")
    note: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    customer: Mapped[Customer] = relationship(back_populates="payments")
    sale: Mapped[Sale | None] = relationship()


class CashAccount(Base):
    __tablename__ = "cash_accounts"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    account_type: Mapped[str] = mapped_column(String(20), default="cash")
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    opening_balance: Mapped[Decimal] = mapped_column(Numeric(16, 2), default=0)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    transactions: Mapped[list["FinanceTransaction"]] = relationship(
        back_populates="account"
    )

class ExpenseCategory(Base):
    __tablename__ = "expense_categories"
    id: Mapped[int] = mapped_column(primary_key=True)
    code: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(160), index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class FinanceTransaction(Base):
    __tablename__ = "finance_transactions"
    id: Mapped[int] = mapped_column(primary_key=True)
    document_number: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("cash_accounts.id"), index=True)
    transaction_type: Mapped[str] = mapped_column(String(20), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(16, 2))
    currency: Mapped[str] = mapped_column(String(10), default="TMT")
    category_id: Mapped[int | None] = mapped_column(
        ForeignKey("expense_categories.id"), nullable=True, index=True
    )
    customer_id: Mapped[int | None] = mapped_column(
        ForeignKey("customers.id"), nullable=True, index=True
    )
    supplier_id: Mapped[int | None] = mapped_column(
        ForeignKey("suppliers.id"), nullable=True, index=True
    )
    related_sale_id: Mapped[int | None] = mapped_column(
        ForeignKey("sales.id"), nullable=True, index=True
    )
    payment_method: Mapped[str] = mapped_column(String(30), default="cash")
    counterparty: Mapped[str] = mapped_column(String(180), default="")
    description: Mapped[str] = mapped_column(Text, default="")
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)

    account: Mapped[CashAccount] = relationship(back_populates="transactions")
    category: Mapped[ExpenseCategory | None] = relationship()
    customer: Mapped[Customer | None] = relationship()
    supplier: Mapped[Supplier | None] = relationship()
    related_sale: Mapped[Sale | None] = relationship()

class ExchangeRate(Base):
    __tablename__ = "exchange_rates"
    id: Mapped[int] = mapped_column(primary_key=True)
    currency: Mapped[str] = mapped_column(String(10), index=True)
    rate_to_tmt: Mapped[Decimal] = mapped_column(Numeric(16, 6))
    effective_date: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, index=True)
    created_by: Mapped[str] = mapped_column(String(80))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
