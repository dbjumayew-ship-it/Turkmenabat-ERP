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
