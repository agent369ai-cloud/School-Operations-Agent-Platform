from fastapi import Depends, HTTPException, Header
from jose import jwt, JWTError
from app.config import settings
from app.database import get_db
from app.models import User, AuditEvent
import uuid

def get_current_user(authorization: str = Header(None), db=Depends(get_db)) -> User:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(401, "Missing token")
    try:
        payload = jwt.decode(authorization[7:], settings.secret_key, algorithms=["HS256"])
        user = db.query(User).filter(User.id == payload["sub"]).first()
        if not user:
            raise HTTPException(401, "Invalid user")
        return user
    except JWTError:
        raise HTTPException(401, "Invalid token")

def require_role(*roles):
    def checker(user: User = Depends(get_current_user)):
        if user.role not in roles:
            raise HTTPException(403, "Insufficient role")
        return user
    return checker

def require_same_school(resource_school_id: str, user: User, db, correlation_id: str):
    if user.school_id != resource_school_id:
        db.add(AuditEvent(correlation_id=correlation_id, actor_id=user.id,
                          event_type="ACCESS_DENIED",
                          payload={"attempted_school_id": resource_school_id, "actor_school_id": user.school_id}))
        db.commit()
        raise HTTPException(403, "Access denied")