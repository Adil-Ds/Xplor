# Password Security

## Why Passwords Are Hashed (Not Encrypted)

Before explaining bcrypt, it's important to understand the difference:

| Approach | Reversible? | What happens if database is stolen? |
|---|---|---|
| Plaintext storage | N/A | Attacker reads all passwords immediately |
| Symmetric encryption (AES) | ✅ Yes | Attacker who finds the key decrypts all passwords |
| SHA-256 hash alone | ❌ No | Attacker cracks with rainbow tables in minutes |
| **bcrypt hash (our approach)** | ❌ No | Attacker cracks one password in ~hours/years |

The goal of password hashing is: even if the database is stolen, the attacker cannot recover the original passwords in a useful timeframe.

---

## The Problem with SHA-256 for Passwords

SHA-256 is a fast hash function. Fast is bad for passwords.

```
SHA-256 speed:    ~1,000,000,000 attempts/second (modern GPU)
bcrypt speed:     ~5 attempts/second (bcrypt rounds=12 on same GPU)

Time to crack 6-char password:
  SHA-256:   < 1 second
  bcrypt:    ~150 years
```

Fast hash functions (MD5, SHA-1, SHA-256) are designed for data integrity — hashing files, certificates, etc. They are deliberately NOT suitable for passwords.

---

## How bcrypt Works

bcrypt is a **key derivation function** specifically designed for password storage.

```
Input: "MyPassword123"
         │
         ▼
1. Generate 16 random bytes of salt (using OS CSPRNG)
         │
         ▼
2. Run Blowfish key setup 2^rounds times (rounds=12 → 4096 iterations)
         │
         ▼
3. Output 24-byte derived key
         │
         ▼
4. Encode as 60-character string:
   $2b$12$<22-char salt><31-char hash>
```

### Why bcrypt is Secure

| Feature | What it does |
|---|---|
| **Unique salt** | Prevents rainbow table attacks — identical passwords produce different hashes |
| **Slow by design** | Work factor makes brute force impractical |
| **Adjustable work factor** | Can increase `rounds` as CPUs get faster |
| **One-way** | Cannot reverse a bcrypt hash — even with the source code |
| **Self-contained** | Hash string contains algorithm, version, rounds, salt — no separate storage needed |

---

## The bcrypt Hash String Format

```
$2b$12$iA1QXXHgEKVyE7mQ8n3Rt.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX
└──┘└─┘└────────────────────────────────────────────────────────┘
  │   │                        │
  │   │         60-char bcrypt string (salt + hash)
  │   │
  │   └── work factor: 12  (2^12 = 4096 iterations)
  │
  └── algorithm version: 2b  (current bcrypt standard)
```

The entire string (60 chars) is stored in the database. There is no need to store the salt separately — it is embedded in the first 22 characters after the work factor.

---

## Work Factor: Why 12?

The work factor (rounds) is the key security tuning parameter.

| Rounds | Iterations | Time per hash (2024 CPU) | OWASP recommendation |
|---|---|---|---|
| 10 | 1,024 | ~80ms | Minimum |
| **12** | **4,096** | **~300ms** | **Current standard ✅** |
| 14 | 16,384 | ~1,200ms | High-security (slow UX) |

**We use rounds=12** (OWASP 2024 recommendation). It takes ~300ms to hash one password — fast enough for login UX, slow enough to make brute-force impractical.

As CPUs get faster over the years, this value should be increased.

---

## Salt: Why Every Hash is Unique

Without salt:
```
hash("password123") → abc123  (always the same)
hash("password123") → abc123  (attacker makes a lookup table)
```

With bcrypt (unique salt per hash):
```
hash("password123") → $2b$12$<salt1>...  (different every time)
hash("password123") → $2b$12$<salt2>...  (different salt)
```

**Rainbow table attack**: A precomputed table of `hash(common_password) → password`. Without salts, attackers can look up any hash instantly. With unique salts, the attacker must crack each hash individually — making the attack O(n × cracking_time) instead of O(1).

---

## Public API Reference

### hash_password(plain_password) → str

```python
from auth.password_hashing import hash_password

hashed = hash_password("MyP@ssw0rd!")
# "$2b$12$iA1QXXHgEKVyE7mQ8n3Rt.XXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXXX"
# This 60-char string is safe to store in your database.
```

- **Never store the plaintext** — discard it after calling this function.
- Two calls with the same password produce different hashes (different salts).
- Raises `ValueError` if password is empty, not a string, or > 72 characters.
- Raises `ImportError` if bcrypt is not installed.

### verify_password(plain, hashed) → bool

```python
from auth.password_hashing import verify_password

verify_password("MyP@ssw0rd!", stored_hash)  # True
verify_password("wrong",       stored_hash)  # False
verify_password("",            stored_hash)  # False (never raises)
```

- Uses `bcrypt.checkpw()` — timing-safe comparison, no side-channel risk.
- Always returns `bool` — never raises for wrong passwords (callers convert `False` to `InvalidCredentialsError`).
- If the stored hash is malformed, returns `False` rather than raising.

### is_valid_password_format(password) → tuple[bool, str]

```python
from auth.password_hashing import is_valid_password_format

ok, reason = is_valid_password_format("weakpass")
# (False, "Password must contain at least one digit (0-9)")

ok, reason = is_valid_password_format("Strong1pass")
# (True, "")
```

Checks:
1. At least 8 characters
2. No longer than 72 characters (bcrypt limit)
3. Contains at least one digit
4. Contains at least one letter

Call this during **registration** to give the user actionable feedback before hashing.

---

## The 72-Byte bcrypt Hard Limit

bcrypt internally processes only the **first 72 bytes** of the input. Characters beyond position 72 are silently ignored by the underlying algorithm.

We enforce this as a hard limit in `hash_password()` — passwords longer than 72 characters raise `ValueError` rather than being silently truncated.

**Why**: Silent truncation means two passwords that are identical in the first 72 chars but different after would both verify successfully against the same hash. This is confusing and potentially dangerous.

If you need to support longer passwords (e.g., passphrases), the standard workaround is to SHA-256 hash the password first (to get a 32-byte result within the limit), then bcrypt that result. This is not implemented here to keep the module simple.

---

## Security Rules (What NOT to Do)

| ❌ Don't | ✅ Do instead |
|---|---|
| Store plaintext passwords | Call `hash_password()` and store the result |
| Use SHA-256 alone for passwords | Use bcrypt — SHA-256 is crackable in seconds |
| Use MD5 for passwords | Use bcrypt |
| Use a global fixed salt | Let bcrypt auto-generate (never call gensalt manually) |
| Use AES to "encrypt" passwords | Hash passwords — encryption is reversible |
| Log the plaintext password | Log only the username (never the password) |
| Return different errors for "user not found" vs "wrong password" | Always use `InvalidCredentialsError` — prevents user enumeration |
| Allow passwords < 8 chars | Call `is_valid_password_format()` before `hash_password()` |

---

## Integration in the Authentication Flow

```python
# REGISTRATION
from auth.auth_utils import register_user

result = register_user("arslan", "SecureP@ss123")
# Returns {"hashed_password": "$2b$12$...", "username": "arslan", "created_at": 1717200000}
# Save result["hashed_password"] to your user database.

# LOGIN
from auth.auth_utils import authenticate_user

stored_hash = db.get_user("arslan").password_hash
auth_resp   = authenticate_user(
    username="arslan",
    stored_hash=stored_hash,
    plain_password=request.json["password"],
    user_id=42,
    role="analyst",
)
# Returns {"success": True, "access_token": "...", "token_type": "bearer", "expires_in": 1800}
```

The calling code **never sees the bcrypt operations** — `authenticate_user()` handles everything internally.
