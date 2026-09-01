# 🔭 Xplor — AI-Powered Data Intelligence Platform

> **Intelligent data analytics with built-in AI models, natural language querying, and enterprise-grade security**  
> Department of Data Science | Semester 4 Capstone Project | 2026

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/Python-3.11%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-green)](https://fastapi.tiangolo.com)
[![React 19](https://img.shields.io/badge/React-19-61dafb)](https://react.dev)
[![Vite](https://img.shields.io/badge/Vite-8-purple)](https://vitejs.dev)
[![HuggingFace](https://img.shields.io/badge/HuggingFace-Transformers-orange)](https://huggingface.co)

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Features](#-features)
- [Architecture](#-architecture)
- [AI Models & Results](#-ai-models--results)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Quick Start](#-quick-start)
- [API Endpoints](#-api-endpoints)
- [Security](#-security)
- [Team](#-team)

---

## 🌟 Overview

**Xplor** is a full-stack AI-powered data intelligence platform that lets users upload datasets, clean them with ML-assisted suggestions, explore and visualize the data, query it in plain English, and auto-generate dashboards and PDF reports — all behind a secure, role-based authentication system.

The platform combines:
- **Local LLMs via Ollama** (primary) with **Groq cloud API** automatic fallback
- **Fine-tuned DistilBERT** for column semantic labeling
- **IsolationForest** for anomaly detection
- **AES-256 encryption**, **JWT auth**, **RBAC**, and **prompt injection guards**

---

## ✨ Features

| Feature | Description |
|---|---|
| 📁 **Dataset Manager** | Upload CSV/Excel/Parquet files, preview, manage versions |
| 🧹 **AI Data Cleaning** | ML-powered suggestions using DistilBERT + IsolationForest |
| 🔍 **Data Explorer** | Filter, sort, pivot, and visualize columns interactively |
| 💬 **AI Chat (NL→Code)** | Ask questions in plain English; LLM generates and executes Pandas code |
| 📊 **Auto Dashboards** | LLM suggests and renders 5 optimal chart widgets per dataset |
| 📄 **PDF Reports** | Auto-generate downloadable PDF reports with charts and AI narrative |
| 🔒 **Security Center** | Audit logs, threat monitoring, RBAC, prompt injection guards |
| ⚙️ **Settings** | Theme, AI model selection (Ollama/Groq), account management |

---

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  FRONTEND (React 19 + Vite)              │
│  LoginPage → HomePage → Datasets → Clean → Explore       │
│            Dashboard → Reports → Chat → Security          │
│  State: Zustand  |  Charts: Recharts  |  UI: TailwindCSS │
└────────────────────────┬────────────────────────────────┘
                         │ HTTP / REST API
┌────────────────────────▼────────────────────────────────┐
│                 BACKEND (FastAPI + Python)                │
│  /auth  /datasets  /clean  /explore  /dashboards         │
│  /reports  /chat  /security  /models/status              │
│  Gateway: JWT Auth  |  DB: SQLAlchemy (SQLite)           │
└──────────┬───────────────────────────┬───────────────────┘
           │                           │
┌──────────▼──────────┐   ┌────────────▼──────────────────┐
│   AI / ML Services   │   │      Security Module           │
│  DistilBERT (HF)    │   │  AES-256 | JWT | RBAC | MFA   │
│  IsolationForest    │   │  Prompt Injection Guard        │
│  Ollama (local LLM) │   │  Audit Logger | File Scanner   │
│  Groq API (fallback)│   └────────────────────────────────┘
└─────────────────────┘
```

---

## 🤖 AI Models & Results

### 1. Column Semantic Labeling — DistilBERT Fine-Tuning

**Model:** `distilbert-base-uncased` fine-tuned for 5 epochs on 420 real column names from public ML datasets (Titanic, UCI Adult, etc.) across **10 semantic classes**: email, phone, name, date, currency, id, address, percentage, numeric, text.

| Metric | Zero-Shot Baseline | Fine-Tuned DistilBERT | Improvement |
|---|---|---|---|
| **Accuracy** | 60.71% | **75.0%** | **+14.3 pp** |
| **Macro F1** | 56.99% | **74.4%** | **+17.4 pp** |

<details>
<summary>📊 Per-Class F1 Scores (click to expand)</summary>

| Class | Zero-Shot F1 | Fine-Tuned F1 | Delta |
|---|---|---|---|
| email | 100.0% | 84.2% | -15.8 |
| phone | 87.5% | 93.3% | +5.8 |
| name | 66.7% | 71.4% | +4.7 |
| date | 85.7% | 85.7% | 0 |
| currency | 63.6% | 84.2% | +20.6 |
| id | 84.2% | 94.7% | +10.5 |
| address | 64.0% | 58.8% | -5.2 |
| percentage | 18.2% | 84.2% | +66.0 |
| numeric | 0.0% | 42.9% | +42.9 |
| text | 0.0% | 44.4% | +44.4 |

</details>

> Evaluation plots: `ai-models/evaluation/distilbert_confusion_matrices.png`, `distilbert_per_class_f1.png`, `distilbert_training_curves.png`

---

### 2. Anomaly Detection — IsolationForest vs IQR Baseline

**Dataset:** KDD Cup 1999 (SA subset, 10%) — **100,655 rows**, 3.36% anomaly rate.

**Model:** IsolationForest (100 estimators, contamination = 0.0336, random_state = 42)

| Metric | IQR Baseline | IsolationForest | Improvement |
|---|---|---|---|
| **Precision** | 0.052 | **0.272** | +22.0 pp |
| **Recall** | 1.000 | 0.260 | -74.0 pp |
| **F1 Score** | 0.098 | **0.266** | **+16.8 pp** |
| **ROC-AUC** | 0.971 | 0.939 | -3.3 pp |
| **False Positive Rate** | 63.9% | **2.4%** | **↓ 61.5 pp** |

> **Key win:** IsolationForest reduced false positives by **61.5 percentage points**, making it far more practical for real-world anomaly flagging.
> Best contamination parameter from sweep: `0.01` (F1 = 0.403).

> Evaluation plots: `ai-models/evaluation/if_roc_curve.png`, `if_precision_recall.png`, `if_score_distribution.png`, `if_contamination_sweep.png`

---

### 3. Local LLM Selection — Qwen2.5 via Ollama

We benchmarked **19 local LLMs** across RAM usage, MMLU, and HumanEval scores to select the best model for CPU-constrained environments.

**Selected: `Qwen2.5` (7B / 4.5 GB Q4)** as primary LLM — best balance of intelligence, code ability, and resource usage.

| Model | Params | RAM (Q4) | MMLU | HumanEval |
|---|---|---|---|---|
| **Qwen2.5-7B** ✅ (selected) | 7B | 4.5 GB | **74.2%** | **72.0%** |
| Llama-3.1-8B | 8B | 4.9 GB | 68.4% | 62.0% |
| Mistral-7B | 7B | 4.1 GB | 63.0% | 41.0% |
| Phi-3.5-mini | 3.8B | 2.4 GB | 69.0% | 59.0% |
| Qwen2.5-3B | 3B | 2.0 GB | 65.6% | 55.5% |
| Qwen2.5-14B | 14B | 8.9 GB | 79.7% | 78.0% |
| Qwen2.5-72B | 72B | 45.0 GB | 86.1% | 86.0% |

> Cloud fallback: **Groq API** (`llama-3.1-8b-instant`) — activates automatically when Ollama is unavailable.

> Full comparison: `ai-models/evaluation/local_llm_comparison.json`, `llm_performance_vs_ram.png`

---

## 🛠️ Tech Stack

### Frontend

| Technology | Version | Purpose |
|---|---|---|
| React | 19 | UI framework |
| Vite | 8 | Build tool & dev server |
| TailwindCSS | 4 | Styling |
| Recharts | 3 | Data visualizations |
| Zustand | 5 | Global state management |
| React Router | 7 | Client-side routing |
| TanStack Table | 8 | Advanced data tables |
| jsPDF + html2canvas | — | PDF report generation |
| PapaParse | 5 | CSV parsing |
| Lucide React | — | Icon library |
| react-dropzone | — | File upload drag & drop |
| react-grid-layout | — | Draggable dashboard grid |

### Backend

| Technology | Version | Purpose |
|---|---|---|
| FastAPI | 0.110+ | REST API framework |
| Python | 3.11+ | Runtime |
| SQLAlchemy | 2.0+ | ORM / database layer |
| Pandas | 2.2+ | Data processing |
| NumPy | 1.26+ | Numerical computing |
| HuggingFace Transformers | 4.38+ | DistilBERT inference |
| scikit-learn | 1.4+ | IsolationForest |
| PyTorch | 2.2+ | DistilBERT backend |
| python-jose | — | JWT authentication |
| bcrypt | — | Password hashing |
| Uvicorn | — | ASGI server |
| requests | 2.31+ | Ollama/Groq HTTP client |

### AI Infrastructure

| Component | Technology |
|---|---|
| Primary LLM | Ollama (local) — Qwen2.5 |
| Cloud Fallback | Groq API — llama-3.1-8b-instant |
| Column Labeling | DistilBERT (HuggingFace Transformers) |
| Anomaly Detection | IsolationForest (scikit-learn) |

---

## 📁 Project Structure

```
Xplor/
├── frontend/                        # React 19 + Vite application
│   ├── src/
│   │   ├── pages/                   # 10 full-featured pages
│   │   │   ├── HomePage.jsx             # Dashboard overview & stats
│   │   │   ├── DatasetsPage.jsx         # Upload & manage datasets
│   │   │   ├── CleanPage.jsx            # AI-assisted data cleaning
│   │   │   ├── ExplorePage.jsx          # Interactive data explorer
│   │   │   ├── DashboardPage.jsx        # Auto-generated chart dashboards
│   │   │   ├── ReportsPage.jsx          # PDF report generation
│   │   │   ├── ChatPage.jsx             # NL→Code AI chat interface
│   │   │   ├── SecurityPage.jsx         # Security audit & monitoring
│   │   │   ├── SettingsPage.jsx         # App & AI model settings
│   │   │   └── LoginPage.jsx            # Authentication
│   │   ├── components/layout/       # AppShell, Sidebar, Navbar
│   │   ├── store/                   # Zustand auth & app state
│   │   ├── api/                     # Axios API client helpers
│   │   └── utils/                   # Utility functions
│   └── package.json
│
├── backend/                         # FastAPI application
│   ├── main.py                      # App entry point, router registration
│   ├── app/
│   │   ├── api/                     # Route handlers
│   │   │   ├── auth.py                  # Login, register, JWT
│   │   │   ├── datasets.py              # Upload, list, delete
│   │   │   ├── clean.py                 # AI cleaning suggestions & ops
│   │   │   ├── explore.py               # Column stats, filters, pivot
│   │   │   ├── dashboards.py            # AI dashboard widget suggestions
│   │   │   ├── reports.py               # Report generation
│   │   │   ├── chat.py                  # NL question answering
│   │   │   └── security.py              # Security status & audit logs
│   │   ├── services/
│   │   │   ├── chat_service.py          # Ollama + Groq LLM orchestration
│   │   │   ├── ml_service.py            # DistilBERT + IsolationForest
│   │   │   ├── data_service.py          # Pandas data operations
│   │   │   └── agent_service.py         # AI agent utilities
│   │   ├── models/                  # SQLAlchemy ORM models
│   │   ├── core/                    # DB engine, config
│   │   └── dependencies/            # FastAPI dependency injection
│   └── requirements.txt
│
├── ai-models/                       # ML training notebooks & evaluation
│   ├── notebooks/
│   │   ├── 01_column_labeling_distilbert.ipynb
│   │   └── 02_anomaly_detection_isolation_forest.ipynb
│   ├── evaluation/                  # Results, plots, JSON metrics
│   │   ├── distilbert_results.json
│   │   ├── isolation_forest_results.json
│   │   ├── local_llm_comparison.json
│   │   └── *.png                        # All evaluation plots
│   ├── models/distilbert-col-labeling/  # Fine-tuned checkpoint
│   └── data/                        # Training datasets
│
├── security/                        # Security module (Python package)
│   ├── auth/
│   │   ├── jwt_handler.py           # JWT creation & verification
│   │   ├── password_hashing.py      # bcrypt helpers
│   │   └── rbac.py                  # Admin / Analyst / Viewer roles
│   ├── encryption/
│   │   ├── aes.py                   # AES-256 file encryption at rest
│   │   └── tls_config.py            # TLS 1.3 setup
│   ├── guards/
│   │   ├── prompt_injection.py      # LLM input sanitization
│   │   ├── sanitization.py          # Data sanitization utilities
│   │   ├── file_upload_guard.py     # MIME + content validation
│   │   ├── audit_logger.py          # AI decision audit trail
│   │   ├── dataset_scanner.py       # Dataset content scanning
│   │   ├── dataset_validator.py     # Schema validation
│   │   ├── security_monitor.py      # Real-time threat monitoring
│   │   └── quarantine_manager.py    # Quarantine for flagged uploads
│   └── tests/test_security.py
│
├── docs/                            # Additional documentation
├── data/                            # Shared / sample data
├── report/                          # Project report files
├── start-backend.ps1                # One-click backend launcher (Windows)
├── start-frontend.ps1               # One-click frontend launcher (Windows)
├── CONTRIBUTING.md
├── SECURITY.md
└── README.md
```

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ and npm
- [Ollama](https://ollama.com) (optional, for local LLM) — or a [Groq API key](https://console.groq.com) (free tier, no credit card)

### 1. Clone the Repository

```bash
git clone https://github.com/Adil-Ds/Xplor.git
cd Xplor
```

### 2. Backend Setup

```bash
cd backend

# Create and activate virtual environment
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # Linux/Mac

# Install dependencies
pip install -r requirements.txt

# Configure environment variables
cp .env.example .env
# Edit .env — set GROQ_API_KEY (optional), OLLAMA_MODEL, etc.

# Start the server
uvicorn main:app --reload --port 8001
```

Backend will be available at: `http://localhost:8001`
Swagger docs: `http://localhost:8001/docs`

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Configure environment
cp .env.example .env
# Set VITE_API_URL=http://localhost:8001

# Start dev server
npm run dev
```

Frontend will be available at: `http://localhost:5173`

### 4. (Optional) Start Ollama for Local LLM

```bash
# Install Ollama from https://ollama.com
ollama serve
ollama pull qwen2.5
```

### Windows One-Click Start

```powershell
# Start backend
.\start-backend.ps1

# Start frontend (separate terminal)
.\start-frontend.ps1
```

---

## 🔌 API Endpoints

All endpoints require JWT authentication (via `Authorization: Bearer <token>` header).

| Method | Path | Description |
|---|---|---|
| `POST` | `/auth/login` | User login, returns JWT |
| `POST` | `/auth/register` | New user registration |
| `GET` | `/datasets` | List all uploaded datasets |
| `POST` | `/datasets/upload` | Upload a new dataset (CSV/Excel/Parquet) |
| `DELETE` | `/datasets/{id}` | Delete a dataset |
| `GET` | `/clean/{id}/suggestions` | Get AI cleaning suggestions |
| `POST` | `/clean/{id}/apply` | Apply a cleaning operation |
| `GET` | `/explore/{id}/stats` | Column statistics |
| `GET` | `/explore/{id}/data` | Paginated data with filters |
| `GET` | `/dashboards/{id}/widgets` | AI-suggested dashboard widgets |
| `GET` | `/reports/{id}` | Generate / fetch report |
| `POST` | `/chat/{id}/ask` | Natural language query → code → result |
| `GET` | `/security/audit-log` | View security audit log |
| `GET` | `/health` | Health check |
| `GET` | `/models/status` | AI model status (Ollama + Groq + ML) |
| `GET` | `/security/status` | Security module status |

---

## 🔒 Security Architecture

Xplor implements a multi-layer security architecture:

| Layer | Implementation |
|---|---|
| **Authentication** | JWT tokens (python-jose) with bcrypt password hashing |
| **Authorization** | RBAC — Admin / Analyst / Viewer roles |
| **MFA** | Firebase TOTP multi-factor authentication |
| **Encryption at Rest** | AES-256 for stored datasets |
| **Encryption in Transit** | TLS 1.3 |
| **Prompt Injection Guard** | Input sanitization + hardening before any LLM call |
| **File Upload Validation** | MIME type verification + content scanning + quarantine |
| **Audit Logging** | Every AI decision logged with timestamp, user, and reasoning |
| **Security Monitoring** | Real-time threat monitoring dashboard |

---

## 🔁 LLM Provider Cascade

```
User Query
    |
    v
[Ollama running?] --YES--> Qwen2.5 (local, private, free)
    |
   NO
    |
    v
[GROQ_API_KEY set?] --YES--> Groq Cloud (llama-3.1-8b-instant)
    |
   NO
    |
    v
Error: "Start Ollama or configure GROQ_API_KEY"
```

---

## 👥 Team

| Name | ID | Role | Responsibilities |
|---|---|---|---|
| **Muhammad Adil** | DS-27 | AI Models Lead | DistilBERT fine-tuning, IsolationForest, LLM selection & benchmarking |
| **Muaz Islam** | DS-23 | Backend Lead | FastAPI design, chat service, Ollama/Groq integration, data APIs |
| **Muhammad Arslan** | DS-15 | Security Lead | JWT/RBAC, AES-256, prompt injection guard, audit logger, file scanning |
| **Sharjeel Anjum** | DS-04 | Frontend Lead | React 19, all 10 pages, Recharts dashboards, PDF export, Zustand store |

---

## 🔀 Branch Strategy

| Branch | Purpose |
|---|---|
| `main` | Production-ready, protected |
| `dev` | Integration branch |
| `feature/ai-models` | AI model training & evaluation |
| `feature/backend` | FastAPI backend development |
| `feature/frontend` | React frontend development |
| `feature/security` | Security module development |

---

## 📚 References

- [Qwen2.5 Model Family](https://huggingface.co/Qwen/Qwen2.5-7B-Instruct)
- [DistilBERT-MNLI (typeform)](https://huggingface.co/typeform/distilbert-base-uncased-mnli)
- [IsolationForest — scikit-learn](https://scikit-learn.org/stable/modules/generated/sklearn.ensemble.IsolationForest.html)
- [KDD Cup 1999 Dataset](http://kdd.ics.uci.edu/databases/kddcup99/kddcup99.html)
- [Ollama](https://ollama.com) | [Groq](https://console.groq.com) | [FastAPI](https://fastapi.tiangolo.com)

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
