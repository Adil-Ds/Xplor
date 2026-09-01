# ─────────────────────────────────────────────────────────────────────────────
# configs/upload_settings.py
#
# Central Configuration for the Secure File & Dataset Upload Protection System
#
# ALL upload-related constants live here.
# No magic numbers or hardcoded strings anywhere in the upload guard modules.
#
# To change a limit: edit here only — it propagates everywhere automatically.
# ─────────────────────────────────────────────────────────────────────────────

from pathlib import Path

# ── Base directory ─────────────────────────────────────────────────────────────
SECURITY_DIR = Path(__file__).parent.parent   # .../security/
STORAGE_DIR  = SECURITY_DIR / "storage"

# ══════════════════════════════════════════════════════════════════════════════
# FILE SIZE LIMITS
# ══════════════════════════════════════════════════════════════════════════════

MAX_FILE_SIZE_MB    = 25                         # Hard upload limit
MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024   # = 26,214,400 bytes

# Warn (but still allow) if file is in the warning zone below the hard limit
WARN_FILE_SIZE_MB    = 20
WARN_FILE_SIZE_BYTES = WARN_FILE_SIZE_MB * 1024 * 1024


# ══════════════════════════════════════════════════════════════════════════════
# ALLOWED FILE TYPES
# ══════════════════════════════════════════════════════════════════════════════

# Allowed extensions (lowercase, with dot)
ALLOWED_EXTENSIONS: frozenset = frozenset({
    ".csv",
    ".xlsx",
    ".json",
})

# Allowed MIME types — maps to accepted extension(s)
# These are the ONLY MIME types that will pass validation.
ALLOWED_MIME_TYPES: frozenset = frozenset({
    "text/csv",
    "application/csv",
    "text/plain",              # some systems use this for .csv
    "application/json",
    "text/json",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
    "application/vnd.ms-excel",  # .xls — rejected at extension stage anyway
})

# Explicit extension → accepted MIME types mapping (for mismatch detection)
EXTENSION_TO_MIME: dict = {
    ".csv" : {
        "text/csv",
        "application/csv",
        "text/plain",
    },
    ".json": {
        "application/json",
        "text/json",
        "text/plain",          # some editors save JSON as text/plain
    },
    ".xlsx": {
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/octet-stream",   # generic binary — allowed for xlsx
    },
}


# ══════════════════════════════════════════════════════════════════════════════
# BLOCKED FILE TYPES
# ══════════════════════════════════════════════════════════════════════════════

# Explicitly rejected extensions — these are NEVER allowed regardless of MIME
BLOCKED_EXTENSIONS: frozenset = frozenset({
    ".exe", ".bat", ".cmd", ".sh",  ".js",  ".dll",
    ".msi", ".ps1", ".vbs", ".jar", ".py",  ".rb",
    ".php", ".pl",  ".sql", ".xml", ".zip", ".tar",
    ".gz",  ".7z",  ".rar", ".htm", ".html",".svg",
    ".pdf", ".doc", ".docx",
})

# Blocked MIME type prefixes — reject any MIME matching these starts
BLOCKED_MIME_PREFIXES: tuple = (
    "application/x-",        # x- types are non-standard / potentially dangerous
    "application/msword",
    "application/x-sh",
    "application/x-executable",
    "application/x-msdos-program",
    "text/html",
    "text/javascript",
    "application/javascript",
    "application/x-javascript",
)


# ══════════════════════════════════════════════════════════════════════════════
# DANGEROUS CONTENT PATTERNS
# ══════════════════════════════════════════════════════════════════════════════

# Strings that — if found in dataset content — trigger dangerous content alert
DANGEROUS_CONTENT_PATTERNS: list = [
    # Script injection
    "<script",
    "</script>",
    "javascript:",
    "vbscript:",
    "data:text/html",
    # Code execution
    "eval(",
    "exec(",
    "__import__(",
    "os.system(",
    "subprocess",
    "import os",
    "import sys",
    # SQL injection
    "drop table",
    "delete from",
    "insert into",
    "update set",
    "union select",
    "or 1=1",
    "' or '",
    "-- ",
    "; drop",
    "xp_cmdshell",
    # Formula injection (CSV formula injection)
    # CSV cells starting with these chars trigger formula execution in Excel/Sheets
    "=cmd|",
    "=HYPERLINK(",
    "=IMPORTXML(",
    # Path traversal
    "../",
    "..\\",
    "/etc/passwd",
    "c:\\windows",
]

# Case-insensitive check for dangerous patterns (True = check case-insensitively)
DANGEROUS_CONTENT_CASE_INSENSITIVE = True


# ══════════════════════════════════════════════════════════════════════════════
# CSV FORMULA INJECTION PREFIXES
# ══════════════════════════════════════════════════════════════════════════════

# CSV cells starting with these characters can execute formulas when opened
# in spreadsheet software (Excel, Google Sheets, LibreOffice Calc).
# Reference: OWASP CSV Injection
CSV_FORMULA_PREFIXES: tuple = ("=", "+", "-", "@", "\t", "\r")


# ══════════════════════════════════════════════════════════════════════════════
# DATASET STRUCTURE VALIDATION
# ══════════════════════════════════════════════════════════════════════════════

CSV_MAX_COLUMNS    = 500       # reject CSVs wider than this
CSV_MAX_ROWS       = 500_000   # reject CSVs taller than this (basic check)
JSON_MAX_DEPTH     = 10        # reject deeply nested JSON (DoS prevention)
JSON_MAX_KEYS      = 10_000    # reject JSON with excessive keys
XLSX_MAX_SHEETS    = 50        # reject workbooks with excessive sheets
XLSX_MAX_ROWS      = 500_000   # reject workbooks with excessive rows


# ══════════════════════════════════════════════════════════════════════════════
# STORAGE DIRECTORY LAYOUT
# ══════════════════════════════════════════════════════════════════════════════

UPLOADS_DIR     = STORAGE_DIR / "uploads"
APPROVED_DIR    = UPLOADS_DIR / "approved"
REJECTED_DIR    = UPLOADS_DIR / "rejected"
QUARANTINE_DIR  = UPLOADS_DIR / "quarantine"

# All storage directories — created automatically by QuarantineManager
UPLOAD_STORAGE_DIRS = [
    UPLOADS_DIR,
    APPROVED_DIR,
    REJECTED_DIR,
    QUARANTINE_DIR,
]


# ══════════════════════════════════════════════════════════════════════════════
# QUARANTINE SETTINGS
# ══════════════════════════════════════════════════════════════════════════════

QUARANTINE_MAX_AGE_DAYS  = 30    # files older than this may be auto-purged
QUARANTINE_MANIFEST_FILE = "quarantine_manifest.json"  # index of quarantined files


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD PIPELINE SEVERITY THRESHOLDS
# ══════════════════════════════════════════════════════════════════════════════

# Prompt injection score at or above this value → quarantine instead of approve
INJECTION_QUARANTINE_THRESHOLD = 0.5

# Dangerous content findings at or above this count → quarantine
DANGEROUS_CONTENT_QUARANTINE_COUNT = 1   # any dangerous content → quarantine

# Severity labels used in ValidationResult and QuarantineRecord
class UploadSeverity:
    LOW      = "low"
    MEDIUM   = "medium"
    HIGH     = "high"
    CRITICAL = "critical"


# ══════════════════════════════════════════════════════════════════════════════
# UPLOAD EVENT TYPES (for audit logging)
# ══════════════════════════════════════════════════════════════════════════════

class UploadEventType:
    UPLOAD_APPROVED            = "upload_approved"
    UPLOAD_REJECTED            = "upload_rejected"
    UPLOAD_QUARANTINED         = "upload_quarantined"
    EXTENSION_BLOCKED          = "extension_blocked"
    MIME_MISMATCH              = "mime_mismatch"
    FILE_TOO_LARGE             = "file_too_large"
    STRUCTURE_INVALID          = "structure_invalid"
    INJECTION_DETECTED         = "injection_detected"
    DANGEROUS_CONTENT_DETECTED = "dangerous_content_detected"
    CORRUPTED_FILE             = "corrupted_file"
