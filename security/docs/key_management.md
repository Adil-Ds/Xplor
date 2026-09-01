# Key Management Guide

## Overview

The Key Management System is responsible for the entire lifecycle of AES-256 encryption keys: generating them securely, saving and loading them safely, validating they meet cryptographic requirements, and rotating them on a schedule.

> [!IMPORTANT]
> No other module in the system should touch raw key bytes. All key operations go through `encryption/key_manager.py`.

---

## Key Format

Keys are stored as **URL-safe Base64-encoded strings**.

| Property | Value |
|---|---|
| Raw size | 32 bytes (256 bits) |
| Stored format | URL-safe Base64 (44 characters + newline) |
| Source of randomness | `os.urandom()` — OS CSPRNG |
| Environment variable | `XPLOR_ENCRYPTION_KEY` |
| Default key file | `storage/keys/master.key` |

---

## Key Loading Priority

`load_key()` tries sources in this order:

```
1. Environment variable  XPLOR_ENCRYPTION_KEY
        │
        ▼ (if not set)
2. Key file  storage/keys/master.key
        │
        ▼ (if not found and allow_generate=True)
3. Auto-generate (development only — logs WARNING)
        │
        ▼ (if allow_generate=False and nothing found)
  → Raises KeyError_
```

### Production Setup

Set the environment variable in your deployment environment or `.env` file:

```bash
# Generate a new key (run once, keep the output secret)
python -c "
import os, base64
key = os.urandom(32)
print(base64.urlsafe_b64encode(key).decode())
"
# Copy the output to your .env file:
XPLOR_ENCRYPTION_KEY=<paste-output-here>
```

### Development Setup

Generate and save a key file:

```python
from encryption.key_manager import generate_key, save_key

key = generate_key()
save_key(key)  # saves to storage/keys/master.key
```

---

## API Reference

### `generate_key() → bytes`

Creates a fresh 32-byte AES-256 key using `os.urandom()`.

```python
from encryption.key_manager import generate_key
key = generate_key()
assert len(key) == 32  # always
```

### `validate_key(key) → None`

Checks that a key is `bytes` and exactly 32 bytes. Raises `InvalidKeyError` otherwise.

```python
from encryption.key_manager import validate_key, InvalidKeyError

try:
    validate_key(some_key)
except InvalidKeyError as e:
    print(f"Bad key: {e}")
```

### `save_key(key, path=None) → Path`

Saves a key to disk as Base64. Default path: `storage/keys/master.key`.

```python
from encryption.key_manager import generate_key, save_key

path = save_key(generate_key())
# → storage/keys/master.key (Base64-encoded, chmod 600 on Unix)
```

### `load_key(path=None, env_var=None, allow_generate=False) → bytes`

Loads the key following the priority order above.

```python
# Production (from env var or key file)
key = load_key()

# Development (auto-generate if nothing found)
key = load_key(allow_generate=True)

# Specific file
key = load_key(path=Path("my_custom.key"))
```

### `rotate_key(path=None) → bytes`

Archives the current key with a timestamp suffix, generates a new key, and saves it.

```python
from encryption.key_manager import rotate_key

new_key = rotate_key()
# Old key: storage/keys/master.key.20260601_120000_000000
# New key: storage/keys/master.key  (now active)
```

### `get_key(allow_generate=False) → bytes`

Returns the cached module-level key singleton. Loads it once and reuses it.

```python
key = get_key()         # production — fails if no key found
key = get_key(allow_generate=True)  # development
```

### `clear_key_cache() → None`

Clears the cached singleton. Use in tests between test cases.

```python
clear_key_cache()  # next get_key() call loads fresh
```

---

## Key Rotation Procedure

Key rotation is the process of replacing the current encryption key with a new one.

> [!WARNING]
> Rotating the key does **NOT** automatically re-encrypt existing data.
> Old encrypted files can still only be decrypted with the key that encrypted them.

### Steps

1. **Rotate the key**:
   ```python
   from encryption.key_manager import rotate_key
   new_key = rotate_key()
   ```

2. **Old key is archived automatically** as `master.key.YYYYMMDD_HHMMSS_ffffff`.

3. **New key becomes active** — all new encryptions use it.

4. **Re-encrypt existing data** (if required by policy):
   ```python
   from encryption.key_manager import load_key
   from pathlib import Path

   old_key_path = Path("storage/keys/master.key.20260601_120000_000000")
   old_key = load_key(path=old_key_path)
   new_key = load_key()  # current active key

   # For each file that was encrypted with the old key:
   # 1. decrypt with old_key → 2. encrypt with new_key → 3. replace .enc file
   ```

5. **When old key is no longer needed**: delete the archive file.

---

## Security Rules

| Rule | Reason |
|---|---|
| Never hardcode keys in source | Keys in git history are permanently compromised |
| Use `os.urandom()` only | Python's `random` module is NOT cryptographically secure |
| Store as Base64 in env vars | Avoids binary encoding issues in environment variables |
| Archive before rotate | Old `.enc` files need the old key to decrypt |
| chmod 600 on key files | Prevent other users reading the key file on Unix |
| Never log raw key bytes | Log only key length or hash, never the key itself |

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `KeyError_: No encryption key found` | `XPLOR_ENCRYPTION_KEY` not set, no key file | Set env var or run `save_key(generate_key())` |
| `InvalidKeyError: Key must be bytes` | Passed a string key | Use `load_key()` instead of raw strings |
| `InvalidKeyError: Key is N bytes` | Key wrong length | Regenerate with `generate_key()` |
| `KeyError_: Could not archive existing key` | File permission issue | Check write access to `storage/keys/` |
| `KeyError_: Key file exists but could not be loaded` | Corrupt or truncated key file | Restore from backup or rotate |
