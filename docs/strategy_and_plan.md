# 🗺️ Xplor — Hackathon Strategy & Implementation Plan
### Google Antigravity Hackathon · Al Seekho Phase II

---

## ⏰ Critical Timeline

| Milestone | Date | Days Left | Action Required |
|-----------|------|-----------|----------------|
| **Register NOW** | May 11, 2026 | **TODAY** | Go to https://linktr.ee/gdglivepakistan |
| Shortlisting announced | May 13, 2026 | 2 days | Wait for confirmation |
| Qualifying Round deadline | May 20, 2026 | 9 days | Submit working prototype + video |
| Final round announcement | May 29, 2026 | 18 days | Prepare full demo |
| Final round deadline | June 5, 2026 | 25 days | Polish + stress test |
| **Final Pitching — Islamabad** | June 7, 2026 | 27 days | Live pitch to judges |

> [!CAUTION]
> Registration closes **TODAY (May 11)**. This is the most urgent action.

---

## 🔍 Honest Project Critique (Critical Assessment)

### What's Strong ✅
1. **Real problem** — Data engineering automation is a legitimate, high-value market
2. **Working backend** — FastAPI running, authentication, file upload, cleaning recipe engine all functional
3. **Working frontend** — Clean UI, dashboard builder, explore page, clean page all exist
4. **Human-in-the-loop** — Recipe-based cleaning with preview is conceptually excellent and judges will love it
5. **Local-first security** — Unique differentiator vs cloud-only tools
6. **Multi-format support** — CSV, XLSX, JSON, Parquet already handled

### Critical Weaknesses ❌
1. **NO AGENTIC AI YET** — The biggest weakness. Currently it's a manual tool with suggestions, not an AI agent. The hackathon evaluates "Agentic Reasoning" at 20% weight. You must build actual agents.
2. **No LLM/Chat interface** — There is no chatbot, no natural language querying. This is a core promised feature.
3. **No local model integration** — distilBERT, T5-small, XGBoost models from ai-models/ folder are not integrated into the pipeline yet
4. **No database connector** — Can only upload files; cannot connect to PostgreSQL/MySQL databases
5. **Cleaning suggestions are rule-based** — Not AI-generated. The "AI suggestions" are simple null percentage thresholds
6. **No Antigravity integration** — Must use Google Antigravity framework for the hackathon
7. **Dashboard not drag-and-drop** — Widgets exist but layout is fixed grid, not truly PowerBI-like
8. **No audit log visible to user** — Transformations applied but not shown as history trail

---

## 📋 Implementation Status

### ✅ FULLY IMPLEMENTED (60%)

#### Data Ingestion & Management
- [x] File upload (CSV, XLSX, JSON, Parquet)
- [x] File parsing with Pandas
- [x] Dataset metadata storage (SQLAlchemy)
- [x] Dataset listing, deletion
- [x] Preview (first 200 rows)

#### Data Cleaning
- [x] 12 cleaning operations (drop nulls, fill nulls, drop duplicates, rename, drop column, cast type, trim, lowercase, uppercase, find/replace, filter rows, parse date)
- [x] Recipe builder UI (add/remove/reset steps)
- [x] Live in-browser preview of cleaned data
- [x] Export cleaned CSV
- [x] Apply recipe to stored dataset

#### Data Exploration (EDA)
- [x] Column profiling (dtype, nulls, unique, min/max/mean/std)
- [x] Distribution analysis (histogram for numeric, bar for categorical)
- [x] Correlation matrix (Pearson)
- [x] Rule-based quality suggestions
- [x] Outlier detection (IQR method)
- [x] Raw data viewer with pagination
- [x] Query builder (filter + group by + aggregate)

#### Dashboard Builder
- [x] Bar, Line, Area, Pie, Scatter charts
- [x] KPI cards, Data tables, Text blocks
- [x] Widget configuration panel
- [x] Multiple dashboards management
- [x] PDF export

#### Infrastructure
- [x] JWT authentication (login/register)
- [x] FastAPI backend with CORS
- [x] SQLAlchemy + SQLite
- [x] Uvicorn hot-reload
- [x] React + Vite frontend running

---

### 🔨 NEEDS TO BE BUILT — Priority Order (40%)

#### P0 — CRITICAL (Must have for qualifying round, May 20)

- [ ] **Google Antigravity Integration** — Wrap the cleaning and analysis pipeline as Antigravity agents
  - Convert `CleanAgent`, `ExploreAgent`, `InsightAgent` into proper Antigravity agent definitions
  - Implement agent-to-agent handoff (Ingest → Clean → Analyze → Insight)
  - Add agent reasoning trace visible to user ("Agent is analyzing column 'age'...")

- [ ] **AI-Powered Cleaning Suggestions** — Replace rule-based hints with model-driven ones
  - Integrate `Isolation Forest` for statistical anomaly detection
  - Use `distilBERT` to classify column semantics (is this a phone number? an email? a date?)
  - Rank suggestions by estimated data quality impact score

- [ ] **Natural Language Chat Agent**
  - Simple NL query → pandas operation pipeline
  - "What is the average age?" → df['age'].mean()
  - "Show me top 10 rows by salary" → df.sort_values('salary').tail(10)
  - Use T5-small or rule-based NL parser (faster to implement)

#### P1 — HIGH (Must have for final round, June 5)

- [ ] **Human-in-the-Loop Upgrade** — Make every AI suggestion a visible accept/reject card
  - Each cleaning suggestion: shows expected impact, row count diff, column preview
  - Batch approve / reject all
  - Edit suggestion parameters before accepting

- [ ] **Database Connector**
  - Connect to PostgreSQL / MySQL via connection string
  - Preview tables, select table to load
  - Support SQL query to load custom result set

- [ ] **Insight Narrative Generator**
  - After EDA completes, generate 3–5 key plain-English insights
  - "Your dataset has 23% missing values in the 'income' column — recommend imputing with median"
  - Use T5-small locally or template-based generation

- [ ] **Audit Log / Transformation History**
  - Show every accepted/rejected suggestion with timestamp and user
  - Downloadable as CSV audit trail

#### P2 — MEDIUM (Nice to have for pitch polish)

- [ ] **Drag-and-drop Dashboard Layout** — True PowerBI-style free positioning of widgets
- [ ] **Urdu Language Support** — At least for the chat agent output
- [ ] **Multi-dataset joins** — Agent detects common key columns and proposes merge
- [ ] **Scheduled reports** — Auto-refresh dashboard on a schedule

---

## 🗓️ Day-by-Day Execution Plan

### NOW — May 11 (Day 0)
- [ ] **Register for the hackathon** at https://linktr.ee/gdglivepakistan
- [ ] Confirm team (2–5 members, aged 18–45, Pakistan residents)
- [ ] Set up team group chat / collaboration

### May 12–14 (3 days) — Antigravity Integration Sprint
- [ ] Read Google Antigravity documentation and examples
- [ ] Create `backend/app/agents/` directory
- [ ] Implement `CleanAgent` as Antigravity agent
- [ ] Implement `AnalyzeAgent` as Antigravity agent
- [ ] Test agent handoff: Ingest → Clean → Analyze

### May 15–17 (3 days) — AI Models Integration Sprint
- [ ] Load distilBERT from `ai-models/` directory
- [ ] Use it to label column semantics (email, phone, date, name, number)
- [ ] Load Isolation Forest model or train on-the-fly per dataset
- [ ] Generate ranked cleaning suggestions from model outputs
- [ ] Replace rule-based hints with model-driven suggestions

### May 18–19 (2 days) — Chat Agent + Human-in-the-Loop Upgrade
- [ ] Build NL query parser → pandas executor pipeline
- [ ] Create chat UI component in frontend
- [ ] Upgrade suggestion cards to accept/reject/modify UI
- [ ] Show before/after diff for each suggestion

### May 20 (Day 9) — Qualifying Round Submission
- [ ] Record 3-minute demo video (screen recording)
- [ ] Write qualifying round submission text
- [ ] Submit before midnight

### May 21–28 — Polish & Test
- [ ] Database connector (PostgreSQL)
- [ ] Insight narrative generator
- [ ] Audit log
- [ ] Bug fixes from qualifying round feedback
- [ ] Performance testing with large datasets (100k+ rows)

### May 29–June 5 — Finals Preparation
- [ ] Drag-and-drop dashboard
- [ ] Practice pitch (3 slides max + live demo)
- [ ] Prepare answers to tough judge questions
- [ ] Stress test entire pipeline end-to-end

### June 6 — Travel to Islamabad
- [ ] Claim travel logistics support from organizers

### June 7 — FINAL PITCH DAY 🏆

---

## 🎯 Winning Strategy

### What Judges Care About Most
Based on the scoring rubric:
1. **(25%) Antigravity** — Make sure every AI operation goes through the Antigravity framework. Don't just use it as a label.
2. **(20%) Agentic Reasoning** — Show the agent's "thinking" — display its reasoning trace in the UI ("Agent detected 3 issues, proposing 2 cleaning steps...")
3. **(20%) Problem Understanding** — Lead the pitch with Pakistan-specific data: "80% of Pakistan's 200,000 SMEs cannot afford data analysts"

### Demo Strategy (7 Minutes Max)
1. **Minute 1**: Upload a messy real-world dataset (hospital records or sales data)
2. **Minute 2**: AI agent scans and proposes 5 cleaning steps — user approves 4, rejects 1 with explanation
3. **Minute 3**: Explore page auto-generates distribution charts and surfaces key insight
4. **Minute 4**: Chat agent answers "What's the average revenue by region?"
5. **Minute 5**: Dashboard auto-suggests 3 charts — user adds them with one click
6. **Minute 6**: Export PDF report — "This is what a data analyst would take 3 days to build. We did it in 5 minutes."
7. **Minute 7**: Q&A

### Differentiators to Emphasize
- **ONLY tool in Pakistan** that runs fully local (privacy-first)
- **Human-in-the-loop** — not black-box AI, but collaborative intelligence
- **No subscription** — runs on your own hardware
- **Built for Pakistan** — designed for hospitals, government, SMEs, not Silicon Valley enterprises

---

## ⚠️ Risk Register

| Risk | Probability | Impact | Mitigation |
|------|------------|--------|-----------|
| Antigravity integration takes too long | High | Critical | Spend days 12–14 entirely on this; have fallback of wrapping existing code minimally |
| Local models too slow on demo hardware | Medium | High | Use smaller models; cache results; demo on pre-loaded dataset |
| Chat agent gives wrong answers | High | High | Restrict to pandas operations only; no LLM hallucination surface |
| Team not shortlisted | Low | Critical | Submit registration today; ensure proposal is strong |
| Network issues at venue | Medium | Medium | Run everything offline; no cloud dependencies |

---

*Strategy document: May 11, 2026 | Xplor Team*
