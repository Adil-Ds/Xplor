import os, uuid
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dataset
from app.services.data_service import parse_uploaded_file, profile_dataset
from app.services.agent_service import run_analysis_pipeline, get_analysis

UPLOAD_DIR = "data/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

router = APIRouter()

@router.get("/")
def list_datasets(db: Session = Depends(get_db), current=Depends(get_current_user)):
    return db.query(Dataset).filter(Dataset.owner_id == current["sub"]).all()

@router.post("/upload", status_code=201)
async def upload_dataset(
    file: UploadFile = File(...),
    background_tasks: BackgroundTasks = BackgroundTasks(),
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    contents = await file.read()
    ext = file.filename.split(".")[-1].lower()
    file_id = str(uuid.uuid4())
    file_path = os.path.join(UPLOAD_DIR, f"{file_id}.{ext}")
    with open(file_path, "wb") as f:
        f.write(contents)

    meta = parse_uploaded_file(file_path, ext, file.filename)
    ds = Dataset(
        id=file_id, owner_id=current["sub"],
        name=file.filename.rsplit(".", 1)[0],
        filename=file.filename, filetype=ext, file_path=file_path,
        rows=meta["rows"], columns=meta["columns"], size_bytes=len(contents),
        col_names=meta["columns_list"],
    )
    db.add(ds); db.commit(); db.refresh(ds)

    # Trigger background AI analysis pipeline
    background_tasks.add_task(run_analysis_pipeline, file_id, meta["data"])

    return {**ds.__dict__, "preview": meta["preview"], "analysis_status": "running"}

@router.get("/{ds_id}/preview")
def get_preview(ds_id: str, rows: int = 100, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404, "Dataset not found")
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    return {"columns": ds.col_names, "rows": meta["preview"][:rows]}

@router.get("/{ds_id}/profile")
def get_profile(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404, "Dataset not found")
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    return profile_dataset(meta["data"])

@router.get("/{ds_id}/analysis")
def get_dataset_analysis(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Poll AI analysis status. Returns running/done/error + results."""
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404, "Dataset not found")
    result = get_analysis(ds_id)
    if result is None:
        return {"status": "pending"}
    return result

@router.delete("/{ds_id}", status_code=204)
def delete_dataset(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404, "Dataset not found")
    try: os.remove(ds.file_path)
    except: pass
    db.delete(ds); db.commit()
