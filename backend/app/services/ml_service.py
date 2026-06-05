"""
ML Service — Column semantic labeling + Anomaly detection
Uses:
  - DistilBERT (typeform/distilbert-base-uncased-mnli) via HuggingFace Transformers
    → zero-shot-classification for column semantic labeling
  - IsolationForest (scikit-learn) for anomaly detection on numeric columns

Model source: https://huggingface.co/typeform/distilbert-base-uncased-mnli
This model is DistilBERT fine-tuned on the MultiNLI entailment dataset,
enabling it to classify text into arbitrary categories via natural language
hypothesis without task-specific fine-tuning.
"""
import re
import logging
from typing import Dict, List, Any

import numpy as np
import pandas as pd

logger = logging.getLogger(__name__)

# ─── distilBERT Pipeline (lazy-loaded) ───────────────────────────────────────
_classifier = None

SEMANTIC_LABELS = [
    "email address",
    "phone number",
    "person name",
    "date or timestamp",
    "currency or price",
    "identifier or ID",
    "street address",
    "percentage",
    "numeric measurement",
    "free text",
]

# Short label mapping from verbose → clean label
LABEL_MAP = {
    "email address": "email",
    "phone number": "phone",
    "person name": "name",
    "date or timestamp": "date",
    "currency or price": "currency",
    "identifier or ID": "id",
    "street address": "address",
    "percentage": "percentage",
    "numeric measurement": "numeric",
    "free text": "text",
}


# The correct zero-shot-classification model:
# typeform/distilbert-base-uncased-mnli is DistilBERT fine-tuned on MultiNLI
# which gives it natural language inference (entailment) capability used for
# zero-shot classification. The base `distilbert-base-uncased` is NOT suitable.
DISTILBERT_MODEL = "typeform/distilbert-base-uncased-mnli"


def _get_classifier():
    """Lazy-load the DistilBERT-MNLI zero-shot classifier via Transformers."""
    global _classifier
    if _classifier is None:
        try:
            from transformers import pipeline
            logger.info(f"Loading zero-shot classifier: {DISTILBERT_MODEL} ...")
            _classifier = pipeline(
                "zero-shot-classification",
                model=DISTILBERT_MODEL,
                # device=-1 forces CPU; change to device=0 for GPU
                device=-1,
            )
            logger.info("DistilBERT-MNLI zero-shot classifier ready.")
        except Exception as e:
            logger.warning(
                f"DistilBERT load failed: {e}. "
                "Falling back to rule-based column labeling."
            )
            _classifier = "fallback"
    return _classifier


# ─── Rule-based fallback (fast, zero dependencies) ───────────────────────────

EMAIL_RE    = re.compile(r'^[\w\.\+\-]+@[\w\-]+\.[a-z]{2,}$', re.I)
PHONE_RE    = re.compile(r'^[\+\-\(\)\d\s]{7,15}$')
DATE_RES    = [
    re.compile(r'\d{4}[-/]\d{2}[-/]\d{2}'),
    re.compile(r'\d{2}[-/]\d{2}[-/]\d{4}'),
    re.compile(r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)', re.I),
]
CURRENCY_RE = re.compile(r'^[\$\€\£\¥\₹]?[\d,]+(\.\d+)?$')
PCT_RE      = re.compile(r'^\d+(\.\d+)?%$')
ID_WORDS    = {'id', 'uuid', 'key', 'code', 'ref', 'sku', 'no', 'num', 'number', 'index'}
NAME_WORDS  = {'name', 'firstname', 'lastname', 'fullname', 'username', 'author', 'person'}
ADDR_WORDS  = {'address', 'street', 'city', 'state', 'country', 'zip', 'postal'}
DATE_WORDS  = {'date', 'time', 'created', 'updated', 'timestamp', 'dob', 'year', 'month', 'day'}
CURR_WORDS  = {'price', 'cost', 'salary', 'revenue', 'amount', 'income', 'wage', 'fee', 'rate'}
PCT_WORDS   = {'pct', 'percent', 'percentage', 'rate', 'ratio'}


def _rule_label(col_name: str, sample_vals: list, dtype: str) -> str:
    """Fast rule-based column semantic labeling."""
    name_lower = col_name.lower().replace('_', '').replace(' ', '').replace('-', '')
    str_vals   = [str(v) for v in sample_vals if v is not None and str(v).strip()]

    # Name-based detection first
    for kw in ID_WORDS:
        if kw in name_lower: return 'id'
    for kw in NAME_WORDS:
        if kw in name_lower: return 'name'
    for kw in ADDR_WORDS:
        if kw in name_lower: return 'address'
    for kw in DATE_WORDS:
        if kw in name_lower: return 'date'
    for kw in CURR_WORDS:
        if kw in name_lower: return 'currency'
    for kw in PCT_WORDS:
        if kw in name_lower: return 'percentage'

    # Value-based detection on sample
    if str_vals:
        email_hits = sum(1 for v in str_vals if EMAIL_RE.match(v.strip()))
        if email_hits / len(str_vals) > 0.7: return 'email'

        phone_hits = sum(1 for v in str_vals if PHONE_RE.match(v.strip()))
        if phone_hits / len(str_vals) > 0.7: return 'phone'

        pct_hits = sum(1 for v in str_vals if PCT_RE.match(v.strip()))
        if pct_hits / len(str_vals) > 0.7: return 'percentage'

        curr_hits = sum(1 for v in str_vals if CURRENCY_RE.match(v.strip()))
        if curr_hits / len(str_vals) > 0.7: return 'currency'

        date_hits = sum(1 for v in str_vals if any(r.search(str(v)) for r in DATE_RES))
        if date_hits / len(str_vals) > 0.5: return 'date'

    # Dtype fallback
    if 'int' in dtype or 'float' in dtype: return 'numeric'
    return 'text'


# ─── Public API: Column labeling ─────────────────────────────────────────────

def label_columns(df: pd.DataFrame) -> Dict[str, str]:
    """
    Assign a semantic label to every column in df.
    Uses distilBERT if available, falls back to rule engine.
    Returns: { "column_name": "email" | "phone" | "name" | "date" | ... }
    """
    classifier = _get_classifier()
    labels: Dict[str, str] = {}

    for col in df.columns:
        dtype     = str(df[col].dtype)
        sample    = df[col].dropna().head(10).tolist()

        if classifier == "fallback" or not sample:
            labels[col] = _rule_label(col, sample, dtype)
        else:
            # Build candidate text: "col_name: val1, val2, val3"
            candidate = f"{col}: {', '.join(str(v) for v in sample[:5])}"
            try:
                result = classifier(candidate, SEMANTIC_LABELS, multi_label=False)
                top    = result["labels"][0]
                labels[col] = LABEL_MAP.get(top, "text")
            except Exception:
                labels[col] = _rule_label(col, sample, dtype)

    return labels


# ─── Public API: Anomaly detection ────────────────────────────────────────────

def detect_anomalies(df: pd.DataFrame, contamination: float = 0.05) -> Dict[str, Any]:
    """
    Run IsolationForest on all numeric columns.
    Returns:
      {
        "anomaly_indices": [list of row indices],
        "anomaly_count": int,
        "total_rows": int,
        "scores": [list of floats, one per row],
        "columns_used": [list of column names]
      }
    """
    from sklearn.ensemble import IsolationForest

    num_df = df.select_dtypes(include=[np.number]).dropna(axis=1, how='all')

    if num_df.empty or num_df.shape[1] == 0:
        return {
            "anomaly_indices": [],
            "anomaly_count": 0,
            "total_rows": len(df),
            "scores": [],
            "columns_used": [],
        }

    # Fill remaining NaNs with column median for model input
    filled = num_df.fillna(num_df.median(numeric_only=True))

    model = IsolationForest(
        contamination=contamination,
        random_state=42,
        n_estimators=100,
    )
    predictions = model.fit_predict(filled)           # 1 = normal, -1 = anomaly
    scores      = model.decision_function(filled)     # more negative = more anomalous

    anomaly_mask    = predictions == -1
    anomaly_indices = [int(i) for i in np.where(anomaly_mask)[0]]

    return {
        "anomaly_indices": anomaly_indices,
        "anomaly_count":   int(anomaly_mask.sum()),
        "total_rows":      len(df),
        "scores":          [round(float(s), 4) for s in scores],
        "columns_used":    list(num_df.columns),
    }


# ─── Public API: AI-powered cleaning suggestions ──────────────────────────────

def generate_ai_suggestions(df: pd.DataFrame, col_labels: Dict[str, str], anomaly_result: Dict) -> List[Dict]:
    """
    Generate rich, ML-informed cleaning suggestions for the UI.
    Each suggestion has:
      - id, column, label, type (warning/info/success),
      - impact (high/medium/low), text, action (dict for CleanPage)
    """
    suggestions = []
    anomaly_indices = set(anomaly_result.get("anomaly_indices", []))

    for col in df.columns:
        label    = col_labels.get(col, "text")
        null_pct = df[col].isna().mean() * 100
        dtype    = str(df[col].dtype)
        is_num   = "int" in dtype or "float" in dtype

        # 1. High missing values → drop or impute
        if null_pct > 50:
            suggestions.append({
                "id":      f"drop_{col}",
                "column":  col,
                "label":   label,
                "type":    "warning",
                "impact":  "high",
                "text":    f'"{col}" has {null_pct:.0f}% missing values — strongly consider dropping this column.',
                "action":  {"op": "drop_column", "column": col},
            })
        elif null_pct > 15:
            fill_with = "mean" if is_num else "mode"
            suggestions.append({
                "id":      f"fill_{col}",
                "column":  col,
                "label":   label,
                "type":    "info",
                "impact":  "medium",
                "text":    f'"{col}" has {null_pct:.0f}% missing — fill with {fill_with}.',
                "action":  {"op": "fill_null", "column": col, "fillWith": fill_with},
            })

        # 2. Anomalies detected in numeric column
        if is_num and anomaly_indices:
            # Count how many anomaly rows have non-null values in this col
            col_anomalies = df.iloc[list(anomaly_indices)][col].notna().sum()
            if col_anomalies > 0:
                suggestions.append({
                    "id":      f"anomaly_{col}",
                    "column":  col,
                    "label":   label,
                    "type":    "warning",
                    "impact":  "high" if col_anomalies > 10 else "medium",
                    "text":    f'"{col}" has {col_anomalies} anomalous rows detected by IsolationForest — review in the Anomalies tab.',
                    "action":  None,
                })

        # 3. Text columns that should be lowercase
        if label in ("name", "text", "address") and not is_num:
            sample = df[col].dropna().head(50).astype(str)
            if sample.str.isupper().mean() > 0.3:
                suggestions.append({
                    "id":      f"lower_{col}",
                    "column":  col,
                    "label":   label,
                    "type":    "info",
                    "impact":  "low",
                    "text":    f'"{col}" has many ALL-CAPS values — consider lowercasing for consistency.',
                    "action":  {"op": "lowercase", "column": col},
                })

        # 4. Trim whitespace for string columns
        if not is_num and label in ("name", "text", "email", "address"):
            sample = df[col].dropna().head(50).astype(str)
            if sample.str.strip().ne(sample).any():
                suggestions.append({
                    "id":      f"trim_{col}",
                    "column":  col,
                    "label":   label,
                    "type":    "info",
                    "impact":  "low",
                    "text":    f'"{col}" has leading/trailing whitespace — trim for cleaner data.',
                    "action":  {"op": "trim_strings", "column": col},
                })

        # 5. Duplicate-heavy ID columns
        if label == "id":
            unique_pct = df[col].nunique() / max(len(df), 1) * 100
            if unique_pct < 90:
                suggestions.append({
                    "id":      f"dupes_{col}",
                    "column":  col,
                    "label":   label,
                    "type":    "warning",
                    "impact":  "medium",
                    "text":    f'"{col}" is an ID column with only {unique_pct:.0f}% unique values — possible duplicates.',
                    "action":  {"op": "drop_duplicates", "column": col},
                })

    if not suggestions:
        suggestions.append({
            "id":     "all_good",
            "column": None,
            "label":  None,
            "type":   "success",
            "impact": "none",
            "text":   "Dataset looks clean! AI found no major quality issues.",
            "action": None,
        })

    return suggestions


# ─── Public API: Model health status ─────────────────────────────────────────

def get_ml_status() -> dict:
    """
    Check readiness of the Transformers (DistilBERT) model.
    Returns a status dict compatible with the /models/status endpoint.
    """
    classifier = _get_classifier()
    distilbert_ok = classifier != "fallback" and classifier is not None
    return {
        "distilbert": {
            "model":   DISTILBERT_MODEL,
            "backend": "HuggingFace Transformers",
            "status":  "ready" if distilbert_ok else "fallback (rule-based)",
            "task":    "zero-shot-classification",
        },
        "isolation_forest": {
            "model":   "IsolationForest",
            "backend": "scikit-learn",
            "status":  "ready",   # always available — pure sklearn, no download
            "task":    "anomaly-detection",
        },
    }
