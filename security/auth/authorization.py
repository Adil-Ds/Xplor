# ─────────────────────────────────────────────────────────────────────────────
# auth/authorization.py
#
# Authorization Engine — Policy Enforcement Layer
#
# WHAT THIS MODULE DOES:
#   This is the TOP of the RBAC stack. It combines:
#     - JWT role extraction  (from token_validator.py)
#     - Permission checking  (from permission_manager.py)
#     - Audit logging        (from AuditLogger)
#     - Exception raising    (from authorization_exceptions.py)
#
# AUTHORIZATION vs AUTHENTICATION:
#   Authentication (JWT system) answers: "WHO are you?"
#   Authorization  (this module)  answers: "WHAT can you do?"
#
#   Example:
#     authenticate_user("arslan", password) → JWT token (WHO you are)
#     authorize(token, "delete_dataset")    → PermissionDeniedError (WHAT you can't do)
#
# PUBLIC API:
#
#   Full pipeline (JWT → role → permission check):
#     authorize(token, permission) → AuthorizationResult
#     authorize_or_raise(token, permission) → identity dict
#
#   Role-only check (already-extracted role):
#     has_permission(role, permission) → bool
#     authorize_role(role, permission) → AuthorizationResult
#
#   Decorator / helper factory:
#     require_permission(permission) → callable guard
#     require_role(role)             → callable guard
#     protect_resource(resource, permission) → callable guard
#
#   JWT helpers:
#     extract_role_from_token(token) → str
#     authorize_from_token(token, permission) → AuthorizationResult
#
# AUTHORIZATION RESULT:
#   All authorize_* functions return an AuthorizationResult dataclass:
#   {
#     "granted"    : True/False,
#     "role"       : "analyst",
#     "permission" : "analyze_data",
#     "username"   : "arslan",
#     "reason"     : ""  (empty = granted, message = denied reason)
#   }
#
# Used by:
#   auth/__init__.py  — re-exported to application
#   tests/test_rbac.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional, Callable, Any

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.permission_manager import get_permission_manager, PermissionManager
from auth.authorization_exceptions import (
    AuthorizationError, PermissionDeniedError, InvalidRoleError, ResourceProtectedError,
)
from configs.security_settings import AuthConfig, EventType

# ── Audit logger integration ──────────────────────────────────────────────────

try:
    from guards.audit_logger import get_audit_logger
    _audit = get_audit_logger()
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
    _audit     = None


def _log_authz_event(message: str, severity: str = "INFO") -> None:
    """Log an authorization event to AuditLogger or stdlib logging."""
    if _HAS_AUDIT and _audit is not None:
        try:
            _audit.log_system_event(message, severity=severity, module_name="RBAC")
        except Exception:
            pass
    else:
        level = getattr(logging, severity, logging.INFO)
        logging.getLogger("security.rbac").log(level, message)


# ── JWT imports (optional — allows authorization.py to work standalone) ───────

try:
    from auth.token_validator import validate_token, get_user_identity
    from auth.auth_exceptions import TokenExpiredError, InvalidTokenError
    _HAS_JWT = True
except ImportError:
    _HAS_JWT = False


# ══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION RESULT
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class AuthorizationResult:
    """
    Structured result of a permission check.

    Every authorize_* function returns this — callers can inspect it
    rather than catching exceptions for expected denials.

    Fields
    ------
    granted    : bool — True if the action is allowed
    role       : str  — the role that was checked
    permission : str  — the permission that was requested
    username   : str  — the username from the JWT (empty if no token used)
    reason     : str  — denial reason (empty if granted)
    user_id    : int  — user_id from JWT (0 if no token used)

    Example
    -------
    result = authorize_role("analyst", "delete_dataset")
    if result.granted:
        perform_deletion()
    else:
        log(f"Denied: {result.reason}")
    """
    granted    : bool = False
    role       : str  = ""
    permission : str  = ""
    username   : str  = ""
    reason     : str  = ""
    user_id    : int  = 0

    def __bool__(self) -> bool:
        """Allow 'if result:' as shorthand for 'if result.granted:'."""
        return self.granted

    def to_dict(self) -> dict:
        """Serialize to a plain dict for logging or API responses."""
        return {
            "granted"    : self.granted,
            "role"       : self.role,
            "permission" : self.permission,
            "username"   : self.username,
            "user_id"    : self.user_id,
            "reason"     : self.reason,
        }


# ══════════════════════════════════════════════════════════════════════════════
# AUTHORIZATION ENGINE
# ══════════════════════════════════════════════════════════════════════════════

class AuthorizationEngine:
    """
    Core authorization decision engine.

    Combines PermissionManager (what a role can do) with audit logging
    and structured result objects. Raises exceptions for unauthorized
    access or returns AuthorizationResult for callers that prefer
    conditional branching over exception handling.

    Attributes
    ----------
    _pm : PermissionManager — the underlying permission checker

    Example
    -------
    >>> engine = AuthorizationEngine()
    >>> result = engine.authorize_role("analyst", "analyze_data")
    >>> result.granted
    True
    >>> engine.authorize_or_raise("viewer_token_string", "delete_dataset")
    # raises PermissionDeniedError
    """

    def __init__(self, permission_manager: PermissionManager = None):
        self._pm = permission_manager or get_permission_manager()

    # ── Role-based checks (no JWT needed) ────────────────────────────────────

    def has_permission(self, role: str, permission: str) -> bool:
        """
        Simple True/False permission check for a role.

        No logging, no exceptions for denied permissions.
        Raises only for invalid roles.

        Parameters
        ----------
        role       : str — the role name
        permission : str — the permission to check

        Returns
        -------
        bool — True if the role has the permission

        Raises
        ------
        InvalidRoleError — if the role is not recognized

        Example
        -------
        >>> engine.has_permission("admin", "manage_users")
        True
        >>> engine.has_permission("viewer", "delete_dataset")
        False
        """
        return self._pm.has_permission(role, permission)

    def authorize_role(
        self,
        role       : str,
        permission : str,
        username   : str = "",
        resource   : str = "",
    ) -> AuthorizationResult:
        """
        Check if a role has a permission, log the result, return AuthorizationResult.

        Use this when you have a role string (not a JWT token).
        Logs both granted and denied results to the audit trail.

        Parameters
        ----------
        role       : str — the role to check (e.g. "analyst")
        permission : str — the permission requested (e.g. "delete_dataset")
        username   : str, optional — user's name (for audit log)
        resource   : str, optional — resource being accessed (for audit log)

        Returns
        -------
        AuthorizationResult — with granted=True/False and reason

        Raises
        ------
        InvalidRoleError — if the role is not a recognized platform role

        Example
        -------
        >>> result = engine.authorize_role("analyst", "upload_dataset", username="arslan")
        >>> result.granted
        True
        >>> result = engine.authorize_role("viewer", "delete_dataset", username="bob")
        >>> result.granted
        False
        >>> result.reason
        "Role 'viewer' does not have permission to 'delete_dataset'"
        """
        try:
            granted = self._pm.has_permission(role, permission)
        except InvalidRoleError as exc:
            _log_authz_event(
                f"INVALID ROLE: user='{username}' presented unknown role='{role}' "
                f"while trying '{permission}' — possible token tampering",
                severity="CRITICAL",
            )
            raise

        if granted:
            _log_authz_event(
                f"GRANTED: user='{username}' role='{role}' → '{permission}'"
                + (f" on '{resource}'" if resource else ""),
                severity="INFO",
            )
            return AuthorizationResult(
                granted=True, role=role, permission=permission,
                username=username,
            )
        else:
            reason = (
                f"Role '{role}' does not have permission to '{permission}'"
                + (f" on '{resource}'" if resource else "")
            )
            _log_authz_event(
                f"DENIED: user='{username}' role='{role}' → '{permission}'"
                + (f" on '{resource}'" if resource else "")
                + " — permission not granted",
                severity="WARNING",
            )
            return AuthorizationResult(
                granted=False, role=role, permission=permission,
                username=username, reason=reason,
            )

    def authorize(
        self,
        role       : str,
        permission : str,
        username   : str = "",
        resource   : str = "",
    ) -> AuthorizationResult:
        """
        Alias for authorize_role(). Provided for cleaner API surface.

        Parameters match authorize_role() exactly.
        """
        return self.authorize_role(role, permission, username=username, resource=resource)

    def authorize_or_raise(
        self,
        role       : str,
        permission : str,
        username   : str = "",
        resource   : str = "",
    ) -> AuthorizationResult:
        """
        Check permission and RAISE PermissionDeniedError if denied.

        Use this in route handlers where you want exceptions rather than
        conditional branching. The exception is automatically logged.

        Parameters
        ----------
        role       : str — the role to check
        permission : str — the required permission
        username   : str, optional — for audit logging
        resource   : str, optional — for error messages and audit logging

        Returns
        -------
        AuthorizationResult — only returned if access is GRANTED

        Raises
        ------
        PermissionDeniedError — if the role does not have the permission
        InvalidRoleError      — if the role is not recognized

        Example
        -------
        >>> engine.authorize_or_raise("analyst", "delete_dataset", username="arslan")
        # raises PermissionDeniedError

        >>> result = engine.authorize_or_raise("admin", "delete_dataset", username="admin_user")
        >>> result.granted
        True
        """
        result = self.authorize_role(role, permission, username=username, resource=resource)
        if not result.granted:
            raise PermissionDeniedError(
                role=role, action=permission, resource=resource
            )
        return result

    # ── JWT-integrated checks ─────────────────────────────────────────────────

    def extract_role_from_token(
        self,
        token  : str,
        secret : Optional[str] = None,
    ) -> tuple:
        """
        Validate a JWT token and extract the role + identity claims.

        Parameters
        ----------
        token  : str — the JWT string
        secret : str, optional — signing secret (for tests)

        Returns
        -------
        tuple[str, str, int] — (role, username, user_id)

        Raises
        ------
        ImportError       — if JWT system is not installed
        TokenExpiredError — if token has expired
        InvalidTokenError — if token is invalid
        InvalidRoleError  — if the token's role claim is not a known role
        """
        if not _HAS_JWT:
            raise ImportError(
                "JWT support requires the auth.token_validator module. "
                "Ensure jwt_handler.py and token_validator.py are present."
            )

        identity = get_user_identity(token, secret=secret)
        role     = identity["role"]
        username = identity["username"]
        user_id  = identity["user_id"]

        # Validate that the role claim is a known platform role
        self._pm._rm.validate_role(role)

        return role, username, user_id

    def authorize_from_token(
        self,
        token      : str,
        permission : str,
        resource   : str = "",
        secret     : Optional[str] = None,
    ) -> AuthorizationResult:
        """
        Full pipeline: validate JWT → extract role → check permission → log.

        This is the COMPLETE authorization check for API route handlers.
        One call does everything.

        Steps:
            1. Validate JWT signature and expiry
            2. Extract role, username, user_id from claims
            3. Validate the role exists in roles.json
            4. Check whether the role has the requested permission
            5. Log the result
            6. Return AuthorizationResult

        Parameters
        ----------
        token      : str — the JWT string (may include "Bearer " prefix)
        permission : str — the required permission
        resource   : str, optional — resource name for error messages
        secret     : str, optional — JWT signing secret (for tests)

        Returns
        -------
        AuthorizationResult — with granted, role, username, user_id, reason

        Raises
        ------
        TokenExpiredError    — if the JWT is expired
        InvalidTokenError    — if the JWT is invalid
        InvalidRoleError     — if the JWT's role is not a platform role
        PermissionDeniedError — not raised here — check result.granted

        Example
        -------
        >>> result = engine.authorize_from_token(
        ...     token="Bearer eyJ...",
        ...     permission="analyze_data",
        ...     resource="dataset_42",
        ... )
        >>> if result:
        ...     process_dataset()
        ... else:
        ...     return {"error": "Access denied"}, 403
        """
        role, username, user_id = self.extract_role_from_token(token, secret=secret)

        result = self.authorize_role(
            role, permission, username=username, resource=resource
        )
        result.user_id = user_id
        return result

    def authorize_from_token_or_raise(
        self,
        token      : str,
        permission : str,
        resource   : str = "",
        secret     : Optional[str] = None,
    ) -> AuthorizationResult:
        """
        Full pipeline with exception on denial.

        Same as authorize_from_token() but raises PermissionDeniedError
        if access is denied instead of returning a result with granted=False.

        Use this in strict route handlers that treat any denial as an error.

        Parameters match authorize_from_token() exactly.

        Raises
        ------
        TokenExpiredError     — JWT expired
        InvalidTokenError     — JWT invalid
        InvalidRoleError      — bad role in JWT
        PermissionDeniedError — permission not granted
        """
        result = self.authorize_from_token(token, permission, resource=resource, secret=secret)
        if not result.granted:
            raise PermissionDeniedError(
                role=result.role, action=permission, resource=resource
            )
        return result

    # ── Resource protection ───────────────────────────────────────────────────

    def protect_resource(
        self,
        resource      : str,
        required_role : str,
        actual_role   : str,
        username      : str = "",
    ) -> AuthorizationResult:
        """
        Protect a named resource by minimum required role.

        Uses the role hierarchy from AuthConfig: admin > analyst > viewer.
        A user with a role at or above the required level gets access.

        Parameters
        ----------
        resource      : str — the resource name (for logging)
        required_role : str — minimum role needed ("admin", "analyst", "viewer")
        actual_role   : str — the user's actual role from their JWT
        username      : str, optional — for audit logging

        Returns
        -------
        AuthorizationResult — granted if actual_role ≥ required_role

        Raises
        ------
        InvalidRoleError      — if either role is not recognized
        ResourceProtectedError — if access is denied

        Example
        -------
        >>> engine.protect_resource("admin_panel", "admin", "analyst", username="arslan")
        # raises ResourceProtectedError
        """
        # Validate both roles
        self._pm._rm.validate_role(required_role)
        self._pm._rm.validate_role(actual_role)

        required_level = AuthConfig.ROLE_HIERARCHY.get(required_role, 0)
        actual_level   = AuthConfig.ROLE_HIERARCHY.get(actual_role, 0)

        granted = actual_level >= required_level

        if granted:
            _log_authz_event(
                f"RESOURCE ACCESS GRANTED: user='{username}' role='{actual_role}' "
                f"→ '{resource}' (requires '{required_role}')",
                severity="INFO",
            )
            return AuthorizationResult(
                granted=True, role=actual_role, permission=f"access:{resource}",
                username=username,
            )
        else:
            _log_authz_event(
                f"RESOURCE ACCESS DENIED: user='{username}' role='{actual_role}' "
                f"→ '{resource}' (requires '{required_role}')",
                severity="WARNING",
            )
            raise ResourceProtectedError(
                resource=resource,
                role=actual_role,
                required_role=required_role,
            )


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON + CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

_engine_instance: Optional[AuthorizationEngine] = None


def get_authorization_engine() -> AuthorizationEngine:
    """Return the module-level singleton AuthorizationEngine."""
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = AuthorizationEngine()
    return _engine_instance


def authorize(role: str, permission: str, username: str = "", resource: str = "") -> AuthorizationResult:
    """Module-level: authorize_role() on the singleton engine."""
    return get_authorization_engine().authorize_role(role, permission, username=username, resource=resource)


def authorize_or_raise(role: str, permission: str, username: str = "", resource: str = "") -> AuthorizationResult:
    """Module-level: authorize_or_raise() on the singleton engine."""
    return get_authorization_engine().authorize_or_raise(role, permission, username=username, resource=resource)


def has_permission(role: str, permission: str) -> bool:
    """Module-level: simple True/False permission check."""
    return get_authorization_engine().has_permission(role, permission)


def authorize_from_token(token: str, permission: str, resource: str = "", secret: str = None) -> AuthorizationResult:
    """Module-level: full JWT→role→permission pipeline."""
    return get_authorization_engine().authorize_from_token(token, permission, resource=resource, secret=secret)


# ══════════════════════════════════════════════════════════════════════════════
# GUARD FACTORIES (for route-level protection)
# ══════════════════════════════════════════════════════════════════════════════

def require_permission(permission: str, resource: str = "") -> Callable:
    """
    Create a guard function that checks a specific permission for a given role.

    Returns a callable: guard(role, username="") → AuthorizationResult
    Raises PermissionDeniedError if the role lacks the permission.

    Designed for future FastAPI/Flask route decoration patterns.

    Parameters
    ----------
    permission : str — the required permission
    resource   : str, optional — resource name for error messages

    Returns
    -------
    Callable — guard(role, username="") → AuthorizationResult

    Example (future FastAPI pattern)
    -------
    >>> check_export = require_permission("export_reports", resource="reports_api")
    >>> check_export("analyst", username="arslan")  # passes
    >>> check_export("viewer", username="bob")      # raises PermissionDeniedError

    # Future decorator usage:
    >>> @app.get("/export")
    >>> @require_permission("export_reports")
    >>> async def export_route(token: str = Depends(get_token)):
    ...     pass
    """
    engine = get_authorization_engine()

    def guard(role: str, username: str = "") -> AuthorizationResult:
        return engine.authorize_or_raise(
            role, permission, username=username, resource=resource
        )

    guard.__name__ = f"guard_require_{permission}"
    guard.__doc__  = f"Guard: requires '{permission}' permission."
    return guard


def require_role(required_role: str, resource: str = "") -> Callable:
    """
    Create a guard function that enforces a minimum role level.

    Returns a callable: guard(actual_role, username="") → AuthorizationResult
    Uses the role hierarchy: admin ≥ analyst ≥ viewer.
    Raises ResourceProtectedError if the actual_role is below required_role.

    Parameters
    ----------
    required_role : str — minimum role (e.g. "admin", "analyst", "viewer")
    resource      : str, optional — resource name for error messages

    Returns
    -------
    Callable — guard(actual_role, username="") → AuthorizationResult

    Example
    -------
    >>> admin_only = require_role("admin", resource="user_management")
    >>> admin_only("admin", username="superuser")   # passes
    >>> admin_only("analyst", username="arslan")    # raises ResourceProtectedError
    """
    engine = get_authorization_engine()

    def guard(actual_role: str, username: str = "") -> AuthorizationResult:
        return engine.protect_resource(
            resource=resource or f"requires_{required_role}_role",
            required_role=required_role,
            actual_role=actual_role,
            username=username,
        )

    guard.__name__ = f"guard_require_role_{required_role}"
    guard.__doc__  = f"Guard: requires role '{required_role}' or higher."
    return guard


def protect_resource(resource: str, required_permission: str) -> Callable:
    """
    Create a permission-based resource guard.

    Returns a callable: guard(role, username="") → AuthorizationResult
    Raises PermissionDeniedError if the role lacks required_permission.

    Parameters
    ----------
    resource            : str — name of the resource being protected
    required_permission : str — the permission required to access it

    Returns
    -------
    Callable — guard(role, username="") → AuthorizationResult

    Example
    -------
    >>> dataset_guard = protect_resource("datasets", "upload_dataset")
    >>> dataset_guard("analyst", username="arslan")  # passes
    >>> dataset_guard("viewer", username="bob")      # raises PermissionDeniedError
    """
    engine = get_authorization_engine()

    def guard(role: str, username: str = "") -> AuthorizationResult:
        return engine.authorize_or_raise(
            role, required_permission, username=username, resource=resource
        )

    guard.__name__ = f"guard_protect_{resource}"
    guard.__doc__  = f"Guard: requires '{required_permission}' to access '{resource}'."
    return guard


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  AUTHORIZATION ENGINE — SELF TEST")
    print("=" * 60)

    engine = AuthorizationEngine()

    # --- Basic grants ---
    r = engine.authorize_role("admin",   "manage_users",   username="admin_user")
    assert r.granted
    print(f"\n  admin → manage_users : GRANTED ✅")

    r = engine.authorize_role("analyst", "analyze_data",  username="arslan")
    assert r.granted
    print(f"  analyst → analyze_data : GRANTED ✅")

    r = engine.authorize_role("viewer",  "view_reports",  username="viewer_user")
    assert r.granted
    print(f"  viewer → view_reports : GRANTED ✅")

    # --- Denials ---
    r = engine.authorize_role("viewer",  "delete_dataset", username="viewer_user")
    assert not r.granted
    print(f"  viewer → delete_dataset : DENIED ✅  reason='{r.reason[:40]}...'")

    r = engine.authorize_role("analyst", "manage_users",  username="arslan")
    assert not r.granted
    print(f"  analyst → manage_users : DENIED ✅")

    # --- authorize_or_raise ---
    try:
        engine.authorize_or_raise("viewer", "delete_dataset", username="bob")
    except PermissionDeniedError:
        print(f"  authorize_or_raise : PermissionDeniedError raised correctly ✅")

    # --- Invalid role ---
    try:
        engine.authorize_role("hacker", "manage_users")
    except InvalidRoleError:
        print(f"  invalid role : InvalidRoleError raised correctly ✅")

    # --- Guard factories ---
    export_guard = require_permission("export_reports")
    export_guard("analyst", username="arslan")  # should pass
    print(f"  require_permission guard : analyst passes export_reports ✅")

    try:
        export_guard("viewer", username="bob")
    except PermissionDeniedError:
        print(f"  require_permission guard : viewer blocked from export_reports ✅")

    admin_guard = require_role("admin", resource="user_management")
    try:
        admin_guard("analyst", username="arslan")
    except ResourceProtectedError:
        print(f"  require_role guard : analyst blocked from admin resource ✅")

    # --- AuthorizationResult bool ---
    r1 = AuthorizationResult(granted=True)
    r2 = AuthorizationResult(granted=False)
    assert bool(r1) is True
    assert bool(r2) is False
    print(f"  AuthorizationResult bool : granted=True→True, False→False ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
