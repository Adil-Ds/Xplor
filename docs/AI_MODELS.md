# Xplor — AI Models Documentation

> **Platform:** Xplor Data Intelligence Platform  
> **Version:** 1.0.0  
> **Last Updated:** May 2026

---

## Overview

Xplor integrates **three AI models** across two distinct backends to deliver intelligent data analysis capabilities — entirely offline and on-device. No data ever leaves the user's machine.

| Model | Source | Backend | Task |
|---|---|---|---|
| **Qwen 2.5** | Alibaba Cloud (via Ollama) | Ollama local REST server | Natural language → pandas code |
| **DistilBERT-MNLI** | HuggingFace (typeform) | HuggingFace Transformers | Column semantic labeling |
| **IsolationForest** | scikit-learn | scikit-learn (in-process) | Anomaly detection |

---

## Model 1 — Qwen 2.5 (Ollama)

### What It Is
**Qwen 2.5** is a large language model from Alibaba Cloud, available in multiple sizes (0.5B → 72B parameters). Xplor uses it through **Ollama**, a local model runner that serves an OpenAI-compatible REST API at `http://localhost:11434`.

### Why Ollama?
- Zero Python dependencies for the LLM itself — Ollama handles model loading, quantization, and GPU offloading automatically.
- The model runs as a separate process; the Python backend simply sends HTTP requests.
- Users can swap any Ollama-compatible model (e.g., `llama3`, `mistral`) by changing `OLLAMA_MODEL` in `chat_service.py`.

### What It Does in Xplor
When a user types a natural language question in the **Chat** tab (e.g., *"What is the average salary by department?"*), Xplor:
1. Builds a **prompt** containing the dataset schema, column types, null counts, and 3 sample rows.
2. Sends the prompt to Qwen 2.5 via Ollama's `/api/generate` endpoint.
3. Qwen returns a **Python code block** that operates on a `df` variable.
4. The backend **safely executes** the code in a sandboxed environment with restricted builtins.
5. The result (scalar, table, or text) is returned to the frontend.

### Configuration
```python
# backend/app/services/chat_service.py
OLLAMA_URL   = "http://localhost:11434/api/generate"
OLLAMA_MODEL = "qwen2.5"
```

### Setup
```bash
# 1. Install Ollama (Windows)
# Download from https://ollama.com/download/windows

# 2. Pull Qwen 2.5 (default tag = 7B Q4 quantized, ~4.4 GB)
ollama pull qwen2.5

# 3. Verify it's running
ollama list
# Should show:  qwen2.5:latest ...
```

### Health Check
```
GET http://localhost:8000/chat/status
```
```json
{
  "running": true,
  "models": ["qwen2.5:latest"],
  "qwen_available": true
}
```

### Prompt Design
The prompt instructs Qwen to:
- Write a single Python expression using the `df` variable.
- Store the result in a variable named `result`.
- Never call `print()` or import libraries.
- Return `"I cannot answer that from the available data."` if unable.

The LLM response is parsed with a regex to extract the fenced ` ```python ``` ` block before execution.

### Security
Code execution uses Python's `exec()` with a **whitelist of safe builtins** — filesystem, network, and OS operations are completely unavailable inside the sandbox.

---

## Model 2 — DistilBERT (HuggingFace Transformers)

### What It Is
**`typeform/distilbert-base-uncased-mnli`** is a **DistilBERT** model (distilled, lighter version of BERT) fine-tuned on the **MultiNLI** (MNLI) natural language inference dataset. Fine-tuning on NLI gives the model *entailment* reasoning: given a premise and a hypothesis, can it determine if the hypothesis follows?

This property is exploited by HuggingFace's `zero-shot-classification` pipeline to classify arbitrary text into user-defined categories **without any task-specific training**.

> ⚠️ **Important note:** The base `distilbert-base-uncased` model (without MNLI fine-tuning) **cannot** perform zero-shot classification — it is only a language model. The MNLI checkpoint is required.

**Model page:** https://huggingface.co/typeform/distilbert-base-uncased-mnli  
**Parameters:** ~66M (vs BERT-base 110M)  
**Size on disk:** ~260 MB  

### What It Does in Xplor
After a dataset is uploaded, the agent pipeline automatically runs **column semantic labeling**:

For each column in the DataFrame, Xplor builds a candidate string:
```
"salary: 45000, 82000, 61000"
```
This is passed to the DistilBERT-MNLI pipeline with 10 candidate labels:
```python
SEMANTIC_LABELS = [
    "email address", "phone number", "person name",
    "date or timestamp", "currency or price", "identifier or ID",
    "street address", "percentage", "numeric measurement", "free text",
]
```
The model returns a ranked list of labels with confidence scores. The top label is mapped to a short label (`"currency"`, `"email"`, `"name"`, etc.) and stored alongside the dataset.

These labels power:
- **Cleaning suggestions** (e.g., trim whitespace on `name`/`email` columns)
- **PII detection** (flagging `email`, `phone`, `name` columns)
- **Anomaly prioritization** (anomalies in `currency` columns are high-impact)

### Fallback Behavior
If the model fails to load (e.g., no internet on first run before caching, insufficient RAM), the system automatically falls back to a **rule-based labeler** using:
- Column name keyword matching (`"email"` → `email`, `"salary"` → `currency`)
- Regex value matching (email pattern, phone pattern, date patterns)
- dtype-based defaults (`int`/`float` → `numeric`)

### Configuration
```python
# backend/app/services/ml_service.py
DISTILBERT_MODEL = "typeform/distilbert-base-uncased-mnli"

_classifier = pipeline(
    "zero-shot-classification",
    model=DISTILBERT_MODEL,
    device=-1,   # -1 = CPU; set to 0 for GPU
)
```

### First-Run Download
On first use, Transformers automatically downloads the model weights (~260 MB) to the HuggingFace cache (`~/.cache/huggingface/`). Subsequent runs load from cache — no internet required.

### Health Check
```
GET http://localhost:8000/models/status
```
```json
{
  "distilbert": {
    "model": "typeform/distilbert-base-uncased-mnli",
    "backend": "HuggingFace Transformers",
    "status": "ready",
    "task": "zero-shot-classification"
  }
}
```

---

## Model 3 — IsolationForest (scikit-learn)

### What It Is
**IsolationForest** is an unsupervised anomaly detection algorithm from scikit-learn. It works by randomly partitioning features using decision trees — anomalous points are isolated in fewer splits (shorter paths) than normal points.

- **No training data needed** — it learns the "normal" distribution from the data itself.
- Handles **multivariate anomalies** across all numeric columns simultaneously.
- Runs **in milliseconds** even on datasets with 100K+ rows.

### What It Does in Xplor
After column labeling, the agent runs anomaly detection on all numeric columns:
1. Selects only numeric columns, drops all-null columns.
2. Fills remaining NaNs with **column medians** (to avoid skewing the model).
3. Fits IsolationForest with `contamination=0.05` (assumes up to 5% of rows are anomalous).
4. Returns:
   - `anomaly_indices` — row indices flagged as anomalous
   - `anomaly_count` — total anomalous rows
   - `scores` — anomaly score per row (more negative = more anomalous)
   - `columns_used` — which columns were analyzed

These results feed into the cleaning suggestions (e.g., *"salary has 12 anomalous rows detected by AI — review or filter"*).

### Configuration
```python
# backend/app/services/ml_service.py
model = IsolationForest(
    contamination=0.05,  # expected fraction of outliers
    random_state=42,     # reproducibility
    n_estimators=100,    # number of trees
)
```

### Health Check
```
GET http://localhost:8000/models/status
```
```json
{
  "isolation_forest": {
    "model": "IsolationForest",
    "backend": "scikit-learn",
    "status": "ready",
    "task": "anomaly-detection"
  }
}
```

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                     XPLOR FRONTEND                          │
│     React (Vite) · localhost:5173                           │
│                                                             │
│   [Chat Tab]    [Clean Tab]    [Explore Tab]                │
└──────┬──────────────┬──────────────────────────────────────┘
       │              │
       ▼              ▼
┌─────────────────────────────────────────────────────────────┐
│                   FASTAPI BACKEND                           │
│                   localhost:8000                            │
│                                                             │
│  /chat/{ds_id}           /clean/{ds_id}/suggestions        │
│  /models/status          /datasets (upload trigger)        │
│                                                             │
│  ┌──────────────────┐  ┌───────────────────────────────┐   │
│  │  chat_service.py │  │       agent_service.py        │   │
│  │                  │  │   (background task on upload) │   │
│  │  1. Build prompt │  │                               │   │
│  │  2. Call Ollama  │  │  Step 1: label_columns()      │   │
│  │  3. Extract code │  │  Step 2: detect_anomalies()   │   │
│  │  4. Safe exec    │  │  Step 3: gen_suggestions()    │   │
│  └────────┬─────────┘  └──────┬──────────┬────────────┘   │
│           │                   │          │                  │
└───────────┼───────────────────┼──────────┼─────────────────┘
            │                   │          │
            ▼                   ▼          ▼
  ┌─────────────────┐  ┌──────────────┐  ┌──────────────────┐
  │   OLLAMA        │  │ TRANSFORMERS │  │  SCIKIT-LEARN    │
  │  (local server) │  │ (in-process) │  │  (in-process)    │
  │                 │  │              │  │                  │
  │  Model: qwen2.5 │  │  Model:      │  │  IsolationForest │
  │  Port: 11434    │  │  distilbert  │  │  contamination=5%│
  │  Backend: C++   │  │  -base-      │  │  n_estimators=100│
  │  (llama.cpp)    │  │  uncased-mnli│  │                  │
  └─────────────────┘  └──────────────┘  └──────────────────┘
```

---

## Complete Pipeline: What Happens on Dataset Upload

```
User uploads CSV/Excel
        │
        ▼
  FastAPI /datasets (POST)
  ├── Save file to disk
  ├── Parse with pandas
  ├── Store metadata in SQLite (Dataset model)
  └── Launch BackgroundTask: run_analysis_pipeline(ds_id, df)
              │
              ├── Step 1: label_columns(df)
              │   ├── [TRY] DistilBERT-MNLI zero-shot for each column
              │   └── [FALLBACK] Rule-based regex + keyword matching
              │
              ├── Step 2: detect_anomalies(df)
              │   ├── Select numeric columns
              │   ├── Fill NaN with median
              │   └── IsolationForest → anomaly_indices + scores
              │
              ├── Step 3: generate_ai_suggestions(df, labels, anomalies)
              │   ├── High missing % → drop/impute suggestion
              │   ├── Anomalies in column → review/filter suggestion
              │   ├── ALL-CAPS text → lowercase suggestion
              │   ├── Leading whitespace → trim suggestion
              │   └── ID column duplicates → deduplicate suggestion
              │
              └── Write data/analysis/{ds_id}.json  ← UI polls this
```

---

## Chat Pipeline: Natural Language Query

```
User types: "Show top 5 customers by total spend"
        │
        ▼
  POST /chat/{ds_id}  { "question": "..." }
        │
        ├── Load df from disk (parse_uploaded_file)
        ├── Build prompt: schema + 3 sample rows + question
        ├── POST to Ollama (qwen2.5) — timeout: 60s
        │
        ├── Qwen responds with:
        │   ```python
        │   result = df.groupby('customer')['spend'].sum()
        │            .nlargest(5).reset_index()
        │   ```
        │
        ├── Extract code block (regex)
        ├── exec() in sandbox with restricted __builtins__
        │
        └── Format result:
            ├── DataFrame → { type: "table", columns, rows }
            ├── Number    → { type: "scalar", value }
            └── String    → { type: "text", value }
```

---

## Setup Guide

### Prerequisites
| Requirement | Version | Notes |
|---|---|---|
| Python | ≥ 3.11 | Backend runtime |
| Ollama | latest | Download from ollama.com |
| RAM | ≥ 8 GB | 4 GB for Qwen 2.5, 4 GB for OS |
| Disk | ≥ 6 GB free | Qwen 2.5 (~4.4 GB) + DistilBERT (~260 MB) |

### Step-by-Step

```bash
# 1. Install Python dependencies
cd backend
pip install -r requirements.txt

# 2. Install Ollama
# Windows: download installer from https://ollama.com/download/windows
# macOS:   brew install ollama

# 3. Pull Qwen 2.5
ollama pull qwen2.5
# Alternatively, a smaller model:
# ollama pull qwen2.5:3b   (~1.9 GB)

# 4. Start Ollama server (runs in background automatically on Windows after install)
ollama serve   # only needed if not already running

# 5. Start Xplor backend
cd backend
python main.py
# → Server running at http://localhost:8000

# 6. Verify all models
curl http://localhost:8000/models/status
```

### Expected `/models/status` Response (All Green)
```json
{
  "qwen2.5": {
    "model": "qwen2.5",
    "backend": "Ollama (local REST server)",
    "status": "ready",
    "task": "natural-language-to-pandas code generation",
    "available_models": ["qwen2.5:latest"]
  },
  "distilbert": {
    "model": "typeform/distilbert-base-uncased-mnli",
    "backend": "HuggingFace Transformers",
    "status": "ready",
    "task": "zero-shot-classification"
  },
  "isolation_forest": {
    "model": "IsolationForest",
    "backend": "scikit-learn",
    "status": "ready",
    "task": "anomaly-detection"
  }
}
```

---

## Troubleshooting

### Qwen / Ollama Issues

| Problem | Solution |
|---|---|
| `Ollama is not running` error | Run `ollama serve` in a terminal |
| `qwen_available: false` | Run `ollama pull qwen2.5` |
| Chat times out | Qwen 2.5 7B is slow on CPU; try `ollama pull qwen2.5:3b` |
| Wrong model name | Check `OLLAMA_MODEL` in `chat_service.py` |

### DistilBERT Issues

| Problem | Solution |
|---|---|
| `status: "fallback (rule-based)"` | First-run download failed — check internet, then restart |
| Very slow first query | Model is downloading (~260 MB) — wait for completion |
| Out of memory error | Close other apps; DistilBERT needs ~500 MB RAM |
| `OSError: Can't load model` | Delete `~/.cache/huggingface/` and re-run |

### General

| Problem | Solution |
|---|---|
| Port 8000 in use | Change port in `main.py`: `uvicorn.run(..., port=8001)` |
| Port 11434 in use | Ollama is already running — that's fine |
| Frontend can't reach backend | Ensure CORS origins include `http://localhost:5173` |

---

## Privacy & Security

All three models run **100% locally**:

- **Qwen 2.5** runs inside Ollama on your machine — prompts and data never leave `localhost:11434`.
- **DistilBERT** runs in-process via Transformers — weights cached at `~/.cache/huggingface/` after first download.
- **IsolationForest** is pure in-memory scikit-learn — zero network activity.

No telemetry, no cloud API calls, no data transmission to external servers.

---

## File Reference

| File | Purpose |
|---|---|
| `backend/app/services/chat_service.py` | Qwen 2.5 / Ollama integration |
| `backend/app/services/ml_service.py` | DistilBERT + IsolationForest logic |
| `backend/app/services/agent_service.py` | Analysis pipeline orchestrator |
| `backend/app/api/chat.py` | `/chat` API routes |
| `backend/app/api/clean.py` | `/clean` API routes (uses suggestions) |
| `backend/main.py` | `/models/status` health endpoint |
| `backend/requirements.txt` | Python dependencies |
