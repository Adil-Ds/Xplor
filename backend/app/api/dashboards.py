from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dashboard

router = APIRouter()

class DashboardIn(BaseModel):
    name: str
    dataset_id: str | None = None
    widgets: list | None = []

@router.get("/")
def list_dashboards(db: Session = Depends(get_db), current=Depends(get_current_user)):
    return db.query(Dashboard).filter(Dashboard.owner_id == current["sub"]).all()

@router.post("/", status_code=201)
def create_dashboard(data: DashboardIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = Dashboard(owner_id=current["sub"], name=data.name, dataset_id=data.dataset_id, widgets=data.widgets or [])
    db.add(d); db.commit(); db.refresh(d)
    return d

@router.get("/{dash_id}")
def get_dashboard(dash_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    return d

@router.put("/{dash_id}")
def update_dashboard(dash_id: str, data: DashboardIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    d.name = data.name; d.dataset_id = data.dataset_id; d.widgets = data.widgets
    db.commit(); return d

@router.delete("/{dash_id}", status_code=204)
def delete_dashboard(dash_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    db.delete(d); db.commit()
