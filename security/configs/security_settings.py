# ─────────────────────────────────────────────────────────────
# configs/security_settings.py
#
# Central configuration for the Layered AI Security Guardrail System.
# All tuneable constants live here — no magic numbers scattered in code.
#
# To adjust behaviour: change values here, not inside guard modules.
# ─────────────────────────────────────────────────────────────

from pathlib import Path

# ── Directory Layout ───────────────────────────────────────────
SECURITY_DIR   = Path(__file__).parent.parent          # .../security/
CONFIGS_DIR    = SECURITY_DIR / "configs"
LOGS_DIR       = SECURITY_DIR / "logs"
GUARDS_DIR     = SECURITY_DIR / "guards"

# ── Pattern & Severity Config Files ───────────────────────────
PATTERNS_FILE_PATH = CONFIGS_DIR / "blocked_patterns.json"
SEVERITY_FILE_PATH = CONFIGS_DIR / "severity_levels.json"

# ── Risk Scoring ───────────────────────────────────────────────
RISK_THRESHOLD = 0.5

# ── Audit Logging ──────────────────────────────────────────────
LOG_FILE_PATH      = LOGS_DIR / "blocked_prompts.log"   # backward compat alias
LOG_LEVEL          = "WARNING"    # DEBUG | INFO | WARNING | CRITICAL
LOG_PREVIEW_LENGTH = 120          # Characters shown in log preview
MAX_PROMPT_LENGTH  = 10_000


# ── Log File Paths (four dedicated files) ──────────────────────
#   security.log            — ALL security events (master audit trail)
#   blocked_prompts.log     — Confirmed attacks (CRITICAL only)
#   suspicious_activity.log — Low-risk warnings
#   system_events.log       — Startup, config reload, health checks
LOG_SECURITY_PATH   = LOGS_DIR / "security.log"
LOG_BLOCKED_PATH    = LOGS_DIR / "blocked_prompts.log"
LOG_SUSPICIOUS_PATH = LOGS_DIR / "suspicious_activity.log"
LOG_SYSTEM_PATH     = LOGS_DIR / "system_events.log"

# Persistent counter — keeps EventIDs unique across restarts
EVENT_COUNTER_PATH  = LOGS_DIR / ".event_counter"


# ── Detection Layer Labels ─────────────────────────────────────
class DetectionLayer:
    RULE_BASED    = "rule_based"
    NORMALIZATION = "normalization"
    DATASET_SCAN  = "dataset_scan"
    HARDENING     = "hardening"


# ── Action Labels ──────────────────────────────────────────────
class Action:
    BLOCKED            = "blocked"
    SANITIZED          = "sanitized"
    WARNING_ONLY       = "warning_only"
    ALLOWED            = "allowed"
    FLAGGED_FOR_REVIEW = "flagged_for_review"


# ── Confidence Labels ──────────────────────────────────────────
class Confidence:
    LOW    = "low"
    MEDIUM = "medium"
    HIGH   = "high"


# ── Event Type Labels ──────────────────────────────────────────
class EventType:
    PROMPT_INJECTION    = "prompt_injection"
    JAILBREAK_ATTEMPT   = "jailbreak_attempt"
    SQL_INJECTION       = "sql_injection"
    CODE_EXECUTION      = "code_execution"
    DATASET_ATTACK      = "dataset_attack"
    UNAUTHORIZED_ACCESS = "unauthorized_access"
    SUSPICIOUS_ACTIVITY = "suspicious_activity"
    SANITIZATION_EVENT  = "sanitization_event"
    SYSTEM_EVENT        = "system_event"
    SAFE_INPUT          = "safe_input"
    # ── Encryption events (added for AES-256 Data Encryption System) ──
    ENCRYPTION_SUCCESS  = "encryption_success"
    DECRYPTION_SUCCESS  = "decryption_success"
    DECRYPTION_FAILED   = "decryption_failed"
    INTEGRITY_VIOLATION = "integrity_violation"
    KEY_ROTATION        = "key_rotation"
    KEY_GENERATED       = "key_generated"
    # ── Authentication events (added for JWT Auth System) ──
    LOGIN_SUCCESS      = "login_success"
    LOGIN_FAILED       = "login_failed"
    TOKEN_GENERATED    = "token_generated"
    TOKEN_EXPIRED      = "token_expired"
    TOKEN_INVALID      = "token_invalid"
    UNAUTHORIZED       = "unauthorized_access"
    LOGOUT             = "logout"
    PASSWORD_CHANGED   = "password_changed"


# ── Monitoring Configuration ───────────────────────────────────
class MonitoringConfig:
    REPEATED_ATTACK_THRESHOLD      = 3
    REPEATED_ATTACK_WINDOW_SECONDS = 300   # 5 minutes
    ESCALATION_SCORE_THRESHOLD     = 0.8
    RECENT_EVENTS_BUFFER_SIZE      = 500


# ── Helper Functions ───────────────────────────────────────────

def confidence_from_score(score: float) -> str:
    """Map a float risk score → low / medium / high."""
    if score >= 0.65:
        return Confidence.HIGH
    elif score >= 0.35:
        return Confidence.MEDIUM
    return Confidence.LOW


def action_from_result(is_safe: bool, score: float) -> str:
    """Derive action label from detection outcome."""
    if not is_safe:
        return Action.BLOCKED
    elif score > 0.0:
        return Action.WARNING_ONLY
    return Action.ALLOWED


def severity_from_score(score: float, is_safe: bool) -> str:
    """
    Map risk score + safety flag to a log severity string.
    Returns one of: INFO | WARNING | CRITICAL
    """
    if not is_safe or score >= 0.65:
        return "CRITICAL"
    elif score >= 0.35:
        return "WARNING"
    return "INFO"


def event_type_from_category(category: str) -> str:
    """Map a detection category name to a standardised EventType label."""
    mapping = {
        "jailbreaking"      : EventType.JAILBREAK_ATTEMPT,
        "sql_injection"     : EventType.SQL_INJECTION,
        "code_execution"    : EventType.CODE_EXECUTION,
        "data_exfiltration" : EventType.UNAUTHORIZED_ACCESS,
        "delimiter_attacks" : EventType.PROMPT_INJECTION,
        "override_attempts" : EventType.PROMPT_INJECTION,
        "role_hijacking"    : EventType.PROMPT_INJECTION,
        "system_probing"    : EventType.PROMPT_INJECTION,
        "indirect_injection": EventType.SUSPICIOUS_ACTIVITY,
    }
    return mapping.get(category, EventType.SUSPICIOUS_ACTIVITY)


# ══════════════════════════════════════════════════════════════════════════════
# ENCRYPTION SYSTEM CONFIGURATION
# Added for AES-256 Data Encryption System
# ══════════════════════════════════════════════════════════════════════════════

class EncryptionConfig:
    """
    Central configuration for the AES-256 encryption subsystem.

    All tuneable cryptographic constants live here.
    Changing values here propagates across all encryption modules.

    Fields:
        ALGORITHM           — human-readable label for the mode used
        KEY_SIZE_BYTES      — must be 32 for AES-256
        IV_SIZE_BYTES       — 12 bytes is the recommended GCM nonce length
        TAG_SIZE_BYTES      — GCM produces a 16-byte authentication tag
        MAX_FILE_SIZE_MB    — reject files larger than this before encrypting
        ENV_KEY_NAME        — environment variable name for the master key
        KEY_FILE_NAME       — filename used when saving a key to disk
        ENCRYPTED_EXT       — extension appended to encrypted files
        TEMP_FILE_LIFETIME  — seconds after which temp decrypted files are wiped
    """
    ALGORITHM           = "AES-256-GCM"
    KEY_SIZE_BYTES      = 32           # 256 bits — required for AES-256
    IV_SIZE_BYTES       = 12           # 96-bit nonce — optimal for GCM mode
    TAG_SIZE_BYTES      = 16           # 128-bit GCM authentication tag
    MAX_FILE_SIZE_MB    = 500          # refuse files larger than 500 MB
    ENV_KEY_NAME        = "XPLOR_ENCRYPTION_KEY"   # env var holding base64 key
    KEY_FILE_NAME       = "master.key"             # key file inside keys/
    ENCRYPTED_EXT       = ".enc"                   # extension for ciphertext files
    TEMP_FILE_LIFETIME  = 3600         # 1 hour — wipe temp files older than this
    CHUNK_SIZE          = 64 * 1024    # 64 KB read chunks for large file handling


# ── Encrypted Storage Directory Layout ────────────────────────────────────────
#
#   security/storage/
#   ├── encrypted/
#   │   ├── datasets/      ← encrypted CSV / tabular data
#   │   ├── reports/       ← encrypted analytics exports
#   │   └── temporary/     ← encrypted short-lived processing files
#   ├── decrypted_temp/    ← plaintext lives here briefly during processing
#   └── keys/              ← master.key and rotated key archives
#
# ─────────────────────────────────────────────────────────────────────────────

STORAGE_DIR         = SECURITY_DIR / "storage"
ENCRYPTED_DIR       = STORAGE_DIR  / "encrypted"
ENCRYPTED_DATASETS  = ENCRYPTED_DIR / "datasets"
ENCRYPTED_REPORTS   = ENCRYPTED_DIR / "reports"
ENCRYPTED_TEMPORARY = ENCRYPTED_DIR / "temporary"
DECRYPTED_TEMP_DIR  = STORAGE_DIR  / "decrypted_temp"
KEYS_DIR            = STORAGE_DIR  / "keys"


# ══════════════════════════════════════════════════════════════════════════════
# JWT AUTHENTICATION CONFIGURATION
# Added for JWT Auth & Password Security System
# ══════════════════════════════════════════════════════════════════════════════

class AuthConfig:
    """
    Central configuration for the JWT Authentication subsystem.

    All auth constants live here. Changing values here propagates
    to jwt_handler, token_validator, and auth_utils.

    Fields:
        JWT_ALGORITHM            — signing algorithm (HS256 recommended)
        TOKEN_EXPIRATION_MINUTES — default access token lifetime
        MIN_SECRET_KEY_LENGTH    — reject secrets shorter than this
        BCRYPT_ROUNDS            — bcrypt work factor (OWASP: 12)
        ENV_SECRET_KEY_NAME      — env var name for JWT secret
        ENV_ALGORITHM_NAME       — env var name for algorithm override
        ENV_EXPIRY_NAME          — env var name for expiry override
        MAX_USERNAME_LENGTH      — input validation limit
        MAX_PASSWORD_LENGTH      — input validation limit (bcrypt max: 72)
        VALID_ROLES              — accepted role values in JWT claims
        ROLE_HIERARCHY           — maps role → numeric level (higher = more access)
    """
    JWT_ALGORITHM            = "HS256"                 # HMAC-SHA256
    TOKEN_EXPIRATION_MINUTES = 30                      # 30-minute default lifetime
    MIN_SECRET_KEY_LENGTH    = 32                      # reject secrets < 32 chars
    BCRYPT_ROUNDS            = 12                      # OWASP 2024 recommendation
    ENV_SECRET_KEY_NAME      = "JWT_SECRET_KEY"        # env var holding the secret
    ENV_ALGORITHM_NAME       = "JWT_ALGORITHM"         # env var for algorithm
    ENV_EXPIRY_NAME          = "TOKEN_EXPIRATION_MINUTES"  # env var for expiry
    MAX_USERNAME_LENGTH      = 64                      # db column size guard
    MAX_PASSWORD_LENGTH      = 72                       # bcrypt HARD LIMIT: only first 72 bytes processed
    VALID_ROLES              = {"admin", "analyst", "viewer"}  # accepted JWT roles
    ROLE_HIERARCHY           = {"admin": 3, "analyst": 2, "viewer": 1}  # access levels
