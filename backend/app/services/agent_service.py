"""
Agent Service — Auto-analysis pipeline orchestrator
Runs automatically in the background after every dataset upload:
  1. Profile columns
  2. Label column semantics (distilBERT)
  3. Run IsolationForest anomaly detection
  4. Generate ranked cleaning suggestions
  5. Store results as a JSON sidecar file next to the dataset
"""
import json
import logging
import os
from datetime import datetime, timezone

import pandas as pd

from app.services.ml_service import label_columns, detect_anomalies, generate_ai_suggestions

logger = logging.getLogger(__name__)

ANALYSIS_DIR = "data/analysis"
os.makedirs(ANALYSIS_DIR, exist_ok=True)


def _analysis_path(ds_id: str) -> str:
    return os.path.join(ANALYSIS_DIR, f"{ds_id}.json")


def run_analysis_pipeline(ds_id: str, df: pd.DataFrame) -> None:
    """
    Full analysis pipeline — called as a FastAPI BackgroundTask.
    Writes results to data/analysis/{ds_id}.json
    """
    logger.info(f"[Agent] Starting analysis for dataset {ds_id} ({len(df)} rows, {len(df.columns)} cols)")
    result = {
        "ds_id":      ds_id,
        "status":     "running",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "col_labels": {},
        "anomalies":  {},
        "suggestions": [],
        "error":       None,
    }

    # Write initial "running" status immediately so the UI can poll
    _write(ds_id, result)

    try:
        # Step 1 — Column semantic labeling
        logger.info(f"[Agent] {ds_id}: labeling columns...")
        col_labels = label_columns(df)
        result["col_labels"] = col_labels

        # Step 2 — Anomaly detection
        logger.info(f"[Agent] {ds_id}: running IsolationForest...")
        anomaly_result = detect_anomalies(df)
        result["anomalies"] = {
            "count":          anomaly_result["anomaly_count"],
            "total_rows":     anomaly_result["total_rows"],
            "indices":        anomaly_result["anomaly_indices"][:500],  # cap for storage
            "columns_used":   anomaly_result["columns_used"],
        }

        # Step 3 — Ranked cleaning suggestions
        logger.info(f"[Agent] {ds_id}: generating suggestions...")
        suggestions = generate_ai_suggestions(df, col_labels, anomaly_result)
        # Sort: high impact first
        priority = {"high": 0, "medium": 1, "low": 2, "none": 3}
        suggestions.sort(key=lambda s: priority.get(s.get("impact", "none"), 3))
        result["suggestions"] = suggestions

        result["status"] = "done"
        result["completed_at"] = datetime.now(timezone.utc).isoformat()
        logger.info(f"[Agent] {ds_id}: analysis complete — {len(suggestions)} suggestions.")

    except Exception as e:
        logger.error(f"[Agent] {ds_id}: pipeline failed: {e}", exc_info=True)
        result["status"] = "error"
        result["error"]  = str(e)

    _write(ds_id, result)


def get_analysis(ds_id: str) -> dict | None:
    """Read cached analysis result for a dataset. Returns None if not yet run."""
    path = _analysis_path(ds_id)
    if not os.path.exists(path):
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return None


def _write(ds_id: str, data: dict) -> None:
    path = _analysis_path(ds_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, default=str)
