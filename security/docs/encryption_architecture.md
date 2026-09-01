# Encryption Architecture

## Overview

The Xplor AES-256 Data Encryption System provides a secure data protection layer for the AI-powered analytics platform. It encrypts sensitive files at rest, decrypts authorized requests safely, and integrates with the existing Audit Logging system to maintain a unified security trail.

---

## Encryption Pipeline

```
Uploaded File / Dataset
        │
        ▼
┌─────────────────────┐
│  secure_storage.py  │  ← Application entry point
│  SecureStorage      │    Combines encryption + key management + audit logging
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  file_encryptor.py  │  ← File I/O and storage routing
│  encrypt_file()     │    Routes to datasets/ reports/ temporary/
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  aes.py             │  ← Core AES-256-GCM cryptographic engine
│  encrypt_bytes()    │    Generates fresh IV, encrypts, appends GCM tag
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  key_manager.py     │  ← Key loading and validation
│  load_key()         │    Reads from env var or key file
└────────┬────────────┘
         │
         ▼
  storage/encrypted/
  datasets/   reports/   temporary/
```

### Decryption Pipeline

```
Authorized Request
        │
        ▼
┌─────────────────────┐
│  secure_storage.py  │  ← retrieve_dataset() / retrieve_report()
│  SecureStorage      │
└────────┬────────────┘
         │  key_manager.get_key()
         ▼
┌─────────────────────┐
│  file_encryptor.py  │  ← decrypt_file()
│                     │    Validates structure before decryption
└────────┬────────────┘
         │
         ▼
┌─────────────────────┐
│  aes.py             │  ← decrypt_bytes()
│                     │    Verifies GCM tag → decrypts → returns plaintext
└────────┬────────────┘
         │
         ▼
  storage/decrypted_temp/  ← plaintext lives here briefly
        │
        ▼  (after processing)
  cleanup_temp_files()     ← plaintext is wiped
```

---

## Why AES-256-GCM?

| Property | AES-256-GCM | AES-256-CBC |
|---|---|---|
| Confidentiality | ✅ | ✅ |
| Integrity (tamper detection) | ✅ Built-in | ❌ Requires separate HMAC |
| Authentication tag | ✅ 16-byte GCM tag | ❌ None |
| Nonce/IV length | 12 bytes (96-bit) | 16 bytes |
| Parallelisable | ✅ | ❌ |
| Used by TLS 1.3 | ✅ | ❌ |

AES-256-GCM is the correct choice because it gives **confidentiality + integrity in one primitive**. A tampered `.enc` file is detected automatically during decryption — no extra HMAC step needed.

---

## Wire Format

Every `.enc` file produced by this system uses this binary layout:

```
┌──────────────┬───────────────┬──────────────────────────┐
│  IV (12 B)   │  TAG (16 B)   │  CIPHERTEXT (N bytes)    │
└──────────────┴───────────────┴──────────────────────────┘
 ^             ^               ^
 Nonce for     GCM auth tag    Encrypted content
 this          (verifies       (same length as
 encryption    integrity)      original plaintext)
```

- **Total overhead per file**: 28 bytes (12 IV + 16 TAG)
- **IV**: Fresh `os.urandom(12)` per encrypt call — never reused
- **TAG**: 16-byte GCM authentication tag — fails if ciphertext is modified

---

## Module Responsibilities

| Module | Responsibility | Should callers use it? |
|---|---|---|
| `aes.py` | Raw AES-256-GCM encrypt/decrypt | Tests and internals only |
| `key_manager.py` | Key lifecycle (generate, save, load, rotate) | `load_key()` and `get_key()` |
| `integrity.py` | SHA-256 hashing, sidecar files, pre-decrypt validation | Optional supplemental checks |
| `file_encryptor.py` | File I/O + storage routing | Called by `secure_storage.py` |
| `secure_storage.py` | **Main application API** — orchestrates everything | **YES — use this** |

### Golden Rule
> Application code should only call `SecureStorage` or the module-level shortcuts in `secure_storage.py`. Never call `aes.py` or `file_encryptor.py` directly from application code.

---

## Security Properties

| Property | Implementation |
|---|---|
| **Confidentiality** | AES-256 with 256-bit key — computationally infeasible to break |
| **Integrity** | GCM authentication tag — any tampered byte causes decryption failure |
| **IV uniqueness** | `os.urandom(12)` per encrypt call — probability of reuse negligible |
| **Key safety** | Keys never hardcoded — loaded from env var or key file |
| **Error safety** | All crypto exceptions mapped to `DecryptionError`/`EncryptionError` — no internal details leaked |
| **Plaintext minimisation** | Decrypted files live only in `decrypted_temp/` — wiped by `cleanup_temp_files()` |

---

## Exception Hierarchy

```
Exception
├── EncryptionError          (aes.py)   — encryption failed
├── DecryptionError          (aes.py)   — decryption failed / tampered / wrong key
├── KeyError_                (key_manager.py) — key not found or unloadable
│   └── InvalidKeyError                  — key wrong type or wrong length
├── IntegrityError           (integrity.py) — SHA-256 check failed
├── FileEncryptionError      (file_encryptor.py) — file-level encryption failed
└── FileDecryptionError      (file_encryptor.py) — file-level decryption failed
```

Callers at the `secure_storage.py` level only need to catch `FileEncryptionError` and `FileDecryptionError`.

---

## Storage Directory Layout

```
security/storage/
├── encrypted/
│   ├── datasets/       ← CSV, Excel, tabular analytics data
│   ├── reports/        ← PDF, JSON analytics exports
│   └── temporary/      ← short-lived AI processing files
├── decrypted_temp/     ← plaintext during processing (auto-cleaned)
└── keys/
    ├── master.key      ← current Base64-encoded AES-256 key
    └── master.key.YYYYMMDD_HHMMSS_ffffff  ← rotated key archives
```

> [!CAUTION]
> Never commit real `.key` files or plaintext data files to version control.
> Add these patterns to `.gitignore`:
> ```
> storage/keys/*.key
> storage/decrypted_temp/*
> ```

---

## Testing

```bash
cd security
python tests/test_encryption.py     # 49 tests — AES engine + integrity
python tests/test_key_manager.py    # 36 tests — key lifecycle
python tests/test_file_encryptor.py # 43 tests — file + SecureStorage
```

All tests use `tempfile.TemporaryDirectory()` — no real data is written to the project storage directory.
