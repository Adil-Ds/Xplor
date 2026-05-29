"""
Data service — file parsing, profiling, and cleaning operations (Pandas-based)
"""
import pandas as pd
import numpy as np
from typing import Any


def parse_uploaded_file(file_path: str, ext: str, filename: str) -> dict:
    """Read a file into a DataFrame and return metadata + preview."""
    try:
        if ext == "csv":
            df = pd.read_csv(file_path)
        elif ext in ("xlsx", "xls"):
            df = pd.read_excel(file_path)
        elif ext == "json":
            df = pd.read_json(file_path)
        elif ext == "parquet":
            df = pd.read_parquet(file_path)
        else:
            df = pd.read_csv(file_path)
    except Exception as e:
        return {"rows": 0, "columns": 0, "columns_list": [], "preview": [], "data": pd.DataFrame(), "error": str(e)}

    df = df.replace({np.nan: None})
    preview = df.head(200).to_dict(orient="records")
    return {
        "rows": len(df),
        "columns": len(df.columns),
        "columns_list": list(df.columns),
        "preview": preview,
        "data": df,
    }


def profile_dataset(df: pd.DataFrame) -> dict:
    """Generate per-column statistics."""
    if isinstance(df, list):
        df = pd.DataFrame(df)
    profiles = {}
    for col in df.columns:
        s = df[col]
        null_count = int(s.isna().sum())
        total      = len(s)
        profile = {
            "column":    col,
            "dtype":     str(s.dtype),
            "total":     total,
            "nulls":     null_count,
            "null_pct":  round(null_count / max(total, 1) * 100, 2),
            "unique":    int(s.nunique()),
        }
        if pd.api.types.is_numeric_dtype(s):
            desc = s.describe()
            profile.update({
                "mean":   round(float(desc.get("mean", 0)), 4),
                "std":    round(float(desc.get("std", 0)), 4),
                "min":    float(desc.get("min", 0)),
                "max":    float(desc.get("max", 0)),
                "q25":    float(desc.get("25%", 0)),
                "median": float(desc.get("50%", 0)),
                "q75":    float(desc.get("75%", 0)),
            })
        profiles[col] = profile
    return profiles


def apply_cleaning_recipe(df: pd.DataFrame, recipe: list[dict]) -> pd.DataFrame:
    """Apply a list of cleaning steps to a DataFrame."""
    for step in recipe:
        op = step.get("op")
        try:
            if op == "drop_nulls":
                cols = step.get("columns") or list(df.columns)
                df = df.dropna(subset=cols)

            elif op == "fill_null":
                col  = step["column"]
                fill = step.get("fillWith", "constant")
                val  = step.get("fillValue", "")
                if fill == "mean":   val = df[col].mean()
                elif fill == "median": val = df[col].median()
                elif fill == "mode": val = df[col].mode()[0] if len(df[col].mode()) > 0 else ""
                df[col] = df[col].fillna(val)

            elif op == "drop_duplicates":
                cols = step.get("columns") or list(df.columns)
                df = df.drop_duplicates(subset=cols)

            elif op == "rename_column":
                df = df.rename(columns={step["oldName"]: step["newName"]})

            elif op == "drop_column":
                df = df.drop(columns=[step["column"]], errors="ignore")

            elif op == "cast_type":
                col = step["column"]
                to  = step.get("toType", "string")
                if to == "number": df[col] = pd.to_numeric(df[col], errors="coerce")
                elif to == "string": df[col] = df[col].astype(str)
                elif to == "date":   df[col] = pd.to_datetime(df[col], errors="coerce").dt.date

            elif op == "trim_strings":
                df[step["column"]] = df[step["column"]].astype(str).str.strip()

            elif op == "lowercase":
                df[step["column"]] = df[step["column"]].astype(str).str.lower()

            elif op == "uppercase":
                df[step["column"]] = df[step["column"]].astype(str).str.upper()

            elif op == "replace_value":
                df[step["column"]] = df[step["column"]].astype(str).str.replace(
                    step.get("findVal", ""), step.get("replaceVal", ""), regex=False
                )

            elif op == "filter_rows":
                col  = step["column"]
                op_  = step.get("operator", "=")
                val  = step.get("value", "")
                if op_ == "=":        df = df[df[col].astype(str) == str(val)]
                elif op_ == "!=":     df = df[df[col].astype(str) != str(val)]
                elif op_ == ">":      df = df[pd.to_numeric(df[col], errors="coerce") > float(val)]
                elif op_ == "<":      df = df[pd.to_numeric(df[col], errors="coerce") < float(val)]
                elif op_ == ">=":     df = df[pd.to_numeric(df[col], errors="coerce") >= float(val)]
                elif op_ == "<=":     df = df[pd.to_numeric(df[col], errors="coerce") <= float(val)]
                elif op_ == "contains": df = df[df[col].astype(str).str.contains(str(val), case=False, na=False)]

            elif op == "parse_date":
                df[step["column"]] = pd.to_datetime(df[step["column"]], errors="coerce")

        except Exception as e:
            print(f"[clean] Step '{op}' failed: {e}")
            continue

    return df.replace({np.nan: None})
