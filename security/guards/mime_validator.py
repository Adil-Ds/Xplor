# ─────────────────────────────────────────────────────────────────────────────
# guards/mime_validator.py
#
# MIME Type Validator — Layer 2 of the Upload Protection Pipeline
#
# PROBLEM BEING SOLVED:
#   File extensions lie. An attacker can rename "malware.exe" to "data.csv"
#   and bypass a naive extension-only check. MIME type validation reads the
#   actual file content (magic bytes) to verify what the file really is.
#
# WHAT ARE MAGIC BYTES?
#   The first few bytes of a file uniquely identify its format:
#     .xlsx: PK\x03\x04  (ZIP-based format)
#     .csv:  UTF-8 text starting with printable characters
#     .json: '{' or '[' (after optional BOM/whitespace)
#     .exe:  MZ          (DOS executable header)
#     .pdf:  %PDF-
#
# HOW THIS MODULE WORKS:
#   1. Read the first 4096 bytes of the file (header sniffing)
#   2. Use python-magic (libmagic) to detect actual MIME type
#   3. Fall back to manual magic byte inspection if python-magic unavailable
#   4. Compare detected MIME type against the extension's allowed MIME set
#   5. Return ValidationResult — match / mismatch
#
# DEFENSE IN DEPTH:
#   Extension check (Layer 1) + MIME check (Layer 2) together make it very
#   hard for an attacker to sneak through a dangerous file as a valid dataset.
#
# Public API:
#   MimeValidator
#     detect_mime(file_path)                → str
#     validate(file_path, extension)        → ValidationResult
#   validate_mime(file_path, extension)     → ValidationResult (convenience)
# ─────────────────────────────────────────────────────────────────────────────

import sys
import logging
from pathlib import Path
from dataclasses import dataclass

sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.upload_settings import (
    EXTENSION_TO_MIME,
    ALLOWED_MIME_TYPES,
    BLOCKED_MIME_PREFIXES,
    UploadSeverity,
)

logger = logging.getLogger("security.mime_validator")

# Try to import python-magic (libmagic bindings)
try:
    import magic as _magic
    _HAS_MAGIC = True
except ImportError:
    _HAS_MAGIC = False
    logger.warning(
        "python-magic not installed. Falling back to manual magic-byte inspection. "
        "Install with: pip install python-magic-bin  (Windows)"
    )


# ── Magic byte signatures for manual fallback ──────────────────────────────────
# (first bytes) → MIME type
_MAGIC_SIGNATURES: list = [
    (b"PK\x03\x04",         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (b"PK\x05\x06",         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (b"PK\x07\x08",         "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"),
    (b"MZ",                  "application/x-msdownload"),      # .exe / .dll
    (b"\x7fELF",             "application/x-executable"),      # Linux ELF binary
    (b"\xca\xfe\xba\xbe",    "application/java-vm"),           # Java class file
    (b"%PDF-",               "application/pdf"),
    (b"\x89PNG\r\n\x1a\n",  "image/png"),
    (b"\xff\xd8\xff",        "image/jpeg"),
    (b"GIF87a",              "image/gif"),
    (b"GIF89a",              "image/gif"),
    (b"RIFF",                "audio/x-wav"),                   # WAV / AVI
    (b"\x1f\x8b",            "application/gzip"),
    (b"BZh",                 "application/x-bzip2"),
    (b"7z\xbc\xaf'",        "application/x-7z-compressed"),
    (b"Rar!\x1a\x07",        "application/x-rar-compressed"),
]

# BOM signatures for text file type detection
_TEXT_BOMS = [
    (b"\xef\xbb\xbf",  "utf-8"),     # UTF-8 BOM
    (b"\xff\xfe",      "utf-16-le"),  # UTF-16 LE BOM
    (b"\xfe\xff",      "utf-16-be"),  # UTF-16 BE BOM
]


# ── ValidationResult ──────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    """
    Result of a single validation step in the upload pipeline.

    Fields
    ------
    passed       : bool  — True if validation passed
    check_name   : str   — Which check this represents (e.g. "mime_type")
    severity     : str   — "low" | "medium" | "high" | "critical"
    reason       : str   — Human-readable explanation
    detected     : str   — What was actually detected (e.g. the real MIME type)
    expected     : str   — What was expected (e.g. allowed MIME types)
    """
    passed   : bool
    check_name: str
    severity : str = UploadSeverity.LOW
    reason   : str = ""
    detected : str = ""
    expected : str = ""

    def __bool__(self) -> bool:
        return self.passed


# ══════════════════════════════════════════════════════════════════════════════
# MIME VALIDATOR
# ══════════════════════════════════════════════════════════════════════════════

class MimeValidator:
    """
    Validates the real MIME type of an uploaded file.

    Uses python-magic (libmagic) when available for accurate detection.
    Falls back to manual magic-byte inspection otherwise.

    WHY NOT TRUST THE EXTENSION?
        Extensions are metadata provided by the uploader — they are trivially
        spoofable. Magic bytes are part of the file content itself. An attacker
        who renames evil.exe to data.csv cannot change the "MZ" header that
        identifies the file as a Windows executable.

    Example
    -------
    >>> v = MimeValidator()
    >>> result = v.validate(Path("data.csv"), ".csv")
    >>> result.passed
    True
    >>> result = v.validate(Path("evil_renamed.csv"), ".csv")  # was .exe
    >>> result.passed
    False
    >>> result.detected
    'application/x-msdownload'
    """

    def detect_mime(self, file_path: Path) -> str:
        """
        Detect the real MIME type of a file by reading its content.

        Uses libmagic when available, falls back to manual byte inspection.

        Parameters
        ----------
        file_path : Path — path to the file to inspect

        Returns
        -------
        str — MIME type string (e.g. "text/csv", "application/x-msdownload")

        Raises
        ------
        FileNotFoundError — if file does not exist
        IOError           — if file cannot be read
        """
        file_path = Path(file_path)
        if not file_path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        # ── Method 1: python-magic (most accurate) ─────────────────────────
        if _HAS_MAGIC:
            try:
                mime = _magic.from_file(str(file_path), mime=True)
                logger.debug(f"libmagic detected: '{mime}' for '{file_path.name}'")
                return mime
            except Exception as e:
                logger.warning(f"libmagic failed ({e}), falling back to manual inspection")

        # ── Method 2: Manual magic byte inspection ─────────────────────────
        return self._detect_by_magic_bytes(file_path)

    def _detect_by_magic_bytes(self, file_path: Path) -> str:
        """
        Inspect the first bytes of a file to determine its type.

        Returns a MIME string. Falls back to content-based heuristics
        for text-based formats (CSV, JSON).
        """
        try:
            with open(file_path, "rb") as f:
                header = f.read(4096)
        except IOError as e:
            logger.error(f"Cannot read file for MIME inspection: {e}")
            return "application/octet-stream"   # unknown binary

        # Check binary magic byte signatures first
        for signature, mime_type in _MAGIC_SIGNATURES:
            if header.startswith(signature):
                return mime_type

        # Strip BOM for text detection
        raw = header
        for bom, _ in _TEXT_BOMS:
            if raw.startswith(bom):
                raw = raw[len(bom):]
                break

        # Attempt to decode as text
        try:
            text_sample = raw.decode("utf-8", errors="strict").strip()
        except UnicodeDecodeError:
            # Not valid UTF-8 → likely binary
            return "application/octet-stream"

        # JSON detection — starts with { or [
        if text_sample.startswith(("{", "[")):
            return "application/json"

        # CSV heuristic — contains commas or tabs with printable ASCII
        lines = text_sample.splitlines()
        if lines:
            first_line = lines[0]
            if "," in first_line or "\t" in first_line:
                return "text/csv"
            # Single-column CSV is still text/plain
            if all(32 <= ord(c) < 127 or c in "\n\r\t" for c in first_line[:200]):
                return "text/plain"

        return "application/octet-stream"

    def validate(self, file_path: Path, extension: str) -> "ValidationResult":
        """
        Validate that the file's real MIME type matches its extension.

        Steps:
            1. Detect the actual MIME type from file content
            2. Check if the detected MIME is in the blocked list
            3. Check if the detected MIME matches the extension's allowed set
            4. Return ValidationResult

        Parameters
        ----------
        file_path : Path — path to the uploaded file
        extension : str  — the file extension (e.g. ".csv")

        Returns
        -------
        ValidationResult — with passed=True/False and reason

        Example
        -------
        >>> v.validate(Path("evil.csv"), ".csv")  # actually an EXE
        ValidationResult(passed=False, detected="application/x-msdownload", ...)
        """
        extension = extension.lower()
        file_path = Path(file_path)

        try:
            detected_mime = self.detect_mime(file_path)
        except (FileNotFoundError, IOError) as e:
            return ValidationResult(
                passed    = False,
                check_name= "mime_type",
                severity  = UploadSeverity.HIGH,
                reason    = f"Cannot read file for MIME detection: {e}",
                detected  = "unknown",
                expected  = ", ".join(sorted(EXTENSION_TO_MIME.get(extension, {"unknown"}))),
            )

        logger.debug(f"MIME detected='{detected_mime}' for ext='{extension}' file='{file_path.name}'")

        # ── Check 1: Is detected MIME explicitly blocked? ──────────────────
        for blocked_prefix in BLOCKED_MIME_PREFIXES:
            if detected_mime.startswith(blocked_prefix):
                logger.warning(
                    f"MIME BLOCKED: file='{file_path.name}' "
                    f"detected='{detected_mime}' matches blocked prefix '{blocked_prefix}'"
                )
                return ValidationResult(
                    passed    = False,
                    check_name= "mime_type",
                    severity  = UploadSeverity.CRITICAL,
                    reason    = (
                        f"Detected MIME type '{detected_mime}' is explicitly blocked. "
                        "This may indicate a dangerous or executable file."
                    ),
                    detected  = detected_mime,
                    expected  = ", ".join(sorted(EXTENSION_TO_MIME.get(extension, set()))),
                )

        # ── Check 2: Does MIME match the extension's allowed set? ──────────
        allowed_for_ext = EXTENSION_TO_MIME.get(extension, set())

        if allowed_for_ext and detected_mime not in allowed_for_ext:
            # Special case: application/octet-stream is allowed for xlsx
            # (some tools produce generic binary output for xlsx)
            if extension == ".xlsx" and detected_mime == "application/octet-stream":
                pass  # accepted — fall through to pass below
            else:
                logger.warning(
                    f"MIME MISMATCH: file='{file_path.name}' "
                    f"ext='{extension}' detected='{detected_mime}' "
                    f"expected_one_of={sorted(allowed_for_ext)}"
                )
                return ValidationResult(
                    passed    = False,
                    check_name= "mime_type",
                    severity  = UploadSeverity.HIGH,
                    reason    = (
                        f"MIME type mismatch: file has extension '{extension}' "
                        f"but real content type is '{detected_mime}'. "
                        "This may indicate a renamed dangerous file."
                    ),
                    detected  = detected_mime,
                    expected  = ", ".join(sorted(allowed_for_ext)),
                )

        logger.info(f"MIME OK: file='{file_path.name}' detected='{detected_mime}'")
        return ValidationResult(
            passed    = True,
            check_name= "mime_type",
            severity  = UploadSeverity.LOW,
            reason    = f"MIME type '{detected_mime}' is valid for extension '{extension}'",
            detected  = detected_mime,
            expected  = ", ".join(sorted(allowed_for_ext)) if allowed_for_ext else "any",
        )


# ── Module-level convenience ───────────────────────────────────────────────────

_validator_instance: MimeValidator = None


def get_mime_validator() -> MimeValidator:
    """Return the module-level singleton MimeValidator."""
    global _validator_instance
    if _validator_instance is None:
        _validator_instance = MimeValidator()
    return _validator_instance


def validate_mime(file_path: Path, extension: str) -> ValidationResult:
    """Module-level convenience: validate MIME type of a file."""
    return get_mime_validator().validate(file_path, extension)


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile, json, os

    print("\n" + "=" * 58)
    print("  MIME VALIDATOR — SELF TEST")
    print("=" * 58)

    v = MimeValidator()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a real JSON file
        json_path = Path(tmpdir) / "data.json"
        json_path.write_text(json.dumps({"key": "value"}))
        r = v.validate(json_path, ".json")
        print(f"\n  JSON file  : passed={r.passed}  detected='{r.detected}'")
        assert r.passed, f"JSON should pass: {r.reason}"

        # Create a real CSV
        csv_path = Path(tmpdir) / "data.csv"
        csv_path.write_text("name,age,salary\nAlice,30,50000\n")
        r2 = v.validate(csv_path, ".csv")
        print(f"  CSV file   : passed={r2.passed}  detected='{r2.detected}'")
        assert r2.passed, f"CSV should pass: {r2.reason}"

        # Create an EXE-like file renamed to .csv (MZ header)
        exe_path = Path(tmpdir) / "evil.csv"
        exe_path.write_bytes(b"MZ" + b"\x00" * 100)
        r3 = v.validate(exe_path, ".csv")
        print(f"  EXE→.csv   : passed={r3.passed}  detected='{r3.detected}'")
        assert not r3.passed, "EXE renamed to .csv should FAIL"

        # Create real XLSX (PK magic bytes)
        xlsx_path = Path(tmpdir) / "data.xlsx"
        xlsx_path.write_bytes(b"PK\x03\x04" + b"\x00" * 100)
        r4 = v.validate(xlsx_path, ".xlsx")
        print(f"  XLSX file  : passed={r4.passed}  detected='{r4.detected}'")
        assert r4.passed, f"XLSX should pass: {r4.reason}"

    print("\n  All assertions passed ✅")
    print("=" * 58 + "\n")
