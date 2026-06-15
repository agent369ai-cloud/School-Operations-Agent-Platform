# app/routers/auth.py
import uuid
import bcrypt
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import School, User

# ❌ REMOVED: pwd_context = CryptContext(...) - No more passlib!
router = APIRouter()

class SchoolRegisterIn(BaseModel):
    school_name: str
    admin_name: str
    admin_email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

@router.post("/register-school", status_code=status.HTTP_201_CREATED)
def register_school(payload: SchoolRegisterIn, db: Session = Depends(get_db)):
    existing_user = db.query(User).filter(User.email == payload.admin_email).first()
    if existing_user:
        raise HTTPException(status_code=400, detail="Account already exists.")
        
    new_school = School(id=str(uuid.uuid4()), name=payload.school_name)
    db.add(new_school)

    # Clean, modern native bcrypt hashing
    password_bytes = payload.password.encode('utf-8')
    salt = bcrypt.gensalt()
    hashed_password = bcrypt.hashpw(password_bytes, salt).decode('utf-8')
    
    new_admin = User(
        id=str(uuid.uuid4()),
        school_id=new_school.id,
        name=payload.admin_name,
        email=payload.admin_email,
        role="ADMIN",
        password_hash=hashed_password
    )
    db.add(new_admin)
    db.commit()
    return {"status": "SUCCESSFULLY_PROVISIONED", "school_id": new_school.id}

@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    
    # ─── NATIVE BCRYPT VERIFICATION ──────────────────────────────────────────
    # Check if user exists and has a password hash
    if not user or not user.password_hash:
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    
    # Convert inputs to bytes to let native bcrypt compare them safely
    password_bytes = payload.password.encode('utf-8')
    hashed_bytes = user.password_hash.encode('utf-8')
    
    # Use bcrypt's native verification check
    if not bcrypt.checkpw(password_bytes, hashed_bytes):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
    # ─────────────────────────────────────────────────────────────────────────
        
    expiration = datetime.now(timezone.utc) + timedelta(hours=8)
    token_claims = {"sub": user.id, "role": user.role, "school_id": user.school_id, "exp": expiration}
    
    SECRET_KEY = "SUPER_SECRET_RELIABLE_SCHOOL_SIGNING_KEY_JWT_TOKEN_CANVAS"
    encoded_jwt = jwt.encode(token_claims, SECRET_KEY, algorithm="HS256")
    return {"access_token": encoded_jwt, "token_type": "bearer"}
