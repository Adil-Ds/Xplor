from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import hash_password, verify_password, create_access_token, get_current_user, require_roles
from app.models.models import User

router = APIRouter()

VALID_ROLES = {"admin", "analyst", "viewer"}


class RegisterIn(BaseModel):
    username: str
    password: str
    email: str | None = None
    role: str = "analyst"


class LoginIn(BaseModel):
    username: str
    password: str


def _user_out(user: User) -> dict:
    return {
        "id":         user.id,
        "username":   user.username,
        "email":      user.email,
        "role":       user.role,
        "created_at": user.created_at.isoformat() if user.created_at else None,
    }


@router.post("/register", status_code=201)
def register(data: RegisterIn, db: Session = Depends(get_db)):
    if db.query(User).filter(User.username == data.username).first():
        raise HTTPException(400, "Username already taken")
    if data.email and db.query(User).filter(User.email == data.email).first():
        raise HTTPException(400, "Email already registered")

    role = data.role.lower() if data.role.lower() in VALID_ROLES else "analyst"

    # First user ever gets admin automatically
    if db.query(User).count() == 0:
        role = "admin"

    user = User(
        username=data.username,
        email=data.email or None,
        hashed_pw=hash_password(data.password),
        role=role,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"token": token, "user": _user_out(user)}


@router.post("/login")
def login(data: LoginIn, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_pw):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid username or password")
    token = create_access_token({"sub": user.id, "username": user.username, "role": user.role})
    return {"token": token, "user": _user_out(user)}


@router.get("/me")
def me(current=Depends(get_current_user), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == current["sub"]).first()
    if not user:
        raise HTTPException(404, "User not found")
    return _user_out(user)


# ── Admin: user management ─────────────────────────────────

@router.get("/users")
def list_users(
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin")),
):
    """List all registered users. Admin only."""
    return [_user_out(u) for u in db.query(User).order_by(User.created_at).all()]


@router.put("/users/{user_id}/role")
def update_role(
    user_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin")),
):
    """Change a user's role. Admin only."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    new_role = (body.get("role") or "").lower()
    if new_role not in VALID_ROLES:
        raise HTTPException(400, f"Invalid role. Choose from: {', '.join(VALID_ROLES)}")
    user.role = new_role
    db.commit()
    return _user_out(user)


@router.delete("/users/{user_id}", status_code=204)
def delete_user(
    user_id: str,
    db: Session = Depends(get_db),
    current=Depends(require_roles("admin")),
):
    """Delete a user account. Admin only. Cannot delete yourself."""
    if user_id == current["sub"]:
        raise HTTPException(400, "You cannot delete your own account")
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "User not found")
    db.delete(user)
    db.commit()
