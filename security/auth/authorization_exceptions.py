# ─────────────────────────────────────────────────────────────────────────────
# auth/authorization_exceptions.py
#
# Custom Exception Hierarchy for the RBAC Authorization System
#
# WHY SEPARATE EXCEPTIONS?
#   The JWT auth system already has AuthError and its subclasses for
#   authentication failures (wrong password, expired token, etc.).
#   Authorization failures are conceptually different:
#     Authentication → WHO are you?   (identity)
#     Authorization  → WHAT can you do? (permission)
#
#   Separate exceptions mean callers can distinguish:
#     - InvalidCredentialsError  (auth failure → 401)
#     - PermissionDeniedError    (authz failure → 403)
#
# HIERARCHY:
#   AuthorizationError (base)
#   ├── PermissionDeniedError  — role doesn't have the requested permission
#   ├── InvalidRoleError       — role string is not in the platform's role set
#   └── ResourceProtectedError — resource requires a permission the user lacks
#
# HTTP Status Code Mapping:
#   PermissionDeniedError   → 403 Forbidden
#   InvalidRoleError        → 401 Unauthorized (token claims an unknown role)
#   ResourceProtectedError  → 403 Forbidden
#
# Used by:
#   auth/rbac.py               — raises InvalidRoleError
#   auth/permission_manager.py — raises InvalidRoleError on bad role
#   auth/authorization.py      — raises PermissionDeniedError, ResourceProtectedError
#   tests/test_rbac.py
# ─────────────────────────────────────────────────────────────────────────────


class AuthorizationError(Exception):
    """
    Base exception for all RBAC authorization failures.

    Catch this to handle any authorization failure in one place.
    Catch subclasses to distinguish specific failure types.

    Attributes
    ----------
    message : str — human-readable description of the failure
    code    : str — machine-readable error code for logging / API responses
    role    : str — the role involved in the failure (may be empty)
    action  : str — the action that was attempted (may be empty)

    Example
    -------
    try:
        authorize(role, permission)
    except AuthorizationError as e:
        audit.log(f"Authorization failure [{e.code}]: {e.message}")
        return {"error": "Access denied"}, 403
    """

    def __init__(
        self,
        message : str = "Authorization error",
        code    : str = "authorization_error",
        role    : str = "",
        action  : str = "",
    ):
        self.message = message
        self.code    = code
        self.role    = role
        self.action  = action
        super().__init__(message)

    def __str__(self) -> str:
        parts = [f"[{self.code}] {self.message}"]
        if self.role:
            parts.append(f"role='{self.role}'")
        if self.action:
            parts.append(f"action='{self.action}'")
        return "  ".join(parts)


# ── Permission Failures ───────────────────────────────────────────────────────

class PermissionDeniedError(AuthorizationError):
    """
    Raised when a role does not have the requested permission.

    This is the most common authorization failure. The user is authenticated
    (their token is valid) but their role does not grant the requested action.

    SECURITY NOTE:
        Do NOT reveal exactly which permissions the role IS missing in
        the user-facing message. That could help attackers understand what
        they need to escalate to. Log the details internally but return
        a generic "Access denied" to the client.

    HTTP mapping: 403 Forbidden

    Raised by:
        auth/authorization.py — authorize(), require_permission()

    Example
    -------
    >>> raise PermissionDeniedError(
    ...     role="viewer",
    ...     action="delete_dataset",
    ...     resource="datasets/revenue_q4.csv"
    ... )
    """

    def __init__(
        self,
        role     : str = "",
        action   : str = "",
        resource : str = "",
    ):
        if role and action:
            msg = (
                f"Role '{role}' does not have permission to '{action}'"
                + (f" on '{resource}'" if resource else "")
                + ". This action has been logged."
            )
        else:
            msg = "Permission denied. This action has been logged."

        super().__init__(
            message = msg,
            code    = "permission_denied",
            role    = role,
            action  = action,
        )
        self.resource = resource


class ResourceProtectedError(AuthorizationError):
    """
    Raised when a resource is protected and the user's role cannot access it
    at all — regardless of the specific action.

    Used when the resource itself (a route, a file category, an admin panel)
    is completely off-limits for a role. More specific than PermissionDeniedError
    because it describes a resource-level block, not just a permission-level block.

    HTTP mapping: 403 Forbidden

    Raised by:
        auth/authorization.py — protect_resource()

    Example
    -------
    >>> raise ResourceProtectedError(
    ...     resource="admin_panel",
    ...     role="analyst",
    ...     required_role="admin"
    ... )
    """

    def __init__(
        self,
        resource      : str = "",
        role          : str = "",
        required_role : str = "",
    ):
        if resource and role:
            req_str = f" (requires role '{required_role}')" if required_role else ""
            msg = (
                f"Resource '{resource}' is protected and cannot be accessed "
                f"by role '{role}'{req_str}."
            )
        else:
            msg = "This resource is protected and cannot be accessed with your current role."

        super().__init__(
            message = msg,
            code    = "resource_protected",
            role    = role,
            action  = f"access:{resource}",
        )
        self.resource      = resource
        self.required_role = required_role


# ── Role Failures ─────────────────────────────────────────────────────────────

class InvalidRoleError(AuthorizationError):
    """
    Raised when a role string is not in the platform's defined role set.

    If a JWT token contains a role claim that is not in {"admin", "analyst", "viewer"},
    this exception is raised. This could indicate:
        - A token was crafted by an attacker with a fake role
        - A user's role was deleted from the system while they were logged in
        - A bug in the token generation code used an incorrect role value

    SECURITY NOTE:
        Tokens with invalid roles should be treated as invalid/tampered.
        This exception should trigger a CRITICAL-level audit log entry.

    HTTP mapping: 401 Unauthorized (the identity claim is invalid)

    Raised by:
        auth/rbac.py — validate_role()
        auth/permission_manager.py — get_permissions()

    Example
    -------
    >>> raise InvalidRoleError(role="superadmin")
    """

    def __init__(self, role: str = "", valid_roles: set = None):
        valid_str = (
            f" Valid roles are: {sorted(valid_roles)}" if valid_roles else ""
        )
        msg = (
            f"Role '{role}' is not a recognized platform role.{valid_str} "
            "This may indicate a tampered token."
            if role
            else "An unrecognized role was presented."
        )
        super().__init__(
            message = msg,
            code    = "invalid_role",
            role    = role,
        )
        self.valid_roles = valid_roles or set()
