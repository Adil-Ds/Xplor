# ─────────────────────────────────────────────────────────────────────────────
# guards/file_upload_guard.py
#
# File Upload Guard — Layers 1–3: Extension, MIME, and Size Validation
#
# WHAT THIS MODULE IS:
#   The first gatekeeper in the upload protection pipeline.
#   It validates the three cheapest checks (fast, no file parsing needed):
#     Layer 1 — Extension validation   (is ".csv" allowed?)
#     Layer 2 — MIME type validation   (does the content match the extension?)
#     Layer 3 — File size validation   (is it under 25 MB?)
#
#   These three checks alone block the most common attack vectors:
#     - Renamed executables          → caught by Layer 1 + 2
#     - Disguised binary uploads     → caught by Layer 2
#     - DoS via oversized files      → caught by Layer 3
#
# HOW IT FITS INTO THE PIPELINE:
#   FileUploadGuard (this file)
#       → DatasetValidator  (structure validation)
#       → UploadScanner     (content scanning + injection detection)
#       → QuarantineManager (storage routing)
#
# PUBLIC API:
#   FileUploadGuard
#     validate_extension(filename)    → ValidationResult
#     validate_size(file_path)        → ValidationResult
#     validate_all(file_path)         → UploadValidationReport
#
#   validate_upload(file_path)        → UploadValidationReport (convenience)
#
# RESULT TYPES:
#   ValidationResult       — result of one check (passed, reason, severity)
#   UploadValidationReport — combined result of all three checks
# ─────────────────────────────────────────────────────────────────────────────

import sys
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional

sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.upload_settings import (
    ALLOWED_EXTENSIONS, BLOCKED_EXTENSIONS,
    MAX_FILE_SIZE_BYTES, MAX_FILE_SIZE_MB,
    WARN_FILE_SIZE_BYTES, WARN_FILE_SIZE_MB,
    UploadSeverity, UploadEventType,
)
from guards.mime_validator import MimeValidator, ValidationResult

logger = logging.getLogger("security.file_upload_guard")

# Audit logger integration (optional)
try:
    from guards.audit_logger import get_audit_logger
    _audit = get_audit_logger()
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
    _audit = None


def _log_upload_event(message: str, severity: str = "INFO") -> None:
    """Log to AuditLogger if available, else fall back to stdlib."""
    if _HAS_AUDIT and _audit:
        try:
            _audit.log_system_event(message, severity=severity, module_name="UPLOAD_GUARD")
        except Exception:
            pass
    logger.log(
        {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}.get(severity, 20),
        message
    )


# ══════════════════════════════════════════════════════════════════════════════
# COMBINED REPORT DATACLASS
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class UploadValidationReport:
    """
    Combined result of all validation layers for one uploaded file.

    Fields
    ------
    file_name        : str          — original filename
    file_size_bytes  : int          — file size in bytes
    extension        : str          — detected extension (e.g. ".csv")
    passed           : bool         — True only if ALL checks passed
    checks           : list         — list of individual ValidationResult objects
    rejection_reason : str          — first failed check's reason (or empty)
    severity         : str          — worst severity across all failed checks
    recommended_action: str         — "approve" | "reject" | "quarantine"

    Usage
    -----
    report = guard.validate_all(Path("upload.csv"))
    if report.passed:
        proceed_to_dataset_validation()
    else:
        return {"error": report.rejection_reason}, 400
    """
    file_name         : str
    file_size_bytes   : int
    extension         : str
    passed            : bool
    checks            : List[ValidationResult] = field(default_factory=list)
    rejection_reason  : str = ""
    severity          : str = UploadSeverity.LOW
    recommended_action: str = "approve"

    def __bool__(self) -> bool:
        return self.passed

    def failed_checks(self) -> List[ValidationResult]:
        """Return only the checks that failed."""
        return [c for c in self.checks if not c.passed]

    def to_dict(self) -> dict:
        """Serialize to plain dict for logging and API responses."""
        return {
            "file_name"          : self.file_name,
            "file_size_bytes"    : self.file_size_bytes,
            "file_size_mb"       : round(self.file_size_bytes / (1024 * 1024), 3),
            "extension"          : self.extension,
            "passed"             : self.passed,
            "severity"           : self.severity,
            "recommended_action" : self.recommended_action,
            "rejection_reason"   : self.rejection_reason,
            "checks": [
                {
                    "name"    : c.check_name,
                    "passed"  : c.passed,
                    "severity": c.severity,
                    "reason"  : c.reason,
                }
                for c in self.checks
            ],
        }


# ══════════════════════════════════════════════════════════════════════════════
# FILE UPLOAD GUARD
# ══════════════════════════════════════════════════════════════════════════════

class FileUploadGuard:
    """
    Validates uploaded files through extension, MIME type, and size checks.

    Design decisions:
        - FAIL FAST: stop at first critical failure (extension or MIME mismatch)
          to avoid unnecessary processing of obviously malicious files
        - ALWAYS LOG: every check result is logged (grant and denial)
        - NEVER TRUST THE EXTENSION ALONE: MIME check always follows extension check
        - RETURN STRUCTURED RESULTS: callers can inspect each check individually

    Attributes
    ----------
    _mime_validator : MimeValidator — MIME detection layer

    Example
    -------
    >>> guard = FileUploadGuard()
    >>> report = guard.validate_all(Path("uploads/data.csv"))
    >>> if report.passed:
    ...     # safe to proceed to dataset validation
    >>> else:
    ...     print(f"Rejected: {report.rejection_reason}")
    """

    def __init__(self, mime_validator: MimeValidator = None):
        self._mime = mime_validator or MimeValidator()

    # ── Layer 1: Extension Validation ─────────────────────────────────────────

    def validate_extension(self, filename: str) -> ValidationResult:
        """
        Check that the file extension is in the platform's allowed set.

        WHAT IS VALIDATED:
            - Extension must be in ALLOWED_EXTENSIONS (.csv, .xlsx, .json)
            - Extension must NOT be in BLOCKED_EXTENSIONS (.exe, .bat, etc.)
            - Files with no extension are rejected
            - Multiple extensions (e.g. data.csv.exe) → uses the last extension

        SECURITY NOTE:
            Extension is just metadata — it can be spoofed. This check is a
            quick first filter. It is always followed by MIME validation.

        Parameters
        ----------
        filename : str — the original filename from the upload

        Returns
        -------
        ValidationResult — passed=True if extension is allowed

        Example
        -------
        >>> guard.validate_extension("data.csv")
        ValidationResult(passed=True, ...)
        >>> guard.validate_extension("malware.exe")
        ValidationResult(passed=False, severity="critical", ...)
        >>> guard.validate_extension("data.csv.exe")
        ValidationResult(passed=False, ...)   # last extension is .exe
        """
        ext = Path(filename).suffix.lower()

        # No extension
        if not ext:
            _log_upload_event(
                f"EXTENSION REJECTED: file='{filename}' — no extension",
                severity="WARNING",
            )
            return ValidationResult(
                passed    = False,
                check_name= "extension",
                severity  = UploadSeverity.MEDIUM,
                reason    = f"File '{filename}' has no extension. Only .csv, .xlsx, .json are allowed.",
                detected  = "(none)",
                expected  = ", ".join(sorted(ALLOWED_EXTENSIONS)),
            )

        # Explicitly blocked extension
        if ext in BLOCKED_EXTENSIONS:
            _log_upload_event(
                f"EXTENSION BLOCKED: file='{filename}' ext='{ext}' — explicitly blocked",
                severity="CRITICAL",
            )
            return ValidationResult(
                passed    = False,
                check_name= "extension",
                severity  = UploadSeverity.CRITICAL,
                reason    = (
                    f"Extension '{ext}' is blocked. Executable and script files "
                    "are never permitted as dataset uploads."
                ),
                detected  = ext,
                expected  = ", ".join(sorted(ALLOWED_EXTENSIONS)),
            )

        # Not in allowed set (but not explicitly blocked)
        if ext not in ALLOWED_EXTENSIONS:
            _log_upload_event(
                f"EXTENSION REJECTED: file='{filename}' ext='{ext}' — not in allowlist",
                severity="WARNING",
            )
            return ValidationResult(
                passed    = False,
                check_name= "extension",
                severity  = UploadSeverity.HIGH,
                reason    = (
                    f"Extension '{ext}' is not an allowed dataset format. "
                    f"Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}"
                ),
                detected  = ext,
                expected  = ", ".join(sorted(ALLOWED_EXTENSIONS)),
            )

        _log_upload_event(
            f"EXTENSION OK: file='{filename}' ext='{ext}'",
            severity="INFO",
        )
        return ValidationResult(
            passed    = True,
            check_name= "extension",
            severity  = UploadSeverity.LOW,
            reason    = f"Extension '{ext}' is allowed.",
            detected  = ext,
            expected  = ", ".join(sorted(ALLOWED_EXTENSIONS)),
        )

    # ── Layer 3: Size Validation ───────────────────────────────────────────────

    def validate_size(self, file_path: Path) -> ValidationResult:
        """
        Check that the uploaded file does not exceed the size limit.

        LIMITS:
            Hard limit: MAX_FILE_SIZE_MB (25 MB) → reject
            Warn limit: WARN_FILE_SIZE_MB (20 MB) → log warning, still pass

        WHY SIZE LIMITS?
            Oversized uploads are a denial-of-service vector:
            - Parsing a 1 GB CSV exhausts server memory
            - Large files with injection payloads are harder to scan quickly
            - Storage costs are bounded by size limits

        Parameters
        ----------
        file_path : Path — path to the uploaded file

        Returns
        -------
        ValidationResult — passed=True if within size limit

        Example
        -------
        >>> guard.validate_size(Path("huge_file.csv"))  # 30 MB file
        ValidationResult(passed=False, severity="high", ...)
        """
        file_path = Path(file_path)

        try:
            size_bytes = file_path.stat().st_size
        except (FileNotFoundError, OSError) as e:
            return ValidationResult(
                passed    = False,
                check_name= "file_size",
                severity  = UploadSeverity.MEDIUM,
                reason    = f"Cannot determine file size: {e}",
                detected  = "unknown",
                expected  = f"≤ {MAX_FILE_SIZE_MB} MB",
            )

        size_mb = size_bytes / (1024 * 1024)

        # Hard limit exceeded
        if size_bytes > MAX_FILE_SIZE_BYTES:
            _log_upload_event(
                f"SIZE REJECTED: file='{file_path.name}' "
                f"size={size_mb:.2f} MB exceeds {MAX_FILE_SIZE_MB} MB limit",
                severity="WARNING",
            )
            return ValidationResult(
                passed    = False,
                check_name= "file_size",
                severity  = UploadSeverity.HIGH,
                reason    = (
                    f"File is {size_mb:.2f} MB, which exceeds the "
                    f"{MAX_FILE_SIZE_MB} MB upload limit."
                ),
                detected  = f"{size_mb:.2f} MB",
                expected  = f"≤ {MAX_FILE_SIZE_MB} MB",
            )

        # Warn zone (but still pass)
        if size_bytes > WARN_FILE_SIZE_BYTES:
            _log_upload_event(
                f"SIZE WARNING: file='{file_path.name}' "
                f"size={size_mb:.2f} MB — approaching {MAX_FILE_SIZE_MB} MB limit",
                severity="INFO",
            )

        _log_upload_event(
            f"SIZE OK: file='{file_path.name}' size={size_mb:.3f} MB",
            severity="INFO",
        )
        return ValidationResult(
            passed    = True,
            check_name= "file_size",
            severity  = UploadSeverity.LOW,
            reason    = f"File size {size_mb:.3f} MB is within the {MAX_FILE_SIZE_MB} MB limit.",
            detected  = f"{size_mb:.3f} MB",
            expected  = f"≤ {MAX_FILE_SIZE_MB} MB",
        )

    # ── Combined Pipeline ──────────────────────────────────────────────────────

    def validate_all(self, file_path: Path) -> UploadValidationReport:
        """
        Run all three validation checks (extension, MIME, size) on an upload.

        FAIL-FAST BEHAVIOUR:
            - Extension check fails → stop immediately (no MIME or size check)
            - MIME check fails      → stop immediately (no size check)
            - All three pass        → report passed=True

        This is intentional: running MIME detection on a known-blocked extension
        wastes time. If the extension is ".exe", we already know to reject it.

        Parameters
        ----------
        file_path : Path — path to the file being validated

        Returns
        -------
        UploadValidationReport — combined report with all check results

        Example
        -------
        >>> guard = FileUploadGuard()
        >>> report = guard.validate_all(Path("data.csv"))
        >>> report.passed
        True
        >>> report = guard.validate_all(Path("evil.exe"))
        >>> report.passed
        False
        >>> report.rejection_reason
        "Extension '.exe' is blocked..."
        """
        file_path = Path(file_path)
        filename  = file_path.name
        checks    : List[ValidationResult] = []

        # Determine file size (0 if unreadable — size check will catch it)
        try:
            size_bytes = file_path.stat().st_size
        except (FileNotFoundError, OSError):
            size_bytes = 0

        ext = Path(filename).suffix.lower()

        # ── Layer 1: Extension ────────────────────────────────────────────────
        ext_result = self.validate_extension(filename)
        checks.append(ext_result)

        if not ext_result.passed:
            return self._build_report(
                filename, size_bytes, ext, checks,
                passed=False,
                action="reject",
            )

        # ── Layer 2: MIME type ────────────────────────────────────────────────
        mime_result = self._mime.validate(file_path, ext)
        checks.append(mime_result)

        if not mime_result.passed:
            return self._build_report(
                filename, size_bytes, ext, checks,
                passed=False,
                # MIME mismatch is suspicious — could be a renamed executable → quarantine
                action="quarantine" if mime_result.severity == UploadSeverity.CRITICAL else "reject",
            )

        # ── Layer 3: File size ────────────────────────────────────────────────
        size_result = self.validate_size(file_path)
        checks.append(size_result)

        if not size_result.passed:
            return self._build_report(
                filename, size_bytes, ext, checks,
                passed=False,
                action="reject",
            )

        # All checks passed
        _log_upload_event(
            f"UPLOAD VALIDATED: file='{filename}' ext='{ext}' "
            f"size={size_bytes / (1024*1024):.3f} MB — all checks passed",
            severity="INFO",
        )
        return self._build_report(
            filename, size_bytes, ext, checks,
            passed=True,
            action="approve",
        )

    def _build_report(
        self,
        filename   : str,
        size_bytes : int,
        extension  : str,
        checks     : List[ValidationResult],
        passed     : bool,
        action     : str,
    ) -> UploadValidationReport:
        """Assemble the UploadValidationReport from completed checks."""
        failed = [c for c in checks if not c.passed]
        worst_severity = (
            max(
                failed,
                key=lambda c: {
                    UploadSeverity.CRITICAL: 4,
                    UploadSeverity.HIGH: 3,
                    UploadSeverity.MEDIUM: 2,
                    UploadSeverity.LOW: 1,
                }.get(c.severity, 0)
            ).severity
            if failed else UploadSeverity.LOW
        )
        reason = failed[0].reason if failed else ""

        return UploadValidationReport(
            file_name          = filename,
            file_size_bytes    = size_bytes,
            extension          = extension,
            passed             = passed,
            checks             = checks,
            rejection_reason   = reason,
            severity           = worst_severity,
            recommended_action = action,
        )


# ── Module-level singleton + convenience ──────────────────────────────────────

_guard_instance: Optional[FileUploadGuard] = None


def get_file_upload_guard() -> FileUploadGuard:
    """Return the module-level singleton FileUploadGuard."""
    global _guard_instance
    if _guard_instance is None:
        _guard_instance = FileUploadGuard()
    return _guard_instance


def validate_upload(file_path: Path) -> UploadValidationReport:
    """Module-level convenience: run all upload checks."""
    return get_file_upload_guard().validate_all(file_path)


def validate_extension(filename: str) -> ValidationResult:
    """Module-level convenience: check extension only."""
    return get_file_upload_guard().validate_extension(filename)


# ── Quick self-test ────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import tempfile, json

    print("\n" + "=" * 58)
    print("  FILE UPLOAD GUARD — SELF TEST")
    print("=" * 58)

    guard = FileUploadGuard()

    with tempfile.TemporaryDirectory() as tmpdir:
        # Valid CSV
        csv_f = Path(tmpdir) / "data.csv"
        csv_f.write_text("name,age\nAlice,30\n")
        r = guard.validate_all(csv_f)
        print(f"\n  data.csv   : passed={r.passed} action={r.recommended_action}")
        assert r.passed

        # Valid JSON
        json_f = Path(tmpdir) / "report.json"
        json_f.write_text(json.dumps({"rows": [1, 2, 3]}))
        r2 = guard.validate_all(json_f)
        print(f"  report.json: passed={r2.passed} action={r2.recommended_action}")
        assert r2.passed

        # Blocked extension
        exe_f = Path(tmpdir) / "malware.exe"
        exe_f.write_bytes(b"MZ" + b"\x00" * 50)
        r3 = guard.validate_all(exe_f)
        print(f"  malware.exe: passed={r3.passed} action={r3.recommended_action}")
        assert not r3.passed and r3.severity == "critical"

        # Renamed EXE
        evil_csv = Path(tmpdir) / "evil.csv"
        evil_csv.write_bytes(b"MZ" + b"\x00" * 50)
        r4 = guard.validate_all(evil_csv)
        print(f"  evil.csv   : passed={r4.passed} action={r4.recommended_action}")
        assert not r4.passed

        # Oversized file (26 MB)
        big_f = Path(tmpdir) / "huge.csv"
        big_f.write_bytes(b"a" * (26 * 1024 * 1024))
        r5 = guard.validate_all(big_f)
        print(f"  huge.csv   : passed={r5.passed} reason='{r5.rejection_reason[:40]}...'")
        assert not r5.passed

    print("\n  All assertions passed ✅")
    print("=" * 58 + "\n")
