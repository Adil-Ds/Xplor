# Secure Storage Guide

## Overview

The `SecureStorage` class in `encryption/secure_storage.py` is the recommended entry point for all encrypted file operations in the Xplor analytics platform. It combines AES-256-GCM encryption, key management, and audit logging into simple, single-call methods.

---

## Storage Directory Structure

```
security/storage/
│
├── encrypted/
│   ├── datasets/        ← Encrypted CSV / Excel / analytics datasets
│   │                       Example: revenue_q3.csv.enc
│   │
│   ├── reports/         ← Encrypted PDF / JSON analytics exports
│   │                       Example: quarterly_report.pdf.enc
│   │
│   └── temporary/       ← Encrypted short-lived AI processing files
│                           Example: ai_batch_001.json.enc
│
├── decrypted_temp/      ← Plaintext files during processing (auto-cleaned)
│                           Example: revenue_q3.csv  (briefly)
│
└── keys/
    ├── master.key       ← Current active encryption key (Base64)
    └── master.key.*     ← Rotated key archives (timestamped)
```

> [!CAUTION]
> The `decrypted_temp/` directory contains **plaintext data**. Add it to `.gitignore`:
> ```
> storage/decrypted_temp/*
> storage/keys/*.key
> ```

---

## Quick Start

```python
from encryption.secure_storage import SecureStorage
from pathlib import Path

# Initialise (loads key from XPLOR_ENCRYPTION_KEY env var or storage/keys/master.key)
storage = SecureStorage()

# Encrypt a dataset
enc_path = storage.store_dataset(Path("uploads/revenue_q3.csv"))
# → storage/encrypted/datasets/revenue_q3.csv.enc

# Use it later
temp_path = storage.retrieve_dataset(enc_path)
# → storage/decrypted_temp/revenue_q3.csv  (plaintext, temporarily)

# Process the file...
# df = pd.read_csv(temp_path)

# Clean up plaintext
storage.cleanup_temp_files()
# → storage/decrypted_temp/ is now empty
```

---

## API Reference

### `SecureStorage.__init__(key=None, allow_generate=False)`

```python
# Production (key loaded from env var or key file)
storage = SecureStorage()

# Testing (inject a known key)
from encryption.key_manager import generate_key
storage = SecureStorage(key=generate_key())

# Development (auto-generate if no key configured)
storage = SecureStorage(allow_generate=True)
```

### Dataset Operations

| Method | Description | Output |
|---|---|---|
| `store_dataset(path, secure_delete=False)` | Encrypt and store a dataset | `Path` to `.enc` file |
| `retrieve_dataset(enc_path)` | Decrypt a dataset for processing | `Path` to plaintext in `decrypted_temp/` |

```python
# Store
enc = storage.store_dataset(Path("data/sales.csv"))

# Store and delete source plaintext
enc = storage.store_dataset(Path("data/sales.csv"), secure_delete=True)

# Retrieve
plain = storage.retrieve_dataset(enc)
```

### Report Operations

| Method | Description | Output |
|---|---|---|
| `store_report(path, secure_delete=False)` | Encrypt and store a report | `Path` to `.enc` file in `reports/` |
| `retrieve_report(enc_path)` | Decrypt a report | `Path` to plaintext in `decrypted_temp/` |

```python
enc = storage.store_report(Path("exports/q3_report.pdf"))
plain = storage.retrieve_report(enc)
```

### Temporary File Operations

| Method | Description |
|---|---|
| `store_temp_file(path)` | Encrypt a processing file in `temporary/`. Always deletes source. |

```python
enc = storage.store_temp_file(Path("processing/batch_001.json"))
```

### Cleanup

```python
# Delete all temp files (max_age_seconds=0 means "delete everything")
deleted = storage.cleanup_temp_files(max_age_seconds=0)

# Delete only files older than 1 hour (the default)
deleted = storage.cleanup_temp_files()

# Keep files younger than 30 minutes
deleted = storage.cleanup_temp_files(max_age_seconds=1800)
```

### Listing

```python
files = storage.list_stored("dataset")
# [{"name": "sales_q3.csv.enc", "size_bytes": 1024, "modified_at": "2026-06-01T12:00:00Z", "path": "..."}]

files = storage.list_stored("report")
files = storage.list_stored("temporary")
```

### Integrity Verification

```python
# Pre-decryption structural check (does not decrypt)
is_valid = storage.verify_integrity(enc_path)
# Raises IntegrityError if the file is too small or structurally invalid
```

---

## Module-Level Shortcuts

For simple scripts that don't need a persistent `SecureStorage` instance:

```python
from encryption.secure_storage import store_dataset, retrieve_dataset, cleanup_temp_files

enc  = store_dataset(Path("uploads/data.csv"))
temp = retrieve_dataset(enc)
cleanup_temp_files()
```

These use the module-level singleton (`get_secure_storage()`).

---

## Typical Workflows

### Analytics Pipeline

```python
from encryption.secure_storage import SecureStorage
from pathlib import Path

storage = SecureStorage()

# 1. User uploads a CSV
enc_path = storage.store_dataset(Path("uploads/user_data.csv"), secure_delete=True)
# user_data.csv is now encrypted and the plaintext upload is deleted

# 2. AI model needs to process it
temp_path = storage.retrieve_dataset(enc_path)
# temp_path is a plaintext CSV in decrypted_temp/

# 3. Run analytics (plaintext accessible here)
# result = run_ai_analysis(temp_path)

# 4. Save the result report
enc_report = storage.store_report(Path("exports/analysis_result.json"), secure_delete=True)

# 5. Wipe all temporary plaintext
storage.cleanup_temp_files(max_age_seconds=0)
```

### Export Workflow

```python
# User requests a report download
temp_report = storage.retrieve_report(enc_report)
# → serve temp_report to user

# After download completes
storage.cleanup_temp_files(max_age_seconds=0)
```

---

## Audit Logging

Every `SecureStorage` operation automatically logs to the existing `AuditLogger`:

| Operation | Log Severity | Log Message Example |
|---|---|---|
| `store_dataset()` success | `INFO` | `Dataset encrypted: 'sales.csv' → 'sales.csv.enc'` |
| `store_dataset()` failure | `CRITICAL` | `Dataset encryption FAILED: 'sales.csv' — ...` |
| `retrieve_dataset()` success | `INFO` | `Dataset decrypted: 'sales.csv.enc' → 'sales.csv'` |
| `retrieve_dataset()` failure | `CRITICAL` | `Dataset decryption FAILED: 'sales.csv.enc' — ...` |
| `cleanup_temp_files()` | `INFO` | `Cleanup: 3 temporary file(s) wiped` |
| `verify_integrity()` failure | `CRITICAL` | `Integrity check FAILED for 'sales.csv.enc'` |

These events appear in `logs/security.log` and `logs/system_events.log` alongside all other security events — one unified audit trail.

---

## Error Handling

```python
from encryption.file_encryptor import FileEncryptionError, FileDecryptionError
from encryption.integrity import IntegrityError

try:
    enc = storage.store_dataset(path)
except FileEncryptionError as e:
    # File too large, source not found, or encryption engine failure
    print(f"Encryption failed: {e}")

try:
    plain = storage.retrieve_dataset(enc_path)
except FileDecryptionError as e:
    # Wrong key, tampered file, missing file, or corrupted ciphertext
    print(f"Decryption failed (possible tampering): {e}")

try:
    storage.verify_integrity(enc_path)
except IntegrityError as e:
    # File too small, structurally invalid
    print(f"Integrity check failed: {e}")
```

---

## Configuration Reference

All settings come from `configs/security_settings.py`:

| Setting | Default | Description |
|---|---|---|
| `EncryptionConfig.ALGORITHM` | `"AES-256-GCM"` | Encryption algorithm label |
| `EncryptionConfig.KEY_SIZE_BYTES` | `32` | Key length in bytes (256 bits) |
| `EncryptionConfig.IV_SIZE_BYTES` | `12` | GCM nonce length |
| `EncryptionConfig.TAG_SIZE_BYTES` | `16` | GCM authentication tag length |
| `EncryptionConfig.MAX_FILE_SIZE_MB` | `500` | Maximum file size for encryption |
| `EncryptionConfig.ENV_KEY_NAME` | `XPLOR_ENCRYPTION_KEY` | Env var name for key |
| `EncryptionConfig.KEY_FILE_NAME` | `master.key` | Key filename in `keys/` |
| `EncryptionConfig.ENCRYPTED_EXT` | `.enc` | Extension for encrypted files |
| `EncryptionConfig.TEMP_FILE_LIFETIME` | `3600` | Seconds before temp cleanup |
| `EncryptionConfig.CHUNK_SIZE` | `65536` | Read chunk size (64 KB) |
