# ─────────────────────────────────────────────────────────────────────────────
# encryption/aes.py
#
# AES-256-GCM Encryption Engine
#
# This is the core cryptographic module. It handles all low-level AES operations
# using the PyCA `cryptography` library — the industry standard for Python crypto.
#
# WHY AES-256-GCM?
#   AES-256-GCM is an "Authenticated Encryption with Associated Data" (AEAD) mode.
#   It provides TWO guarantees in a single primitive:
#     1. CONFIDENTIALITY — ciphertext reveals nothing about the plaintext
#     2. INTEGRITY       — any tampering with the ciphertext is detected
#
#   This means we do NOT need a separate HMAC or SHA check — GCM does it for us.
#   It's the mode used by TLS 1.3, Google Cloud, and AWS for data at rest.
#
# WIRE FORMAT (what we store in .enc files):
#   ┌──────────────┬───────────────┬──────────────────────────┐
#   │  IV (12 B)   │  TAG (16 B)   │  CIPHERTEXT (variable)   │
#   └──────────────┴───────────────┴──────────────────────────┘
#   Total overhead per encrypted value: 28 bytes
#
# SECURITY RULES FOLLOWED:
#   ✅ Fresh random 12-byte IV generated for EVERY encrypt call
#   ✅ IV is NEVER reused (IV reuse with the same key breaks GCM security)
#   ✅ Raw cryptographic exceptions are caught and re-raised as safe custom types
#   ✅ No custom cryptographic algorithms
#   ✅ No hardcoded keys or IVs
#   ✅ Authenticated encryption — tampered data fails decryption
#
# Public API:
#   encrypt_bytes(plaintext, key) → bytes        (raw bytes in, encrypted bytes out)
#   decrypt_bytes(ciphertext, key) → bytes        (encrypted bytes in, plaintext out)
#   encrypt_text(plaintext, key) → bytes          (string in, encrypted bytes out)
#   decrypt_text(ciphertext, key) → str           (encrypted bytes in, string out)
#   encrypt_file(src_path, key) → bytes           (file path in, encrypted bytes out)
#   decrypt_file(ciphertext, key) → bytes         (encrypted bytes in, file bytes out)
#
# Used by:
#   encryption/file_encryptor.py  — calls encrypt_bytes / decrypt_bytes
#   encryption/secure_storage.py  — calls encrypt_bytes / decrypt_bytes indirectly
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path

# ── Graceful settings import ──────────────────────────────────────────────────
# Works whether run as a standalone script or imported as part of the package.

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import EncryptionConfig
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class EncryptionConfig:
        KEY_SIZE_BYTES = 32
        IV_SIZE_BYTES  = 12
        TAG_SIZE_BYTES = 16
        CHUNK_SIZE     = 64 * 1024

# ── Cryptography library import ───────────────────────────────────────────────

try:
    from cryptography.hazmat.primitives.ciphers.aead import AESGCM
    _HAS_CRYPTO = True
except ImportError:
    _HAS_CRYPTO = False


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTION TYPES
# ══════════════════════════════════════════════════════════════════════════════

class EncryptionError(Exception):
    """
    Raised when encryption fails.

    Callers catch this instead of raw cryptographic exceptions so that
    sensitive internal details never leak into application-level error handling.

    Example:
        try:
            cipher = encrypt_bytes(data, key)
        except EncryptionError as e:
            logger.error(f"Encryption failed: {e}")
    """


class DecryptionError(Exception):
    """
    Raised when decryption fails.

    Common causes:
        - Wrong key supplied
        - Ciphertext was tampered with (GCM tag mismatch)
        - Data is truncated or corrupted (not a valid .enc file)
        - IV/ciphertext extracted from wrong offsets

    Security note: the error message intentionally does NOT reveal
    whether it was a wrong key vs a tampered file. Both are reported
    as a generic decryption failure to prevent oracle attacks.

    Example:
        try:
            plain = decrypt_bytes(cipher, key)
        except DecryptionError as e:
            audit.log_system_event(f"Decryption failed: {e}", severity="CRITICAL")
    """


# ══════════════════════════════════════════════════════════════════════════════
# INTERNAL VALIDATION HELPERS
# ══════════════════════════════════════════════════════════════════════════════

def _require_crypto() -> None:
    """Raise ImportError with a clear install message if cryptography is missing."""
    if not _HAS_CRYPTO:
        raise ImportError(
            "The 'cryptography' package is required for encryption.\n"
            "Install it with:  pip install cryptography"
        )


def _validate_key(key: bytes) -> None:
    """
    Confirm the key is exactly 32 bytes (256 bits).

    Why 32 bytes exactly?
        AES-256 requires a 256-bit key. Shorter keys use AES-128 or AES-192,
        which provide weaker security guarantees. We enforce the exact size
        so there is no ambiguity about which AES variant is being used.

    Raises
    ------
    EncryptionError if the key length is wrong.
    """
    if not isinstance(key, bytes):
        raise EncryptionError(
            f"Encryption key must be bytes, got {type(key).__name__}. "
            "Use key_manager.load_key() to obtain a valid key."
        )
    if len(key) != EncryptionConfig.KEY_SIZE_BYTES:
        raise EncryptionError(
            f"Invalid key length: {len(key)} bytes. "
            f"AES-256 requires exactly {EncryptionConfig.KEY_SIZE_BYTES} bytes (256 bits). "
            "Use key_manager.generate_key() to create a valid key."
        )


def _validate_ciphertext(data: bytes) -> None:
    """
    Confirm the ciphertext is at least IV + TAG bytes long.

    A valid encrypted blob must contain at minimum:
        12 bytes (IV) + 16 bytes (GCM tag) = 28 bytes

    Anything shorter cannot possibly be a valid encrypted payload and
    likely indicates a truncated file or an incorrect input.

    Raises
    ------
    DecryptionError if the data is too short to be a valid ciphertext.
    """
    min_size = EncryptionConfig.IV_SIZE_BYTES + EncryptionConfig.TAG_SIZE_BYTES
    if len(data) < min_size:
        raise DecryptionError(
            f"Ciphertext too short: {len(data)} bytes. "
            f"Minimum valid size is {min_size} bytes (IV + GCM tag). "
            "The file may be corrupted, truncated, or is not an encrypted file."
        )


# ══════════════════════════════════════════════════════════════════════════════
# CORE ENCRYPTION / DECRYPTION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def encrypt_bytes(plaintext: bytes, key: bytes) -> bytes:
    """
    Encrypt arbitrary bytes using AES-256-GCM.

    This is the primary building block used by all other encrypt functions.
    Every call generates a fresh random IV — the same plaintext encrypted
    twice will produce two different ciphertexts (semantic security).

    Wire format of returned bytes:
        [ IV (12 bytes) ][ GCM TAG (16 bytes) ][ CIPHERTEXT (N bytes) ]

    The GCM tag authenticates both the IV and the ciphertext, so any
    bit-flip anywhere in the returned bytes will be detected on decryption.

    Parameters
    ----------
    plaintext : bytes — the data to encrypt (any length, including empty)
    key       : bytes — 32-byte AES-256 key (from key_manager.load_key())

    Returns
    -------
    bytes — IV + TAG + CIPHERTEXT packed together

    Raises
    ------
    EncryptionError — if key is invalid or encryption fails unexpectedly
    ImportError     — if the cryptography package is not installed

    Example
    -------
    >>> key = key_manager.generate_key()
    >>> cipher = encrypt_bytes(b"sensitive data", key)
    >>> len(cipher)  # always 28 bytes longer than plaintext
    42
    """
    _require_crypto()
    _validate_key(key)

    try:
        # Generate a fresh 12-byte random IV (nonce) for this encryption only.
        # NEVER reuse this IV with the same key — doing so breaks GCM security.
        iv = os.urandom(EncryptionConfig.IV_SIZE_BYTES)

        # Create the AES-GCM cipher object with our 256-bit key
        aesgcm = AESGCM(key)

        # Encrypt and authenticate.
        # AESGCM.encrypt() returns CIPHERTEXT + TAG concatenated (tag is last 16 bytes).
        # We rearrange to store:  IV | TAG | CIPHERTEXT  (makes IV extraction trivial)
        encrypted_with_tag = aesgcm.encrypt(iv, plaintext, associated_data=None)

        # encrypted_with_tag layout from PyCA: CIPHERTEXT || TAG (tag appended at end)
        tag        = encrypted_with_tag[-EncryptionConfig.TAG_SIZE_BYTES:]
        ciphertext = encrypted_with_tag[:-EncryptionConfig.TAG_SIZE_BYTES]

        # Final layout stored to disk: IV || TAG || CIPHERTEXT
        return iv + tag + ciphertext

    except (EncryptionError, ImportError):
        raise
    except Exception as exc:
        # Never expose raw cryptographic exception details to callers
        raise EncryptionError(
            f"Encryption failed unexpectedly. "
            "Check that the key is valid and the cryptography library is installed."
        ) from exc


def decrypt_bytes(data: bytes, key: bytes) -> bytes:
    """
    Decrypt AES-256-GCM encrypted bytes and verify integrity.

    The GCM authentication tag is verified BEFORE any plaintext is returned.
    If the tag check fails (wrong key, tampered data, corrupted file),
    a DecryptionError is raised immediately and no plaintext is exposed.

    Expected wire format of `data`:
        [ IV (12 bytes) ][ GCM TAG (16 bytes) ][ CIPHERTEXT (N bytes) ]

    Parameters
    ----------
    data : bytes — the encrypted payload produced by encrypt_bytes()
    key  : bytes — the same 32-byte key used during encryption

    Returns
    -------
    bytes — the original plaintext

    Raises
    ------
    DecryptionError — if the key is wrong, ciphertext is tampered, or data is corrupted
    ImportError     — if the cryptography package is not installed

    Example
    -------
    >>> plain = decrypt_bytes(cipher, key)
    >>> plain == b"sensitive data"
    True
    """
    _require_crypto()
    _validate_key(key)
    _validate_ciphertext(data)

    try:
        iv_len  = EncryptionConfig.IV_SIZE_BYTES
        tag_len = EncryptionConfig.TAG_SIZE_BYTES

        # Unpack wire format:  IV || TAG || CIPHERTEXT
        iv         = data[:iv_len]
        tag        = data[iv_len : iv_len + tag_len]
        ciphertext = data[iv_len + tag_len:]

        aesgcm = AESGCM(key)

        # PyCA AESGCM.decrypt() expects:  CIPHERTEXT || TAG
        # It raises InvalidTag if authentication fails — we catch and re-raise safely
        plaintext = aesgcm.decrypt(iv, ciphertext + tag, associated_data=None)
        return plaintext

    except DecryptionError:
        raise
    except Exception as exc:
        # Map ALL cryptographic failures to one safe message.
        # This prevents attackers from distinguishing "wrong key" vs "tampered data".
        raise DecryptionError(
            "Decryption failed. The file may be corrupted, tampered with, "
            "or the wrong encryption key was supplied."
        ) from exc


# ── Text convenience wrappers ─────────────────────────────────────────────────

def encrypt_text(plaintext: str, key: bytes, encoding: str = "utf-8") -> bytes:
    """
    Encrypt a Unicode string using AES-256-GCM.

    Encodes the string to bytes first (default UTF-8), then delegates to
    encrypt_bytes(). This is the recommended function for encrypting text fields,
    API responses, configuration values, and log content.

    Parameters
    ----------
    plaintext : str  — the text to encrypt
    key       : bytes — 32-byte AES-256 key
    encoding  : str  — text encoding (default UTF-8)

    Returns
    -------
    bytes — encrypted payload (IV + TAG + CIPHERTEXT)

    Raises
    ------
    EncryptionError — if key invalid or encryption fails
    """
    if not isinstance(plaintext, str):
        raise EncryptionError(
            f"encrypt_text() expects a str, got {type(plaintext).__name__}. "
            "Use encrypt_bytes() for binary data."
        )
    return encrypt_bytes(plaintext.encode(encoding), key)


def decrypt_text(data: bytes, key: bytes, encoding: str = "utf-8") -> str:
    """
    Decrypt AES-256-GCM encrypted bytes back to a Unicode string.

    Decrypts to bytes first, then decodes to str. Raises DecryptionError
    if decryption fails for any reason (wrong key, tampered data, etc.).

    Parameters
    ----------
    data     : bytes — encrypted payload produced by encrypt_text()
    key      : bytes — the same 32-byte key used during encryption
    encoding : str   — expected text encoding (default UTF-8)

    Returns
    -------
    str — the original plaintext string

    Raises
    ------
    DecryptionError — if decryption or UTF-8 decoding fails
    """
    raw = decrypt_bytes(data, key)
    try:
        return raw.decode(encoding)
    except UnicodeDecodeError as exc:
        raise DecryptionError(
            "Decryption succeeded but the result is not valid UTF-8. "
            "The data may have been encrypted with a different encoding."
        ) from exc


# ── File convenience wrappers ─────────────────────────────────────────────────

def encrypt_file(src_path: Path, key: bytes) -> bytes:
    """
    Read a file from disk and return its encrypted bytes.

    The file is read in one call (suitable for files up to ~500 MB as
    configured in EncryptionConfig.MAX_FILE_SIZE_MB). For production
    streaming of very large files, use file_encryptor.py which handles
    chunked reading.

    Parameters
    ----------
    src_path : Path  — path to the plaintext source file
    key      : bytes — 32-byte AES-256 key

    Returns
    -------
    bytes — the encrypted payload ready to be written to an .enc file

    Raises
    ------
    EncryptionError — if the file is missing or encryption fails
    FileNotFoundError — if src_path does not exist
    """
    src_path = Path(src_path)
    if not src_path.exists():
        raise FileNotFoundError(
            f"Source file not found: {src_path}. "
            "Ensure the file exists before calling encrypt_file()."
        )
    if not src_path.is_file():
        raise EncryptionError(
            f"Path is not a file: {src_path}. Only regular files can be encrypted."
        )

    try:
        plaintext = src_path.read_bytes()
    except OSError as exc:
        raise EncryptionError(
            f"Could not read file '{src_path.name}': {exc}"
        ) from exc

    return encrypt_bytes(plaintext, key)


def decrypt_file(data: bytes, key: bytes) -> bytes:
    """
    Decrypt an encrypted file payload and return the original file bytes.

    This is the inverse of encrypt_file(). The caller is responsible for
    writing the returned bytes to a destination file path.

    Parameters
    ----------
    data : bytes — the encrypted payload read from an .enc file
    key  : bytes — the same 32-byte key used during encryption

    Returns
    -------
    bytes — the original file contents (ready to write to disk)

    Raises
    ------
    DecryptionError — if decryption or integrity verification fails
    """
    return decrypt_bytes(data, key)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  AES-256-GCM ENGINE — SELF TEST")
    print("=" * 60)

    # Generate a fresh 32-byte key inline for demo purposes only
    test_key = os.urandom(32)
    print(f"\n  Key generated : {len(test_key)} bytes  ✅")

    # --- Text round-trip ---
    original_text = "Sensitive analytics data: Q3 revenue = $4,200,000"
    encrypted     = encrypt_text(original_text, test_key)
    decrypted     = decrypt_text(encrypted, test_key)

    assert decrypted == original_text, "Text round-trip FAILED"
    print(f"  Text encrypt  : {len(original_text)} chars → {len(encrypted)} bytes ciphertext  ✅")
    print(f"  Text decrypt  : '{decrypted[:40]}...'  ✅")

    # --- IV uniqueness check ---
    enc1 = encrypt_bytes(b"same data", test_key)
    enc2 = encrypt_bytes(b"same data", test_key)
    assert enc1 != enc2, "IV uniqueness FAILED — same ciphertext produced twice!"
    print(f"  IV uniqueness : two encryptions of same data produce different ciphertext  ✅")

    # --- Bytes round-trip ---
    binary_data = os.urandom(1024)  # simulate 1 KB of random binary data
    enc_bin     = encrypt_bytes(binary_data, test_key)
    dec_bin     = decrypt_bytes(enc_bin, test_key)
    assert dec_bin == binary_data, "Binary round-trip FAILED"
    print(f"  Binary data   : 1024 bytes encrypted and decrypted correctly  ✅")

    # --- Tamper detection ---
    tampered = bytearray(encrypted)
    tampered[20] ^= 0xFF          # flip bits in the ciphertext region
    try:
        decrypt_text(bytes(tampered), test_key)
        print("  Tamper detect : ❌ FAIL — tampered ciphertext was accepted!")
    except DecryptionError:
        print(f"  Tamper detect : tampered ciphertext correctly rejected  ✅")

    # --- Wrong key detection ---
    wrong_key = os.urandom(32)
    try:
        decrypt_text(encrypted, wrong_key)
        print("  Wrong key     : ❌ FAIL — wrong key was accepted!")
    except DecryptionError:
        print(f"  Wrong key     : wrong key correctly rejected  ✅")

    # --- Wire format verification ---
    iv_size  = EncryptionConfig.IV_SIZE_BYTES
    tag_size = EncryptionConfig.TAG_SIZE_BYTES
    sample   = encrypt_bytes(b"hello", test_key)
    assert len(sample) == iv_size + tag_size + len(b"hello"), "Wire format FAILED"
    print(f"  Wire format   : IV({iv_size}B) + TAG({tag_size}B) + plaintext = {len(sample)}B  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
