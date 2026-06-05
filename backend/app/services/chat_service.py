"""
Chat Service — Ollama (local) with Groq cloud API fallback.

Priority:
  1. Ollama (local, private, free)  — used when running
  2. Groq  (cloud, free tier)       — automatic fallback when Ollama is down
     Sign up free at https://console.groq.com  (14,400 req/day, no credit card)
"""
import json
import os
import re
from typing import Any

import pandas as pd
import numpy as np
import requests
from pathlib import Path
from dotenv import load_dotenv

# Resolve .env relative to this file: chat_service.py → services → app → backend/.env
load_dotenv(Path(__file__).parent.parent.parent / ".env")

# ── Ollama (local) ────────────────────────────────────────────────────────────
OLLAMA_URL   = os.getenv("OLLAMA_URL",   "http://localhost:11434/api/generate")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "qwen2.5")

# ── Groq cloud fallback ───────────────────────────────────────────────────────
GROQ_API_KEY          = os.getenv("GROQ_API_KEY",          "")
GROQ_MODEL            = os.getenv("GROQ_MODEL",            "llama-3.1-8b-instant")
GROQ_FALLBACK_ENABLED = os.getenv("GROQ_FALLBACK_ENABLED", "true").lower() == "true"
GROQ_URL              = "https://api.groq.com/openai/v1/chat/completions"


def _call_ollama(prompt: str, timeout: int = 180, model: str = None,
                 num_predict: int = 512) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": model or OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": num_predict,
        }
    }
    try:
        resp = requests.post(OLLAMA_URL, json=payload, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
        return data.get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError("Ollama is not running. Start it with: ollama serve")
    except requests.exceptions.Timeout:
        raise RuntimeError("Ollama timed out after 3 minutes. Try a shorter question or check Ollama resources.")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


def _call_groq(prompt: str, max_tokens: int = 1024) -> str:
    """Call the Groq cloud API (OpenAI-compatible endpoint)."""
    if not GROQ_API_KEY:
        raise RuntimeError(
            "GROQ_API_KEY is not set. Add it to backend/.env — "
            "get a free key at https://console.groq.com"
        )
    resp = requests.post(
        GROQ_URL,
        json={
            "model":       GROQ_MODEL,
            "messages":    [{"role": "user", "content": prompt}],
            "temperature": 0.1,
            "max_tokens":  max_tokens,
        },
        headers={
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type":  "application/json",
        },
        timeout=30,
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"].strip()


def _call_ai(prompt: str, model: str = None, num_predict: int = 512,
             provider: str = "auto") -> str:
    """
    Dispatch an LLM call based on the requested provider.

    provider:
      "ollama" → use local Ollama only (no fallback). Raises if Ollama is down.
      "groq"   → use Groq cloud only. Raises if no key / unreachable.
      "auto"   → try Ollama first, transparently fall back to Groq when Ollama
                 is down/timed-out (requires GROQ_FALLBACK_ENABLED + GROQ_API_KEY).
    """
    provider = (provider or "auto").lower()

    # ── Force Groq ──
    if provider == "groq":
        return _call_groq(prompt, max_tokens=num_predict)

    # ── Force Ollama (no fallback) ──
    if provider == "ollama":
        return _call_ollama(prompt, model=model, num_predict=num_predict)

    # ── Auto: Ollama first, Groq fallback ──
    try:
        return _call_ollama(prompt, model=model, num_predict=num_predict)
    except RuntimeError as ollama_err:
        msg = str(ollama_err).lower()
        if GROQ_FALLBACK_ENABLED and GROQ_API_KEY and ("not running" in msg or "timed out" in msg):
            try:
                return _call_groq(prompt, max_tokens=num_predict)
            except Exception as groq_err:
                raise RuntimeError(
                    f"Ollama unavailable ({ollama_err}) and Groq fallback also failed: {groq_err}"
                )
        raise


def check_groq_status() -> dict:
    """Check whether Groq API key is configured and reachable."""
    if not GROQ_API_KEY:
        return {"configured": False, "model": GROQ_MODEL,
                "status": "no API key — add GROQ_API_KEY to backend/.env"}
    if not GROQ_FALLBACK_ENABLED:
        return {"configured": True, "model": GROQ_MODEL, "status": "disabled (GROQ_FALLBACK_ENABLED=false)"}
    try:
        # Lightweight ping — ask for 1 token
        requests.post(
            GROQ_URL,
            json={"model": GROQ_MODEL, "messages": [{"role": "user", "content": "hi"}], "max_tokens": 1},
            headers={"Authorization": f"Bearer {GROQ_API_KEY}", "Content-Type": "application/json"},
            timeout=8,
        ).raise_for_status()
        return {"configured": True, "model": GROQ_MODEL, "status": "ready"}
    except Exception as e:
        return {"configured": True, "model": GROQ_MODEL, "status": f"error: {e}"}


def _build_context(df: pd.DataFrame, question: str) -> str:
    """Build a prompt context from the dataframe schema + sample."""
    # Column info
    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        nulls = int(df[col].isna().sum())
        sample_vals = df[col].dropna().head(3).tolist()
        col_info.append(f"  - {col} (type: {dtype}, nulls: {nulls}, samples: {sample_vals})")

    col_block = "\n".join(col_info)
    sample_rows = df.head(3).replace({np.nan: None}).to_dict(orient="records")
    sample_block = json.dumps(sample_rows, default=str, indent=2)

    prompt = f"""You are a data analysis assistant. You have access to a pandas DataFrame called `df`.

Dataset Info:
- Total rows: {len(df)}
- Total columns: {len(df.columns)}
- Columns:
{col_block}

Sample rows:
{sample_block}

User Question: {question}

Instructions:
1. Write a single Python expression or short block of code using the `df` variable.
2. Store the final result in a variable called `result`.
3. `result` should be one of: a number, a string, a list, or a pandas DataFrame/Series.
4. Do NOT use print(). Do NOT import anything. Do NOT modify `df`.
5. If you cannot answer from this data, set result = "I cannot answer that from the available data."
6. Wrap your code in ```python ... ``` blocks.

Write the Python code now:"""
    return prompt


def _extract_code(llm_response: str) -> str:
    """Extract python code block from LLM response."""
    # Try fenced code block first
    pattern = r"```(?:python)?\s*\n?(.*?)```"
    match = re.search(pattern, llm_response, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()
    # Fallback: return raw response if it looks like code
    lines = [l for l in llm_response.strip().splitlines() if not l.startswith("#")]
    return "\n".join(lines).strip()


def _safe_execute(code: str, df: pd.DataFrame) -> Any:
    """Safely execute extracted pandas code."""
    # Restrict builtins to safe ones
    safe_builtins = {
        "__builtins__": {
            "len": len, "sum": sum, "min": min, "max": max,
            "round": round, "abs": abs, "sorted": sorted,
            "list": list, "dict": dict, "str": str, "int": int,
            "float": float, "bool": bool, "range": range,
            "enumerate": enumerate, "zip": zip, "map": map,
            "filter": filter, "any": any, "all": all,
            "print": lambda *a, **k: None,  # no-op print
        }
    }
    local_vars = {"df": df.copy(), "pd": pd, "np": np}
    exec(compile(code, "<chat>", "exec"), safe_builtins, local_vars)
    return local_vars.get("result", "Code executed but no result was produced.")


def _format_result(result: Any) -> dict:
    """Convert result to a JSON-serializable response dict."""
    if isinstance(result, pd.DataFrame):
        result = result.replace({np.nan: None})
        return {
            "type": "table",
            "columns": list(result.columns),
            "rows": result.head(50).to_dict(orient="records"),
            "total_rows": len(result),
        }
    elif isinstance(result, pd.Series):
        result = result.reset_index()
        result = result.replace({np.nan: None})
        return {
            "type": "table",
            "columns": list(result.columns),
            "rows": result.head(50).to_dict(orient="records"),
            "total_rows": len(result),
        }
    elif isinstance(result, (int, float, np.integer, np.floating)):
        return {"type": "scalar", "value": round(float(result), 4)}
    elif isinstance(result, str):
        return {"type": "text", "value": result}
    elif isinstance(result, (list, dict)):
        return {"type": "text", "value": json.dumps(result, default=str)}
    else:
        return {"type": "text", "value": str(result)}


def answer_question(df: pd.DataFrame, question: str, model: str = None,
                    provider: str = "auto") -> dict:
    """
    Main entry point: take a DataFrame and a natural language question,
    return a structured answer dict.
    """
    prompt = _build_context(df, question)
    llm_response = _call_ai(prompt, model=model, provider=provider)

    # Extract and execute code
    code = _extract_code(llm_response)
    if not code:
        return {"type": "text", "value": "I could not generate code for that question.", "code": ""}

    try:
        result = _safe_execute(code, df)
        formatted = _format_result(result)
        formatted["code"] = code  # include for transparency
        formatted["question"] = question
        return formatted
    except Exception as e:
        return {
            "type": "error",
            "value": f"Code execution failed: {str(e)}",
            "code": code,
            "question": question,
        }


def check_ollama_status() -> dict:
    """Check if Ollama is running and list all available models."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        qwen_available = any("qwen" in m.lower() for m in models)
        default_available = any(m.startswith(OLLAMA_MODEL) for m in models)
        return {
            "running": True,
            "models": models,
            "qwen_available": qwen_available,
            "default_model": OLLAMA_MODEL,
            "default_model_available": default_available,
        }
    except Exception:
        return {
            "running": False,
            "models": [],
            "qwen_available": False,
            "default_model": OLLAMA_MODEL,
            "default_model_available": False,
        }


def generate_insights(df: pd.DataFrame, model: str = None, provider: str = "auto") -> str:
    """Generate a 2-paragraph plain English insight narrative from the dataset schema and samples."""
    col_info = []
    for col in df.columns:
        dtype = str(df[col].dtype)
        sample_vals = df[col].dropna().head(3).tolist()
        col_info.append(f"  - {col} (type: {dtype}, samples: {sample_vals})")

    col_block = "\n".join(col_info)

    prompt = f"""You are an expert Data Analyst. You have been given the schema of a dataset.

Dataset Info:
- Total rows: {len(df)}
- Total columns: {len(df.columns)}
- Columns:
{col_block}

Task:
Write a 2-paragraph professional business narrative summarizing what this dataset appears to be about and what kinds of insights or hypotheses a business user might explore. Be concise, insightful, and professional. Do not write code.
"""
    return _call_ai(prompt, model=model, provider=provider)


def suggest_dashboard_widgets(df: pd.DataFrame, model: str = None,
                              schema: list = None, row_count: int = None,
                              provider: str = "auto") -> list:
    """
    Suggest 5 meaningful dashboard widgets.
    Uses `schema` (list of dicts with name/dtype/samples/unique) when available
    for richer context; falls back to reading `df` directly.
    """
    # Build column descriptions with sample values
    col_info = []
    if schema:
        for col in schema:
            name    = col.get("name", "?")
            dtype   = col.get("dtype", "object")
            samples = col.get("samples", [])
            unique  = col.get("unique", "?")
            is_num  = "float" in dtype or "int" in dtype
            kind    = "numeric" if is_num else "categorical/text"
            col_info.append(
                f"  - {name} ({kind}, {unique} unique values, "
                f"samples: {samples[:5]})"
            )
        total_rows = row_count or 100
    else:
        for col in df.columns:
            dtype   = str(df[col].dtype)
            samples = df[col].dropna().head(5).tolist()
            unique  = int(df[col].nunique())
            is_num  = "int" in dtype or "float" in dtype
            kind    = "numeric" if is_num else "categorical/text"
            col_info.append(
                f"  - {col} ({kind}, {unique} unique values, "
                f"samples: {samples})"
            )
        total_rows = row_count or len(df)

    col_block  = "\n".join(col_info)
    col_names  = [c.get("name") if schema else c for c in (schema or list(df.columns))]
    num_cols   = [c.get("name") if schema else c
                  for c in (schema or [])
                  if ("float" in (c.get("dtype","") if schema else str(df[c].dtype)) or
                      "int"   in (c.get("dtype","") if schema else str(df[c].dtype)))]
    if not schema:
        num_cols = [c for c in df.columns
                    if "int" in str(df[c].dtype) or "float" in str(df[c].dtype)]
    cat_cols   = [c for c in col_names if c not in num_cols]

    prompt = f"""You are a senior BI Analyst building a Power BI-style analytical dashboard.

Dataset: {total_rows:,} rows

Columns:
{col_block}

Numeric columns  : {num_cols}
Categorical cols : {cat_cols}

──────────────────────────────────────────
TASK: Return EXACTLY 5 widgets as a JSON array.
──────────────────────────────────────────

COMPOSITION RULES (must follow):
1. Include 1-2 KPI cards — pick the most important numeric metrics.
2. Include 1 BAR or HBAR chart — show a top-N category comparison.
3. Include 1 LINE or AREA chart — show a trend over the most sequential/temporal column.
4. Include 1 PIE chart — show composition/share. Only use it if a categorical column has ≤ 10 unique values.
5. If no pie candidate, use SCATTER (correlation between 2 numeric cols) or a second bar.

CHART TYPE RULES:
- "kpi"     → xCol: null,  yCol: numeric column, aggregate: sum/mean/count
- "bar"     → xCol: categorical column, yCol: numeric column
- "hbar"    → xCol: categorical column, yCol: numeric column (use when category names are long)
- "line"    → xCol: date/time/sequential/categorical column, yCol: numeric column
- "area"    → same as line — prefer for cumulative trends
- "pie"     → xCol: categorical column with ≤10 unique, yCol: numeric column
- "scatter" → xCol: numeric column, yCol: numeric column (shows correlation)

TITLE RULES — be specific and analytical:
  ✓ GOOD: "Total Revenue by Region"  |  "Monthly Profit Trend"  |  "Avg Order Value"
  ✗ BAD:  "bar chart"                |  "line"                  |  "KPI 1"

Aggregations: sum, mean, count, min, max

RETURN FORMAT — start with [ and end with ], nothing else outside the array:
[
  {{"type":"kpi","title":"...","xCol":null,"yCol":"...","aggregate":"..."}},
  {{"type":"bar","title":"...","xCol":"...","yCol":"...","aggregate":"..."}},
  ...5 total items...
]

JSON:"""

    response = _call_ai(prompt, model=model, num_predict=1500, provider=provider)

    # Extract JSON — handle markdown fences and leading text
    for pattern in [
        r"```(?:json)?\s*\n?(.*?)\n?```",   # fenced block
        r"(\[.*\])",                          # bare array anywhere in response
    ]:
        match = re.search(pattern, response, re.DOTALL | re.IGNORECASE)
        if match:
            candidate = match.group(1).strip()
            try:
                widgets = json.loads(candidate)
                if isinstance(widgets, list) and widgets:
                    # Validate and sanitise each widget
                    clean = []
                    for w in widgets:
                        if not isinstance(w, dict): continue
                        if w.get("type") not in {"bar","hbar","line","area","pie","scatter","kpi","table"}:
                            w["type"] = "bar"
                        if w.get("type") == "kpi":
                            w["xCol"] = None
                        clean.append(w)
                    if clean:
                        return clean
            except Exception:
                continue

    return []
