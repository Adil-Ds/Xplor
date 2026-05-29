"""
Chat API Router — Natural language questions against datasets
Endpoints:
  GET  /chat/status            → check if Ollama + Qwen are ready
  POST /chat/{ds_id}           → answer a NL question about the dataset
"""
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dataset
from app.services.data_service import parse_uploaded_file
from app.services.chat_service import answer_question, check_ollama_status

router = APIRouter()


def _load_df(ds_id: str, owner_id: str, db: Session):
    """Load a dataset dataframe, raising 404 if not found."""
    ds = db.query(Dataset).filter(
        Dataset.id == ds_id,
        Dataset.owner_id == owner_id,
    ).first()
    if not ds:
        raise HTTPException(status_code=404, detail="Dataset not found")
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    return meta["data"]


@router.get("/status")
def ollama_status():
    """Check if Ollama is running and Qwen model is available."""
    return check_ollama_status()


@router.post("/{ds_id}")
def chat_with_dataset(
    ds_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Answer a natural language question about a dataset.
    Body: { "question": "What is the average salary?" }
    """
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    df = _load_df(ds_id, current["sub"], db)
    result = answer_question(df, question)
    return result
