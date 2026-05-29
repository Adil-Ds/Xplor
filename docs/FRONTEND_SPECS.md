# Xplor Platform — Frontend UI/UX Architecture & Requirements

## Project Overview
**Xplor** is a local-first, AI-powered secure data analysis platform. It allows users to upload datasets (CSV, Excel) securely, automatically analyzes them using on-device machine learning models (Qwen 2.5, DistilBERT, IsolationForest), provides AI-driven cleaning suggestions, and enables natural language chatting with data. The core value proposition is **enterprise-grade data intelligence with zero cloud data exfiltration.**

## User Roles
1. **Analyst:** Uploads data, cleans it, chats with it, and builds dashboards.
2. **Admin:** Manages platform settings, user access, and views global security audit logs.

## Main Features
- **Local AI Chat:** Natural language to pandas code generation (powered by local Ollama/Qwen).
- **Auto-Profiling:** Automatic column semantic labeling (e.g., detecting PII, currency, dates).
- **Anomaly Detection:** Automatic identification of outliers in numeric data.
- **Smart Data Cleaning:** 1-click execution of AI-recommended data cleaning steps (impute missing, drop dupes, normalize text).
- **Interactive Dashboards:** Drag-and-drop widget builder for charts and metrics.
- **Secure Architecture:** Everything runs offline/locally.

---

## Pages Required

### 1. Authentication
- **Login / Signup:** Sleek, glassmorphic login form with email/password and an optional SSO button placeholder.

### 2. Main Application (Sidebar Layout)
- **Dashboard (Home):** High-level overview, recent datasets, recent dashboards, and system status (AI models health).
- **Datasets Directory:** Grid/List view of uploaded datasets, size, row count, and analysis status.
- **Dataset Workspace (The Core Workflow)**
  - **Overview Tab:** Data preview table, column metadata, null distributions, AI profiling tags.
  - **Clean Tab:** A side-by-side view. Left: AI suggestions list (e.g., "Drop column X (90% nulls)"). Right: A recipe list showing applied transformations.
  - **Chat Tab:** A ChatGPT-style interface split with a data table/chart view. Users ask questions, AI generates insights or filtered tables.
  - **Explore Tab:** Drag-and-drop charting canvas.
- **Dashboards:** Grid of saved dashboards. Clicking one opens the view mode.
- **Settings / Security:** Model health monitoring (Qwen, DistilBERT statuses), user profile.

---

## Components Required
- **Data Table:** Highly optimized, sticky headers, pagination, column sorting, and custom cell renderers for specific semantic types (e.g., pill badges for 'currency' or 'email').
- **Chat Interface:** Message bubbles (user vs AI), markdown rendering for AI responses, embedded tables/charts inside chat bubbles, typing indicator.
- **AI Suggestion Card:** Contains an icon indicating severity (warning, info), a description ("Age has 15 anomalies"), and a primary action button ("Filter anomalies").
- **Stat Cards:** Clean metrics (e.g., "Total Rows", "Anomalies Found") with sparkline charts.
- **Upload Dropzone:** Dashed border, animated hover state, progress bar with file parsing status.
- **Model Status Indicator:** A pulsing dot (green=ready, yellow=downloading, red=error) with a tooltip showing backend details.

---

## Dashboard Structure (Main App Layout)
- **Left Sidebar:** Collapsible. Contains branding, primary navigation links (Home, Datasets, Dashboards, Settings), and a bottom user profile dropdown.
- **Top Header:** Breadcrumbs (e.g., `Datasets / Q3_Financials.csv / Chat`), Global Search (Cmd+K), and a notification bell.
- **Main Content Area:** Max-width constrained or fluid depending on the view. Soft gray/dark background to make white/dark cards pop.

---

## UI/UX Style
- **Aesthetic:** Modern, futuristic, premium SaaS (inspired by Linear, Vercel, Stripe).
- **Theme:** Default Dark Mode (deep space blues, slate grays) with high-contrast vibrant accents (electric blue, neon purple) for AI elements.
- **Corners:** Rounded (`rounded-xl` or `rounded-2xl` for large cards, `rounded-lg` for buttons).
- **Borders:** Subtle, 1px low-opacity borders on cards (`border-white/10` in dark mode) to create definition without clutter.
- **Shadows:** Soft, diffused shadows for elevation; harsh shadows avoided.
- **Glassmorphism:** Used sparingly for sticky headers or floating action bars (backdrop-blur).

---

## Design System

### Color/Theme Recommendations (Dark Mode Focus)
- **Background:** `zinc-950` (#09090b) or a very deep navy `#0a0a0f`.
- **Card/Surface:** `zinc-900` (#18181b) or `#13131a`.
- **Primary Accent (AI Magic):** A gradient from Indigo-500 to Purple-500.
- **Secondary Accent:** Electric Cyan or Teal for success/ready states.
- **Text:** Primary: `zinc-50` (white), Secondary: `zinc-400` (muted gray).
- **Semantic:** Error (Rose-500), Warning (Amber-500), Success (Emerald-500).

### Typography Recommendations
- **Primary Font:** `Inter`, `Geist`, or `Plus Jakarta Sans`. Clean, geometric sans-serif.
- **Monospace (for data/code):** `JetBrains Mono` or `Fira Code`.
- **Hierarchy:**
  - H1: Semi-bold, tight tracking (e.g., `-tracking-tight`).
  - Body: Regular weight, relaxed line height.
  - Labels: Uppercase, extra small, wide tracking (e.g., `text-xs uppercase tracking-wider text-muted-foreground`).

---

## Animations
- **Page Transitions:** Gentle fade-in and slight slide-up (`translate-y-2` to `translate-y-0`).
- **Hover States:** Cards lift slightly (`-translate-y-1`) with an intensified shadow or border glow.
- **Chat:** New messages slide up and fade in. "AI Thinking" shows a subtle pulsing gradient skeleton or typing dots.
- **Micro-interactions:** Buttons scale down slightly on click (`active:scale-95`).

---

## Responsive Design Requirements
- **Desktop (1024px+):** Full sidebar, complex data tables with many columns visible, side-by-side chat and data views.
- **Tablet (768px - 1023px):** Sidebar collapses to icons only. Data tables allow horizontal scrolling.
- **Mobile (<768px):** Sidebar becomes a bottom navigation bar or hamburger menu. Data tables convert to stacked card views or strict horizontal scroll. Chat takes full screen.

---

## Suggested React Component Structure
```
src/
├── components/
│   ├── layout/
│   │   ├── Sidebar.jsx
│   │   ├── Topbar.jsx
│   │   └── AppShell.jsx
│   ├── ui/               # shadcn/ui generic components
│   │   ├── button.jsx
│   │   ├── card.jsx
│   │   ├── table.jsx
│   │   └── badge.jsx
│   └── domain/           # Specific to Xplor
│       ├── dataset/
│       │   ├── DataPreviewTable.jsx
│       │   ├── ColumnProfiler.jsx
│       │   └── CleaningRecipe.jsx
│       ├── chat/
│       │   ├── ChatInterface.jsx
│       │   ├── MessageBubble.jsx
│       │   └── CodeExecutor.jsx
│       └── shared/
│           ├── AISuggestionCard.jsx
│           └── ModelStatusBadge.jsx
```

---

## Tailwind Styling Guidelines
- Use CSS variables for colors to allow easy theming (shadcn/ui style): `bg-background`, `text-foreground`, `bg-primary`, `text-primary-foreground`.
- Utilize `backdrop-blur-md bg-background/80` for sticky headers.
- Use `ring-offset-background focus-visible:ring-2 focus-visible:ring-ring` for accessible focus states.
- For AI gradients: `bg-gradient-to-r from-indigo-500 via-purple-500 to-pink-500 bg-clip-text text-transparent`.

---

## 🤖 AI Prompt for Stitch/V0/Lovable/Bolt

**Copy and paste the prompt below into your chosen AI frontend builder:**

> "Act as a world-class UI engineer. Build a modern, premium SaaS frontend for 'Xplor', a local-first AI data analysis platform. The aesthetic must be heavily inspired by Linear, Vercel, and OpenAI — dark mode by default, deep zinc backgrounds, glassmorphism, subtle 1px borders, and glowing indigo/purple gradients for AI elements.
> 
> Use React, Tailwind CSS, Framer Motion, and shadcn/ui components. Use Lucide React for icons.
> 
> **Build the 'Dataset Workspace' view. It needs:**
> 
> 1.  **Layout:** A collapsible left sidebar with navigation icons. A top header with breadcrumbs and a pulsing 'AI Models Ready' green dot.
> 2.  **Main Content Area:** A tabbed interface with tabs: Overview, Clean, Chat, Explore.
> 3.  **Active Tab - 'Chat':** 
>     - **Left Panel (Chat):** A ChatGPT-style chat interface. Show a user message asking "Find anomalies in Q3 revenue" and an AI response explaining the findings. The chat input should look sleek with an inner shadow and a submit icon.
>     - **Right Panel (Data Context):** A beautifully styled data table showing a snippet of financial data. The table headers should be sticky and have small pill badges next to column names (e.g., 'Revenue' has a 'Currency' badge, 'Date' has a 'Date' badge).
> 
> Ensure the typography uses Inter with tight letter spacing for headings. Add subtle hover micro-interactions to buttons and table rows using Framer motion or Tailwind transitions. Make it look like an expensive, enterprise-grade application."

---

## Advanced UI Enhancements (For Later)
- **Command Menu (Cmd+K):** Implement a global search palette (like Raycast) to quickly jump to datasets or trigger AI commands.
- **Skeleton Loaders:** Instead of spinners, use pulsing skeletons matching the layout of the data table or cards while the backend runs pandas operations.
- **Confetti/Delight:** A subtle animation when a complex dataset is successfully cleaned and ready for analysis.
- **Resizable Panels:** Use `react-resizable-panels` to let users drag the width between the Chat interface and the Data Table.
