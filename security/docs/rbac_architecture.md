# RBAC Architecture

## Overview

The Xplor RBAC (Role-Based Access Control) System is the authorization layer for the AI analytics platform. It controls **what authenticated users are allowed to do** — distinct from the JWT system which controls **who they are**.

---

## Authentication vs Authorization

```
                  Authentication               Authorization
                  (JWT System)                 (RBAC System)
                       │                            │
Question:         "WHO are you?"             "WHAT can you do?"
                       │                            │
Mechanism:    bcrypt + JWT token            roles.json + permission check
                       │                            │
Failure:       401 Unauthorized              403 Forbidden
                       │                            │
Exception:   InvalidCredentialsError      PermissionDeniedError
             TokenExpiredError            ResourceProtectedError
```

> Authentication must happen BEFORE authorization. A valid JWT is required before RBAC checks are meaningful.

---

## Role Structure

```
                    ADMIN (level 3)
                    ┌───────────────────────────────┐
                    │ manage_users                  │
                    │ upload_dataset                │
                    │ delete_dataset                │
                    │ analyze_data                  │
                    │ export_reports                │
                    │ view_reports                  │
                    │ view_dashboards               │
                    │ view_logs                     │
                    │ manage_roles                  │
                    │ configure_system              │
                    └───────────────────────────────┘
                              ▼ (subset of admin)
                    ANALYST (level 2)
                    ┌───────────────────────────────┐
                    │ upload_dataset                │
                    │ analyze_data                  │
                    │ export_reports                │
                    │ view_reports                  │
                    │ view_dashboards               │
                    └───────────────────────────────┘
                              ▼ (subset of analyst)
                    VIEWER (level 1)
                    ┌───────────────────────────────┐
                    │ view_reports                  │
                    │ view_dashboards               │
                    └───────────────────────────────┘
```

**Least Privilege**: Each role has the minimum permissions required for its function. If an analyst account is compromised, the attacker cannot delete datasets or manage users.

---

## Module Architecture

```
configs/roles.json           ← single source of truth for all permissions
        │
        ▼
auth/rbac.py                 ← RoleManager: loads, caches, validates roles
   RoleManager
        │
        ▼
auth/permission_manager.py   ← PermissionManager: checks, batches, reports
   PermissionManager
        │
        ▼
auth/authorization.py        ← AuthorizationEngine: policy + logging + guards
   AuthorizationEngine
        │
        ├── authorize_role(role, permission)
        ├── authorize_or_raise(role, permission)
        ├── authorize_from_token(jwt, permission)
        ├── protect_resource(resource, required_role, actual_role)
        ├── require_permission(permission) → guard factory
        └── require_role(required_role)   → guard factory
```

### Layer Responsibilities

| Module | Layer | Question it answers |
|---|---|---|
| `roles.json` | Data | "What permissions does each role have?" |
| `rbac.py` | Data Access | "Does this role exist? What are its permissions?" |
| `permission_manager.py` | Logic | "Does this role have this specific permission?" |
| `authorization.py` | Policy | "Should this user be allowed? Log it. Raise if not." |
| `authorization_exceptions.py` | Errors | "What kind of failure was this?" |

---

## Complete Authorization Flow

```
API Request arrives
       │
       ▼
1. JWT Validation (auth system)
   validate_token(jwt_string)
       │
       ├── expired → TokenExpiredError → 401
       ├── invalid → InvalidTokenError  → 401
       └── valid   → {user_id, username, role}
                         │
                         ▼
2. Role Extraction
   role = payload["role"]   # e.g. "analyst"
                         │
                         ▼
3. Role Validation (RBAC)
   RoleManager.validate_role(role)
       │
       ├── unknown → InvalidRoleError → 401 (tampered token)
       └── known   → continue
                         │
                         ▼
4. Permission Check
   PermissionManager.has_permission(role, permission)
       │
       ├── False → PermissionDeniedError → 403
       └── True  → continue
                         │
                         ▼
5. Audit Log
   "GRANTED: user='arslan' role='analyst' → 'analyze_data'"
                         │
                         ▼
6. Access Granted → execute the action
```

---

## Dependency Order (import order)

```
authorization_exceptions.py   (no dependencies)
        ↓
rbac.py                        (imports authorization_exceptions)
        ↓
permission_manager.py          (imports rbac)
        ↓
authorization.py               (imports permission_manager + auth JWT system)
```

---

## Guard Factories (Future Route Protection)

The `authorization.py` module provides guard factories designed for FastAPI/Flask route protection:

```python
from auth.authorization import require_permission, require_role, protect_resource

# Create guards (once at module level)
admin_only    = require_role("admin", resource="user_management")
export_access = require_permission("export_reports", resource="reports_api")
dataset_guard = protect_resource("datasets", "upload_dataset")

# Use in route handlers
def delete_user_route(token: str):
    identity = validate_token(token)
    admin_only(identity["role"], username=identity["username"])  # raises if not admin
    # ... safe to proceed

# Future FastAPI pattern:
# @app.post("/datasets/upload")
# @require_permission("upload_dataset")
# async def upload(user = Depends(get_current_user)):
#     ...
```

---

## Exception Hierarchy

```
Exception
└── AuthorizationError  (base — code, message, role, action)
    ├── PermissionDeniedError   → role lacks the permission     → 403
    ├── InvalidRoleError        → role not in platform roles    → 401
    └── ResourceProtectedError  → resource-level block          → 403
```

### When to catch which

```python
try:
    engine.authorize_or_raise(role, permission)

except InvalidRoleError:
    # Token was tampered — log at CRITICAL, return 401
    return {"error": "Session invalid. Please log in again."}, 401

except PermissionDeniedError:
    # Valid user, insufficient role — return 403
    return {"error": "You don't have permission to perform this action."}, 403

except AuthorizationError:
    # Catch-all for any other authorization failure
    return {"error": "Access denied."}, 403
```

---

## Security Properties

| Property | Implementation |
|---|---|
| Least privilege | Each role has only the permissions it needs |
| Central policy | `roles.json` is the single source of truth — no hardcoded permissions |
| Tamper-resistant | `InvalidRoleError` catches unknown roles from modified JWTs |
| Audit trail | Every grant/deny logged via `AuditLogger` |
| No security-by-obscurity | Denied permissions are logged in detail (not hidden from audit) |
| Reload without restart | `RoleManager.reload()` picks up roles.json changes at runtime |

---

## Testing

```bash
cd security
python tests/test_rbac.py  # 223 tests — all passing
```

Total across all auth + rbac tests: **435 tests, all passing**.
