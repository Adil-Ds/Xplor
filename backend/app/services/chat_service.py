"""
Chat Service — Ollama / Qwen 2.5 natural language query engine
Converts user questions into pandas operations against the loaded dataset.
"""
import json
import re
import traceback
from typing import Any
import pandas as pd
import numpy as np
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5"


def _call_ollama(prompt: str, timeout: int = 60) -> str:
    """Send a prompt to Ollama and return the response text."""
    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.1,
            "num_predict": 512,
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
        raise RuntimeError("Ollama timed out. Try a simpler question.")
    except Exception as e:
        raise RuntimeError(f"Ollama error: {e}")


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


def answer_question(df: pd.DataFrame, question: str) -> dict:
    """
    Main entry point: take a DataFrame and a natural language question,
    return a structured answer dict.
    """
    # Build prompt and call LLM
    prompt = _build_context(df, question)
    llm_response = _call_ollama(prompt)

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
    """Check if Ollama is running and Qwen model is available."""
    try:
        resp = requests.get("http://localhost:11434/api/tags", timeout=5)
        resp.raise_for_status()
        models = [m["name"] for m in resp.json().get("models", [])]
        qwen_available = any("qwen" in m.lower() for m in models)
        return {
            "running": True,
            "models": models,
            "qwen_available": qwen_available,
        }
    except Exception:
        return {"running": False, "models": [], "qwen_available": False}
