# ─────────────────────────────────────────────────────────────────────────────
# encryption/file_encryptor.py
#
# File-Level Encryption and Decryption with Storage Routing
#
# This module sits between the raw AES engine (aes.py) and the high-level
# orchestrator (secure_storage.py). Its job is purely mechanical:
#
#   1. ENCRYPT A FILE  →  write the .enc file to the right storage directory
#   2. DECRYPT A FILE  →  write the plaintext to decrypted_temp/
#   3. ROUTE FILES     →  datasets/, reports/, or temporary/ based on category
#   4. CLEANUP         →  optionally delete source file after encrypt
#
# STORAGE ROUTING TABLE:
#   Category "dataset"   → storage/encrypted/datasets/<name>.enc
#   Category "report"    → storage/encrypted/reports/<name>.enc
#   Category "temporary" → storage/encrypted/temporary/<name>.enc
#   (default)            → storage/encrypted/datasets/<name>.enc
#
# DECRYPTED TEMP FILES:
#   Decrypted files always land in storage/decrypted_temp/<name>
#   They are NOT automatically cleaned up here — secure_storage.py handles
#   that via cleanup_temp_files(). This separation keeps file_encryptor.py
#   focused on a single responsibility.
#
# LARGE FILE SUPPORT:
#   encrypt_file_chunked() reads in 64 KB chunks to avoid loading entire
#   large datasets into memory at once.
#
# Public API:
#   encrypt_file(src_path, key, category, secure_delete) → Path (.enc path)
#   decrypt_file(enc_path, key, dest_dir) → Path (decrypted path)
#   encrypt_file_chunked(src_path, key, category) → Path (.enc path)
#   get_encrypted_dir(category) → Path
#   list_encrypted_files(category) → list[Path]
#
# Used by:
#   encryption/secure_storage.py — calls encrypt_file() and decrypt_file()
#   tests/test_file_encryptor.py — tests all functions with temp directories
# ─────────────────────────────────────────────────────────────────────────────

import os
import sys
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import (
        EncryptionConfig,
        ENCRYPTED_DATASETS,
        ENCRYPTED_REPORTS,
        ENCRYPTED_TEMPORARY,
        DECRYPTED_TEMP_DIR,
    )
    from encryption.aes import encrypt_bytes, decrypt_bytes, EncryptionError, DecryptionError
    from encryption.integrity import validate_encrypted_file, IntegrityError
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class EncryptionConfig:
        KEY_SIZE_BYTES = 32
        ENCRYPTED_EXT  = ".enc"
        CHUNK_SIZE     = 64 * 1024
        MAX_FILE_SIZE_MB = 500

    _base = Path(__file__).parent.parent / "storage"
    ENCRYPTED_DATASETS  = _base / "encrypted" / "datasets"
    ENCRYPTED_REPORTS   = _base / "encrypted" / "reports"
    ENCRYPTED_TEMPORARY = _base / "encrypted" / "temporary"
    DECRYPTED_TEMP_DIR  = _base / "decrypted_temp"

    from encryption.aes import encrypt_bytes, decrypt_bytes, EncryptionError, DecryptionError
    from encryption.integrity import validate_encrypted_file, IntegrityError


# ══════════════════════════════════════════════════════════════════════════════
# CUSTOM EXCEPTIONS
# ══════════════════════════════════════════════════════════════════════════════

class FileEncryptionError(Exception):
    """
    Raised when encrypting a file fails.

    Wraps EncryptionError and OS-level errors into a single clean type
    so callers in secure_storage.py only need to catch one exception type.
    """


class FileDecryptionError(Exception):
    """
    Raised when decrypting a file fails.

    Covers wrong key, tampered ciphertext, corrupt .enc file, and I/O errors.
    Callers should log these events as CRITICAL security events.
    """


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE ROUTING HELPERS
# ══════════════════════════════════════════════════════════════════════════════

# Maps category strings to their storage directories
_CATEGORY_TO_DIR: dict = {
    "dataset"   : ENCRYPTED_DATASETS,
    "datasets"  : ENCRYPTED_DATASETS,
    "report"    : ENCRYPTED_REPORTS,
    "reports"   : ENCRYPTED_REPORTS,
    "temporary" : ENCRYPTED_TEMPORARY,
    "temp"      : ENCRYPTED_TEMPORARY,
}


def get_encrypted_dir(category: str = "dataset") -> Path:
    """
    Return the encrypted storage directory for the given category.

    Parameters
    ----------
    category : str — one of: "dataset", "report", "temporary"
                     (case-insensitive, plurals accepted)

    Returns
    -------
    Path — the resolved directory path

    Example
    -------
    >>> get_encrypted_dir("report")
    PosixPath('.../storage/encrypted/reports')
    """
    return _CATEGORY_TO_DIR.get(category.lower(), ENCRYPTED_DATASETS)


def _ensure_dirs(category: str) -> tuple:
    """Create storage directories if they don't exist. Returns (enc_dir, temp_dir)."""
    enc_dir  = get_encrypted_dir(category)
    enc_dir.mkdir(parents=True, exist_ok=True)
    DECRYPTED_TEMP_DIR.mkdir(parents=True, exist_ok=True)
    return enc_dir, DECRYPTED_TEMP_DIR


def _check_file_size(path: Path) -> None:
    """Reject files above the configured MAX_FILE_SIZE_MB limit."""
    size_mb = path.stat().st_size / (1024 * 1024)
    if size_mb > EncryptionConfig.MAX_FILE_SIZE_MB:
        raise FileEncryptionError(
            f"File '{path.name}' is {size_mb:.1f} MB, which exceeds the maximum "
            f"allowed size of {EncryptionConfig.MAX_FILE_SIZE_MB} MB. "
            "Split large files before encrypting."
        )


def _secure_delete(path: Path) -> None:
    """
    Delete a plaintext file after encryption.

    NOTE: This performs a simple os.unlink(). For high-security environments,
    a proper secure-erase (overwrite with random bytes before delete) would be
    used. Simple deletion is appropriate for SSDs and most OS environments where
    the OS handles secure storage at the hardware level.
    """
    try:
        path.unlink(missing_ok=True)
    except OSError:
        pass  # Best effort — log at higher level if needed


# ══════════════════════════════════════════════════════════════════════════════
# MAIN ENCRYPT / DECRYPT FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def encrypt_file(
    src_path      : Path,
    key           : bytes,
    category      : str  = "dataset",
    secure_delete : bool = False,
    dest_dir      : Optional[Path] = None,
) -> Path:
    """
    Encrypt a file and save it to the encrypted storage directory.

    Reads the source file, encrypts all bytes with AES-256-GCM, and
    writes a .enc file to the appropriate storage directory. The original
    plaintext file is optionally deleted after successful encryption.

    Encrypted file naming:
        source: uploaded_data.csv
        encrypted: storage/encrypted/datasets/uploaded_data.csv.enc

    Parameters
    ----------
    src_path      : Path — path to the plaintext source file
    key           : bytes — 32-byte AES-256 key
    category      : str  — storage routing: "dataset" | "report" | "temporary"
    secure_delete : bool — if True, delete the plaintext source after encryption
    dest_dir      : Path, optional — override destination directory

    Returns
    -------
    Path — path to the written .enc file

    Raises
    ------
    FileEncryptionError — if source not found, file too large, or encryption fails

    Example
    -------
    >>> enc_path = encrypt_file(Path("data/sales.csv"), key, category="dataset")
    >>> enc_path.name
    'sales.csv.enc'
    """
    src_path = Path(src_path)

    # --- Input validation ---
    if not src_path.exists():
        raise FileEncryptionError(
            f"Source file not found: '{src_path}'. "
            "Verify the path before calling encrypt_file()."
        )
    if not src_path.is_file():
        raise FileEncryptionError(
            f"'{src_path}' is not a regular file."
        )
    _check_file_size(src_path)

    # --- Read plaintext ---
    try:
        plaintext = src_path.read_bytes()
    except OSError as exc:
        raise FileEncryptionError(
            f"Could not read '{src_path.name}': {exc}"
        ) from exc

    # --- Encrypt ---
    try:
        ciphertext = encrypt_bytes(plaintext, key)
    except EncryptionError as exc:
        raise FileEncryptionError(
            f"Encryption failed for '{src_path.name}': {exc}"
        ) from exc

    # --- Write .enc file ---
    enc_dir  = Path(dest_dir) if dest_dir else get_encrypted_dir(category)
    enc_dir.mkdir(parents=True, exist_ok=True)

    enc_name = src_path.name + EncryptionConfig.ENCRYPTED_EXT
    enc_path = enc_dir / enc_name

    try:
        enc_path.write_bytes(ciphertext)
    except OSError as exc:
        raise FileEncryptionError(
            f"Could not write encrypted file '{enc_name}': {exc}"
        ) from exc

    # --- Optional secure delete of plaintext source ---
    if secure_delete:
        _secure_delete(src_path)

    return enc_path


def decrypt_file(
    enc_path : Path,
    key      : bytes,
    dest_dir : Optional[Path] = None,
) -> Path:
    """
    Decrypt an .enc file and save the plaintext to a temporary directory.

    Reads the encrypted file, verifies its structure, decrypts with AES-256-GCM
    (which also verifies the GCM authentication tag), and writes the recovered
    plaintext to decrypted_temp/.

    The caller is responsible for processing the decrypted file and then
    deleting it. Use secure_storage.cleanup_temp_files() to wipe all temp files.

    Decrypted file naming:
        encrypted: storage/encrypted/datasets/sales.csv.enc
        decrypted: storage/decrypted_temp/sales.csv

    Parameters
    ----------
    enc_path : Path — path to the .enc encrypted file
    key      : bytes — the same 32-byte key used during encryption
    dest_dir : Path, optional — override the temp destination directory

    Returns
    -------
    Path — path to the decrypted plaintext file in decrypted_temp/

    Raises
    ------
    FileDecryptionError — if file not found, invalid structure, or decryption fails

    Example
    -------
    >>> plain_path = decrypt_file(Path("storage/encrypted/datasets/sales.csv.enc"), key)
    >>> plain_path.name
    'sales.csv'
    """
    enc_path = Path(enc_path)

    # --- Input validation ---
    if not enc_path.exists():
        raise FileDecryptionError(
            f"Encrypted file not found: '{enc_path}'. "
            "Check that the file exists in the encrypted storage directory."
        )
    if not enc_path.is_file():
        raise FileDecryptionError(
            f"'{enc_path}' is not a regular file."
        )

    # --- Read ciphertext ---
    try:
        ciphertext = enc_path.read_bytes()
    except OSError as exc:
        raise FileDecryptionError(
            f"Could not read encrypted file '{enc_path.name}': {exc}"
        ) from exc

    # --- Pre-decryption structural check ---
    if not validate_encrypted_file(ciphertext):
        raise FileDecryptionError(
            f"'{enc_path.name}' is too small to be a valid encrypted file "
            f"({len(ciphertext)} bytes). The file may be corrupted or not encrypted."
        )

    # --- Decrypt (GCM tag verification happens here) ---
    try:
        plaintext = decrypt_bytes(ciphertext, key)
    except DecryptionError as exc:
        raise FileDecryptionError(
            f"Decryption failed for '{enc_path.name}': {exc}. "
            "The file may be corrupted, tampered with, or a different key was used."
        ) from exc

    # --- Write decrypted output to temp directory ---
    temp_dir = Path(dest_dir) if dest_dir else DECRYPTED_TEMP_DIR
    temp_dir.mkdir(parents=True, exist_ok=True)

    # Remove the .enc extension to restore the original filename
    if enc_path.name.endswith(EncryptionConfig.ENCRYPTED_EXT):
        orig_name = enc_path.name[: -len(EncryptionConfig.ENCRYPTED_EXT)]
    else:
        orig_name = enc_path.name + ".decrypted"

    out_path = temp_dir / orig_name

    try:
        out_path.write_bytes(plaintext)
    except OSError as exc:
        raise FileDecryptionError(
            f"Could not write decrypted file '{orig_name}': {exc}"
        ) from exc

    return out_path


# ══════════════════════════════════════════════════════════════════════════════
# CHUNKED ENCRYPTION (for very large files)
# ══════════════════════════════════════════════════════════════════════════════

def encrypt_file_chunked(
    src_path      : Path,
    key           : bytes,
    category      : str  = "dataset",
    secure_delete : bool = False,
) -> Path:
    """
    Encrypt a large file by reading it in 64 KB chunks.

    Behaves identically to encrypt_file() but avoids loading the entire
    file into memory at once. Recommended for files > 100 MB.

    The entire file is still encrypted as a single AES-GCM operation —
    chunking is only for the reading phase, not the crypto operation.

    For true streaming encryption of multi-GB files, a different approach
    (e.g., encrypting each chunk independently with its own IV) would be
    needed. This function covers the common analytics dataset use case.

    Parameters
    ----------
    src_path      : Path — path to the source file
    key           : bytes — 32-byte AES-256 key
    category      : str  — storage routing category
    secure_delete : bool — delete plaintext source after encryption

    Returns
    -------
    Path — path to the written .enc file
    """
    src_path = Path(src_path)

    if not src_path.exists() or not src_path.is_file():
        raise FileEncryptionError(
            f"Source file not found or is not a regular file: '{src_path}'"
        )
    _check_file_size(src_path)

    # Read in chunks and assemble into one bytes object
    chunks = []
    try:
        with src_path.open("rb") as fh:
            while True:
                block = fh.read(EncryptionConfig.CHUNK_SIZE)
                if not block:
                    break
                chunks.append(block)
    except OSError as exc:
        raise FileEncryptionError(
            f"Could not read '{src_path.name}' during chunked encryption: {exc}"
        ) from exc

    plaintext = b"".join(chunks)

    try:
        ciphertext = encrypt_bytes(plaintext, key)
    except EncryptionError as exc:
        raise FileEncryptionError(str(exc)) from exc

    enc_dir  = get_encrypted_dir(category)
    enc_dir.mkdir(parents=True, exist_ok=True)
    enc_path = enc_dir / (src_path.name + EncryptionConfig.ENCRYPTED_EXT)

    try:
        enc_path.write_bytes(ciphertext)
    except OSError as exc:
        raise FileEncryptionError(
            f"Could not write chunked encrypted file: {exc}"
        ) from exc

    if secure_delete:
        _secure_delete(src_path)

    return enc_path


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE LISTING UTILITIES
# ══════════════════════════════════════════════════════════════════════════════

def list_encrypted_files(category: str = "dataset") -> list:
    """
    List all encrypted .enc files in a storage category directory.

    Parameters
    ----------
    category : str — "dataset" | "report" | "temporary"

    Returns
    -------
    list[Path] — sorted list of .enc file paths

    Example
    -------
    >>> files = list_encrypted_files("dataset")
    >>> [f.name for f in files]
    ['sales_q3.csv.enc', 'sales_q4.csv.enc']
    """
    enc_dir = get_encrypted_dir(category)
    if not enc_dir.exists():
        return []
    return sorted(
        f for f in enc_dir.iterdir()
        if f.is_file() and f.suffix == EncryptionConfig.ENCRYPTED_EXT
    )


def list_temp_files() -> list:
    """
    List all files currently in the decrypted_temp directory.

    Returns
    -------
    list[Path] — sorted list of temporary decrypted file paths
    """
    if not DECRYPTED_TEMP_DIR.exists():
        return []
    return sorted(f for f in DECRYPTED_TEMP_DIR.iterdir() if f.is_file())


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import os
    import tempfile
    from encryption.key_manager import generate_key

    print("\n" + "=" * 60)
    print("  FILE ENCRYPTOR — SELF TEST")
    print("=" * 60)

    key = generate_key()

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        enc_dir  = tmp_path / "encrypted"
        dec_dir  = tmp_path / "decrypted_temp"

        # --- Create a test CSV ---
        csv_file = tmp_path / "sales_q3.csv"
        csv_content = b"product,revenue,quarter\nWidget A,150000,Q3\nWidget B,220000,Q3"
        csv_file.write_bytes(csv_content)
        print(f"\n  Source file    : {csv_file.name}  ({len(csv_content)} bytes)")

        # --- Encrypt ---
        enc_path = encrypt_file(csv_file, key, dest_dir=enc_dir)
        assert enc_path.exists()
        assert enc_path.suffix == ".enc"
        print(f"  Encrypted to   : {enc_path.name}  ({enc_path.stat().st_size} bytes)  ✅")

        # --- .enc is unreadable as plaintext ---
        enc_bytes = enc_path.read_bytes()
        assert csv_content not in enc_bytes
        print(f"  Plaintext not readable from .enc file  ✅")

        # --- Decrypt ---
        dec_path = decrypt_file(enc_path, key, dest_dir=dec_dir)
        assert dec_path.exists()
        assert dec_path.read_bytes() == csv_content
        print(f"  Decrypted to   : {dec_path.name}  ✅  (content matches original)")

        # --- Wrong key ---
        wrong_key = generate_key()
        try:
            decrypt_file(enc_path, wrong_key, dest_dir=dec_dir)
            print("  Wrong key      : ❌ FAIL — accepted wrong key")
        except FileDecryptionError:
            print(f"  Wrong key      : correctly rejected  ✅")

        # --- JSON file round-trip ---
        json_file = tmp_path / "report.json"
        json_content = b'{"quarter":"Q3","revenue":4200000,"currency":"USD"}'
        json_file.write_bytes(json_content)
        enc_json = encrypt_file(json_file, key, category="report", dest_dir=enc_dir)
        dec_json = decrypt_file(enc_json, key, dest_dir=dec_dir)
        assert dec_json.read_bytes() == json_content
        print(f"  JSON round-trip : {json_file.name} → {enc_json.name} → {dec_json.name}  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
