"""
Xplor Backend — FastAPI Main Application
"""
import uvicorn
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env")  # explicit path — works regardless of cwd

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.database import engine, Base
from app.api import auth, datasets, clean, explore, dashboards, reports, chat
from app.services.chat_service import check_ollama_status, check_groq_status
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
app.include_router(chat.router,       prefix="/chat",       tags=["Chat"])


@app.get("/health", tags=["System"])
def health():
    return {"status": "ok", "app": "Xplor", "version": "1.0.0"}


@app.get("/models/status", tags=["System"])
def models_status():
    """
    Aggregate health check for all AI providers:
      - Ollama  (local)           primary LLM
      - Groq    (cloud fallback)  activates automatically when Ollama is down
      - DistilBERT                column semantic labelling
      - IsolationForest           anomaly detection
    """
    from app.services.chat_service import OLLAMA_MODEL, GROQ_MODEL, GROQ_FALLBACK_ENABLED, GROQ_API_KEY

    ollama = check_ollama_status()
    groq   = check_groq_status()
    ml     = get_ml_status()

    if ollama["running"] and ollama["models"]:
        ollama_entries = {
            m: {
                "model":      m,
                "backend":    "Ollama (local)",
                "status":     "ready",
                "task":       "LLM inference",
                "is_default": m.startswith(OLLAMA_MODEL),
            }
            for m in ollama["models"]
        }
    else:
        ollama_entries = {
            OLLAMA_MODEL: {
                "model":      OLLAMA_MODEL,
                "backend":    "Ollama (local)",
                "status":     "not running" if not ollama["running"] else "model not pulled",
                "task":       "LLM inference",
                "is_default": True,
            }
        }

    return {
        "ollama": {
            "running":                 ollama["running"],
            "default_model":           OLLAMA_MODEL,
            "default_model_available": ollama["default_model_available"],
            "available_models":        ollama["models"],
            "models":                  ollama_entries,
        },
        "groq": {
            "provider":          "Groq Cloud (https://console.groq.com)",
            "model":             GROQ_MODEL,
            "fallback_enabled":  GROQ_FALLBACK_ENABLED,
            "api_key_set":       bool(GROQ_API_KEY),
            "status":            groq["status"],
            "note": (
                "Active fallback — will be used automatically when Ollama is unavailable."
                if GROQ_FALLBACK_ENABLED and GROQ_API_KEY else
                "Set GROQ_API_KEY in backend/.env to enable cloud fallback."
            ),
        },
        **ml,
    }


if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
