import uuid as uuid_lib
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Report

router = APIRouter()

class ReportIn(BaseModel):
    title: str
    description: str | None = None
    dashboard_id: str | None = None
    dataset_id: str | None = None

@router.get("/")
def list_reports(db: Session = Depends(get_db), current=Depends(get_current_user)):
    return db.query(Report).filter(Report.owner_id == current["sub"]).all()

@router.post("/", status_code=201)
def create_report(data: ReportIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    r = Report(
        owner_id=current["sub"], title=data.title, description=data.description,
        dashboard_id=data.dashboard_id, dataset_id=data.dataset_id,
        share_token=str(uuid_lib.uuid4())[:12],
    )
    db.add(r); db.commit(); db.refresh(r)
    return r

@router.delete("/{report_id}", status_code=204)
def delete_report(report_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    r = db.query(Report).filter(Report.id == report_id, Report.owner_id == current["sub"]).first()
    if not r: raise HTTPException(404)
    db.delete(r); db.commit()

@router.post("/{report_id}/share")
def share_report(report_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    r = db.query(Report).filter(Report.id == report_id, Report.owner_id == current["sub"]).first()
    if not r: raise HTTPException(404)
    return {"share_url": f"/report/{r.share_token}", "token": r.share_token}
