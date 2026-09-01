# ─────────────────────────────────────────────────────────────────────────────
# encryption/__init__.py
#
# Public API for the Xplor AES-256 Data Encryption System.
#
# Import from this package like:
#   from encryption import SecureStorage, generate_key, load_key
#   from encryption import encrypt_text, decrypt_text
#   from encryption import EncryptionError, DecryptionError
#
# Architecture reminder:
#   Application code → secure_storage.SecureStorage (high-level)
#   Tests / internals → aes, key_manager, file_encryptor, integrity (low-level)
# ─────────────────────────────────────────────────────────────────────────────

# ── AES engine ────────────────────────────────────────────────────────────────
from encryption.aes import (
    encrypt_bytes,
    decrypt_bytes,
    encrypt_text,
    decrypt_text,
    encrypt_file,
    decrypt_file,
    EncryptionError,
    DecryptionError,
)

# ── Key management ────────────────────────────────────────────────────────────
from encryption.key_manager import (
    generate_key,
    save_key,
    load_key,
    validate_key,
    rotate_key,
    get_key,
    clear_key_cache,
    KeyError_,
    InvalidKeyError,
)

# ── Integrity utilities ───────────────────────────────────────────────────────
from encryption.integrity import (
    hash_bytes,
    hash_file,
    verify_file_hash,
    save_hash_file,
    load_and_verify_hash,
    validate_encrypted_file,
    is_encrypted_file,
    IntegrityError,
)

# ── File encryptor ────────────────────────────────────────────────────────────
from encryption.file_encryptor import (
    encrypt_file as encrypt_file_to_storage,
    decrypt_file as decrypt_file_from_storage,
    encrypt_file_chunked,
    list_encrypted_files,
    list_temp_files,
    get_encrypted_dir,
    FileEncryptionError,
    FileDecryptionError,
)

# ── High-level orchestrator (recommended public API) ─────────────────────────
from encryption.secure_storage import (
    SecureStorage,
    get_secure_storage,
    store_dataset,
    retrieve_dataset,
    cleanup_temp_files,
)

__all__ = [
    # AES engine
    "encrypt_bytes", "decrypt_bytes", "encrypt_text", "decrypt_text",
    "EncryptionError", "DecryptionError",
    # Key management
    "generate_key", "save_key", "load_key", "validate_key",
    "rotate_key", "get_key", "clear_key_cache",
    "KeyError_", "InvalidKeyError",
    # Integrity
    "hash_bytes", "hash_file", "verify_file_hash",
    "save_hash_file", "load_and_verify_hash",
    "validate_encrypted_file", "is_encrypted_file", "IntegrityError",
    # File encryptor
    "encrypt_file_to_storage", "decrypt_file_from_storage",
    "encrypt_file_chunked", "list_encrypted_files", "list_temp_files",
    "get_encrypted_dir", "FileEncryptionError", "FileDecryptionError",
    # High-level
    "SecureStorage", "get_secure_storage",
    "store_dataset", "retrieve_dataset", "cleanup_temp_files",
]
