from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user
from app.models.models import User

router = APIRouter()

class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None

class LoginIn(BaseModel):
    username: str
    password: str

@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    user = User(username=data.username, email=data.email, hashed_pw=hash_password(data.password))
    db.add(user); db.commit(); db.refresh(user)
    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}

@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_pw):
        raise HTTPException(401, "Invalid credentials")
    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"token": token, "user": {"id": user.id, "username": user.username, "role": user.role}}

@router.get("/me")
def me(current=Depends(get_current_user)):
    return current
