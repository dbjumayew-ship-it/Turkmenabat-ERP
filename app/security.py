import base64,hashlib,hmac,os,secrets
from datetime import datetime,timedelta,timezone
import jwt
JWT_SECRET=os.getenv("JWT_SECRET","development-secret-change-me")
def hash_password(password:str)->str:
    salt=secrets.token_bytes(16); it=310000
    d=hashlib.pbkdf2_hmac("sha256",password.encode(),salt,it)
    return f"pbkdf2_sha256${it}${base64.b64encode(salt).decode()}${base64.b64encode(d).decode()}"
def verify_password(password:str,stored:str)->bool:
    try:
        a,it,s,d=stored.split("$",3)
        if a!="pbkdf2_sha256": return False
        x=hashlib.pbkdf2_hmac("sha256",password.encode(),base64.b64decode(s),int(it))
        return hmac.compare_digest(x,base64.b64decode(d))
    except Exception:return False
def create_token(username,role):
    n=datetime.now(timezone.utc)
    return jwt.encode({"sub":username,"role":role,"iat":n,"exp":n+timedelta(hours=12)},JWT_SECRET,algorithm="HS256")
def decode_token(token): return jwt.decode(token,JWT_SECRET,algorithms=["HS256"])
