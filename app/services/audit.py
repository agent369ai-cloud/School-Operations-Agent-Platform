# app/routers/auth.py
import uuid
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, Depends, HTTPException, status
try:
    from passlib.context import CryptContext
except ImportError:
    CryptContext = None
from jose import jwt
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import School, User

# Enforce secure password hashing configurations
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
router = APIRouter()

# --- 📋 Pydantic Verification Input Schemas ---
class SchoolRegisterIn(BaseModel):
    school_name: str
    admin_name: str
    admin_email: EmailStr
    password: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

# --- 🚀 Auth Web Routing Endpoints ---

@router.post("/register-school", status_code=status.HTTP_201_CREATED)
def register_school(payload: SchoolRegisterIn, db: Session = Depends(get_db)):
    """
    Registers a brand new School entity alongside its primary Admin User profile 
    using defensive database transactional isolation constraints.
    """
    # Check if user email already exists across the platform bounds
    existing_user = db.query(User).filter(User.email == payload.admin_email).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail="An account profile with this email address already exists."
        )
        
    # 1. Spawn the isolated School root structure
    new_school = School(
        id=str(uuid.uuid4()),
        name=payload.school_name
    )
    db.add(new_school)
    
    # 2. Hash the private password string safely before storage mutations
    hashed_password = pwd_context.hash(payload.password)
    
    # 3. Provision the primary School Admin user account
    new_admin = User(
        id=str(uuid.uuid4()),
        school_id=new_school.id,
        name=payload.admin_name,
        email=payload.admin_email,
        role="ADMIN",  # 👈 Enforces absolute structural admin access context bounds
        password_hash=hashed_password
    )
    db.add(new_admin)
    db.commit()
    
    return {
        "status": "SUCCESSFULLY_PROVISIONED", 
        "school_id": new_school.id, 
        "admin_id": new_admin.id
    }

@router.post("/login")
def login(payload: LoginIn, db: Session = Depends(get_db)):
    """
    Evaluates profile text strings and returns a cryptographic, 
    role-scoped JWT token valid for 8 hours.
    """
    user = db.query(User).filter(User.email == payload.email).first()
    
    # Verify the user profile exists and decrypt/verify the incoming password hash
    if not user or not user.password_hash or not pwd_context.verify(payload.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Invalid email or password credentials provided."
        )
        
    # Standard security practice: Explicit timezone expiration delta calculation
    expiration_delta = datetime.now(timezone.utc) + timedelta(hours=8)
    
    token_claims = {
        "sub": user.id,
        "role": user.role,
        "school_id": user.school_id,
        "exp": expiration_delta
    }
    
    # Generate the cryptographic signature using a default fallback if config values are blank
    SECRET_KEY = "SUPER_SECRET_RELIABLE_SCHOOL_SIGNING_KEY_JWT_TOKEN_CANVAS"
    
    encoded_jwt = jwt.encode(token_claims, SECRET_KEY, algorithm="HS256")
    
    return {
        "access_token": encoded_jwt, 
        "token_type": "bearer"
    }
