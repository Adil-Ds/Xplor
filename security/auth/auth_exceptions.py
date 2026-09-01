# ─────────────────────────────────────────────────────────────────────────────
# auth/auth_exceptions.py
#
# Custom Exception Hierarchy for the JWT Authentication System
#
# WHY CUSTOM EXCEPTIONS?
#   Generic exceptions (ValueError, Exception) give callers no context about
#   WHY something failed. Custom exceptions allow callers to distinguish
#   "wrong password" from "token expired" from "role too low" and handle
#   each case correctly — logging the right severity, returning the right
#   HTTP status code, and presenting the right message to the user.
#
# SECURITY PRINCIPLE:
#   Exception messages are written for DEVELOPERS and AUDIT LOGS.
#   They should NEVER be sent raw to end users (that leaks internals).
#   Use build_error_response() in auth_utils.py to produce user-safe messages.
#
# HIERARCHY:
#   AuthError (base — catch-all for the auth subsystem)
#   ├── InvalidCredentialsError  — wrong username or password at login
#   ├── TokenExpiredError        — JWT exp claim is in the past
#   ├── InvalidTokenError        — bad signature / malformed / missing claims
#   ├── UnauthorizedAccessError  — valid token but role is insufficient
#   ├── WeakSecretError          — JWT_SECRET_KEY too short or not set
#   └── UserNotFoundError        — username not found in the user store
#
# Used by:
#   auth/password_hashing.py  — raises InvalidCredentialsError
#   auth/jwt_handler.py       — raises TokenExpiredError, InvalidTokenError, WeakSecretError
#   auth/token_validator.py   — raises all token-related exceptions
#   auth/auth_utils.py        — raises UnauthorizedAccessError, UserNotFoundError
# ─────────────────────────────────────────────────────────────────────────────


class AuthError(Exception):
    """
    Base exception for all authentication and authorisation failures.

    Catch this if you want to handle any auth-related failure in one place.
    Catch the subclasses if you need to distinguish between specific failure types.

    Attributes
    ----------
    message : str  — human-readable description of the failure
    code    : str  — machine-readable error code for logging / API responses

    Example
    -------
    try:
        validate_token(token)
    except AuthError as e:
        audit.log(f"Auth failure [{e.code}]: {e.message}")
    """

    def __init__(self, message: str = "Authentication error", code: str = "auth_error"):
        self.message = message
        self.code    = code
        super().__init__(message)

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


# ── Credential Failures ───────────────────────────────────────────────────────

class InvalidCredentialsError(AuthError):
    """
    Raised when a user provides an incorrect username or password.

    SECURITY NOTE:
        The message intentionally does NOT specify whether the username
        or the password was wrong. This prevents user enumeration attacks
        where an attacker can discover valid usernames by getting a different
        error for "user not found" vs "wrong password".

    Raised by:
        auth_utils.validate_credentials() — when password doesn't match
        auth_utils.authenticate_user()    — when login fails

    Example:
        raise InvalidCredentialsError()  # generic "invalid credentials"
    """

    def __init__(self, message: str = "Invalid username or password"):
        super().__init__(message=message, code="invalid_credentials")


class UserNotFoundError(AuthError):
    """
    Raised internally when a username does not exist in the user store.

    IMPORTANT: This exception is for INTERNAL USE ONLY.
    It must NEVER be propagated to API responses — callers should convert
    it to InvalidCredentialsError to prevent user enumeration.

    Raised by:
        auth_utils.authenticate_user() — when username lookup fails

    Example:
        raise UserNotFoundError(username="ghost_user")
    """

    def __init__(self, username: str = ""):
        msg = f"User not found: '{username}'" if username else "User not found"
        super().__init__(message=msg, code="user_not_found")
        self.username = username


# ── Token Failures ────────────────────────────────────────────────────────────

class TokenExpiredError(AuthError):
    """
    Raised when a JWT token's expiration time (exp claim) is in the past.

    Token expiry is a critical security control. An expired token means the
    user must re-authenticate — this limits the damage if a token is stolen
    (stolen tokens become useless after expiry).

    Raised by:
        auth/jwt_handler.py  — decode_token() when PyJWT raises ExpiredSignatureError
        auth/token_validator.py — validate_token()

    Example:
        raise TokenExpiredError(expired_at="2026-06-01T10:00:00Z")
    """

    def __init__(self, expired_at: str = ""):
        msg = (
            f"Token expired at {expired_at}. Please log in again."
            if expired_at
            else "Token has expired. Please log in again."
        )
        super().__init__(message=msg, code="token_expired")
        self.expired_at = expired_at


class InvalidTokenError(AuthError):
    """
    Raised when a JWT token fails validation for any reason other than expiry.

    Common causes:
        - Signature verification failure (token was tampered with or wrong secret)
        - Malformed token (not three Base64 segments separated by dots)
        - Missing required claims (user_id, username, role, exp, iat)
        - Wrong algorithm (e.g., token signed with RS256, we expect HS256)
        - Token is None or empty string

    SECURITY NOTE:
        The reason string should be detailed enough for audit logs but must NOT
        be forwarded to API clients — it could help attackers understand what
        makes a valid token.

    Raised by:
        auth/jwt_handler.py  — decode_token()
        auth/token_validator.py — validate_token(), extract_claims()

    Example:
        raise InvalidTokenError(reason="Signature verification failed")
    """

    def __init__(self, reason: str = "Token is invalid or has been tampered with"):
        super().__init__(message=reason, code="invalid_token")
        self.reason = reason


# ── Authorisation Failures ────────────────────────────────────────────────────

class UnauthorizedAccessError(AuthError):
    """
    Raised when a user's token is VALID but their ROLE is insufficient
    to access the requested resource.

    This is a distinct failure from authentication:
        - Authentication: proving WHO you are (login, token verification)
        - Authorisation:  proving you have PERMISSION (role check)

    HTTP mapping:
        InvalidCredentialsError → 401 Unauthorized (authentication failed)
        UnauthorizedAccessError → 403 Forbidden (authenticated but not allowed)

    Raised by:
        auth/token_validator.py — require_role()
        auth/rbac.py            — permission checks

    Example:
        raise UnauthorizedAccessError(
            required_role="admin", actual_role="viewer"
        )
    """

    def __init__(
        self,
        required_role : str = "",
        actual_role   : str = "",
        resource      : str = "",
    ):
        if required_role and actual_role:
            msg = (
                f"Access denied: role '{actual_role}' cannot access "
                f"'{resource or 'this resource'}' (requires '{required_role}' or higher)"
            )
        else:
            msg = "Access denied: insufficient permissions"
        super().__init__(message=msg, code="unauthorized")
        self.required_role = required_role
        self.actual_role   = actual_role
        self.resource      = resource


# ── Configuration Failures ────────────────────────────────────────────────────

class WeakSecretError(AuthError):
    """
    Raised when the JWT_SECRET_KEY is missing, empty, or too short.

    A weak secret key makes it possible to brute-force token signatures.
    We enforce a minimum of 32 characters (AuthConfig.MIN_SECRET_KEY_LENGTH).

    This exception is raised at STARTUP / import time so misconfiguration
    is caught immediately rather than silently producing insecure tokens.

    Raised by:
        auth/jwt_handler.py — _load_secret() on startup

    Example:
        raise WeakSecretError(actual_length=8, required_length=32)
    """

    def __init__(self, actual_length: int = 0, required_length: int = 32):
        if actual_length == 0:
            msg = (
                f"JWT_SECRET_KEY environment variable is not set. "
                f"Set a random secret of at least {required_length} characters."
            )
        else:
            msg = (
                f"JWT_SECRET_KEY is too short: {actual_length} characters. "
                f"Minimum required: {required_length} characters. "
                "Use: python -c \"import secrets; print(secrets.token_hex(32))\""
            )
        super().__init__(message=msg, code="weak_secret")
        self.actual_length   = actual_length
        self.required_length = required_length
