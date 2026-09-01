# ─────────────────────────────────────────────────────────────────────────────
# encryption/key_manager.py
#
# Secure Key Management System
#
# This module is the single place in the codebase where encryption keys are
# touched. No other module should handle raw key bytes — they should call
# load_key() here and pass the returned bytes to aes.py functions.
#
# WHY ISOLATE KEY MANAGEMENT?
#   Centralising all key operations in one module means:
#     - Key loading logic is audited in exactly one place
#     - Rotating the key mechanism (e.g., switching to AWS KMS) only changes
#       this file, not every module that uses encryption
#     - Accidental key exposure (print(), logging, repr()) is minimised
#     - Tests can inject a fake key without modifying production logic
#
# KEY LOADING PRIORITY (load_key() tries in this order):
#   1. Environment variable  XPLOR_ENCRYPTION_KEY  (base64-encoded 32 bytes)
#   2. Key file              storage/keys/master.key
#   3. Auto-generate (DEV ONLY) — logs a loud WARNING when this fallback fires
#
# KEY STORAGE FORMAT:
#   Keys are stored as URL-safe Base64-encoded strings.
#   32 raw bytes → 44 Base64 characters (with padding).
#   This format is human-inspectable, copy-pasteable, and .env compatible.
#
# KEY ROTATION:
#   rotate_key() archives the current key with a timestamp suffix,
#   then writes a freshly generated key. Old keys remain available for
#   decrypting archives encrypted with the previous key.
#
# Public API:
#   generate_key() → bytes          (create a new random 32-byte key)
#   save_key(key, path)             (write base64 key to a file)
#   load_key(path, env_var) → bytes (load from env / file / generate)
#   validate_key(key)               (check key is valid bytes of right length)
#   rotate_key(path) → bytes        (archive old key, generate + save new one)
#   get_key() → bytes               (return the shared singleton key)
#
# Used by:
#   encryption/file_encryptor.py  — calls get_key() or load_key()
#   encryption/secure_storage.py  — calls get_key()
#   tests/test_key_manager.py     — tests all public functions directly
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
import base64
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import EncryptionConfig, KEYS_DIR
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class EncryptionConfig:
        KEY_SIZE_BYTES = 32
        ENV_KEY_NAME   = "XPLOR_ENCRYPTION_KEY"
        KEY_FILE_NAME  = "master.key"

    KEYS_DIR = Path(__file__).parent.parent / "storage" / "keys"

# ── Dotenv support (optional) ─────────────────────────────────────────────────
# load_dotenv() reads .env into os.environ so load_key() can find the key.
# If python-dotenv isn't installed, we silently skip it — env vars set by the
# shell or CI system still work without the package.

try:
    from dotenv import load_dotenv as _load_dotenv
    _load_dotenv()
    _HAS_DOTENV = True
except ImportError:
    _HAS_DOTENV = False

# ── Module logger ─────────────────────────────────────────────────────────────
# This logger is separate from the audit logger so key events can be captured
# even before the full security module is initialised.

_log = logging.getLogger("security.encryption.key_manager")
_log.setLevel(logging.DEBUG)
if not _log.handlers:
    _log.addHandler(logging.StreamHandler())


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class KeyError_(Exception):
    """
    Raised for any key management failure.

    Named KeyError_ (with underscore) to avoid shadowing Python's built-in KeyError.
    Callers should handle this to detect missing or invalid keys gracefully.
    """


class InvalidKeyError(KeyError_):
    """
    Raised specifically when a key fails validation (wrong length, wrong type).

    Separate from KeyError_ so callers can distinguish "key not found" from
    "key found but invalid".
    """


# ══════════════════════════════════════════════════════════════════════════════
# KEY GENERATION
# ══════════════════════════════════════════════════════════════════════════════

def generate_key() -> bytes:
    """
    Generate a cryptographically secure random 32-byte (256-bit) AES key.

    Uses os.urandom() which is backed by the operating system's CSPRNG
    (Cryptographically Secure Pseudo-Random Number Generator):
        - On Linux/macOS: getrandom() syscall / /dev/urandom
        - On Windows: CryptGenRandom (Win32 API)

    This is the ONLY correct way to generate AES keys in Python.
    Never use random.random(), uuid4(), or hash functions for key generation.

    Returns
    -------
    bytes — 32 random bytes suitable for AES-256

    Example
    -------
    >>> key = generate_key()
    >>> len(key)
    32
    >>> type(key)
    <class 'bytes'>
    """
    key = os.urandom(EncryptionConfig.KEY_SIZE_BYTES)
    _log.debug(
        f"Generated new {EncryptionConfig.KEY_SIZE_BYTES * 8}-bit encryption key"
    )
    return key


# ══════════════════════════════════════════════════════════════════════════════
# KEY VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def validate_key(key) -> None:
    """
    Validate that a key object is a bytes value of exactly 32 bytes.

    This function is the authoritative validator called by load_key(),
    save_key(), and any external code that receives a key from an untrusted source.

    Parameters
    ----------
    key : any — the value to validate

    Raises
    ------
    InvalidKeyError — if the key is not bytes or not exactly 32 bytes long

    Example
    -------
    >>> validate_key(b"x" * 32)    # passes silently
    >>> validate_key(b"short")     # raises InvalidKeyError
    """
    if not isinstance(key, bytes):
        raise InvalidKeyError(
            f"Key must be bytes, got {type(key).__name__}. "
            "Load keys using key_manager.load_key() — never construct raw strings."
        )
    if len(key) != EncryptionConfig.KEY_SIZE_BYTES:
        raise InvalidKeyError(
            f"Key is {len(key)} bytes. "
            f"AES-256 requires exactly {EncryptionConfig.KEY_SIZE_BYTES} bytes (256 bits). "
            "Use key_manager.generate_key() to create a correctly sized key."
        )


# ══════════════════════════════════════════════════════════════════════════════
# KEY SERIALISATION: SAVE & LOAD
# ══════════════════════════════════════════════════════════════════════════════

def _key_to_b64(key: bytes) -> str:
    """Encode raw key bytes to a URL-safe Base64 string (with padding)."""
    return base64.urlsafe_b64encode(key).decode("ascii")


def _b64_to_key(b64_string: str) -> bytes:
    """
    Decode a URL-safe Base64 string back to raw key bytes.

    Raises InvalidKeyError if the base64 string is malformed or the resulting
    key is not 32 bytes.
    """
    try:
        key = base64.urlsafe_b64decode(b64_string.strip())
    except Exception as exc:
        raise InvalidKeyError(
            "Failed to Base64-decode the encryption key. "
            "The key value appears to be corrupt or incorrectly formatted."
        ) from exc
    validate_key(key)
    return key


def save_key(key: bytes, path: Optional[Path] = None) -> Path:
    """
    Save a 32-byte key to a file as a Base64-encoded string.

    The key file contains a single line: the URL-safe Base64 representation
    of the 32 raw key bytes. This makes the file human-readable and easy to
    copy into a .env file or secret manager.

    The parent directory is created automatically if it does not exist.
    File permissions are set to owner-read-only (chmod 600) on Unix systems.
    On Windows, no permission change is applied (rely on NTFS ACLs).

    Parameters
    ----------
    key  : bytes        — 32-byte key to save
    path : Path, optional — destination file path
                            Defaults to KEYS_DIR / EncryptionConfig.KEY_FILE_NAME

    Returns
    -------
    Path — the path where the key was written

    Raises
    ------
    InvalidKeyError — if the key fails validation
    KeyError_       — if the file cannot be written

    Example
    -------
    >>> key = generate_key()
    >>> saved_path = save_key(key)
    >>> saved_path.exists()
    True
    """
    validate_key(key)
    dest = Path(path) if path else KEYS_DIR / EncryptionConfig.KEY_FILE_NAME
    dest.parent.mkdir(parents=True, exist_ok=True)

    try:
        dest.write_text(_key_to_b64(key), encoding="ascii")
        # Attempt to restrict key file permissions on Unix
        try:
            dest.chmod(0o600)
        except (AttributeError, NotImplementedError, OSError):
            pass  # Windows — ignore permission setting
        _log.info(f"Encryption key saved to: {dest}")
        return dest
    except OSError as exc:
        raise KeyError_(f"Could not save key to '{dest}': {exc}") from exc


def load_key(
    path       : Optional[Path] = None,
    env_var    : Optional[str]  = None,
    allow_generate: bool = False,
) -> bytes:
    """
    Load a 32-byte AES-256 encryption key using the following priority:

        1. Environment variable (name from env_var or EncryptionConfig.ENV_KEY_NAME)
        2. Key file at `path` (defaults to KEYS_DIR / master.key)
        3. Auto-generate a new key (ONLY if allow_generate=True)

    Priority 1 — Environment Variable:
        The env var should contain the Base64-encoded key string.
        Set it in .env or in your CI/CD secrets:
            XPLOR_ENCRYPTION_KEY=<base64-encoded-32-bytes>

    Priority 2 — Key File:
        The file should contain one line: the Base64-encoded key string.
        Create with: key_manager.save_key(generate_key())

    Priority 3 — Auto-generate:
        Only used when allow_generate=True (safe for development/testing).
        Logs a loud WARNING because auto-generated keys are not persisted —
        data encrypted with them cannot be recovered after restart.

    Parameters
    ----------
    path           : Path, optional — path to the key file
    env_var        : str, optional  — environment variable name to check first
    allow_generate : bool           — whether to auto-generate if key not found

    Returns
    -------
    bytes — 32-byte AES-256 key

    Raises
    ------
    KeyError_ — if no key source is found and allow_generate=False

    Example
    -------
    >>> key = load_key()              # production: reads from env or key file
    >>> key = load_key(allow_generate=True)   # dev: auto-generates if not found
    """
    env_name = env_var or EncryptionConfig.ENV_KEY_NAME

    # Priority 1: environment variable
    raw_env = os.environ.get(env_name)
    if raw_env:
        _log.debug(f"Loading encryption key from environment variable '{env_name}'")
        return _b64_to_key(raw_env)

    # Priority 2: key file
    key_file = Path(path) if path else KEYS_DIR / EncryptionConfig.KEY_FILE_NAME
    if key_file.exists():
        _log.debug(f"Loading encryption key from file: {key_file}")
        try:
            b64_text = key_file.read_text(encoding="ascii").strip()
            return _b64_to_key(b64_text)
        except (OSError, InvalidKeyError) as exc:
            raise KeyError_(
                f"Key file '{key_file}' exists but could not be loaded: {exc}"
            ) from exc

    # Priority 3: auto-generate (development only)
    if allow_generate:
        _log.warning(
            "⚠️  No encryption key found in environment or key file. "
            "Auto-generating a temporary key for development. "
            "THIS KEY IS NOT PERSISTED — data encrypted with it cannot be recovered "
            "after restart. Set XPLOR_ENCRYPTION_KEY or run save_key(generate_key())."
        )
        return generate_key()

    raise KeyError_(
        f"No encryption key found. Tried:\n"
        f"  1. Environment variable '{env_name}' — not set\n"
        f"  2. Key file '{key_file}' — not found\n\n"
        "To fix this:\n"
        "  Option A (recommended): generate and save a key:\n"
        "      from encryption.key_manager import generate_key, save_key\n"
        "      save_key(generate_key())\n\n"
        "  Option B: set the environment variable:\n"
        "      XPLOR_ENCRYPTION_KEY=<base64-encoded-32-bytes>"
    )


# ══════════════════════════════════════════════════════════════════════════════
# KEY ROTATION
# ══════════════════════════════════════════════════════════════════════════════

def rotate_key(path: Optional[Path] = None) -> bytes:
    """
    Rotate the encryption key: archive the current key, generate a new one.

    Key rotation is a standard security practice. After rotation:
        - The new key is saved as master.key (used for all future encryptions)
        - The old key is archived as master.key.YYYYMMDD_HHMMSS (for re-decryption)

    IMPORTANT: Rotating the key does NOT re-encrypt existing data.
    Data encrypted with the old key must still be decrypted with the old key.
    To re-encrypt, you must: decrypt with old key → encrypt with new key.

    Parameters
    ----------
    path : Path, optional — key file path (defaults to KEYS_DIR / master.key)

    Returns
    -------
    bytes — the newly generated key

    Raises
    ------
    KeyError_ — if the new key cannot be saved

    Example
    -------
    >>> old_key = load_key()
    >>> new_key = rotate_key()
    >>> new_key != old_key
    True
    """
    key_file = Path(path) if path else KEYS_DIR / EncryptionConfig.KEY_FILE_NAME
    key_file.parent.mkdir(parents=True, exist_ok=True)

    # Archive the current key if it exists
    if key_file.exists():
        timestamp  = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S_%f")
        archive    = key_file.with_suffix(f".key.{timestamp}")
        try:
            key_file.rename(archive)
            _log.info(f"Old key archived to: {archive.name}")
        except OSError as exc:
            raise KeyError_(
                f"Could not archive existing key before rotation: {exc}"
            ) from exc

    # Generate and save a new key
    new_key = generate_key()
    save_key(new_key, key_file)
    _log.info(
        f"Key rotation complete. New key saved to: {key_file.name}. "
        "Remember: existing encrypted data must be re-encrypted with the new key."
    )
    return new_key


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_cached_key: Optional[bytes] = None


def get_key(allow_generate: bool = False) -> bytes:
    """
    Return the shared encryption key singleton.

    Loads the key once on first call and caches it in module memory.
    All modules that need the key should call get_key() rather than
    calling load_key() independently — this avoids repeatedly reading
    the key file on every encryption operation.

    Parameters
    ----------
    allow_generate : bool — allow auto-generating if no key found (dev only)

    Returns
    -------
    bytes — 32-byte AES-256 key

    Raises
    ------
    KeyError_ — if no key is available and allow_generate=False
    """
    global _cached_key
    if _cached_key is None:
        _cached_key = load_key(allow_generate=allow_generate)
    return _cached_key


def clear_key_cache() -> None:
    """
    Clear the cached key from module memory.

    Call this in tests between test cases to avoid cross-test key contamination.
    In production, call this if you rotate the key mid-process.
    """
    global _cached_key
    _cached_key = None


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    print("\n" + "=" * 60)
    print("  KEY MANAGER — SELF TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path    = Path(tmp)
        key_file    = tmp_path / "test.key"

        # --- Generate ---
        key = generate_key()
        assert isinstance(key, bytes) and len(key) == 32
        print(f"\n  generate_key()  : {len(key)} bytes  ✅")

        # --- Validate ---
        validate_key(key)
        print(f"  validate_key()  : valid key passes silently  ✅")

        try:
            validate_key(b"too_short")
        except InvalidKeyError:
            print(f"  validate_key()  : short key correctly rejected  ✅")

        # --- Save / Load round-trip ---
        saved = save_key(key, key_file)
        assert saved.exists()
        loaded = load_key(path=key_file)
        assert loaded == key
        print(f"  save / load     : round-trip verified  ✅")

        # --- Env var loading ---
        import base64
        os.environ["_TEST_XPLOR_KEY"] = base64.urlsafe_b64encode(key).decode()
        from_env = load_key(env_var="_TEST_XPLOR_KEY")
        assert from_env == key
        del os.environ["_TEST_XPLOR_KEY"]
        print(f"  load from env   : env var round-trip verified  ✅")

        # --- Auto-generate fallback ---
        gen = load_key(path=tmp_path / "nonexistent.key", allow_generate=True)
        assert isinstance(gen, bytes) and len(gen) == 32
        print(f"  auto-generate   : fallback generates valid key  ✅")

        # --- Rotate ---
        new_key = rotate_key(key_file)
        assert new_key != key
        loaded_new = load_key(path=key_file)
        assert loaded_new == new_key
        # Old key should be archived
        archives = list(key_file.parent.glob("*.key.*"))
        assert len(archives) == 1
        print(f"  rotate_key()    : new key saved, old archived ({archives[0].name})  ✅")

        # --- Singleton ---
        clear_key_cache()
        k1 = get_key(allow_generate=True)
        k2 = get_key(allow_generate=True)
        assert k1 is k2
        clear_key_cache()
        print(f"  get_key()       : singleton returns same object on repeated calls  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
