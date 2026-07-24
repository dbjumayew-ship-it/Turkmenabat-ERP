import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
DATABASE_URL=os.getenv("DATABASE_URL","sqlite:///./erp.db")
if DATABASE_URL.startswith("postgres://"): DATABASE_URL=DATABASE_URL.replace("postgres://","postgresql://",1)
engine=create_engine(DATABASE_URL,pool_pre_ping=True,connect_args={"check_same_thread":False} if DATABASE_URL.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autocommit=False,autoflush=False)
class Base(DeclarativeBase): pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
