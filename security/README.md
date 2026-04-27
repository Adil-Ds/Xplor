# Security Module

## Owner: Mahnoor Amir (DS-14)

## Structure

```
security/
├── auth/
│   ├── mfa_config.py        # Firebase TOTP MFA setup
│   └── rbac.py              # Role-Based Access Control (Admin/Analyst/Viewer)
├── encryption/
│   ├── aes.py               # AES-256 file encryption at rest
│   └── tls_config.py        # TLS 1.3 configuration
├── guards/
│   ├── prompt_injection.py  # Input sanitization + LLM guardrails
│   └── audit_logger.py      # AI decision audit logging
├── tests/
│   └── test_security.py
└── README.md
```

## Responsibilities

- MFA + RBAC: Firebase TOTP, three roles (Admin / Analyst / Viewer)
- Encryption: AES-256 at rest, TLS 1.3 in transit
- Prompt Injection Guard: sanitize user inputs before reaching AI
- Audit Logs: log every AI decision with reasoning

## ⚠️ IMPORTANT

Never hardcode secrets. Use environment variables only.
