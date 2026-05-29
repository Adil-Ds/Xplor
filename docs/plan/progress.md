# 📋 Xplor — Live Progress Tracker
> Updated after every implementation step. Read `docs/strategy.md` for the full plan.

---

## ⏱️ Current Status

| Phase | Steps | Done | Status |
|-------|-------|------|--------|
| Phase 1 — AI Backend | 3 steps | 0 | ⏳ Not started |
| Phase 2 — HITL Upgrade | 1 step | 0 | ⏳ Waiting |
| Phase 3 — Agentic Pipeline | 1 step | 0 | ⏳ Waiting |
| Phase 4 — Polish | 1 step | 0 | ⏳ Waiting |
| **TOTAL** | **10 sub-steps** | **0** | **0%** |

---

## ✅ Step-by-Step Checklist

### PHASE 1 — AI Backend

#### Step 1 · Chat Backend (Ollama / Qwen 2.5)
- [ ] Create `backend/app/services/chat_service.py`
  - [ ] Ollama HTTP call to Qwen 2.5
  - [ ] Dataset context loader (column names + sample rows)
  - [ ] Prompt builder (NL question → pandas instruction)
  - [ ] Safe pandas executor with error handling
  - [ ] Plain English result formatter
- [ ] Create `backend/app/api/chat.py`
  - [ ] `POST /chat/{ds_id}` endpoint
  - [ ] Request/response models
  - [ ] Auth dependency
- [ ] Edit `backend/main.py` → register chat router

#### Step 2 · Chat Frontend
- [ ] Create `frontend/src/pages/ChatPage.jsx`
  - [ ] Message thread UI (user + assistant bubbles)
  - [ ] Input box + send button
  - [ ] Dataset context header
  - [ ] Result table renderer (for tabular answers)
  - [ ] Loading / typing indicator
- [ ] Create `frontend/src/pages/ChatPage.css`
- [ ] Edit `frontend/src/App.jsx` → add `/chat/:id` route

#### Step 3 · Wire Chat into Navigation
- [ ] Edit `frontend/src/components/layout/Sidebar.jsx` → Chat nav link
- [ ] Edit `frontend/src/pages/ExplorePage.jsx` → "Ask AI" button → links to ChatPage

#### Step 4 · distilBERT Column Labeler
- [ ] Create `backend/app/services/ml_service.py`
  - [ ] Load HuggingFace distilBERT pipeline (zero-shot classification)
  - [ ] `label_columns(df)` → returns dict of {col: semantic_label}
  - [ ] Labels: email, phone, name, date, currency, id, address, category, numeric, unknown
- [ ] Edit `backend/app/api/datasets.py` → call labeler after upload, store in DB
- [ ] Edit `backend/app/models/models.py` → add `col_labels` JSON field to Dataset

#### Step 5 · Isolation Forest Anomaly Detection
- [ ] Edit `backend/app/services/ml_service.py`
  - [ ] `detect_anomalies(df)` → IsolationForest on numeric cols
  - [ ] Returns row indices + anomaly scores
- [ ] Edit `backend/app/api/explore.py` → add `GET /explore/{ds_id}/anomalies` endpoint
- [ ] Edit `frontend/src/pages/ExplorePage.jsx` → Anomaly tab with highlighted table

---

### PHASE 2 — Human-in-the-Loop

#### Step 6 · AI Suggestion Cards (Accept / Reject)
- [ ] Edit `backend/app/api/explore.py` → `/suggestions` returns structured action payloads
  - [ ] Each suggestion: `{type, column, message, action_op, action_params, impact_score}`
- [ ] Edit `frontend/src/pages/ExplorePage.jsx`
  - [ ] Replace plain text hints with interactive cards
  - [ ] Accept button → calls `POST /clean/{ds_id}/step` to add to recipe
  - [ ] Reject button → dismisses with feedback
  - [ ] Impact score badge (High / Medium / Low)
- [ ] Edit `frontend/src/pages/ExplorePage.css` → card styles

---

### PHASE 3 — Agentic Auto-Pipeline

#### Step 7 · Upload → Auto-Agent
- [ ] Create `backend/app/services/agent_service.py`
  - [ ] `run_post_upload_pipeline(ds_id, db)` async function
  - [ ] Calls: profile → label_columns → detect_anomalies → generate_suggestions
  - [ ] Stores suggestions in DB
- [ ] Edit `backend/app/api/datasets.py` → trigger agent pipeline in background after upload
- [ ] Edit `backend/app/models/models.py` → add `ai_suggestions` JSON + `analysis_status` field
- [ ] Edit `frontend/src/pages/DatasetsPage.jsx`
  - [ ] Show analysis status badge (Analyzing… / Ready / Error)
  - [ ] "View AI Suggestions" button on dataset card

---

### PHASE 4 — Polish & Integration

#### Step 8 · Homepage + Final Wiring
- [ ] Edit `frontend/src/pages/HomePage.jsx` → Update feature cards to reflect AI features
- [ ] Test full end-to-end flow:
  - [ ] Upload CSV → auto-analysis runs → suggestions appear
  - [ ] Accept 3 suggestions → recipe auto-fills → apply cleaning
  - [ ] Chat: "What is the average salary?" → correct answer
  - [ ] Anomaly tab shows highlighted rows
  - [ ] Dashboard auto-suggests chart types
- [ ] Fix any bugs found in testing
- [ ] Record demo video (3 minutes)

---

## 📝 Execution Log

| Step | Date | Status | Notes |
|------|------|--------|-------|
| Project setup / servers running | May 11, 2026 | ✅ Done | Backend :8000, Frontend :3000 |
| Step 1 — Chat backend | — | ⏳ Next | — |
| Step 2 — Chat frontend | — | ⏳ — | — |
| Step 3 — Nav wiring | — | ⏳ — | — |
| Step 4 — distilBERT labeler | — | ⏳ — | — |
| Step 5 — IsolationForest | — | ⏳ — | — |
| Step 6 — HITL cards | — | ⏳ — | — |
| Step 7 — Auto-agent pipeline | — | ⏳ — | — |
| Step 8 — Final polish + test | — | ⏳ — | — |
