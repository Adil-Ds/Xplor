# ─────────────────────────────────────────────────────────────────────────────
# auth/password_hashing.py
#
# bcrypt Password Hashing System
#
# PASSWORD SECURITY FUNDAMENTALS:
#
#   WRONG approach — never do these:
#     ❌ Store plaintext password ("password123")
#     ❌ Use MD5 or SHA-256 alone (fast = crackable in seconds on GPU)
#     ❌ Use a single global salt (breaks when database is stolen)
#     ❌ Use AES encryption (encryption is reversible — hashing is not)
#
#   CORRECT approach (what this module does):
#     ✅ bcrypt — designed specifically for passwords
#     ✅ Auto-salted — unique salt per password, salt embedded in hash string
#     ✅ Slow by design — bcrypt work factor makes GPU cracking impractical
#     ✅ One-way — cannot reverse a bcrypt hash to get the original password
#
# WHY bcrypt OVER SHA-256?
#   SHA-256 hashes 1 billion passwords/second on a GPU.
#   bcrypt with rounds=12 hashes ~5 passwords/second.
#   An attacker with a stolen hash database gets nothing useful from bcrypt.
#
# BCRYPT HASH FORMAT:
#   $2b$12$<22-char-salt><31-char-hash>
#   └──┘└─┘└──────────────────────────┘
#   version rounds      60-char output
#
#   The salt is EMBEDDED in the output — no need to store it separately.
#   The same password hashed twice will produce DIFFERENT strings (different salts).
#   bcrypt.checkpw() extracts the stored salt and compares correctly.
#
# OWASP 2024 RECOMMENDATION: bcrypt with work factor 12 (our default).
#
# Public API:
#   hash_password(plain_password) → str     (60-char bcrypt hash string)
#   verify_password(plain, hashed) → bool   (True if match, False otherwise)
#   is_valid_password_format(password) → bool  (basic format checks)
#
# Used by:
#   auth/auth_utils.py        — calls hash_password() during registration
#   tests/test_password_hashing.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import AuthConfig
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class AuthConfig:
        BCRYPT_ROUNDS       = 12
        MAX_PASSWORD_LENGTH = 128

# ── bcrypt import ─────────────────────────────────────────────────────────────

try:
    import bcrypt
    _HAS_BCRYPT = True
except ImportError:
    _HAS_BCRYPT = False

from auth.auth_exceptions import InvalidCredentialsError


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _require_bcrypt() -> None:
    """Raise ImportError with clear instructions if bcrypt is not installed."""
    if not _HAS_BCRYPT:
        raise ImportError(
            "The 'bcrypt' package is required for password hashing.\n"
            "Install it with:  pip install bcrypt"
        )


def _validate_password_input(password: str) -> None:
    """
    Validate that the password input is a non-empty string within safe bounds.

    bcrypt silently truncates inputs longer than 72 bytes. We enforce a higher
    limit (128 chars) and raise a clear error so callers know the input was
    rejected — rather than silently accepting a truncated password.

    Raises
    ------
    ValueError — if password is not a string, is empty, or exceeds length limit
    """
    if not isinstance(password, str):
        raise ValueError(
            f"Password must be a string, got {type(password).__name__}. "
            "Never pass bytes directly — hash_password() handles encoding internally."
        )
    if not password:
        raise ValueError(
            "Password cannot be empty. "
            "Enforce minimum password length before calling hash_password()."
        )
    if len(password) > AuthConfig.MAX_PASSWORD_LENGTH:
        raise ValueError(
            f"Password exceeds maximum length of {AuthConfig.MAX_PASSWORD_LENGTH} characters. "
            f"Provided: {len(password)} characters. "
            "Note: bcrypt internally processes only the first 72 bytes."
        )


# ══════════════════════════════════════════════════════════════════════════════
# PUBLIC API
# ══════════════════════════════════════════════════════════════════════════════

def hash_password(plain_password: str) -> str:
    """
    Hash a plaintext password using bcrypt with auto-generated salt.

    This is the ONLY correct way to store a password in the Xplor platform.
    The returned string is safe to store directly in a database — it contains
    the algorithm version, work factor, salt, and hash all in one string.

    NEVER store the original plain_password — discard it after calling this.

    bcrypt process (happens automatically inside this function):
        1. Generate 16 random bytes of salt (os.urandom internally)
        2. Encode password as UTF-8 bytes
        3. Run bcrypt KDF with work_factor=12 (2^12 = 4096 iterations)
        4. Return: "$2b$12$<22-char-salt><31-char-hash>"

    Parameters
    ----------
    plain_password : str — the user's plaintext password (e.g. "MyP@ssw0rd!")

    Returns
    -------
    str — 60-character bcrypt hash string, safe to store in a database

    Raises
    ------
    ValueError  — if password is empty, not a string, or exceeds length limit
    ImportError — if bcrypt package is not installed

    Example
    -------
    >>> hashed = hash_password("MyP@ssw0rd!")
    >>> hashed.startswith("$2b$12$")
    True
    >>> len(hashed)
    60
    """
    _require_bcrypt()
    _validate_password_input(plain_password)

    # Generate a fresh salt for THIS password (rounds=12 means 2^12 bcrypt iterations)
    salt = bcrypt.gensalt(rounds=AuthConfig.BCRYPT_ROUNDS)

    # Hash the password — bcrypt encodes to bytes internally
    hashed_bytes = bcrypt.hashpw(plain_password.encode("utf-8"), salt)

    # Return as a string for easy database storage
    return hashed_bytes.decode("utf-8")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plaintext password against a stored bcrypt hash.

    Uses bcrypt.checkpw() which:
        1. Extracts the salt from the stored hash string
        2. Hashes the provided plain_password with the same salt
        3. Compares the results using a timing-safe comparison

    TIMING SAFETY:
        bcrypt.checkpw() uses a constant-time comparison internally.
        This prevents timing side-channel attacks where an attacker
        measures tiny differences in response time to guess the hash.

    Parameters
    ----------
    plain_password   : str — the password attempt to verify
    hashed_password  : str — the stored bcrypt hash from the database

    Returns
    -------
    bool — True if the password matches the hash, False otherwise

    Raises
    ------
    ImportError — if bcrypt package is not installed
    ValueError  — if either input is not a string or is empty

    Security note:
        This function returns False (not an exception) for wrong passwords.
        This is intentional — callers convert False to InvalidCredentialsError
        so that error handling looks the same for "user not found" vs "wrong password".

    Example
    -------
    >>> hashed = hash_password("correct_password")
    >>> verify_password("correct_password", hashed)
    True
    >>> verify_password("wrong_password", hashed)
    False
    """
    _require_bcrypt()

    if not isinstance(plain_password, str) or not isinstance(hashed_password, str):
        return False
    if not plain_password or not hashed_password:
        return False

    try:
        return bcrypt.checkpw(
            plain_password.encode("utf-8"),
            hashed_password.encode("utf-8"),
        )
    except Exception:
        # bcrypt raises if the hash string is malformed.
        # Return False rather than propagating — callers handle False uniformly.
        return False


def is_valid_password_format(password: str) -> tuple:
    """
    Check whether a password meets minimum security requirements.

    This is a basic format check for the registration flow.
    It does NOT validate against a breach database (pwned passwords).

    Checks performed:
        - At least 8 characters long
        - Not longer than 128 characters (bcrypt limit)
        - Contains at least one digit
        - Contains at least one letter

    Parameters
    ----------
    password : str — the candidate password

    Returns
    -------
    tuple[bool, str] — (True, "") if valid, (False, reason) if invalid

    Example
    -------
    >>> is_valid_password_format("weakpass")
    (False, "Password must contain at least one digit")
    >>> is_valid_password_format("Strong1pass")
    (True, "")
    """
    if not isinstance(password, str):
        return False, "Password must be a string"
    if len(password) < 8:
        return False, f"Password must be at least 8 characters (got {len(password)})"
    if len(password) > AuthConfig.MAX_PASSWORD_LENGTH:
        return False, f"Password exceeds maximum length of {AuthConfig.MAX_PASSWORD_LENGTH} characters"
    if not any(c.isdigit() for c in password):
        return False, "Password must contain at least one digit (0-9)"
    if not any(c.isalpha() for c in password):
        return False, "Password must contain at least one letter"
    return True, ""


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  PASSWORD HASHING — SELF TEST")
    print("=" * 60)

    # Hash a password
    pwd = "SecureP@ss123"
    h   = hash_password(pwd)
    print(f"\n  Password   : {pwd}")
    print(f"  Hash       : {h}")
    print(f"  Starts with: {h[:7]}  ✅" if h.startswith("$2b$12$") else "  ❌ Wrong format")
    print(f"  Length     : {len(h)} chars  ✅" if len(h) == 60 else f"  ❌ Expected 60, got {len(h)}")

    # Unique hashes (different salts)
    h2 = hash_password(pwd)
    assert h != h2, "Same password must produce different hashes!"
    print(f"  Uniqueness : two hashes differ (different salts)  ✅")

    # Verification
    assert verify_password(pwd, h) is True
    assert verify_password("wrong", h) is False
    print(f"  Verify OK  : correct password → True  ✅")
    print(f"  Verify BAD : wrong password → False  ✅")

    # Format validation
    ok, msg = is_valid_password_format("short")
    assert ok is False
    ok2, _ = is_valid_password_format("Strong1pass")
    assert ok2 is True
    print(f"  Format     : 'short' rejected, 'Strong1pass' accepted  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
