# ─────────────────────────────────────────────────────────────────────────────
# auth/jwt_handler.py
#
# JWT Token Generation and Decoding Engine
#
# WHAT IS A JWT?
#   JSON Web Token — a compact, self-contained token for transmitting claims
#   between parties. Structured as three Base64url-encoded segments:
#
#   HEADER.PAYLOAD.SIGNATURE
#   └────┘ └─────┘ └───────┘
#    algo   claims  HMAC-SHA256(header+payload, secret)
#
# WHY JWT?
#   Stateless — the server doesn't need to store session state in a database.
#   The token contains all necessary claims and its own proof of authenticity.
#   Valid as long as the signature checks out AND the exp claim hasn't passed.
#
# TOKEN PAYLOAD (what we put in every token):
#   {
#     "user_id"  : 42,                        ← who the user is
#     "username" : "arslan",                  ← human-readable identity
#     "role"     : "analyst",                 ← for RBAC enforcement
#     "iat"      : 1717200000,                ← issued at (Unix timestamp)
#     "exp"      : 1717201800                 ← expires at (iat + 30 minutes)
#   }
#
# ALGORITHM: HS256 (HMAC-SHA256)
#   Symmetric — same secret signs and verifies. Correct for a single-server
#   API. For multi-server or microservice scenarios, RS256 (RSA asymmetric)
#   would be needed so verification servers don't hold the signing key.
#
# SECRET KEY RULES:
#   - Loaded from JWT_SECRET_KEY environment variable
#   - Must be at least 32 characters (AuthConfig.MIN_SECRET_KEY_LENGTH)
#   - WeakSecretError raised at module load time if misconfigured
#
# Public API:
#   create_access_token(payload, expires_minutes) → str  (JWT string)
#   decode_token(token) → dict                           (verified payload dict)
#   verify_token(token) → bool                           (True / False)
#
# Used by:
#   auth/token_validator.py  — calls decode_token()
#   auth/auth_utils.py       — calls create_access_token(), decode_token()
#   tests/test_jwt.py
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from datetime import datetime, timezone, timedelta
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
        JWT_ALGORITHM            = "HS256"
        TOKEN_EXPIRATION_MINUTES = 30
        MIN_SECRET_KEY_LENGTH    = 32
        ENV_SECRET_KEY_NAME      = "JWT_SECRET_KEY"
        ENV_ALGORITHM_NAME       = "JWT_ALGORITHM"
        ENV_EXPIRY_NAME          = "TOKEN_EXPIRATION_MINUTES"
        VALID_ROLES              = {"admin", "analyst", "viewer"}

# ── PyJWT import ──────────────────────────────────────────────────────────────

try:
    import jwt as _jwt
    from jwt.exceptions import (
        ExpiredSignatureError      as _ExpiredSignatureError,
        InvalidTokenError          as _PyJWTInvalidTokenError,
        DecodeError                as _DecodeError,
        InvalidSignatureError      as _InvalidSignatureError,
    )
    _HAS_JWT = True
except ImportError:
    _HAS_JWT = False

# ── dotenv ────────────────────────────────────────────────────────────────────

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
except ImportError:
    pass

from auth.auth_exceptions import (
    TokenExpiredError, InvalidTokenError, WeakSecretError,
)


# ══════════════════════════════════════════════════════════════════════════════
# SECRET KEY LOADING
# ══════════════════════════════════════════════════════════════════════════════

def _load_secret() -> str:
    """
    Load and validate the JWT signing secret from the environment.

    Priority:
        1. JWT_SECRET_KEY environment variable
        2. WeakSecretError raised if not found or too short

    The minimum length (32 chars) is enforced here at load time so that
    misconfiguration is caught immediately — not silently at the first
    token operation.

    Returns
    -------
    str — the secret key string

    Raises
    ------
    WeakSecretError — if JWT_SECRET_KEY is not set or is too short
    """
    secret = os.environ.get(AuthConfig.ENV_SECRET_KEY_NAME, "")
    required = AuthConfig.MIN_SECRET_KEY_LENGTH

    if not secret:
        raise WeakSecretError(actual_length=0, required_length=required)
    if len(secret) < required:
        raise WeakSecretError(actual_length=len(secret), required_length=required)

    return secret


def _load_algorithm() -> str:
    """Load JWT algorithm from env var, defaulting to AuthConfig.JWT_ALGORITHM."""
    return os.environ.get(AuthConfig.ENV_ALGORITHM_NAME, AuthConfig.JWT_ALGORITHM)


def _load_expiry_minutes() -> int:
    """Load token expiry from env var, defaulting to AuthConfig.TOKEN_EXPIRATION_MINUTES."""
    raw = os.environ.get(AuthConfig.ENV_EXPIRY_NAME, "")
    try:
        return int(raw) if raw else AuthConfig.TOKEN_EXPIRATION_MINUTES
    except ValueError:
        return AuthConfig.TOKEN_EXPIRATION_MINUTES


def _require_jwt() -> None:
    """Raise ImportError with install instructions if PyJWT is missing."""
    if not _HAS_JWT:
        raise ImportError(
            "The 'PyJWT' package is required for JWT operations.\n"
            "Install it with:  pip install PyJWT"
        )


# ══════════════════════════════════════════════════════════════════════════════
# REQUIRED CLAIMS VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

# Every Xplor JWT must contain these fields in its payload
REQUIRED_CLAIMS = {"user_id", "username", "role", "exp", "iat"}


def _validate_payload_claims(payload: dict) -> None:
    """
    Verify that a decoded payload contains all required claims.

    Called after decode_token() successfully verifies the signature and expiry.
    Catches tokens that are technically valid JWT but missing Xplor-specific claims.

    Raises
    ------
    InvalidTokenError — if any required claim is missing
    """
    missing = REQUIRED_CLAIMS - set(payload.keys())
    if missing:
        raise InvalidTokenError(
            reason=f"Token is missing required claims: {sorted(missing)}. "
            "This token may have been created by a different system."
        )

    # Validate role claim value
    role = payload.get("role", "")
    if role not in AuthConfig.VALID_ROLES:
        raise InvalidTokenError(
            reason=f"Token contains an invalid role claim: '{role}'. "
            f"Expected one of: {sorted(AuthConfig.VALID_ROLES)}"
        )


# ══════════════════════════════════════════════════════════════════════════════
# TOKEN CREATION
# ══════════════════════════════════════════════════════════════════════════════

def create_access_token(
    payload         : dict,
    expires_minutes : Optional[int] = None,
    secret          : Optional[str] = None,
) -> str:
    """
    Create a signed JWT access token from a user payload dict.

    Automatically adds:
        iat — issued at (current UTC Unix timestamp)
        exp — expires at (iat + expires_minutes)

    The token is signed with HS256 using the JWT_SECRET_KEY secret.
    Any modification to the payload after signing will invalidate the signature.

    Parameters
    ----------
    payload         : dict — must include: user_id (int), username (str), role (str)
    expires_minutes : int, optional — token lifetime in minutes
                      Defaults to TOKEN_EXPIRATION_MINUTES env var or AuthConfig
    secret          : str, optional — override the secret (for testing only)

    Returns
    -------
    str — signed JWT string (format: HEADER.PAYLOAD.SIGNATURE)

    Raises
    ------
    WeakSecretError  — if JWT_SECRET_KEY is not set or too short
    InvalidTokenError — if required payload fields are missing
    ImportError       — if PyJWT is not installed

    Example
    -------
    >>> token = create_access_token({"user_id": 42, "username": "arslan", "role": "analyst"})
    >>> token.count(".")  # three parts separated by two dots
    2
    """
    _require_jwt()

    sec       = secret or _load_secret()
    algo      = _load_algorithm()
    exp_mins  = expires_minutes if expires_minutes is not None else _load_expiry_minutes()

    # Validate that required fields are in the caller-supplied payload
    required_input = {"user_id", "username", "role"}
    missing = required_input - set(payload.keys())
    if missing:
        raise InvalidTokenError(
            reason=f"Cannot create token: payload is missing fields: {sorted(missing)}. "
            "Use auth_utils.generate_user_payload() to build a correct payload."
        )

    # Validate role value
    if payload.get("role") not in AuthConfig.VALID_ROLES:
        raise InvalidTokenError(
            reason=f"Invalid role '{payload.get('role')}' in payload. "
            f"Must be one of: {sorted(AuthConfig.VALID_ROLES)}"
        )

    now = datetime.now(timezone.utc)

    full_payload = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + timedelta(minutes=exp_mins)).timestamp()),
    }

    try:
        token = _jwt.encode(full_payload, sec, algorithm=algo)
        # PyJWT ≥2.0 returns str; earlier versions returned bytes
        return token if isinstance(token, str) else token.decode("utf-8")
    except Exception as exc:
        raise InvalidTokenError(
            reason=f"Token creation failed: {exc}"
        ) from exc


# ══════════════════════════════════════════════════════════════════════════════
# TOKEN DECODING
# ══════════════════════════════════════════════════════════════════════════════

def decode_token(
    token  : str,
    secret : Optional[str] = None,
) -> dict:
    """
    Decode and fully verify a JWT token.

    Verification steps (all happen inside PyJWT automatically):
        1. Base64url-decode the three segments
        2. Verify the HMAC-SHA256 signature against the secret
        3. Check the exp claim — reject if in the past
        4. Check the iat claim — reject if in the future (clock skew guard)

    After PyJWT verification passes, we additionally check that
    all Xplor-required claims (user_id, username, role) are present.

    Parameters
    ----------
    token  : str — the JWT string to decode and verify
    secret : str, optional — override the secret (for testing only)

    Returns
    -------
    dict — the verified payload (user_id, username, role, iat, exp)

    Raises
    ------
    TokenExpiredError  — if the token's exp claim is in the past
    InvalidTokenError  — if signature is wrong, token is malformed, or claims missing
    WeakSecretError    — if JWT_SECRET_KEY is not configured
    ImportError        — if PyJWT is not installed

    Example
    -------
    >>> payload = decode_token(token)
    >>> payload["username"]
    'arslan'
    >>> payload["role"]
    'analyst'
    """
    _require_jwt()

    if not token or not isinstance(token, str):
        raise InvalidTokenError(
            reason="Token must be a non-empty string. Received: "
            f"{type(token).__name__}"
        )

    sec  = secret or _load_secret()
    algo = _load_algorithm()

    try:
        payload = _jwt.decode(
            token,
            sec,
            algorithms=[algo],
            options={"require": ["exp", "iat"]},
        )
        _validate_payload_claims(payload)
        return payload

    except _ExpiredSignatureError as exc:
        # Extract expiry time from token for a helpful error message
        try:
            unverified = _jwt.decode(token, options={"verify_signature": False})
            exp_ts     = unverified.get("exp", 0)
            exp_str    = datetime.fromtimestamp(exp_ts, tz=timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%SZ"
            )
        except Exception:
            exp_str = "unknown"
        raise TokenExpiredError(expired_at=exp_str) from exc

    except (InvalidTokenError,):
        raise  # re-raise our own exception without wrapping

    except (_InvalidSignatureError,):
        raise InvalidTokenError(
            reason="Token signature verification failed. "
            "The token may have been tampered with or signed with a different secret."
        ) from None

    except (_DecodeError, _PyJWTInvalidTokenError) as exc:
        raise InvalidTokenError(
            reason=f"Token could not be decoded: {exc}. "
            "The token may be malformed, truncated, or not a valid JWT."
        ) from exc

    except Exception as exc:
        raise InvalidTokenError(
            reason=f"Unexpected error during token verification: {exc}"
        ) from exc


# ══════════════════════════════════════════════════════════════════════════════
# CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def verify_token(token: str, secret: Optional[str] = None) -> bool:
    """
    Check whether a token is valid without raising an exception.

    Useful for middleware checks where you only need True/False and
    will handle the False case with a generic "unauthorised" response.

    Parameters
    ----------
    token  : str — the JWT string to check
    secret : str, optional — override the secret (for testing only)

    Returns
    -------
    bool — True if token is valid and not expired, False otherwise

    Example
    -------
    >>> verify_token("valid_token_string")
    True
    >>> verify_token("expired_or_tampered")
    False
    """
    try:
        decode_token(token, secret=secret)
        return True
    except Exception:
        return False


def get_token_expiry(token: str) -> Optional[datetime]:
    """
    Extract the expiry datetime from a token WITHOUT verifying the signature.

    Useful for logging "token expired at X" in audit events without needing
    the secret key (e.g., in a logging middleware that receives tokens).

    WARNING: Do NOT use this for security decisions — it skips signature verification.

    Parameters
    ----------
    token : str — any JWT string (signature not verified)

    Returns
    -------
    datetime or None — expiry as UTC datetime, or None if extraction fails
    """
    _require_jwt()
    try:
        unverified = _jwt.decode(token, options={"verify_signature": False})
        exp        = unverified.get("exp")
        return datetime.fromtimestamp(exp, tz=timezone.utc) if exp else None
    except Exception:
        return None


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import time

    print("\n" + "=" * 60)
    print("  JWT HANDLER — SELF TEST")
    print("=" * 60)

    # Set a test secret so the self-test works without .env
    TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
    os.environ["JWT_SECRET_KEY"] = TEST_SECRET

    payload = {"user_id": 42, "username": "arslan", "role": "analyst"}

    # --- Create ---
    token = create_access_token(payload, expires_minutes=30, secret=TEST_SECRET)
    assert isinstance(token, str) and token.count(".") == 2
    print(f"\n  create_access_token : {token[:40]}...  ✅")

    # --- Decode ---
    decoded = decode_token(token, secret=TEST_SECRET)
    assert decoded["username"] == "arslan"
    assert decoded["role"] == "analyst"
    assert decoded["user_id"] == 42
    assert "exp" in decoded and "iat" in decoded
    print(f"  decode_token        : user={decoded['username']}, role={decoded['role']}  ✅")

    # --- Role claim ---
    assert "role" in decoded
    print(f"  role claim          : '{decoded['role']}'  ✅")

    # --- verify_token ---
    assert verify_token(token, secret=TEST_SECRET) is True
    print(f"  verify_token        : valid token returns True  ✅")

    # --- Expired token ---
    expired_token = create_access_token(payload, expires_minutes=-1, secret=TEST_SECRET)
    time.sleep(0.1)
    try:
        decode_token(expired_token, secret=TEST_SECRET)
        print("  Expired token       : ❌ FAIL — accepted expired token!")
    except TokenExpiredError:
        print(f"  Expired token       : correctly raises TokenExpiredError  ✅")

    # --- Wrong secret ---
    try:
        decode_token(token, secret="wrong_secret_key_minimum_32_chars")
        print("  Wrong secret        : ❌ FAIL — accepted wrong secret!")
    except InvalidTokenError:
        print(f"  Wrong secret        : correctly raises InvalidTokenError  ✅")

    # --- Malformed token ---
    try:
        decode_token("not.a.jwt", secret=TEST_SECRET)
        print("  Malformed token     : ❌ FAIL — accepted malformed token!")
    except InvalidTokenError:
        print(f"  Malformed token     : correctly raises InvalidTokenError  ✅")

    # --- WeakSecretError ---
    try:
        _load_secret.__module__  # ensure function is accessible
        import os as _os
        _os.environ["JWT_SECRET_KEY"] = "short"
        _load_secret()
        print("  Weak secret         : ❌ FAIL — accepted weak secret!")
    except WeakSecretError:
        print(f"  Weak secret         : correctly raises WeakSecretError  ✅")
    finally:
        os.environ["JWT_SECRET_KEY"] = TEST_SECRET

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
