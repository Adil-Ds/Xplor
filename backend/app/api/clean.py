from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dataset
from app.services.data_service import parse_uploaded_file, apply_cleaning_recipe

router = APIRouter()

class StepIn(BaseModel):
    op: str
    column: str | None = None
    columns: list[str] | None = None
    oldName: str | None = None
    newName: str | None = None
    fillWith: str | None = None
    fillValue: str | None = None
    toType: str | None = None
    findVal: str | None = None
    replaceVal: str | None = None
    operator: str | None = None
    value: str | None = None
    textContent: str | None = None

@router.get("/{ds_id}/recipe")
def get_recipe(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404)
    return {"recipe": ds.recipe or []}

@router.post("/{ds_id}/step")
def add_step(ds_id: str, step: StepIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404)
    recipe = list(ds.recipe or [])
    recipe.append(step.model_dump(exclude_none=True))
    ds.recipe = recipe
    db.commit()
    return {"recipe": recipe}

@router.get("/{ds_id}/preview")
def preview_cleaned(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404)
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    df   = apply_cleaning_recipe(meta["data"], ds.recipe or [])
    return {"rows": len(df), "columns": list(df.columns), "preview": df.head(100).to_dict(orient="records")}

@router.post("/{ds_id}/apply")
def apply_recipe(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404)
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    df   = apply_cleaning_recipe(meta["data"], ds.recipe or [])
    # Overwrite stored file with cleaned version
    df.to_csv(ds.file_path.rsplit(".", 1)[0] + "_clean.csv", index=False)
    ds.rows = len(df); ds.columns = len(df.columns); ds.col_names = list(df.columns)
    db.commit()
    return {"status": "applied", "rows": len(df), "columns": len(df.columns)}

@router.delete("/{ds_id}/recipe/{step_idx}", status_code=204)
def remove_step(ds_id: str, step_idx: int, db: Session = Depends(get_db), current=Depends(get_current_user)):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds: raise HTTPException(404)
    recipe = list(ds.recipe or [])
    if 0 <= step_idx < len(recipe): recipe.pop(step_idx)
    ds.recipe = recipe; db.commit()
