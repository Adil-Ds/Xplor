# ─────────────────────────────────────────────────────────────────────────────
# auth/auth_utils.py
#
# Authentication Utilities and High-Level Auth Orchestrator
#
# This module is the MAIN ENTRY POINT for application code performing
# authentication operations. It combines:
#   - password_hashing.py   — hashing and verification
#   - jwt_handler.py        — token creation and decoding
#   - token_validator.py    — validation and role enforcement
#   - AuditLogger           — automatic security event logging
#
# DESIGN PRINCIPLE:
#   Application code (API handlers, middleware) should call this module.
#   It should NOT call password_hashing.py or jwt_handler.py directly.
#   This keeps authentication logic in one place and ensures audit events
#   are never accidentally omitted.
#
# KEY FUNCTIONS:
#
#   authenticate_user(username, stored_hash, password)
#       → Complete login flow: verify password → create token → log result
#       → Returns AuthResponse dict or raises InvalidCredentialsError
#
#   validate_request_token(token, required_role)
#       → Complete request validation: validate → role check → return identity
#       → Returns identity dict or raises InvalidTokenError / UnauthorizedAccessError
#
#   generate_user_payload(user_id, username, role) → dict
#       → Build a correctly-structured token payload
#
#   build_auth_response(token, expires_in) → dict
#       → Standard success response shape for login endpoints
#
#   build_error_response(message) → dict
#       → Standard failure response shape (user-safe message)
#
# Public API (full list):
#   authenticate_user()         — full login flow
#   validate_request_token()    — full request validation
#   register_user()             — hash password for new user
#   logout_user()               — log logout event
#   generate_user_payload()     — build token payload dict
#   get_current_timestamp()     — UTC Unix timestamp
#   validate_credentials()      — basic field validation
#   build_auth_response()       — success response dict
#   build_error_response()      — failure response dict
#   get_user_role()             — extract role from token
#   get_user_identity()         — extract identity from token
#
# Used by:
#   Application API handlers (future Xplor backend)
#   tests/test_token_validation.py  — integration scenarios
# ─────────────────────────────────────────────────────────────────────────────

import sys
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import AuthConfig, EventType
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class AuthConfig:
        TOKEN_EXPIRATION_MINUTES = 30
        MAX_USERNAME_LENGTH      = 64
        MAX_PASSWORD_LENGTH      = 128
        VALID_ROLES              = {"admin", "analyst", "viewer"}

    class EventType:
        LOGIN_SUCCESS    = "login_success"
        LOGIN_FAILED     = "login_failed"
        TOKEN_GENERATED  = "token_generated"
        TOKEN_EXPIRED    = "token_expired"
        TOKEN_INVALID    = "token_invalid"
        UNAUTHORIZED     = "unauthorized_access"
        LOGOUT           = "logout"
        PASSWORD_CHANGED = "password_changed"

# ── Local auth imports ────────────────────────────────────────────────────────

from auth.password_hashing import hash_password, verify_password, is_valid_password_format
from auth.jwt_handler import create_access_token, decode_token, verify_token
from auth.token_validator import (
    validate_token, require_role, extract_claims,
    get_user_role as _get_user_role,
    get_user_identity as _get_user_identity,
)
from auth.auth_exceptions import (
    InvalidCredentialsError, TokenExpiredError, InvalidTokenError,
    UnauthorizedAccessError, UserNotFoundError, AuthError,
)

# ── Audit logger integration ──────────────────────────────────────────────────

try:
    from guards.audit_logger import get_audit_logger
    _audit = get_audit_logger()
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
    _audit     = None


def _log_auth_event(message: str, severity: str = "INFO") -> None:
    """Log an auth event to AuditLogger if available, otherwise fall back to stdlib logging."""
    if _HAS_AUDIT and _audit is not None:
        try:
            _audit.log_system_event(message, severity=severity, module_name="Auth")
        except Exception:
            pass
    else:
        level = getattr(logging, severity, logging.INFO)
        logging.getLogger("security.auth").log(level, message)


# ══════════════════════════════════════════════════════════════════════════════
# TIMESTAMP UTILITY
# ══════════════════════════════════════════════════════════════════════════════

def get_current_timestamp() -> int:
    """
    Return the current UTC time as a Unix timestamp (integer seconds since epoch).

    Used in audit log entries and auth response metadata.

    Returns
    -------
    int — seconds since 1970-01-01T00:00:00Z

    Example
    -------
    >>> ts = get_current_timestamp()
    >>> type(ts)
    <class 'int'>
    """
    return int(datetime.now(timezone.utc).timestamp())


# ══════════════════════════════════════════════════════════════════════════════
# PAYLOAD BUILDER
# ══════════════════════════════════════════════════════════════════════════════

def generate_user_payload(
    user_id  : int,
    username : str,
    role     : str,
) -> dict:
    """
    Build a correctly-structured JWT payload for a given user.

    Use this instead of constructing the dict manually to ensure all
    required fields are present and validated before token creation.

    The iat and exp fields are NOT added here — jwt_handler.create_access_token()
    adds them automatically at signing time.

    Parameters
    ----------
    user_id  : int — unique user identifier from your database
    username : str — the user's login name (included in token for readability)
    role     : str — one of "admin", "analyst", "viewer"

    Returns
    -------
    dict — {"user_id": int, "username": str, "role": str}

    Raises
    ------
    ValueError — if user_id is not a positive integer
    ValueError — if role is not in AuthConfig.VALID_ROLES

    Example
    -------
    >>> payload = generate_user_payload(user_id=42, username="arslan", role="analyst")
    >>> payload
    {"user_id": 42, "username": "arslan", "role": "analyst"}
    """
    if not isinstance(user_id, int) or user_id <= 0:
        raise ValueError(
            f"user_id must be a positive integer, got {user_id!r}. "
            "Use the integer primary key from your user database table."
        )
    if not isinstance(username, str) or not username.strip():
        raise ValueError("username must be a non-empty string")
    if role not in AuthConfig.VALID_ROLES:
        raise ValueError(
            f"Invalid role '{role}'. Must be one of: {sorted(AuthConfig.VALID_ROLES)}"
        )
    return {
        "user_id" : user_id,
        "username": username.strip(),
        "role"    : role,
    }


# ══════════════════════════════════════════════════════════════════════════════
# CREDENTIAL VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def validate_credentials(username: str, password: str) -> tuple:
    """
    Perform basic input validation on login credentials before auth logic.

    This catches obviously invalid inputs (empty, too long) before we
    even attempt a database lookup or bcrypt operation.

    Parameters
    ----------
    username : str — the submitted username
    password : str — the submitted password (plaintext, will be verified not stored)

    Returns
    -------
    tuple[bool, str] — (True, "") if inputs are acceptable,
                       (False, reason) if validation fails

    Example
    -------
    >>> validate_credentials("", "password")
    (False, "Username cannot be empty")
    >>> validate_credentials("arslan", "pass")
    (True, "")
    """
    if not isinstance(username, str) or not username.strip():
        return False, "Username cannot be empty"
    if len(username) > AuthConfig.MAX_USERNAME_LENGTH:
        return False, f"Username exceeds maximum length of {AuthConfig.MAX_USERNAME_LENGTH}"
    if not isinstance(password, str) or not password:
        return False, "Password cannot be empty"
    if len(password) > AuthConfig.MAX_PASSWORD_LENGTH:
        return False, f"Password exceeds maximum length of {AuthConfig.MAX_PASSWORD_LENGTH}"
    return True, ""


# ══════════════════════════════════════════════════════════════════════════════
# RESPONSE BUILDERS
# ══════════════════════════════════════════════════════════════════════════════

def build_auth_response(
    token      : str,
    expires_in : int,
    username   : str = "",
    role       : str = "",
) -> dict:
    """
    Build a standard successful authentication response dict.

    This is the shape that login endpoints return to clients.
    Modelled after OAuth2 bearer token responses.

    Parameters
    ----------
    token      : str — the signed JWT access token
    expires_in : int — token lifetime in seconds (e.g. 1800 for 30 minutes)
    username   : str, optional — include username in response for UX
    role       : str, optional — include role in response for UX

    Returns
    -------
    dict — {
        "success"      : True,
        "access_token" : "<jwt_string>",
        "token_type"   : "bearer",
        "expires_in"   : 1800,
        "username"     : "arslan",     (if provided)
        "role"         : "analyst"     (if provided)
    }

    Example
    -------
    >>> response = build_auth_response(token, expires_in=1800, username="arslan", role="analyst")
    """
    response = {
        "success"      : True,
        "access_token" : token,
        "token_type"   : "bearer",
        "expires_in"   : expires_in,
    }
    if username:
        response["username"] = username
    if role:
        response["role"] = role
    return response


def build_error_response(message: str, error_code: str = "") -> dict:
    """
    Build a standard failure response dict for auth errors.

    SECURITY NOTE:
        The message here is for the CLIENT (end user or API consumer).
        It should be generic enough to not reveal internal implementation details.
        Do NOT pass raw exception messages directly — use user-safe strings.

    Parameters
    ----------
    message    : str — user-safe error description
    error_code : str, optional — machine-readable code for the client

    Returns
    -------
    dict — {"success": False, "message": str, "error_code": str (if provided)}

    Example
    -------
    >>> build_error_response("Invalid credentials")
    {"success": False, "message": "Invalid credentials"}

    >>> build_error_response("Session expired", error_code="token_expired")
    {"success": False, "message": "Session expired", "error_code": "token_expired"}
    """
    response = {"success": False, "message": message}
    if error_code:
        response["error_code"] = error_code
    return response


# ══════════════════════════════════════════════════════════════════════════════
# REGISTRATION FLOW
# ══════════════════════════════════════════════════════════════════════════════

def register_user(username: str, plain_password: str) -> dict:
    """
    Hash a password for a new user registration.

    Returns a dict with the hashed password ready to store in the database.
    Does NOT create the user in the database — the caller handles persistence.

    Registration flow:
        1. Validate password format (length, complexity)
        2. Hash with bcrypt (rounds=12)
        3. Return hash + audit log entry
        4. Caller stores hash in database

    Parameters
    ----------
    username       : str — the new user's username (for audit logging only)
    plain_password : str — the new user's chosen password

    Returns
    -------
    dict — {"hashed_password": str, "username": str, "created_at": int}

    Raises
    ------
    ValueError — if password fails format validation

    Example
    -------
    >>> result = register_user("arslan", "SecureP@ss123")
    >>> db.save_user(username="arslan", password_hash=result["hashed_password"])
    """
    ok, reason = is_valid_password_format(plain_password)
    if not ok:
        raise ValueError(f"Password does not meet requirements: {reason}")

    hashed = hash_password(plain_password)

    _log_auth_event(
        f"New user registered: '{username}' — password hashed with bcrypt rounds=12",
        severity="INFO",
    )

    return {
        "hashed_password": hashed,
        "username"       : username,
        "created_at"     : get_current_timestamp(),
    }


# ══════════════════════════════════════════════════════════════════════════════
# AUTHENTICATION (LOGIN) FLOW
# ══════════════════════════════════════════════════════════════════════════════

def authenticate_user(
    username        : str,
    stored_hash     : str,
    plain_password  : str,
    user_id         : int = 0,
    role            : str = "viewer",
    expires_minutes : Optional[int] = None,
    secret          : Optional[str] = None,
) -> dict:
    """
    Execute the complete login authentication flow.

    Steps:
        1. Validate input fields (username/password not empty)
        2. Verify password against stored bcrypt hash
        3. Generate JWT token on success
        4. Log the result (success or failure) to AuditLogger
        5. Return standard auth response dict

    Parameters
    ----------
    username        : str — the login username
    stored_hash     : str — the bcrypt hash retrieved from the database
    plain_password  : str — the submitted plaintext password
    user_id         : int — the database user ID (for token payload)
    role            : str — the user's role (default "viewer")
    expires_minutes : int, optional — token lifetime override
    secret          : str, optional — JWT secret override (for testing)

    Returns
    -------
    dict — successful build_auth_response() output:
           {"success": True, "access_token": "...", "token_type": "bearer",
            "expires_in": 1800, "username": "arslan", "role": "analyst"}

    Raises
    ------
    InvalidCredentialsError — if password does not match the stored hash

    Example
    -------
    >>> # In your API login handler:
    >>> user = db.get_user_by_username(username)
    >>> auth_result = authenticate_user(
    ...     username=username,
    ...     stored_hash=user.password_hash,
    ...     plain_password=request.json["password"],
    ...     user_id=user.id,
    ...     role=user.role,
    ... )
    >>> return auth_result, 200
    """
    exp_mins = expires_minutes or AuthConfig.TOKEN_EXPIRATION_MINUTES

    # --- Step 1: Input validation ---
    ok, reason = validate_credentials(username, plain_password)
    if not ok:
        _log_auth_event(
            f"Login rejected (invalid input): '{username}' — {reason}",
            severity="WARNING",
        )
        raise InvalidCredentialsError()

    # --- Step 2: Password verification ---
    if not verify_password(plain_password, stored_hash):
        _log_auth_event(
            f"Login FAILED: '{username}' — incorrect password",
            severity="CRITICAL",
        )
        raise InvalidCredentialsError()

    # --- Step 3: Token generation ---
    payload = generate_user_payload(user_id=user_id or 1, username=username, role=role)
    token   = create_access_token(payload, expires_minutes=exp_mins, secret=secret)

    # --- Step 4: Audit log success ---
    _log_auth_event(
        f"Login SUCCESS: '{username}' (role='{role}', user_id={user_id}) — "
        f"token issued, expires in {exp_mins} minutes",
        severity="INFO",
    )

    # --- Step 5: Return standard response ---
    return build_auth_response(
        token=token,
        expires_in=exp_mins * 60,
        username=username,
        role=role,
    )


# ══════════════════════════════════════════════════════════════════════════════
# REQUEST VALIDATION FLOW
# ══════════════════════════════════════════════════════════════════════════════

def validate_request_token(
    token         : str,
    required_role : str = "viewer",
    resource      : str = "",
    secret        : Optional[str] = None,
) -> dict:
    """
    Validate an incoming request token and optionally enforce a minimum role.

    This is the function API middleware should call for every protected endpoint.
    It handles the full validation pipeline with integrated audit logging.

    Steps:
        1. Validate token (signature, expiry, claims) via token_validator
        2. Enforce required_role via role hierarchy
        3. Log the result
        4. Return identity dict on success

    Parameters
    ----------
    token         : str — JWT from the Authorization header
    required_role : str — minimum role required (default "viewer")
    resource      : str, optional — resource name for error messages
    secret        : str, optional — JWT secret override (for testing)

    Returns
    -------
    dict — {"user_id": int, "username": str, "role": str}

    Raises
    ------
    InvalidTokenError       — if token is invalid/malformed/wrong-signature
    TokenExpiredError       — if token is expired
    UnauthorizedAccessError — if user's role is insufficient

    Example
    -------
    >>> # In a protected API route:
    >>> identity = validate_request_token(
    ...     token=request.headers["Authorization"].split(" ")[1],
    ...     required_role="analyst",
    ...     resource="analytics_dashboard",
    ... )
    >>> print(f"Request from: {identity['username']}")
    """
    try:
        payload = require_role(
            token, required_role=required_role, resource=resource, secret=secret
        )
        identity = {
            "user_id" : payload["user_id"],
            "username": payload["username"],
            "role"    : payload["role"],
        }
        _log_auth_event(
            f"Token validated: user='{identity['username']}' role='{identity['role']}' "
            f"accessed '{resource or 'resource'}'",
            severity="INFO",
        )
        return identity

    except TokenExpiredError as exc:
        claims = extract_claims(token)
        _log_auth_event(
            f"Token EXPIRED: user='{claims.get('username', 'unknown')}' — {exc.message}",
            severity="WARNING",
        )
        raise

    except UnauthorizedAccessError as exc:
        claims = extract_claims(token)
        _log_auth_event(
            f"UNAUTHORIZED: user='{claims.get('username', 'unknown')}' "
            f"role='{claims.get('role', '?')}' tried to access '{resource}' "
            f"(requires '{exc.required_role}')",
            severity="CRITICAL",
        )
        raise

    except (InvalidTokenError, AuthError) as exc:
        _log_auth_event(
            f"INVALID TOKEN: {exc.message if hasattr(exc, 'message') else str(exc)}",
            severity="CRITICAL",
        )
        raise


# ══════════════════════════════════════════════════════════════════════════════
# LOGOUT
# ══════════════════════════════════════════════════════════════════════════════

def logout_user(token: str, secret: Optional[str] = None) -> dict:
    """
    Log a user logout event.

    NOTE: JWT is stateless — there is no server-side token invalidation
    in this implementation. Logout is achieved by:
        1. Logging the event (for audit trail)
        2. Telling the client to discard the token

    For a production system requiring immediate revocation, you would add
    a token blacklist (Redis set) and check it in validate_token().

    Parameters
    ----------
    token  : str — the JWT being logged out
    secret : str, optional — JWT secret override (for testing)

    Returns
    -------
    dict — {"success": True, "message": "Logged out successfully"}
    """
    claims = extract_claims(token)
    username = claims.get("username", "unknown")

    _log_auth_event(
        f"Logout: user='{username}' token discarded by client",
        severity="INFO",
    )

    return {"success": True, "message": "Logged out successfully"}


# ── Re-export convenience wrappers ────────────────────────────────────────────

def get_user_role(token: str, secret: Optional[str] = None) -> str:
    """Extract the role claim from a validated token. Delegates to token_validator."""
    return _get_user_role(token, secret=secret)


def get_user_identity(token: str, secret: Optional[str] = None) -> dict:
    """Extract identity dict from a validated token. Delegates to token_validator."""
    return _get_user_identity(token, secret=secret)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    print("\n" + "=" * 60)
    print("  AUTH UTILS — SELF TEST")
    print("=" * 60)

    TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
    os.environ["JWT_SECRET_KEY"] = TEST_SECRET

    # --- register_user ---
    reg = register_user("arslan", "SecureP@ss123")
    assert reg["hashed_password"].startswith("$2b$")
    print(f"\n  register_user       : hash={reg['hashed_password'][:20]}...  ✅")

    # --- authenticate_user (success) ---
    stored_hash = reg["hashed_password"]
    auth_resp   = authenticate_user(
        username="arslan", stored_hash=stored_hash,
        plain_password="SecureP@ss123", user_id=42, role="analyst",
        expires_minutes=30, secret=TEST_SECRET,
    )
    assert auth_resp["success"] is True
    assert auth_resp["token_type"] == "bearer"
    assert "access_token" in auth_resp
    print(f"  authenticate_user   : success response correct  ✅")

    # --- authenticate_user (failure) ---
    try:
        authenticate_user(
            username="arslan", stored_hash=stored_hash,
            plain_password="WRONG_PASSWORD", user_id=42, role="analyst",
            secret=TEST_SECRET,
        )
        print("  Wrong password      : ❌ FAIL — accepted wrong password!")
    except InvalidCredentialsError:
        print(f"  Wrong password      : InvalidCredentialsError raised  ✅")

    # --- validate_request_token ---
    token = auth_resp["access_token"]
    identity = validate_request_token(token, required_role="analyst",
                                      resource="dashboard", secret=TEST_SECRET)
    assert identity["username"] == "arslan"
    print(f"  validate_request    : identity={identity}  ✅")

    # --- logout_user ---
    logout = logout_user(token, secret=TEST_SECRET)
    assert logout["success"] is True
    print(f"  logout_user         : '{logout['message']}'  ✅")

    # --- generate_user_payload ---
    p = generate_user_payload(1, "arslan", "analyst")
    assert p == {"user_id": 1, "username": "arslan", "role": "analyst"}
    print(f"  generate_user_payload: {p}  ✅")

    # --- build_auth_response / build_error_response ---
    ok_resp  = build_auth_response("fake.token.here", 1800, "arslan", "analyst")
    err_resp = build_error_response("Invalid credentials", "invalid_credentials")
    assert ok_resp["success"]  is True
    assert err_resp["success"] is False
    print(f"  build_auth_response  : success=True, token_type='{ok_resp['token_type']}'  ✅")
    print(f"  build_error_response : success=False, code='{err_resp['error_code']}'  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
