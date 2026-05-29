import numpy as np
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dataset
from app.services.data_service import parse_uploaded_file, profile_dataset

router = APIRouter()

def load_df(ds_id, owner_id, db):
    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == owner_id).first()
    if not ds: raise HTTPException(404)
    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    return meta["data"]

@router.get("/{ds_id}/stats")
def stats(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    df = load_df(ds_id, current["sub"], db)
    return profile_dataset(df)

@router.get("/{ds_id}/correlation")
def correlation(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    df = load_df(ds_id, current["sub"], db)
    num_df = df.select_dtypes(include=[np.number])
    if num_df.shape[1] < 2:
        return {"columns": [], "matrix": []}
    corr = num_df.corr().round(3)
    return {"columns": list(corr.columns), "matrix": corr.values.tolist()}

@router.get("/{ds_id}/distribution")
def distribution(ds_id: str, column: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    df = load_df(ds_id, current["sub"], db)
    if column not in df.columns: raise HTTPException(400, "Column not found")
    s = df[column].dropna()
    if pd.api.types.is_numeric_dtype(s):
        hist, edges = np.histogram(s.dropna(), bins=15)
        return {"type": "numeric", "bins": [{"bin": round(float(e),2), "count": int(c)} for e,c in zip(edges, hist)]}
    else:
        vc = s.value_counts().head(20)
        return {"type": "categorical", "values": [{"value": str(k), "count": int(v)} for k,v in vc.items()]}

@router.get("/{ds_id}/outliers")
def outliers(ds_id: str, column: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    df = load_df(ds_id, current["sub"], db)
    if column not in df.columns: raise HTTPException(400)
    s = pd.to_numeric(df[column], errors="coerce").dropna()
    q1, q3 = s.quantile(0.25), s.quantile(0.75)
    iqr = q3 - q1
    mask = (s < q1 - 1.5*iqr) | (s > q3 + 1.5*iqr)
    return {"count": int(mask.sum()), "q1": float(q1), "q3": float(q3), "iqr": float(iqr), "lower_fence": float(q1-1.5*iqr), "upper_fence": float(q3+1.5*iqr)}

@router.get("/{ds_id}/suggestions")
def suggestions(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """
    AI-powered cleaning suggestions.
    Uses cached agent analysis if available, falls back to real-time ML inference.
    """
    from app.services.agent_service import get_analysis
    from app.services.ml_service import label_columns, detect_anomalies, generate_ai_suggestions

    df = load_df(ds_id, current["sub"], db)

    # Try cached analysis first (already run by agent pipeline after upload)
    cached = get_analysis(ds_id)
    if cached and cached.get("status") == "done":
        return {
            "suggestions": cached.get("suggestions", []),
            "col_labels":  cached.get("col_labels", {}),
            "anomaly_summary": {
                "count": cached.get("anomalies", {}).get("count", 0),
                "total_rows": cached.get("anomalies", {}).get("total_rows", len(df)),
            },
            "source": "cache",
        }

    # Real-time fallback — run analysis now
    col_labels = label_columns(df)
    anomaly_result = detect_anomalies(df)
    hints = generate_ai_suggestions(df, col_labels, anomaly_result)

    return {
        "suggestions": hints,
        "col_labels":  col_labels,
        "anomaly_summary": {
            "count":      anomaly_result["anomaly_count"],
            "total_rows": anomaly_result["total_rows"],
        },
        "source": "realtime",
    }

@router.get("/{ds_id}/anomalies")
def anomalies_endpoint(ds_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    """
    Run IsolationForest anomaly detection.
    Returns flagged row indices + anomalous rows for highlighting in the UI.
    """
    from app.services.agent_service import get_analysis
    from app.services.ml_service import detect_anomalies

    df = load_df(ds_id, current["sub"], db)

    # Use cached result if available
    cached = get_analysis(ds_id)
    if cached and cached.get("status") == "done" and cached.get("anomalies"):
        a = cached["anomalies"]
        indices = a.get("indices", [])
        anomaly_rows = df.iloc[indices].replace({np.nan: None}).to_dict(orient="records") if indices else []
        return {
            "anomaly_count":   a.get("count", 0),
            "total_rows":      a.get("total_rows", len(df)),
            "columns_used":    a.get("columns_used", []),
            "anomaly_indices": indices,
            "anomaly_rows":    anomaly_rows[:200],
            "source":          "cache",
        }

    # Real-time fallback
    result = detect_anomalies(df)
    indices = result["anomaly_indices"]
    anomaly_rows = df.iloc[indices].replace({np.nan: None}).to_dict(orient="records") if indices else []
    return {
        "anomaly_count":   result["anomaly_count"],
        "total_rows":      result["total_rows"],
        "columns_used":    result["columns_used"],
        "anomaly_indices": indices,
        "anomaly_rows":    anomaly_rows[:200],
        "source":          "realtime",
    }

@router.post("/{ds_id}/query")
def query(ds_id: str, body: dict, db: Session = Depends(get_db), current=Depends(get_current_user)):
    df = load_df(ds_id, current["sub"], db)
    filters = body.get("filters", [])
    group_by = body.get("groupBy")
    agg_col  = body.get("aggCol")
    agg_fn   = body.get("aggFn", "sum")

    for f in filters:
        col, op, val = f.get("column"), f.get("operator","="), f.get("value","")
        if col not in df.columns: continue
        try:
            if op == "=":          df = df[df[col].astype(str)==str(val)]
            elif op == "!=":       df = df[df[col].astype(str)!=str(val)]
            elif op == ">":        df = df[pd.to_numeric(df[col],errors="coerce")>float(val)]
            elif op == "<":        df = df[pd.to_numeric(df[col],errors="coerce")<float(val)]
            elif op == "contains": df = df[df[col].astype(str).str.contains(str(val),case=False,na=False)]
        except: pass

    if group_by and agg_col and group_by in df.columns and agg_col in df.columns:
        fn_map = {"sum": "sum","mean":"mean","count":"count","min":"min","max":"max"}
        result = getattr(df.groupby(group_by)[agg_col], fn_map.get(agg_fn,"sum"))().reset_index()
        result.columns = [group_by, agg_col]
        return {"rows": result.replace({np.nan:None}).to_dict(orient="records"), "columns": list(result.columns)}

    return {"rows": df.head(200).replace({np.nan:None}).to_dict(orient="records"), "columns": list(df.columns)}
