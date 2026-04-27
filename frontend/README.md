# Frontend — React 18

## Owner: Nabiha Saqib (DS-30)

## Structure

```
frontend/
├── public/
├── src/
│   ├── components/
│   │   ├── Dashboard/       # Live auto-updating dashboard
│   │   ├── GraphBuilder/    # Drag-and-drop Power BI-style charts
│   │   ├── FileUpload/      # Upload & preview component
│   │   ├── NLQuery/         # Natural language query UI
│   │   ├── RiskScore/       # 0-100 risk score display
│   │   └── Auth/            # Login, MFA screens
│   ├── pages/               # Page-level components
│   ├── hooks/               # Custom React hooks
│   ├── services/            # API call functions (axios)
│   ├── store/               # State management
│   └── utils/               # Helpers
├── package.json
└── .env.example
```

## Setup

```bash
npm install
cp .env.example .env.local
npm run dev
```
