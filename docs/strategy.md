# 🚀 Xplor — Master Implementation Strategy
### Google Antigravity Hackathon · Al Seekho Phase II

> **Deadline:** Qualifying Round → May 20 | Finals → June 7
> **Track progress in:** `docs/plan/progress.md`

---

## 🗂️ What We Are Building (6 Additions to Existing Project)

The existing project is ~58% done. Below are the 6 concrete features we must add, in exact implementation order:

---

## PHASE 1 — AI Backend (Days 1–3) 🤖

### Step 1 · Ollama / Qwen 2.5 Chat Agent
**What:** A `/chat/{ds_id}` API endpoint that takes a natural language question from the user and answers it using the actual dataset loaded in memory via Qwen 2.5 running on Ollama.

**Files to create/edit:**
- `backend/app/api/chat.py` ← NEW — chat router
- `backend/app/services/chat_service.py` ← NEW — Ollama call + pandas executor
- `backend/main.py` ← EDIT — register chat router
- `frontend/src/pages/ChatPage.jsx` ← NEW — chat UI
- `frontend/src/pages/ChatPage.css` ← NEW — chat styles
- `frontend/src/App.jsx` ← EDIT — add `/chat/:id` route
- `frontend/src/components/layout/Sidebar.*` ← EDIT — add Chat nav link

**How it works:**
```
User types: "What is the average salary by department?"
→ Backend loads dataset from file
→ Converts NL to pandas code using Qwen 2.5 prompt
→ Executes pandas code safely
→ Returns result as table + plain English summary
```

---

### Step 2 · distilBERT Column Semantic Labeler
**What:** When a dataset is uploaded, auto-call a local distilBERT pipeline to classify what each column *means* (email, phone, name, date, currency, ID, address, etc.). Store labels in DB. Use them to generate smarter cleaning suggestions.

**Files to create/edit:**
- `backend/app/services/ml_service.py` ← NEW — distilBERT + IsolationForest wrappers
- `backend/app/api/datasets.py` ← EDIT — call column labeler after upload
- `backend/app/api/explore.py` ← EDIT — include column labels in suggestions

---

### Step 3 · Isolation Forest Anomaly Detection
**What:** After dataset upload or on the Explore page, run IsolationForest on all numeric columns. Return anomaly scores per row. Highlight anomaly rows in the data table.

**Files to create/edit:**
- `backend/app/services/ml_service.py` ← EDIT — add anomaly detection function
- `backend/app/api/explore.py` ← EDIT — add `/explore/{ds_id}/anomalies` endpoint
- `frontend/src/pages/ExplorePage.jsx` ← EDIT — add anomaly tab

---

## PHASE 2 — Human-in-the-Loop Upgrade (Day 4) 🧑‍💼

### Step 4 · AI-Powered Cleaning Suggestions with Accept/Reject Cards
**What:** Right now cleaning suggestions on ExplorePage are read-only text. Upgrade them so:
1. Suggestions come from the ML model (column labels + null stats + anomalies)
2. Each suggestion is a card with: Impact score, Preview diff, **Accept ✅** / **Reject ❌** buttons
3. Accepting a suggestion auto-adds the corresponding step to the CleanPage recipe

**Files to create/edit:**
- `backend/app/api/explore.py` ← EDIT — richer suggestions with action payloads
- `frontend/src/pages/ExplorePage.jsx` ← EDIT — replace text hints with action cards
- `frontend/src/pages/ExplorePage.css` ← EDIT — card styles

---

## PHASE 3 — Agentic Auto-Pipeline (Day 5) ⚙️

### Step 5 · Upload → Auto-Analyze Agent
**What:** When a dataset is uploaded, automatically trigger the full analysis pipeline in the background:
1. Profile columns
2. Run distilBERT labeling
3. Run IsolationForest
4. Generate ranked cleaning plan
5. Show a "Your dataset is ready — review AI suggestions" notification

**Files to create/edit:**
- `backend/app/api/datasets.py` ← EDIT — trigger analysis pipeline post-upload
- `backend/app/services/agent_service.py` ← NEW — orchestrates the pipeline
- `frontend/src/pages/DatasetsPage.jsx` ← EDIT — show analysis status badge

---

## PHASE 4 — Polish & Integration (Day 6) ✨

### Step 6 · Chat UI + Sidebar + Homepage Update
**What:** Wire everything into the navigation. Add Chat page to sidebar. Update homepage to show "AI-Powered" features. Test full end-to-end flow.

**Files to create/edit:**
- `frontend/src/components/layout/Sidebar.jsx` ← EDIT — add Chat nav item
- `frontend/src/pages/HomePage.jsx` ← EDIT — update feature cards
- `frontend/src/App.jsx` ← EDIT — add chat route
- All new CSS files polished

---

## 🔢 Implementation Order (Execute Exactly in This Sequence)

```
Step 1 → Chat backend (chat.py + chat_service.py)
Step 2 → Chat frontend (ChatPage.jsx)
Step 3 → Wire chat into main.py + App.jsx + Sidebar
Step 4 → ml_service.py (distilBERT column labeler)
Step 5 → ml_service.py (IsolationForest anomaly detection)
Step 6 → Upgrade explore.py suggestions endpoint
Step 7 → Upgrade ExplorePage HITL cards
Step 8 → agent_service.py (auto-pipeline on upload)
Step 9 → Wire agent into datasets.py upload endpoint
Step 10 → Final polish: HomePage + Sidebar + test
```

---

## 📁 New Files to Be Created

| File | Purpose |
|------|---------|
| `backend/app/api/chat.py` | Chat API router |
| `backend/app/services/chat_service.py` | Ollama/Qwen integration |
| `backend/app/services/ml_service.py` | distilBERT + IsolationForest |
| `backend/app/services/agent_service.py` | Auto-pipeline orchestrator |
| `frontend/src/pages/ChatPage.jsx` | Chat UI |
| `frontend/src/pages/ChatPage.css` | Chat styles |
| `docs/plan/progress.md` | Live progress tracker |

---

## 🔧 Existing Files to Be Modified

| File | Change |
|------|--------|
| `backend/main.py` | Register chat router |
| `backend/app/api/datasets.py` | Trigger agent pipeline on upload |
| `backend/app/api/explore.py` | Richer AI suggestions endpoint |
| `frontend/src/App.jsx` | Add `/chat/:id` route |
| `frontend/src/components/layout/Sidebar.jsx` | Add Chat nav link |
| `frontend/src/pages/ExplorePage.jsx` | Accept/Reject suggestion cards + anomaly tab |
| `frontend/src/pages/DatasetsPage.jsx` | Analysis status badge |
| `frontend/src/pages/HomePage.jsx` | Updated AI feature cards |

---

*Strategy last updated: May 11, 2026*
