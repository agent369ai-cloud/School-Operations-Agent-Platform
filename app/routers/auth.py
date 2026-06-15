# app/routers/auth.py
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from passlib.context import CryptContext
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import School, User

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
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
    
    hashed_password = pwd_context.hash(payload.password)
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
    if not user or not user.password_hash or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Invalid credentials.")
        
    expiration = datetime.now(timezone.utc) + timedelta(hours=8)
    token_claims = {"sub": user.id, "role": user.role, "school_id": user.school_id, "exp": expiration}
    
    SECRET_KEY = "SUPER_SECRET_RELIABLE_SCHOOL_SIGNING_KEY_JWT_TOKEN_CANVAS"
    encoded_jwt = jwt.encode(token_claims, SECRET_KEY, algorithm="HS256")
    return {"access_token": encoded_jwt, "token_type": "bearer"}
