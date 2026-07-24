from datetime import datetime
from decimal import Decimal
from sqlalchemy import String,Boolean,DateTime,Integer,Numeric,ForeignKey,Text
from sqlalchemy.orm import Mapped,mapped_column,relationship
from .database import Base
class User(Base):
    __tablename__="users"
    id:Mapped[int]=mapped_column(primary_key=True)
    username:Mapped[str]=mapped_column(String(80),unique=True,index=True)
    full_name:Mapped[str]=mapped_column(String(150))
    password_hash:Mapped[str]=mapped_column(String(300))
    role:Mapped[str]=mapped_column(String(40),default="director")
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class AuditLog(Base):
    __tablename__="audit_logs"
    id:Mapped[int]=mapped_column(primary_key=True)
    username:Mapped[str]=mapped_column(String(80))
    action:Mapped[str]=mapped_column(String(120))
    details:Mapped[str]=mapped_column(String(500),default="")
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
class DashboardMetric(Base):
    __tablename__="dashboard_metrics"
    id:Mapped[int]=mapped_column(primary_key=True)
    metric_key:Mapped[str]=mapped_column(String(80),unique=True)
    metric_label:Mapped[str]=mapped_column(String(120))
    value:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    unit:Mapped[str]=mapped_column(String(30),default="")
    sort_order:Mapped[int]=mapped_column(Integer,default=0)
class RawMaterial(Base):
    __tablename__="raw_materials"
    id:Mapped[int]=mapped_column(primary_key=True)
    code:Mapped[str]=mapped_column(String(40),unique=True,index=True)
    name:Mapped[str]=mapped_column(String(160),index=True)
    unit:Mapped[str]=mapped_column(String(20),default="кг")
    minimum_stock:Mapped[Decimal]=mapped_column(Numeric(14,3),default=0)
    is_active:Mapped[bool]=mapped_column(Boolean,default=True)
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow)
    movements:Mapped[list['RawMaterialMovement']]=relationship(back_populates='material')
class RawMaterialMovement(Base):
    __tablename__="raw_material_movements"
    id:Mapped[int]=mapped_column(primary_key=True)
    material_id:Mapped[int]=mapped_column(ForeignKey("raw_materials.id"),index=True)
    movement_type:Mapped[str]=mapped_column(String(20))
    quantity:Mapped[Decimal]=mapped_column(Numeric(14,3))
    unit_price:Mapped[Decimal]=mapped_column(Numeric(14,2),default=0)
    supplier_or_destination:Mapped[str]=mapped_column(String(200),default="")
    document_number:Mapped[str]=mapped_column(String(80),default="")
    note:Mapped[str]=mapped_column(Text,default="")
    created_by:Mapped[str]=mapped_column(String(80))
    created_at:Mapped[datetime]=mapped_column(DateTime,default=datetime.utcnow,index=True)
    material:Mapped[RawMaterial]=relationship(back_populates='movements')
