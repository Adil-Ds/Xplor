from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.models import Dashboard

router = APIRouter()

class DashboardIn(BaseModel):
    name: str
    dataset_id: str | None = None
    widgets: list | None = []

@router.get("/")
def list_dashboards(db: Session = Depends(get_db), current=Depends(get_current_user)):
    return db.query(Dashboard).filter(Dashboard.owner_id == current["sub"]).all()

@router.post("/", status_code=201)
def create_dashboard(data: DashboardIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = Dashboard(owner_id=current["sub"], name=data.name, dataset_id=data.dataset_id, widgets=data.widgets or [])
    db.add(d); db.commit(); db.refresh(d)
    return d

@router.get("/{dash_id}")
def get_dashboard(dash_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    return d

@router.put("/{dash_id}")
def update_dashboard(dash_id: str, data: DashboardIn, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    d.name = data.name; d.dataset_id = data.dataset_id; d.widgets = data.widgets
    db.commit(); return d

@router.delete("/{dash_id}", status_code=204)
def delete_dashboard(dash_id: str, db: Session = Depends(get_db), current=Depends(get_current_user)):
    d = db.query(Dashboard).filter(Dashboard.id == dash_id, Dashboard.owner_id == current["sub"]).first()
    if not d: raise HTTPException(404)
    db.delete(d); db.commit()

@router.get("/suggest/{ds_id}")
def suggest(ds_id: str, model: str = None, provider: str = "auto",
            db: Session = Depends(get_db), current=Depends(get_current_user)):
    """Suggest widgets using a backend-stored dataset (requires prior upload)."""
    from app.models.models import Dataset
    from app.services.data_service import parse_uploaded_file
    from app.services.chat_service import suggest_dashboard_widgets

    ds = db.query(Dataset).filter(Dataset.id == ds_id, Dataset.owner_id == current["sub"]).first()
    if not ds:
        raise HTTPException(404, "Dataset not found on server — re-upload the file first.")

    meta = parse_uploaded_file(ds.file_path, ds.filetype, ds.filename)
    df   = meta["data"]

    try:
        widgets = suggest_dashboard_widgets(df, model=model, provider=provider)
        return {"widgets": widgets}
    except RuntimeError as e:
        msg = str(e)
        if "timed out" in msg.lower():
            raise HTTPException(504, msg)
        if "not running" in msg.lower():
            raise HTTPException(503, msg)
        raise HTTPException(500, msg)


@router.post("/widget-insight")
def widget_insight(body: dict, current=Depends(get_current_user)):
    """
    Generate a 3-bullet AI insight for a single dashboard widget.
    Body: {
      "title": str, "type": str, "xCol": str|null, "yCol": str,
      "aggregate": str, "chartData": [{"name":…,"value":…}], "rowCount": int
    }
    """
    from app.services.chat_service import _call_ai

    title      = body.get("title", "Chart")
    chart_type = body.get("type", "bar")
    x_col      = body.get("xCol") or "category"
    y_col      = body.get("yCol") or "value"
    aggregate  = body.get("aggregate", "sum")
    chart_data = body.get("chartData", [])[:15]
    row_count  = int(body.get("rowCount") or 0)
    provider   = (body.get("provider") or "auto").lower()

    if not chart_data:
        raise HTTPException(400, "chartData is required")

    values = [item.get("value", 0) for item in chart_data
              if isinstance(item.get("value"), (int, float))]

    data_lines = []
    for item in chart_data:
        name = item.get("name", "N/A")
        val  = item.get("value", 0)
        try:
            data_lines.append(f"  • {name}: {val:,.2f}")
        except (ValueError, TypeError):
            data_lines.append(f"  • {name}: {val}")
    data_block = "\n".join(data_lines)

    stats_block = ""
    if values:
        total = sum(values)
        avg   = total / len(values)
        stats_block = (
            f"Total: {total:,.2f} | Average: {avg:,.2f} | "
            f"Max: {max(values):,.2f} | Min: {min(values):,.2f}"
        )

    chart_desc = {
        "bar":     f"bar chart — {aggregate} of '{y_col}' per '{x_col}'",
        "hbar":    f"horizontal bar — {aggregate} of '{y_col}' per '{x_col}'",
        "line":    f"line chart — {aggregate} of '{y_col}' over '{x_col}'",
        "area":    f"area chart — {aggregate} of '{y_col}' over '{x_col}'",
        "pie":     f"pie/donut — {aggregate} of '{y_col}' by '{x_col}'",
        "scatter": f"scatter plot — '{x_col}' vs '{y_col}'",
        "kpi":     f"KPI metric — {aggregate} of '{y_col}'",
    }.get(chart_type, f"chart of '{y_col}'")

    prompt = f"""You are a senior data analyst. Interpret this dashboard chart for a business user.

Chart: "{title}"
Type: {chart_desc}
Dataset: {row_count:,} rows total
Statistics: {stats_block}

Data ({len(chart_data)} items shown):
{data_block}

Write exactly 3 concise bullet points. Start each line with "•".
Bullet 1: The single top finding — name the leading item and its value.
Bullet 2: A notable pattern, trend, or comparison visible in the data.
Bullet 3: A concrete business implication or recommended action.

Rules: each bullet under 20 words, use actual numbers, be specific not generic.

Bullets:"""

    try:
        text = _call_ai(prompt, num_predict=280, provider=provider)
        lines = [l.strip() for l in text.splitlines() if l.strip()]
        bullets = []
        for line in lines:
            if line.startswith(("•", "-", "*")) or (len(line) > 1 and line[0].isdigit() and line[1] in ".):"):
                clean = line.lstrip("•-*0123456789.) ").strip()
                if clean:
                    bullets.append(f"• {clean}")
            elif not bullets and line:
                bullets.append(f"• {line}")
            if len(bullets) == 3:
                break
        if not bullets:
            bullets = [f"• {l}" for l in lines[:3]]
        return {"insight": "\n".join(bullets[:3])}
    except RuntimeError as e:
        msg = str(e)
        if "timed out" in msg.lower():
            raise HTTPException(504, msg)
        if "not running" in msg.lower():
            raise HTTPException(503, msg)
        raise HTTPException(500, msg)


@router.post("/suggest-schema")
def suggest_from_schema(body: dict, current=Depends(get_current_user)):
    """
    Suggest 5 analytical widgets from a column schema — no DB lookup required.
    Body: {
      "columns": [{"name":"col","dtype":"float64","samples":[1,2,3],"unique":50}],
      "row_count": 1000,
      "model": null
    }
    """
    import pandas as pd
    from app.services.chat_service import suggest_dashboard_widgets

    columns   = body.get("columns", [])
    row_count = body.get("row_count", 100)
    model     = body.get("model") or None
    provider  = (body.get("provider") or "auto").lower()

    if not columns:
        raise HTTPException(400, "columns list is required")

    # Build a small DataFrame so the function signature is satisfied,
    # but pass the rich `schema` list so the prompt gets real sample values
    df_data = {}
    for col in columns:
        name  = col.get("name", "col")
        dtype = (col.get("dtype") or "object").lower()
        samples = col.get("samples") or []
        if "float" in dtype or "int" in dtype:
            vals = [float(s) for s in samples if s is not None][:5] or [0.0]
        else:
            vals = [str(s) for s in samples if s is not None][:5] or [""]
        df_data[name] = vals

    # Pad all columns to the same length
    max_len = max(len(v) for v in df_data.values()) if df_data else 1
    for k in df_data:
        while len(df_data[k]) < max_len:
            df_data[k].append(df_data[k][-1])

    df = pd.DataFrame(df_data)

    try:
        widgets = suggest_dashboard_widgets(df, model=model,
                                            schema=columns, row_count=row_count,
                                            provider=provider)
        return {"widgets": widgets, "row_count": row_count}
    except RuntimeError as e:
        msg = str(e)
        if "timed out" in msg.lower():
            raise HTTPException(504, msg)
        if "not running" in msg.lower():
            raise HTTPException(503, msg)
        raise HTTPException(500, msg)
