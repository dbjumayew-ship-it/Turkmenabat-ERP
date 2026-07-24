import os,base64,hashlib,hmac,secrets,jwt
from datetime import datetime,timedelta,timezone
SECRET=os.getenv("JWT_SECRET","dev-secret")
def hash_password(p):
    s=secrets.token_bytes(16); i=310000; d=hashlib.pbkdf2_hmac("sha256",p.encode(),s,i)
    return f"pbkdf2_sha256${i}${base64.b64encode(s).decode()}${base64.b64encode(d).decode()}"
def verify_password(p,stored):
    try:
        _,i,s,d=stored.split("$",3); actual=hashlib.pbkdf2_hmac("sha256",p.encode(),base64.b64decode(s),int(i))
        return hmac.compare_digest(actual,base64.b64decode(d))
    except: return False
def create_token(u,r):
    now=datetime.now(timezone.utc); return jwt.encode({"sub":u,"role":r,"iat":now,"exp":now+timedelta(hours=12)},SECRET,algorithm="HS256")
def decode_token(t): return jwt.decode(t,SECRET,algorithms=["HS256"])
