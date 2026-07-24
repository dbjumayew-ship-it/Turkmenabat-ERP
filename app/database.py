import os
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker
url=os.getenv("DATABASE_URL","sqlite:///./erp.db")
if url.startswith("postgres://"): url=url.replace("postgres://","postgresql://",1)
engine=create_engine(url,pool_pre_ping=True,connect_args={"check_same_thread":False} if url.startswith("sqlite") else {})
SessionLocal=sessionmaker(bind=engine,autocommit=False,autoflush=False)
class Base(DeclarativeBase): pass
def get_db():
    db=SessionLocal()
    try: yield db
    finally: db.close()
