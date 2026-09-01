# JWT Token Lifecycle

## What is a JWT?

A JSON Web Token (JWT) is a compact, URL-safe string for securely transmitting claims between parties. It does not require the server to store session state — the token itself carries all necessary information and its own proof of integrity.

```
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9
.
eyJ1c2VyX2lkIjo0MiwidXNlcm5hbWUiOiJhcnNsYW4iLCJyb2xlIjoiYW5hbHlzdCIsImlhdCI6MTc...
.
SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c
└──────────────────┘ └────────────────────────────────────────┘ └─────────────────────┘
       HEADER                      PAYLOAD                            SIGNATURE
```

Each segment is **Base64url-encoded** (not encrypted — anyone can decode them). Security comes from the **SIGNATURE**, not obscurity.

---

## JWT Structure

### Header
```json
{
  "alg": "HS256",
  "typ": "JWT"
}
```

- `alg` — Signing algorithm. We use `HS256` (HMAC with SHA-256).
- `typ` — Token type. Always `"JWT"` for JSON Web Tokens.

### Payload (Claims)

```json
{
  "user_id"  : 42,
  "username" : "arslan",
  "role"     : "analyst",
  "iat"      : 1717200000,
  "exp"      : 1717201800
}
```

| Claim | Type | Purpose |
|---|---|---|
| `user_id` | int | Database primary key of the user |
| `username` | str | Human-readable identity (for UX + logs) |
| `role` | str | For RBAC: `"admin"`, `"analyst"`, `"viewer"` |
| `iat` | int | Issued At — UTC Unix timestamp when token was created |
| `exp` | int | Expiration — UTC Unix timestamp when token becomes invalid |

> **Important**: Payload claims are Base64-encoded, NOT encrypted. Never put sensitive data (passwords, full PII, credit cards) in a JWT payload.

### Signature

```
HMAC-SHA256(
  Base64url(header) + "." + Base64url(payload),
  secret_key
)
```

The signature is computed over the header and payload using the server's secret key. Any modification to either the header or payload causes the signature to fail verification — the server knows the token was tampered with.

---

## Token Lifecycle

```
1. USER LOGS IN
   ┌──────────────────────────────────────┐
   │  authenticate_user(username, pwd)    │
   │  → verify password with bcrypt       │
   │  → generate_user_payload()           │
   │  → create_access_token(payload, 30m) │
   │        │                             │
   │        └── sign with JWT_SECRET_KEY  │
   │  → return token string               │
   └──────────────────────────────────────┘

2. CLIENT STORES THE TOKEN
   ┌──────────────────────────────────────┐
   │  Client stores JWT in:               │
   │    localStorage (simple)             │
   │    HttpOnly cookie (more secure)     │
   │    Memory only (most secure)         │
   └──────────────────────────────────────┘

3. CLIENT MAKES AUTHENTICATED REQUEST
   ┌──────────────────────────────────────┐
   │  HTTP Header:                        │
   │  Authorization: Bearer <jwt_token>   │
   └──────────────────────────────────────┘

4. SERVER VALIDATES TOKEN
   ┌──────────────────────────────────────┐
   │  validate_request_token(token)       │
   │    1. Strip "Bearer " prefix         │
   │    2. Verify HMAC-SHA256 signature   │
   │    3. Check exp claim ≤ now          │
   │    4. Verify required claims present │
   │    5. Check role if required         │
   │  → return {user_id, username, role}  │
   └──────────────────────────────────────┘

5. TOKEN EXPIRES
   ┌──────────────────────────────────────┐
   │  After 30 minutes (default):         │
   │  decode_token() → TokenExpiredError  │
   │  → Client must log in again          │
   │  → Old token cannot be renewed       │
   └──────────────────────────────────────┘
```

---

## Signature Verification

The server checks: `HMAC-SHA256(header.payload, secret) == signature`

| Scenario | Signature check | Result |
|---|---|---|
| Original, unmodified token | ✅ Matches | Accepted |
| Payload tampered (changed role) | ❌ Doesn't match | `InvalidTokenError` |
| Header tampered (changed alg) | ❌ Doesn't match | `InvalidTokenError` |
| Token from different server (wrong secret) | ❌ Doesn't match | `InvalidTokenError` |
| Completely fabricated token | ❌ Doesn't match | `InvalidTokenError` |
| Expired token | ✅ Matches | `TokenExpiredError` (signature OK but exp in past) |

---

## Token Expiration Design

Tokens have a short lifetime (30 minutes by default) for security:

```
00:00  Token issued (iat)
  │
  │   User can make authenticated requests
  │
30:00  Token expires (exp)
  │
  │   Token rejected — TokenExpiredError
  │
  ▼   User must log in again for a new token
```

**Why short-lived tokens?**
- If a token is stolen (e.g., XSS attack), it becomes useless after 30 minutes
- No server-side session state to maintain
- Forces regular re-authentication

**Refresh Tokens (not yet implemented):**
Production systems often use a "refresh token" pattern where a long-lived refresh token (7 days) can obtain a new short-lived access token without re-entering a password. This can be added as a future enhancement.

---

## Algorithm Choice: HS256 vs RS256

| Algorithm | Type | Use case |
|---|---|---|
| **HS256** (our choice) | Symmetric — same secret signs and verifies | Single-server API |
| RS256 | Asymmetric — private key signs, public key verifies | Microservices, multiple verifiers |

HS256 is correct here because:
- Single backend server both issues and verifies tokens
- Simpler key management (one secret, not a key pair)
- Equally secure when the secret is strong (≥ 32 chars)

---

## Secret Key Requirements

```python
# Generate a secure secret:
import secrets
print(secrets.token_hex(32))  # 64-char hex string
# → f3a1b7c2d9e4f8a3b6c1d5e7f2a4b8c3d6e1f5a8b2c7d4e9f3a6b1c8d5e2f7
```

| Secret length | Security | Assessment |
|---|---|---|
| < 32 chars | ❌ | `WeakSecretError` — rejected at startup |
| 32 chars | ✅ | Minimum accepted |
| 64 chars (recommended) | ✅✅ | `secrets.token_hex(32)` output |
| Random hex/base64 | ✅✅ | Best — maximum entropy |

---

## Token Format in HTTP

```
GET /api/analytics/reports HTTP/1.1
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ1c2VyX2lkIjo...
```

The `validate_token()` function automatically strips the `Bearer ` prefix, accepting tokens both with and without it.

---

## Audit Events Logged for Tokens

| Event | Severity | When logged |
|---|---|---|
| Login success → token issued | INFO | `authenticate_user()` success |
| Login failure | CRITICAL | `authenticate_user()` failure |
| Token validated | INFO | `validate_request_token()` success |
| Token expired | WARNING | `TokenExpiredError` caught |
| Invalid token | CRITICAL | `InvalidTokenError` caught |
| Unauthorised (role too low) | CRITICAL | `UnauthorizedAccessError` caught |
| Logout | INFO | `logout_user()` called |
