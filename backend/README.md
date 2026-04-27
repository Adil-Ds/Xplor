# Backend — FastAPI

## Owner: Laiba Shahid (DS-17)

## Structure

```
backend/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── api/
│   │   ├── routes/
│   │   │   ├── upload.py    # File upload endpoints
│   │   │   ├── analysis.py  # Analysis endpoints
│   │   │   ├── auth.py      # Auth & MFA endpoints
│   │   │   └── query.py     # NL query endpoints
│   │   └── dependencies.py  # Shared FastAPI deps
│   ├── core/
│   │   ├── config.py        # Settings (reads .env)
│   │   ├── security.py      # AES-256, TLS helpers
│   │   └── firebase.py      # Firebase Admin SDK
│   ├── models/              # Pydantic request/response schemas
│   ├── services/            # Business logic layer
│   └── utils/               # Helpers
├── tests/                   # Pytest unit tests
├── requirements.txt
└── .env.example             # Template — copy to .env locally
```

## Setup

```bash
pip install -r requirements.txt
cp .env.example .env          # Fill in your keys
uvicorn app.main:app --reload
```
