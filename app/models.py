from datetime import datetime
from sqlalchemy import String, Boolean, DateTime, Numeric, Integer
from sqlalchemy.orm import Mapped,mapped_column
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
class DashboardMetric(Base):
    __tablename__="dashboard_metrics"
    id:Mapped[int]=mapped_column(primary_key=True)
    metric_key:Mapped[str]=mapped_column(String(80),unique=True)
    metric_label:Mapped[str]=mapped_column(String(120))
    value:Mapped[float]=mapped_column(Numeric(14,2),default=0)
    unit:Mapped[str]=mapped_column(String(30),default="")
    sort_order:Mapped[int]=mapped_column(Integer,default=0)
