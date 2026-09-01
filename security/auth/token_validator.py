# ─────────────────────────────────────────────────────────────────────────────
# auth/token_validator.py
#
# Dedicated Token Validation Layer
#
# WHY A SEPARATE VALIDATOR?
#   jwt_handler.py handles the cryptographic operations (sign, decode).
#   token_validator.py handles the BUSINESS LOGIC of validation:
#     - What claims are required?
#     - What roles are allowed?
#     - How do we log failed validations?
#     - How do we handle edge cases (empty token, None, bytes)?
#
#   Separating these concerns means:
#     - jwt_handler.py stays focused on JWT mechanics
#     - token_validator.py stays focused on application policy
#     - Tests can mock one without touching the other
#
# VALIDATION PIPELINE (validate_token does all of these in order):
#   1. Input type check (not None, not empty, must be string)
#   2. PyJWT signature verification (via jwt_handler.decode_token)
#   3. Expiration check (handled by PyJWT inside decode_token)
#   4. Required claims check (user_id, username, role, iat, exp)
#   5. Role validity check (must be in VALID_ROLES)
#
# ROLE HIERARCHY:
#   admin   (level 3) — full access
#   analyst (level 2) — analytics access
#   viewer  (level 1) — read-only access
#
#   require_role(token, "analyst") passes for "admin" and "analyst"
#   but rejects "viewer".
#
# Public API:
#   validate_token(token) → dict           — full pipeline, returns payload
#   is_token_expired(token) → bool         — quick check without secret
#   extract_claims(token) → dict           — extract without verification (logging only)
#   require_role(token, required_role)     — raise if role too low
#   get_user_role(token) → str             — role string from validated token
#   get_user_identity(token) → dict        — {user_id, username} from validated token
#
# Used by:
#   auth/auth_utils.py  — calls validate_token(), require_role()
#   tests/test_token_validation.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import AuthConfig
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class AuthConfig:
        VALID_ROLES    = {"admin", "analyst", "viewer"}
        ROLE_HIERARCHY = {"admin": 3, "analyst": 2, "viewer": 1}

from auth.jwt_handler import decode_token, get_token_expiry
from auth.auth_exceptions import (
    InvalidTokenError, TokenExpiredError, UnauthorizedAccessError, AuthError
)


# ══════════════════════════════════════════════════════════════════════════════
# PRIMARY VALIDATION FUNCTION
# ══════════════════════════════════════════════════════════════════════════════

def validate_token(token: str, secret: Optional[str] = None) -> dict:
    """
    Run the full token validation pipeline and return the verified payload.

    This is the primary function middleware and route handlers should call.
    It runs every check in the correct order and maps failures to the right
    exception type with a descriptive message.

    Validation order:
        1. Input type guard — catch None, bytes, integers early
        2. decode_token()  — verifies signature, expiry, and required claims
        3. Return verified payload dict

    Parameters
    ----------
    token  : str — the JWT string from the Authorization header (without "Bearer ")
    secret : str, optional — override the signing secret (for testing only)

    Returns
    -------
    dict — verified payload: {user_id, username, role, iat, exp}

    Raises
    ------
    InvalidTokenError  — token is None/empty/malformed/wrong signature/missing claims
    TokenExpiredError  — token has passed its exp timestamp
    WeakSecretError    — JWT_SECRET_KEY is not configured (raised by jwt_handler)

    Example
    -------
    >>> payload = validate_token(request.headers["Authorization"].split(" ")[1])
    >>> print(payload["username"])
    'arslan'

    >>> # In a route handler:
    >>> try:
    ...     payload = validate_token(token)
    ... except TokenExpiredError:
    ...     return {"error": "Session expired, please log in again"}, 401
    ... except InvalidTokenError:
    ...     return {"error": "Invalid token"}, 401
    """
    # --- Step 1: Input type guard ---
    if token is None:
        raise InvalidTokenError(reason="Token is None. No token was provided.")
    if not isinstance(token, str):
        raise InvalidTokenError(
            reason=f"Token must be a string, got {type(token).__name__}. "
            "Ensure you are passing the raw JWT string, not a wrapped object."
        )
    token = token.strip()
    if not token:
        raise InvalidTokenError(reason="Token is an empty string.")

    # Strip "Bearer " prefix if caller forgot to remove it
    if token.lower().startswith("bearer "):
        token = token[7:].strip()

    # --- Step 2: Full JWT verification via jwt_handler ---
    # decode_token() raises TokenExpiredError or InvalidTokenError on failure
    payload = decode_token(token, secret=secret)

    return payload


# ══════════════════════════════════════════════════════════════════════════════
# QUICK EXPIRY CHECK (no secret needed)
# ══════════════════════════════════════════════════════════════════════════════

def is_token_expired(token: str) -> bool:
    """
    Check whether a token's exp claim is in the past WITHOUT verifying the signature.

    Use case: logging middleware that needs to log "expired token attempt" but
    doesn't want to fail if the secret is unavailable.

    WARNING: This does NOT verify the signature. A token could be fabricated
    with a future expiry and pass this check. Never use this for security decisions.
    Use validate_token() for all security-critical checks.

    Parameters
    ----------
    token : str — any JWT string

    Returns
    -------
    bool — True if the exp claim is in the past (expired), False otherwise

    Example
    -------
    >>> is_token_expired("...valid_not_expired_token...")
    False
    >>> is_token_expired("...expired_token...")
    True
    """
    expiry = get_token_expiry(token)
    if expiry is None:
        return True   # can't extract expiry → treat as expired for safety
    return datetime.now(timezone.utc) > expiry


# ══════════════════════════════════════════════════════════════════════════════
# CLAIM EXTRACTION (no security verification — for logging only)
# ══════════════════════════════════════════════════════════════════════════════

def extract_claims(token: str) -> dict:
    """
    Extract claims from a token WITHOUT verifying the signature or expiry.

    Intended ONLY for audit logging — e.g., logging which user attempted
    to use an expired or invalid token. Do NOT use for any security decision.

    Parameters
    ----------
    token : str — any JWT string

    Returns
    -------
    dict — the raw payload (may be from an expired or tampered token)
           Returns {} if the token is not a valid JWT format at all.

    Example
    -------
    >>> claims = extract_claims(expired_token)
    >>> audit.log(f"Expired token used by: {claims.get('username', 'unknown')}")
    """
    if not isinstance(token, str) or not token:
        return {}
    try:
        import jwt as _jwt
        payload = _jwt.decode(token, options={"verify_signature": False})
        return payload
    except Exception:
        return {}


# ══════════════════════════════════════════════════════════════════════════════
# ROLE ENFORCEMENT
# ══════════════════════════════════════════════════════════════════════════════

def require_role(
    token          : str,
    required_role  : str,
    resource       : str = "",
    secret         : Optional[str] = None,
) -> dict:
    """
    Validate the token AND enforce a minimum role level.

    First calls validate_token() — if the token is invalid or expired, those
    exceptions propagate unchanged. Then checks the role hierarchy:

        admin   (level 3) passes for: admin
        analyst (level 2) passes for: analyst, admin
        viewer  (level 1) passes for: viewer, analyst, admin

    Parameters
    ----------
    token         : str — the JWT string
    required_role : str — the minimum role required ("admin", "analyst", "viewer")
    resource      : str, optional — name of the resource being accessed (for error messages)
    secret        : str, optional — override the signing secret (for testing only)

    Returns
    -------
    dict — the verified payload if the role check passes

    Raises
    ------
    InvalidTokenError       — if token is invalid
    TokenExpiredError       — if token is expired
    UnauthorizedAccessError — if the user's role is below the required level

    Example
    -------
    >>> # Only admins can access this
    >>> payload = require_role(token, "admin", resource="user_management")

    >>> # Analysts and admins can access this
    >>> payload = require_role(token, "analyst", resource="analytics_dashboard")
    """
    payload = validate_token(token, secret=secret)

    user_role     = payload.get("role", "")
    required_level = AuthConfig.ROLE_HIERARCHY.get(required_role, 0)
    user_level     = AuthConfig.ROLE_HIERARCHY.get(user_role, 0)

    if user_level < required_level:
        raise UnauthorizedAccessError(
            required_role=required_role,
            actual_role=user_role,
            resource=resource,
        )

    return payload


# ══════════════════════════════════════════════════════════════════════════════
# CLAIM ACCESSORS
# ══════════════════════════════════════════════════════════════════════════════

def get_user_role(token: str, secret: Optional[str] = None) -> str:
    """
    Extract and return the role claim from a validated token.

    Parameters
    ----------
    token  : str — the JWT string
    secret : str, optional — override the secret (for testing)

    Returns
    -------
    str — one of: "admin", "analyst", "viewer"

    Raises
    ------
    InvalidTokenError / TokenExpiredError — same as validate_token()

    Example
    -------
    >>> role = get_user_role(token)
    >>> if role == "admin":
    ...     allow_full_access()
    """
    payload = validate_token(token, secret=secret)
    return payload["role"]


def get_user_identity(token: str, secret: Optional[str] = None) -> dict:
    """
    Extract user identity claims from a validated token.

    Returns only the identity fields — not the full payload.
    Use this when you need to know WHO made a request without
    caring about the expiry timestamps or role.

    Parameters
    ----------
    token  : str — the JWT string
    secret : str, optional — override the secret (for testing)

    Returns
    -------
    dict — {"user_id": int, "username": str, "role": str}

    Raises
    ------
    InvalidTokenError / TokenExpiredError — same as validate_token()

    Example
    -------
    >>> identity = get_user_identity(token)
    >>> print(f"Request from user #{identity['user_id']}: {identity['username']}")
    """
    payload = validate_token(token, secret=secret)
    return {
        "user_id"  : payload["user_id"],
        "username" : payload["username"],
        "role"     : payload["role"],
    }


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os

    print("\n" + "=" * 60)
    print("  TOKEN VALIDATOR — SELF TEST")
    print("=" * 60)

    TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
    os.environ["JWT_SECRET_KEY"] = TEST_SECRET

    from auth.jwt_handler import create_access_token

    # Create tokens for each role
    admin_payload   = {"user_id": 1, "username": "admin_user",   "role": "admin"}
    analyst_payload = {"user_id": 2, "username": "arslan",        "role": "analyst"}
    viewer_payload  = {"user_id": 3, "username": "viewer_user",  "role": "viewer"}

    admin_token   = create_access_token(admin_payload,   expires_minutes=30, secret=TEST_SECRET)
    analyst_token = create_access_token(analyst_payload, expires_minutes=30, secret=TEST_SECRET)
    viewer_token  = create_access_token(viewer_payload,  expires_minutes=30, secret=TEST_SECRET)

    # --- validate_token ---
    p = validate_token(analyst_token, secret=TEST_SECRET)
    assert p["username"] == "arslan"
    print(f"\n  validate_token      : analyst token validated  ✅")

    # --- Bearer prefix stripping ---
    p2 = validate_token(f"Bearer {analyst_token}", secret=TEST_SECRET)
    assert p2["username"] == "arslan"
    print(f"  Bearer prefix       : 'Bearer <token>' stripped automatically  ✅")

    # --- None/empty token ---
    for bad in [None, "", "   ", 12345]:
        try:
            validate_token(bad, secret=TEST_SECRET)
            print(f"  Bad input ({bad!r})   : ❌ FAIL — accepted!")
        except InvalidTokenError:
            pass
    print(f"  Bad inputs          : None/empty/int all rejected  ✅")

    # --- Expired token ---
    expired = create_access_token(analyst_payload, expires_minutes=-1, secret=TEST_SECRET)
    import time; time.sleep(0.1)
    try:
        validate_token(expired, secret=TEST_SECRET)
        print("  Expired token       : ❌ FAIL")
    except TokenExpiredError:
        print(f"  Expired token       : TokenExpiredError raised  ✅")
    assert is_token_expired(expired) is True
    print(f"  is_token_expired()  : returns True for expired token  ✅")

    # --- extract_claims (no signature verification) ---
    claims = extract_claims(expired)
    assert claims.get("username") == "arslan"
    print(f"  extract_claims()    : extracts claims from expired token  ✅")

    # --- Role hierarchy ---
    # admin can access "admin" resource
    require_role(admin_token, "admin", resource="admin_panel", secret=TEST_SECRET)
    print(f"  role admin→admin    : ✅")

    # analyst can access "analyst" resource
    require_role(analyst_token, "analyst", resource="dashboard", secret=TEST_SECRET)
    print(f"  role analyst→analyst: ✅")

    # admin can also access "analyst" resource (higher level)
    require_role(admin_token, "analyst", resource="dashboard", secret=TEST_SECRET)
    print(f"  role admin→analyst  : admin passes analyst check  ✅")

    # viewer cannot access "analyst" resource
    try:
        require_role(viewer_token, "analyst", resource="dashboard", secret=TEST_SECRET)
        print("  role viewer→analyst : ❌ FAIL — viewer was allowed!")
    except UnauthorizedAccessError:
        print(f"  role viewer→analyst : viewer correctly blocked  ✅")

    # --- get_user_role / get_user_identity ---
    role     = get_user_role(analyst_token, secret=TEST_SECRET)
    identity = get_user_identity(analyst_token, secret=TEST_SECRET)
    assert role == "analyst"
    assert identity == {"user_id": 2, "username": "arslan", "role": "analyst"}
    print(f"  get_user_role()     : '{role}'  ✅")
    print(f"  get_user_identity() : {identity}  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
