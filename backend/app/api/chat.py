"""
Chat API Router — Natural language questions against datasets
Endpoints:
  GET  /chat/status            → check if Ollama + Qwen are ready
  GET  /chat/models            → list all models available in Ollama
  POST /chat/{ds_id}           → answer a NL question about the dataset
                                  body: { "question": "...", "model": "qwen2.5" (optional) }
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dataset
from app.services.data_service import parse_uploaded_file
from app.services.chat_service import answer_question, check_ollama_status, OLLAMA_MODEL

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
    """Check if Ollama is running and report available models."""
    return check_ollama_status()


@router.get("/models")
def available_models():
    """List all models currently available in Ollama."""
    status = check_ollama_status()
    return {
        "running": status["running"],
        "models": status["models"],
        "default_model": OLLAMA_MODEL,
        "default_model_available": status["default_model_available"],
    }


@router.post("/{ds_id}")
def chat_with_dataset(
    ds_id: str,
    body: dict,
    db: Session = Depends(get_db),
    current=Depends(get_current_user),
):
    """
    Answer a natural language question about a dataset.
    Body: { "question": "What is the average salary?", "model": "qwen2.5" }
    The model field is optional — omit to use the server default (qwen2.5).
    """
    question = (body.get("question") or "").strip()
    if not question:
        raise HTTPException(status_code=400, detail="question is required")

    model    = (body.get("model") or "").strip() or None
    provider = (body.get("provider") or "auto").strip().lower()

    df = _load_df(ds_id, current["sub"], db)

    try:
        result = answer_question(df, question, model=model, provider=provider)
        result["provider"] = provider
        result["model_used"] = model or OLLAMA_MODEL
        return result
    except RuntimeError as e:
        msg = str(e)
        # Distinguish timeout vs not-running so the frontend can show the right message
        if "timed out" in msg.lower():
            raise HTTPException(status_code=504, detail=msg)
        if "not running" in msg.lower():
            raise HTTPException(status_code=503, detail=msg)
        raise HTTPException(status_code=500, detail=msg)
