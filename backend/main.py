"""
Xplor Backend — FastAPI Main Application
"""
import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.api import auth, datasets, clean, explore, dashboards, reports, chat
from app.services.chat_service import check_ollama_status
from app.services.ml_service import get_ml_status

# Create tables
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="Xplor API",
    description="Data Intelligence Platform — Backend API",
    version="1.0.0",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth.router,       prefix="/auth",       tags=["Auth"])
app.include_router(datasets.router,   prefix="/datasets",   tags=["Datasets"])
app.include_router(clean.router,      prefix="/clean",      tags=["Cleaning"])
app.include_router(explore.router,    prefix="/explore",    tags=["Explore"])
app.include_router(dashboards.router, prefix="/dashboards", tags=["Dashboards"])
app.include_router(reports.router,    prefix="/reports",    tags=["Reports"])
app.include_router(chat.router,        prefix="/chat",        tags=["Chat"])

@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "app": "Xplor", "version": "1.0.0"}


@app.get("/models/status", tags=["System"])
def models_status():
    """
    Aggregate health check for all AI models:
      - Qwen 2.5   → Ollama (local HTTP server)
      - DistilBERT → HuggingFace Transformers (in-process)
      - IsolationForest → scikit-learn (in-process)
    """
    ollama = check_ollama_status()
    ml     = get_ml_status()
    return {
        "qwen2.5": {
            "model":   "qwen2.5",
            "backend": "Ollama (local REST server)",
            "status":  "ready" if ollama["qwen_available"] else (
                       "ollama running, model not pulled" if ollama["running"]
                       else "ollama not running"
            ),
            "task":    "natural-language-to-pandas code generation",
            "available_models": ollama["models"],
        },
        **ml,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
