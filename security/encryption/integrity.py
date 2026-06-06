# ─────────────────────────────────────────────────────────────────────────────
# encryption/integrity.py
#
# File Integrity Verification Utilities
#
# This module provides supplemental integrity checks BEYOND the GCM tag:
#
#   1. HASH-BASED VERIFICATION (SHA-256)
#      Compute a SHA-256 fingerprint of a file and compare it later.
#      Used to detect corruption or tampering at the file system level.
#
#   2. PRE-DECRYPTION VALIDATION
#      Before attempting to decrypt a .enc file, check that it looks like
#      a valid encrypted payload (minimum size, correct structure).
#      This prevents wasting time decrypting obviously corrupt files
#      and gives cleaner error messages.
#
# WHY DO WE NEED THIS IF GCM ALREADY VERIFIES INTEGRITY?
#   GCM's authentication tag verifies integrity DURING decryption.
#   These utilities verify integrity BEFORE decryption:
#     - Quickly detect obviously corrupt files without loading the crypto stack
#     - Generate standalone file fingerprints for comparison in audit logs
#     - Support external integrity checking workflows (e.g., checksums alongside backups)
#
# DESIGN PRINCIPLE:
#   All functions in this module are STATELESS and pure — they take inputs,
#   return outputs, and have no side effects. This makes them trivially testable.
#
# Public API:
#   hash_file(path) → str              (SHA-256 hex digest of a file)
#   hash_bytes(data) → str             (SHA-256 hex digest of bytes)
#   verify_file_hash(path, expected_hash) → bool
#   save_hash_file(path)               (write .sha256 sidecar next to the file)
#   load_and_verify_hash(path) → bool  (check file against its .sha256 sidecar)
#   validate_encrypted_file(data) → bool  (pre-decryption sanity check)
#   is_encrypted_file(path) → bool     (check by extension and minimum size)
#
# Used by:
#   encryption/file_encryptor.py  — calls validate_encrypted_file() before decrypt
#   encryption/secure_storage.py  — calls hash_file() and verify_file_hash()
#   tests/test_encryption.py      — tests all functions directly
# ─────────────────────────────────────────────────────────────────────────────

import hashlib
import sys
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import EncryptionConfig
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class EncryptionConfig:
        IV_SIZE_BYTES  = 12
        TAG_SIZE_BYTES = 16
        ENCRYPTED_EXT  = ".enc"
        CHUNK_SIZE     = 64 * 1024


# ══════════════════════════════════════════════════════════════════════════════
# INTEGRITY EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class IntegrityError(Exception):
    """
    Raised when a file integrity check fails.

    This indicates the file may have been tampered with, corrupted during
    storage or transmission, or replaced with a different file.

    Example:
        try:
            verify_file_hash(path, stored_hash)
        except IntegrityError as e:
            audit.log_system_event(str(e), severity="CRITICAL")
    """


# ══════════════════════════════════════════════════════════════════════════════
# SHA-256 HASH FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def hash_bytes(data: bytes) -> str:
    """
    Compute the SHA-256 hash of raw bytes.

    SHA-256 produces a unique 256-bit fingerprint for any input.
    The same bytes always produce the same hash — even one changed bit
    produces a completely different hash (avalanche effect).

    Parameters
    ----------
    data : bytes — the data to hash

    Returns
    -------
    str — lowercase hex string of the SHA-256 digest (64 characters)

    Example
    -------
    >>> hash_bytes(b"hello")
    '2cf24dba5fb0a30e26e83b2ac5b9e29e1b161e5c1fa7425e73043362938b9824'
    """
    if not isinstance(data, bytes):
        raise TypeError(f"hash_bytes() expects bytes, got {type(data).__name__}")
    return hashlib.sha256(data).hexdigest()


def hash_file(path: Path, chunk_size: Optional[int] = None) -> str:
    """
    Compute the SHA-256 hash of a file without loading it fully into memory.

    Reads the file in chunks (default 64 KB) so large datasets can be
    hashed without exhausting RAM. This is important for analytics files
    which may be hundreds of megabytes.

    Parameters
    ----------
    path       : Path — path to the file to hash
    chunk_size : int, optional — read chunk size in bytes (default: 64 KB)

    Returns
    -------
    str — lowercase hex SHA-256 digest (64 characters)

    Raises
    ------
    FileNotFoundError — if the file does not exist
    IntegrityError    — if the file cannot be read

    Example
    -------
    >>> digest = hash_file(Path("dataset.csv"))
    >>> len(digest)
    64
    """
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(
            f"Cannot hash file — not found: {path}"
        )
    if not path.is_file():
        raise IntegrityError(f"Path is not a regular file: {path}")

    chunk = chunk_size or EncryptionConfig.CHUNK_SIZE
    hasher = hashlib.sha256()

    try:
        with path.open("rb") as fh:
            while True:
                block = fh.read(chunk)
                if not block:
                    break
                hasher.update(block)
    except OSError as exc:
        raise IntegrityError(
            f"Could not read file '{path.name}' for hashing: {exc}"
        ) from exc

    return hasher.hexdigest()


def verify_file_hash(path: Path, expected_hash: str) -> bool:
    """
    Verify that a file's SHA-256 hash matches the expected value.

    Uses hmac.compare_digest() for timing-safe comparison, preventing
    timing side-channel attacks where an attacker could infer the correct
    hash by measuring how long the comparison takes.

    Parameters
    ----------
    path          : Path — path to the file to check
    expected_hash : str  — the SHA-256 hex string to compare against

    Returns
    -------
    bool — True if the hash matches, False if it does not

    Raises
    ------
    FileNotFoundError — if the file does not exist
    IntegrityError    — if the file cannot be read

    Example
    -------
    >>> original_hash = hash_file(path)
    >>> verify_file_hash(path, original_hash)
    True
    """
    import hmac
    actual_hash = hash_file(path)
    # Use hmac.compare_digest() to prevent timing attacks
    return hmac.compare_digest(actual_hash.lower(), expected_hash.lower())


# ══════════════════════════════════════════════════════════════════════════════
# HASH SIDECAR FILES (.sha256)
# ══════════════════════════════════════════════════════════════════════════════

def save_hash_file(path: Path) -> Path:
    """
    Compute a file's SHA-256 hash and save it as a sidecar .sha256 file.

    The sidecar file is saved next to the original with a .sha256 extension.
    Example:  dataset.csv.enc  →  dataset.csv.enc.sha256

    This allows integrity verification later without recalculating from scratch
    at decryption time:
        1. Before encrypting: hash_file(plaintext) → save .sha256
        2. Before decrypting: load_and_verify_hash(enc_path) to confirm

    Parameters
    ----------
    path : Path — path to the file to hash

    Returns
    -------
    Path — path to the written .sha256 sidecar file

    Raises
    ------
    IntegrityError — if hash cannot be computed or sidecar cannot be saved
    """
    digest = hash_file(path)
    sidecar = path.with_suffix(path.suffix + ".sha256")
    try:
        sidecar.write_text(digest, encoding="ascii")
    except OSError as exc:
        raise IntegrityError(
            f"Could not save hash sidecar for '{path.name}': {exc}"
        ) from exc
    return sidecar


def load_and_verify_hash(path: Path) -> bool:
    """
    Verify a file against its stored .sha256 sidecar.

    Reads the expected hash from the .sha256 sidecar file (written by
    save_hash_file()) and compares it against the current file hash.

    Parameters
    ----------
    path : Path — path to the file to verify (not to the .sha256 file)

    Returns
    -------
    bool — True if the file matches its stored hash

    Raises
    ------
    IntegrityError — if the sidecar file is missing or unreadable
    FileNotFoundError — if the main file does not exist
    """
    sidecar = path.with_suffix(path.suffix + ".sha256")
    if not sidecar.exists():
        raise IntegrityError(
            f"Hash sidecar not found: {sidecar.name}. "
            "The file integrity cannot be verified without it."
        )
    try:
        expected = sidecar.read_text(encoding="ascii").strip()
    except OSError as exc:
        raise IntegrityError(
            f"Could not read hash sidecar '{sidecar.name}': {exc}"
        ) from exc

    return verify_file_hash(path, expected)


# ══════════════════════════════════════════════════════════════════════════════
# PRE-DECRYPTION VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

def validate_encrypted_file(data: bytes) -> bool:
    """
    Check whether bytes look like a valid AES-256-GCM encrypted payload.

    This is a STRUCTURAL check only — it does not attempt decryption.
    Used as a fast gate before calling decrypt_bytes() to give clearer
    error messages for obviously invalid inputs.

    Checks performed:
        1. Minimum size: must be at least IV (12) + TAG (16) = 28 bytes
           Anything shorter cannot be a valid encrypted payload.
        2. Type check: must be bytes

    NOTE: Passing this check does NOT guarantee the data is correctly
    encrypted with the right key — only decryption will confirm that.
    The GCM authentication tag handles the cryptographic verification.

    Parameters
    ----------
    data : bytes — the candidate encrypted payload

    Returns
    -------
    bool — True if data passes the structural check

    Raises
    ------
    TypeError — if data is not bytes

    Example
    -------
    >>> validate_encrypted_file(b"tiny")       # False (too short)
    False
    >>> validate_encrypted_file(os.urandom(64))  # True (right size)
    True
    """
    if not isinstance(data, bytes):
        raise TypeError(
            f"validate_encrypted_file() expects bytes, got {type(data).__name__}"
        )

    min_size = EncryptionConfig.IV_SIZE_BYTES + EncryptionConfig.TAG_SIZE_BYTES
    return len(data) >= min_size


def is_encrypted_file(path: Path) -> bool:
    """
    Check whether a file looks like an encrypted .enc file.

    Tests:
        1. File must exist and be a regular file
        2. File extension must be .enc (configurable via EncryptionConfig.ENCRYPTED_EXT)
        3. File size must be at least 28 bytes (IV + TAG minimum)

    Parameters
    ----------
    path : Path — path to the file to check

    Returns
    -------
    bool — True if the file appears to be an encrypted .enc file

    Example
    -------
    >>> is_encrypted_file(Path("report.pdf.enc"))
    True
    >>> is_encrypted_file(Path("report.pdf"))
    False
    """
    path = Path(path)
    if not path.exists() or not path.is_file():
        return False
    if path.suffix != EncryptionConfig.ENCRYPTED_EXT:
        return False
    min_size = EncryptionConfig.IV_SIZE_BYTES + EncryptionConfig.TAG_SIZE_BYTES
    return path.stat().st_size >= min_size


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import tempfile

    print("\n" + "=" * 60)
    print("  INTEGRITY MODULE — SELF TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # --- hash_bytes ---
        digest = hash_bytes(b"hello")
        assert len(digest) == 64 and all(c in "0123456789abcdef" for c in digest)
        print(f"\n  hash_bytes()           : 64-char hex digest  ✅")

        # --- hash_file ---
        test_file = tmp_path / "test.csv"
        test_file.write_bytes(b"name,age\nAlice,30\nBob,25")
        file_hash = hash_file(test_file)
        assert len(file_hash) == 64
        print(f"  hash_file()            : {file_hash[:16]}...  ✅")

        # --- verify_file_hash: match ---
        assert verify_file_hash(test_file, file_hash) is True
        print(f"  verify_file_hash()     : correct hash passes  ✅")

        # --- verify_file_hash: mismatch ---
        assert verify_file_hash(test_file, "a" * 64) is False
        print(f"  verify_file_hash()     : wrong hash returns False  ✅")

        # --- sidecar save/load ---
        sidecar = save_hash_file(test_file)
        assert sidecar.exists()
        assert load_and_verify_hash(test_file) is True
        print(f"  sidecar save/load      : round-trip verified  ✅")

        # --- validate_encrypted_file: valid ---
        fake_enc = os.urandom(64)
        assert validate_encrypted_file(fake_enc) is True
        print(f"  validate (valid)       : 64-byte payload passes  ✅")

        # --- validate_encrypted_file: too short ---
        assert validate_encrypted_file(b"tiny") is False
        print(f"  validate (too short)   : 4-byte payload rejected  ✅")

        # --- is_encrypted_file ---
        enc_file = tmp_path / "dataset.csv.enc"
        enc_file.write_bytes(os.urandom(64))
        assert is_encrypted_file(enc_file) is True
        assert is_encrypted_file(test_file) is False
        print(f"  is_encrypted_file()    : .enc detected, .csv rejected  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
