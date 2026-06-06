# ─────────────────────────────────────────────────────────────────────────────
# encryption/secure_storage.py
#
# High-Level Encrypted Storage Orchestrator
#
# This is the module that APPLICATION CODE should call. It combines:
#   - File encryption/decryption    (file_encryptor.py)
#   - Key management                (key_manager.py)
#   - Audit logging                 (guards/audit_logger.py)
#   - Temporary file cleanup        (our own cleanup_temp_files())
#
# DESIGN PRINCIPLE:
#   Application code should NEVER call aes.py or file_encryptor.py directly.
#   It should only call secure_storage.py. This means:
#     - One call stores a dataset:  SecureStorage.store_dataset(path)
#     - One call retrieves it:      SecureStorage.retrieve_dataset(enc_path)
#     - One call cleans up:         SecureStorage.cleanup_temp_files()
#
#   Audit logging happens automatically inside each method — callers don't
#   need to remember to log anything.
#
# AUDIT LOGGING INTEGRATION:
#   Uses the existing AuditLogger from guards/audit_logger.py via
#   log_system_event() for all encryption events. This means encryption
#   events appear in security.log and system_events.log alongside prompt
#   injection events — one unified audit trail.
#
# Public API:
#   SecureStorage (class)
#     .store_dataset(path, secure_delete) → Path
#     .store_report(path, secure_delete)  → Path
#     .store_temp_file(path)              → Path
#     .retrieve_dataset(enc_path) → Path
#     .retrieve_report(enc_path)  → Path
#     .cleanup_temp_files(max_age_seconds) → int
#     .list_stored(category) → list[dict]
#
#   Module-level convenience functions:
#     store_dataset(path) → Path
#     retrieve_dataset(enc_path) → Path
#     cleanup_temp_files() → int
#     get_secure_storage() → SecureStorage  (singleton)
#
# Used by:
#   Application code (future Xplor API handlers)
#   tests/test_file_encryptor.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import time
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

# ── Graceful settings import ──────────────────────────────────────────────────

try:
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import (
        EncryptionConfig,
        DECRYPTED_TEMP_DIR,
        ENCRYPTED_DATASETS,
        ENCRYPTED_REPORTS,
        ENCRYPTED_TEMPORARY,
        KEYS_DIR,
    )
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class EncryptionConfig:
        TEMP_FILE_LIFETIME = 3600
        MAX_FILE_SIZE_MB   = 500
        ENCRYPTED_EXT      = ".enc"

    _base              = Path(__file__).parent.parent / "storage"
    DECRYPTED_TEMP_DIR = _base / "decrypted_temp"
    ENCRYPTED_DATASETS = _base / "encrypted" / "datasets"
    ENCRYPTED_REPORTS  = _base / "encrypted" / "reports"
    ENCRYPTED_TEMPORARY= _base / "encrypted" / "temporary"
    KEYS_DIR           = _base / "keys"

# ── Local module imports ──────────────────────────────────────────────────────

from encryption.key_manager import (
    load_key, get_key, clear_key_cache, generate_key, save_key,
    KeyError_, InvalidKeyError,
)
from encryption.file_encryptor import (
    encrypt_file, decrypt_file, encrypt_file_chunked,
    list_encrypted_files, list_temp_files,
    FileEncryptionError, FileDecryptionError,
)
from encryption.integrity import (
    hash_file, verify_file_hash, save_hash_file,
    validate_encrypted_file, IntegrityError,
)

# ── Audit logger integration (graceful — works without the guards module) ─────

try:
    from guards.audit_logger import get_audit_logger
    _audit = get_audit_logger()
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
    _audit = None


def _log_event(message: str, severity: str = "INFO") -> None:
    """
    Log a security event to the audit logger if available,
    otherwise fall back to the Python standard logging module.
    """
    if _HAS_AUDIT and _audit is not None:
        try:
            _audit.log_system_event(message, severity=severity, module_name="SecureStorage")
        except Exception:
            pass  # never let audit failure crash the encryption operation
    else:
        level = getattr(logging, severity, logging.INFO)
        logging.getLogger("security.encryption.secure_storage").log(level, message)


# ══════════════════════════════════════════════════════════════════════════════
# SECURE STORAGE CLASS
# ══════════════════════════════════════════════════════════════════════════════

class SecureStorage:
    """
    High-level encrypted file storage for the Xplor analytics platform.

    This is the public interface for all encrypted file operations.
    It combines encryption, key management, and audit logging into single
    method calls so application code stays clean and audit events are
    never accidentally omitted.

    Usage:
        storage = SecureStorage()
        enc_path = storage.store_dataset(Path("uploads/revenue_q3.csv"))
        # ... revenue_q3.csv is now encrypted at rest

        temp_path = storage.retrieve_dataset(enc_path)
        # ... do analytics work on temp_path

        storage.cleanup_temp_files()
        # ... temp plaintext is wiped

    Key loading:
        On construction, the key is loaded using key_manager.load_key().
        Set XPLOR_ENCRYPTION_KEY in your .env file or generate a key file
        with key_manager.save_key(key_manager.generate_key()).

    Audit logging:
        Every store/retrieve/cleanup/failure writes to the existing
        AuditLogger (security.log and system_events.log).
    """

    def __init__(
        self,
        key            : Optional[bytes] = None,
        allow_generate : bool = False,
    ):
        """
        Initialise the secure storage layer.

        Parameters
        ----------
        key            : bytes, optional — inject a key directly (for tests)
        allow_generate : bool            — allow auto-generating key if none found

        Raises
        ------
        KeyError_ — if no key is found and allow_generate=False
        """
        if key is not None:
            from encryption.key_manager import validate_key
            validate_key(key)
            self._key = key
        else:
            self._key = get_key(allow_generate=allow_generate)

        # Ensure all storage directories exist
        for d in [DECRYPTED_TEMP_DIR, ENCRYPTED_DATASETS, ENCRYPTED_REPORTS,
                  ENCRYPTED_TEMPORARY, KEYS_DIR]:
            d.mkdir(parents=True, exist_ok=True)

        _log_event("SecureStorage initialised", severity="INFO")

    # ══ Dataset operations ════════════════════════════════════════════════════

    def store_dataset(
        self,
        src_path      : Path,
        secure_delete : bool = False,
    ) -> Path:
        """
        Encrypt and store an uploaded dataset file.

        Accepts CSV, Excel, JSON, or any file format used for analytics data.
        Writes the encrypted file to storage/encrypted/datasets/.

        Parameters
        ----------
        src_path      : Path — path to the plaintext dataset file
        secure_delete : bool — delete the source plaintext after encryption

        Returns
        -------
        Path — path to the encrypted .enc file

        Raises
        ------
        FileEncryptionError — if encryption fails
        """
        src_path = Path(src_path)
        try:
            enc_path = encrypt_file(
                src_path, self._key, category="dataset",
                secure_delete=secure_delete,
            )
            _log_event(
                f"Dataset encrypted successfully: '{src_path.name}' → '{enc_path.name}' "
                f"({enc_path.stat().st_size} bytes)",
                severity="INFO",
            )
            return enc_path
        except FileEncryptionError as exc:
            _log_event(
                f"Dataset encryption FAILED: '{src_path.name}' — {exc}",
                severity="CRITICAL",
            )
            raise

    def retrieve_dataset(self, enc_path: Path) -> Path:
        """
        Decrypt an encrypted dataset for authorized processing.

        Writes the decrypted file to storage/decrypted_temp/.
        Call cleanup_temp_files() after processing to wipe the plaintext.

        Parameters
        ----------
        enc_path : Path — path to the .enc encrypted dataset file

        Returns
        -------
        Path — path to the decrypted temporary file

        Raises
        ------
        FileDecryptionError — if decryption or integrity check fails
        """
        enc_path = Path(enc_path)
        try:
            temp_path = decrypt_file(enc_path, self._key)
            _log_event(
                f"Dataset decrypted successfully: '{enc_path.name}' → '{temp_path.name}'",
                severity="INFO",
            )
            return temp_path
        except FileDecryptionError as exc:
            _log_event(
                f"Dataset decryption FAILED: '{enc_path.name}' — {exc}",
                severity="CRITICAL",
            )
            raise

    # ══ Report operations ═════════════════════════════════════════════════════

    def store_report(
        self,
        src_path      : Path,
        secure_delete : bool = False,
    ) -> Path:
        """
        Encrypt and store an analytics report.

        Writes encrypted output to storage/encrypted/reports/.

        Parameters / Returns / Raises: same as store_dataset().
        """
        src_path = Path(src_path)
        try:
            enc_path = encrypt_file(
                src_path, self._key, category="report",
                secure_delete=secure_delete,
            )
            _log_event(
                f"Report encrypted successfully: '{src_path.name}' → '{enc_path.name}'",
                severity="INFO",
            )
            return enc_path
        except FileEncryptionError as exc:
            _log_event(
                f"Report encryption FAILED: '{src_path.name}' — {exc}",
                severity="CRITICAL",
            )
            raise

    def retrieve_report(self, enc_path: Path) -> Path:
        """
        Decrypt an encrypted analytics report for authorized download.

        Parameters / Returns / Raises: same as retrieve_dataset().
        """
        enc_path = Path(enc_path)
        try:
            temp_path = decrypt_file(enc_path, self._key)
            _log_event(
                f"Report decrypted successfully: '{enc_path.name}'",
                severity="INFO",
            )
            return temp_path
        except FileDecryptionError as exc:
            _log_event(
                f"Report decryption FAILED: '{enc_path.name}' — {exc}",
                severity="CRITICAL",
            )
            raise

    # ══ Temporary file operations ═════════════════════════════════════════════

    def store_temp_file(self, src_path: Path) -> Path:
        """
        Encrypt a short-lived processing file in storage/encrypted/temporary/.

        These files are expected to have a short lifespan (within one
        processing pipeline run). Use cleanup_temp_files() to remove them.

        Parameters / Returns / Raises: same as store_dataset().
        """
        src_path = Path(src_path)
        try:
            enc_path = encrypt_file(
                src_path, self._key, category="temporary", secure_delete=True
            )
            _log_event(
                f"Temp file encrypted: '{src_path.name}' → '{enc_path.name}'",
                severity="INFO",
            )
            return enc_path
        except FileEncryptionError as exc:
            _log_event(
                f"Temp file encryption FAILED: '{src_path.name}' — {exc}",
                severity="WARNING",
            )
            raise

    # ══ Cleanup ═══════════════════════════════════════════════════════════════

    def cleanup_temp_files(self, max_age_seconds: Optional[int] = None) -> int:
        """
        Securely delete all files in the decrypted_temp directory.

        Removes plaintext files that were written during decryption.
        This should be called after analytics processing is complete
        to ensure plaintext never lingers unnecessarily.

        Parameters
        ----------
        max_age_seconds : int, optional — only delete files older than this
                          many seconds. Defaults to EncryptionConfig.TEMP_FILE_LIFETIME
                          (3600 seconds = 1 hour). Pass 0 to delete everything.

        Returns
        -------
        int — number of files deleted

        Example
        -------
        >>> deleted = storage.cleanup_temp_files(max_age_seconds=0)  # wipe all
        >>> deleted
        3
        """
        max_age = max_age_seconds if max_age_seconds is not None else EncryptionConfig.TEMP_FILE_LIFETIME
        now     = time.time()
        deleted = 0

        temp_files = list_temp_files()
        for f in temp_files:
            try:
                age = now - f.stat().st_mtime
                if age >= max_age:
                    f.unlink(missing_ok=True)
                    deleted += 1
            except OSError:
                pass  # best effort

        if deleted > 0:
            _log_event(
                f"Cleanup: {deleted} temporary decrypted file(s) wiped from decrypted_temp/",
                severity="INFO",
            )
        return deleted

    # ══ Listing ══════════════════════════════════════════════════════════════

    def list_stored(self, category: str = "dataset") -> list:
        """
        List all encrypted files in a storage category with metadata.

        Parameters
        ----------
        category : str — "dataset" | "report" | "temporary"

        Returns
        -------
        list[dict] — each dict contains: name, size_bytes, modified_at, path
        """
        files = list_encrypted_files(category)
        result = []
        for f in files:
            try:
                stat = f.stat()
                result.append({
                    "name"       : f.name,
                    "size_bytes" : stat.st_size,
                    "modified_at": datetime.fromtimestamp(
                        stat.st_mtime, tz=timezone.utc
                    ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    "path"       : str(f),
                })
            except OSError:
                pass
        return result

    # ══ Integrity verification ════════════════════════════════════════════════

    def verify_integrity(self, enc_path: Path) -> bool:
        """
        Verify the structural integrity of an encrypted file.

        Performs a pre-decryption size/structure check. Does NOT decrypt
        the file — use retrieve_dataset() for that.

        Parameters
        ----------
        enc_path : Path — path to the .enc file

        Returns
        -------
        bool — True if the file passes structural integrity checks

        Raises
        ------
        IntegrityError — if the check fails with a specific reason
        """
        enc_path = Path(enc_path)
        if not enc_path.exists():
            raise IntegrityError(f"File not found: '{enc_path.name}'")

        data   = enc_path.read_bytes()
        result = validate_encrypted_file(data)

        if not result:
            _log_event(
                f"Integrity check FAILED for '{enc_path.name}' — "
                "file is too small to be valid ciphertext",
                severity="CRITICAL",
            )
            raise IntegrityError(
                f"'{enc_path.name}' failed integrity check: "
                "file is too small to contain valid AES-256-GCM encrypted data."
            )

        _log_event(
            f"Integrity check passed for '{enc_path.name}'",
            severity="INFO",
        )
        return True


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON AND CONVENIENCE FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

_default_storage: Optional[SecureStorage] = None


def get_secure_storage(allow_generate: bool = False) -> SecureStorage:
    """
    Return the shared SecureStorage singleton.

    Creates the instance on first call and reuses it subsequently.
    Use this in application code to avoid re-loading the key on every request.

    Parameters
    ----------
    allow_generate : bool — allow auto-generating a key if none found (dev only)
    """
    global _default_storage
    if _default_storage is None:
        _default_storage = SecureStorage(allow_generate=allow_generate)
    return _default_storage


def store_dataset(path: Path, secure_delete: bool = False) -> Path:
    """Module-level shortcut: encrypt and store a dataset file."""
    return get_secure_storage(allow_generate=True).store_dataset(path, secure_delete)


def retrieve_dataset(enc_path: Path) -> Path:
    """Module-level shortcut: decrypt a dataset file."""
    return get_secure_storage(allow_generate=True).retrieve_dataset(enc_path)


def cleanup_temp_files(max_age_seconds: int = 0) -> int:
    """Module-level shortcut: wipe temporary decrypted files."""
    return get_secure_storage(allow_generate=True).cleanup_temp_files(max_age_seconds)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile

    print("\n" + "=" * 60)
    print("  SECURE STORAGE — SELF TEST")
    print("=" * 60)

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Override storage directories to temp for the self-test
        import encryption.file_encryptor as _fe
        import encryption.secure_storage as _ss

        _fe.ENCRYPTED_DATASETS  = tmp_path / "enc" / "datasets"
        _fe.ENCRYPTED_REPORTS   = tmp_path / "enc" / "reports"
        _fe.DECRYPTED_TEMP_DIR  = tmp_path / "temp"
        _ss.DECRYPTED_TEMP_DIR  = tmp_path / "temp"

        from encryption.key_manager import generate_key
        key     = generate_key()
        storage = SecureStorage(key=key)
        print(f"\n  SecureStorage  : initialised with fresh key  ✅")

        # Create test files
        csv_path = tmp_path / "sales_q3.csv"
        csv_path.write_text("product,revenue\nWidget A,150000")
        json_path = tmp_path / "report_q3.json"
        json_path.write_text('{"quarter":"Q3","revenue":4200000}')

        # --- Store dataset ---
        enc_ds = storage.store_dataset(csv_path)
        assert enc_ds.exists() and enc_ds.suffix == ".enc"
        print(f"  store_dataset  : '{enc_ds.name}'  ✅")

        # --- Store report ---
        enc_rp = storage.store_report(json_path)
        assert enc_rp.exists()
        print(f"  store_report   : '{enc_rp.name}'  ✅")

        # --- Retrieve dataset ---
        dec_ds = storage.retrieve_dataset(enc_ds)
        assert dec_ds.read_text() == csv_path.read_text()
        print(f"  retrieve_dataset : content matches original  ✅")

        # --- Verify integrity ---
        assert storage.verify_integrity(enc_ds) is True
        print(f"  verify_integrity : valid .enc file passes  ✅")

        # --- List stored ---
        listed = storage.list_stored("dataset")
        assert any(enc_ds.name == item["name"] for item in listed)
        print(f"  list_stored    : {len(listed)} dataset(s) found  ✅")

        # --- Cleanup ---
        deleted = storage.cleanup_temp_files(max_age_seconds=0)
        assert deleted >= 1
        print(f"  cleanup        : {deleted} temp file(s) wiped  ✅")

    print("\n  All self-tests passed.")
    print("=" * 60 + "\n")
