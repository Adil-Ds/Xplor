# Authentication Architecture

## Overview

The Xplor JWT Authentication System provides a secure authentication layer for the AI-powered analytics platform. It protects passwords with bcrypt, issues signed JWT access tokens, validates authenticated requests, enforces role-based access, and integrates with the existing Audit Logging System.

---

## Complete Authentication Flow

```
┌─────────────────────────────────────────────────────────┐
│                    REGISTRATION FLOW                    │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  User submits password                                  │
│         │                                               │
│         ▼                                               │
│  register_user()      ← auth_utils.py                   │
│         │                                               │
│         ▼                                               │
│  is_valid_password_format()  ← password_hashing.py      │
│         │                                               │
│         ▼                                               │
│  hash_password()  →  $2b$12$<salt><hash>                │
│         │                                               │
│         ▼                                               │
│  Store in database  ← caller's responsibility           │
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                      LOGIN FLOW                         │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  User submits username + password                       │
│         │                                               │
│         ▼                                               │
│  authenticate_user()   ← auth_utils.py                  │
│         │                                               │
│         ├── validate_credentials()  (empty? too long?)  │
│         │                                               │
│         ├── verify_password(plain, stored_hash)         │
│         │        │                                      │
│         │        ├── True  → continue                   │
│         │        └── False → InvalidCredentialsError    │
│         │                                               │
│         ├── generate_user_payload(user_id, username, role)
│         │                                               │
│         ├── create_access_token(payload, 30min)         │
│         │        │                                      │
│         │        └── JWT: HEADER.PAYLOAD.SIGNATURE      │
│         │                                               │
│         ├── log_system_event("login_success")  ← audit  │
│         │                                               │
│         └── build_auth_response()                       │
│                  {success: True, access_token: "...",   │
│                   token_type: "bearer", expires_in: 1800}
│                                                         │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│                 PROTECTED REQUEST FLOW                  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  Client sends: Authorization: Bearer <jwt_token>        │
│         │                                               │
│         ▼                                               │
│  validate_request_token(token, required_role="analyst") │
│         │                                               │
│         ├── validate_token(token)                       │
│         │        ├── Strip "Bearer " prefix             │
│         │        ├── decode_token()                     │
│         │        │    ├── Verify HMAC-SHA256 signature   │
│         │        │    ├── Check exp claim (not expired)  │
│         │        │    └── Validate required claims       │
│         │        └── Return verified payload            │
│         │                                               │
│         ├── require_role(token, "analyst")              │
│         │        └── Check role hierarchy level         │
│         │                                               │
│         ├── log_system_event("token_validated")         │
│         │                                               │
│         └── Return {user_id, username, role}            │
│                                                         │
└─────────────────────────────────────────────────────────┘
```

---

## Module Responsibilities

| Module | Responsibility | Should callers use it? |
|---|---|---|
| `auth_exceptions.py` | Custom exception hierarchy | Import exceptions |
| `password_hashing.py` | bcrypt hash + verify | Tests and internals only |
| `jwt_handler.py` | JWT create + decode + verify | Tests and internals only |
| `token_validator.py` | Validation pipeline + role enforcement | Middleware |
| `auth_utils.py` | **Main application API** — full flows | **YES — use this** |
| `auth/__init__.py` | Clean public exports | Import from `auth` package |

### Golden Rule
> Application code calls `authenticate_user()` and `validate_request_token()` from `auth_utils.py`. Never call `jwt_handler.py` or `password_hashing.py` directly from API handlers.

---

## Exception Hierarchy

```
Exception
└── AuthError  (base — catch-all for auth failures)
    ├── InvalidCredentialsError  → wrong username or password at login
    ├── TokenExpiredError        → JWT exp claim is in the past
    ├── InvalidTokenError        → bad signature / malformed / missing claims
    ├── UnauthorizedAccessError  → valid token but role is insufficient
    ├── WeakSecretError          → JWT_SECRET_KEY too short or not set
    └── UserNotFoundError        → username not found (internal use only)
```

### HTTP Status Code Mapping

| Exception | HTTP Status | Meaning |
|---|---|---|
| `InvalidCredentialsError` | 401 | Authentication failed |
| `TokenExpiredError` | 401 | Session expired — re-login required |
| `InvalidTokenError` | 401 | Token is invalid/tampered |
| `UnauthorizedAccessError` | 403 | Authenticated but not permitted |
| `WeakSecretError` | 500 | Server misconfiguration |

---

## Authentication vs Authorisation

| Concept | Question | Implementation |
|---|---|---|
| **Authentication** | WHO are you? | `authenticate_user()` → bcrypt + JWT |
| **Authorisation** | WHAT can you do? | `require_role()` → role hierarchy |

These are intentionally separate steps. A valid token proves identity (authentication). The role claim inside the token determines what resources can be accessed (authorisation).

---

## Role Hierarchy

```
admin   (level 3) ─── full platform access
    │
    └── analyst (level 2) ─── analytics + viewer access
            │
            └── viewer (level 1) ─── read-only access
```

`require_role(token, "analyst")` passes for `admin` and `analyst`, but blocks `viewer`.

---

## Security Properties

| Property | Implementation |
|---|---|
| Passwords never stored in plaintext | bcrypt — one-way hash, cannot reverse |
| Passwords are salted | bcrypt auto-generates a unique salt per hash |
| Tokens are signed | HMAC-SHA256 — any modification invalidates the token |
| Tokens expire automatically | JWT `exp` claim — rejected after 30 minutes |
| Secrets are validated | `WeakSecretError` raised if secret < 32 chars |
| Timing-safe comparison | `bcrypt.checkpw()` — no timing side-channel |
| User enumeration prevented | `InvalidCredentialsError` for both "wrong user" and "wrong pass" |
| Audit trail | Every login success/failure logged to `AuditLogger` |

---

## Testing

```bash
cd security
python tests/test_password_hashing.py  # 54 tests — bcrypt
python tests/test_jwt.py               # 67 tests — JWT engine
python tests/test_token_validation.py  # 91 tests — validation + full flows
```

Total: **212 tests, all passing**.
