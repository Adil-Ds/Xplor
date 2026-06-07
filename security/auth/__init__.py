# ─────────────────────────────────────────────────────────────────────────────
# auth/__init__.py
#
# Public API for the Xplor JWT Authentication & Password Security System
# and the RBAC Authorization System.
#
# Application code imports from here:
#   from auth import authenticate_user, validate_request_token
#   from auth import authorize, authorize_or_raise, authorize_from_token
#   from auth import require_permission, require_role_guard
#   from auth import PermissionDeniedError, InvalidRoleError
#
# Architecture reminder:
#   Authentication → auth_utils.py       (WHO are you?)
#   Authorization  → authorization.py    (WHAT can you do?)
# ─────────────────────────────────────────────────────────────────────────────

# ── Auth Exceptions ───────────────────────────────────────────────────────────
from auth.auth_exceptions import (
    AuthError,
    InvalidCredentialsError,
    TokenExpiredError,
    InvalidTokenError,
    UnauthorizedAccessError,
    WeakSecretError,
    UserNotFoundError,
)

# ── Password hashing ──────────────────────────────────────────────────────────
from auth.password_hashing import (
    hash_password,
    verify_password,
    is_valid_password_format,
)

# ── JWT engine ────────────────────────────────────────────────────────────────
from auth.jwt_handler import (
    create_access_token,
    decode_token,
    verify_token,
    get_token_expiry,
)

# ── Token validation ──────────────────────────────────────────────────────────
from auth.token_validator import (
    validate_token,
    is_token_expired,
    extract_claims,
    get_user_role,
    get_user_identity,
)

# ── High-level auth orchestrator (recommended application API) ────────────────
from auth.auth_utils import (
    authenticate_user,
    validate_request_token,
    register_user,
    logout_user,
    generate_user_payload,
    get_current_timestamp,
    validate_credentials,
    build_auth_response,
    build_error_response,
)

# ── RBAC Authorization Exceptions ─────────────────────────────────────────────
from auth.authorization_exceptions import (
    AuthorizationError,
    PermissionDeniedError,
    InvalidRoleError,
    ResourceProtectedError,
)

# ── RBAC Role Manager ─────────────────────────────────────────────────────────
from auth.rbac import (
    RoleManager,
    get_role_manager,
)

# ── RBAC Permission Manager ───────────────────────────────────────────────────
from auth.permission_manager import (
    PermissionManager,
    get_permission_manager,
    has_permission,
    get_permissions,
    check_permissions,
)

# ── RBAC Authorization Engine (recommended RBAC API) ─────────────────────────
from auth.authorization import (
    AuthorizationEngine,
    AuthorizationResult,
    get_authorization_engine,
    authorize,
    authorize_or_raise,
    authorize_from_token,
    require_permission,
    protect_resource,
)

# NOTE: require_role exists in two modules with different purposes:
#   authorization.require_role     → RBAC guard factory  (returns a callable)
#   token_validator.require_role   → JWT role check      (validates token + raises)
# Import directly from the source module to be unambiguous.
from auth.authorization import require_role as require_role_guard
from auth.token_validator import require_role as require_role_jwt


__all__ = [
    # ── Auth Exceptions
    "AuthError", "InvalidCredentialsError", "TokenExpiredError",
    "InvalidTokenError", "UnauthorizedAccessError", "WeakSecretError",
    "UserNotFoundError",
    # ── Password hashing
    "hash_password", "verify_password", "is_valid_password_format",
    # ── JWT engine
    "create_access_token", "decode_token", "verify_token", "get_token_expiry",
    # ── Token validation
    "validate_token", "is_token_expired", "extract_claims",
    "get_user_role", "get_user_identity",
    # ── Auth orchestrator
    "authenticate_user", "validate_request_token", "register_user",
    "logout_user", "generate_user_payload", "get_current_timestamp",
    "validate_credentials", "build_auth_response", "build_error_response",
    # ── RBAC exceptions
    "AuthorizationError", "PermissionDeniedError", "InvalidRoleError",
    "ResourceProtectedError",
    # ── RBAC core
    "RoleManager", "get_role_manager",
    "PermissionManager", "get_permission_manager",
    "has_permission", "get_permissions", "check_permissions",
    # ── RBAC engine
    "AuthorizationEngine", "AuthorizationResult", "get_authorization_engine",
    "authorize", "authorize_or_raise", "authorize_from_token",
    # ── RBAC guards
    "require_permission", "require_role_guard", "protect_resource",
    # ── JWT role guard (different from RBAC guard factory)
    "require_role_jwt",
]
