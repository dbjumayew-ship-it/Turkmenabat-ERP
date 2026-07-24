import os,jwt
from pathlib import Path
from contextlib import asynccontextmanager
from fastapi import FastAPI,Request,Form,Depends,HTTPException
from fastapi.responses import HTMLResponse,RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from .database import Base,engine,SessionLocal,get_db
from .models import User,DashboardMetric
from .security import hash_password,verify_password,create_token,decode_token
BASE=Path(__file__).resolve().parent
def seed():
    Base.metadata.create_all(bind=engine); db=SessionLocal()
    try:
        u=os.getenv("ADMIN_USERNAME","director")
        if not db.query(User).filter_by(username=u).first(): db.add(User(username=u,full_name=os.getenv("ADMIN_FULL_NAME","Director"),password_hash=hash_password(os.getenv("ADMIN_PASSWORD","ChangeMe123!")),role="director"))
        if db.query(DashboardMetric).count()==0:
            db.add_all([DashboardMetric(metric_key="raw",metric_label="Сырьё на складе",value=0,unit="кг",sort_order=1),DashboardMetric(metric_key="finished",metric_label="Готовая продукция",value=0,unit="бут.",sort_order=2),DashboardMetric(metric_key="today",metric_label="Произведено сегодня",value=0,unit="бут.",sort_order=3),DashboardMetric(metric_key="sales",metric_label="Продажи за месяц",value=0,unit="TMT",sort_order=4)])
        db.commit()
    finally: db.close()
@asynccontextmanager
async def lifespan(app): seed(); yield
app=FastAPI(title="Türkmenabat ERP API",lifespan=lifespan)
app.mount("/static",StaticFiles(directory=BASE/"static"),name="static")
templates=Jinja2Templates(directory=BASE/"templates")
def current(request:Request,db:Session=Depends(get_db)):
    t=request.cookies.get("erp_token") or (request.headers.get("Authorization","")[7:] if request.headers.get("Authorization","").startswith("Bearer ") else None)
    if not t: raise HTTPException(401)
    try: p=decode_token(t)
    except jwt.PyJWTError: raise HTTPException(401)
    u=db.query(User).filter_by(username=p.get("sub")).first()
    if not u: raise HTTPException(401)
    return u
@app.get("/api/health")
def health(): return {"status":"ok"}
@app.post("/api/login")
def api_login(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=username).first()
    if not u or not verify_password(password,u.password_hash): raise HTTPException(401,"Неверный логин или пароль")
    return {"access_token":create_token(u.username,u.role),"token_type":"bearer"}
@app.get("/api/dashboard")
def api_dashboard(user:User=Depends(current),db:Session=Depends(get_db)):
    m=db.query(DashboardMetric).order_by(DashboardMetric.sort_order).all(); return {"user":user.full_name,"metrics":[{"label":x.metric_label,"value":float(x.value),"unit":x.unit} for x in m]}
@app.get("/",response_class=HTMLResponse)
def home(request:Request): return templates.TemplateResponse("login.html",{"request":request})
@app.post("/web/login")
def web_login(username:str=Form(...),password:str=Form(...),db:Session=Depends(get_db)):
    u=db.query(User).filter_by(username=username).first()
    if not u or not verify_password(password,u.password_hash): return RedirectResponse("/?error=1",303)
    r=RedirectResponse("/dashboard",303); r.set_cookie("erp_token",create_token(u.username,u.role),httponly=True,secure=os.getenv("COOKIE_SECURE","false").lower()=="true",samesite="lax",max_age=43200); return r
@app.get("/dashboard",response_class=HTMLResponse)
def dashboard(request:Request,db:Session=Depends(get_db)):
    try: u=current(request,db)
    except HTTPException: return RedirectResponse("/",303)
    m=db.query(DashboardMetric).order_by(DashboardMetric.sort_order).all(); return templates.TemplateResponse("dashboard.html",{"request":request,"user":u,"metrics":m})
@app.get("/logout")
def logout():
    r=RedirectResponse("/",303); r.delete_cookie("erp_token"); return r
