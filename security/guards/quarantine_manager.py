# ─────────────────────────────────────────────────────────────────────────────
# guards/quarantine_manager.py
#
# Quarantine Manager — Final Stage of the Upload Protection Pipeline
#
# WHAT THIS MODULE DOES:
#   After all validation and scanning layers complete, the QuarantineManager
#   routes the uploaded file to the correct storage location:
#
#   ┌─────────────────────────────────────────────────┐
#   │  All checks PASSED + scan CLEAN                 │→  storage/uploads/approved/
#   │  Extension/MIME/size FAILED                     │→  storage/uploads/rejected/
#   │  Scan found injection/dangerous content         │→  storage/uploads/quarantine/
#   └─────────────────────────────────────────────────┘
#
# WHY QUARANTINE INSTEAD OF DELETE?
#   Suspicious files must NOT be silently deleted:
#   - Security teams need to review them for threat intelligence
#   - They may contain evidence for incident investigations
#   - False positives need human review before deletion
#   The quarantine acts as a holding area for review, not an automatic delete.
#
# QUARANTINE MANIFEST:
#   Every quarantined file is indexed in quarantine_manifest.json with:
#     - original_filename, quarantined_filename
#     - quarantine_reason, severity, timestamp
#   This makes it easy to audit what was quarantined and why.
#
# Public API:
#   QuarantineManager
#     approve(file_path, metadata)     → StorageResult
#     reject(file_path, reason)        → StorageResult
#     quarantine(file_path, reason, severity) → StorageResult
#     route(file_path, action, reason) → StorageResult
#   get_quarantine_manifest()          → list[dict]  (convenience)
# ─────────────────────────────────────────────────────────────────────────────

import sys
import json
import logging
import shutil
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from configs.upload_settings import (
    APPROVED_DIR, REJECTED_DIR, QUARANTINE_DIR,
    UPLOAD_STORAGE_DIRS, QUARANTINE_MANIFEST_FILE,
    UploadSeverity, UploadEventType,
)

logger = logging.getLogger("security.quarantine_manager")

# Audit logger integration (optional)
try:
    from guards.audit_logger import get_audit_logger
    _audit = get_audit_logger()
    _HAS_AUDIT = True
except ImportError:
    _HAS_AUDIT = False
    _audit = None


def _log_storage_event(message: str, severity: str = "INFO") -> None:
    if _HAS_AUDIT and _audit:
        try:
            _audit.log_system_event(message, severity=severity, module_name="QUARANTINE_MGR")
        except Exception:
            pass
    logger.log(
        {"DEBUG": 10, "INFO": 20, "WARNING": 30, "ERROR": 40, "CRITICAL": 50}.get(severity, 20),
        message
    )


# ══════════════════════════════════════════════════════════════════════════════
# RESULT TYPE
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class StorageResult:
    """
    Result of a storage routing decision.

    Fields
    ------
    success         : bool — True if file was moved successfully
    action          : str  — "approved" | "rejected" | "quarantined"
    destination     : Path — where the file ended up
    original_name   : str  — original filename
    stored_name     : str  — possibly renamed filename (UUID-prefixed for quarantine)
    reason          : str  — why this action was taken
    severity        : str  — UploadSeverity value
    quarantine_id   : str  — unique ID for quarantined files (empty if not quarantined)
    timestamp       : str  — ISO 8601 UTC timestamp
    """
    success       : bool
    action        : str
    destination   : Path
    original_name : str
    stored_name   : str
    reason        : str
    severity      : str  = UploadSeverity.LOW
    quarantine_id : str  = ""
    timestamp     : str  = ""

    def __bool__(self) -> bool:
        return self.success

    def to_dict(self) -> dict:
        return {
            "success"      : self.success,
            "action"       : self.action,
            "destination"  : str(self.destination),
            "original_name": self.original_name,
            "stored_name"  : self.stored_name,
            "reason"       : self.reason,
            "severity"     : self.severity,
            "quarantine_id": self.quarantine_id,
            "timestamp"    : self.timestamp,
        }


# ══════════════════════════════════════════════════════════════════════════════
# QUARANTINE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class QuarantineManager:
    """
    Routes validated (and rejected/flagged) uploads to the correct storage area.

    Storage layout created automatically on first use:
        storage/
        └── uploads/
            ├── approved/    ← clean files ready for the analytics pipeline
            ├── rejected/    ← files that failed validation (bad extension, size, etc.)
            └── quarantine/  ← suspicious files awaiting human review

    QUARANTINE MANIFEST:
        Every quarantined file is logged in storage/uploads/quarantine/quarantine_manifest.json
        This JSON array is append-only and human-readable.

    Example
    -------
    >>> qm = QuarantineManager()
    >>> result = qm.approve(Path("data.csv"), metadata={"uploader": "arslan"})
    >>> result.action
    "approved"
    >>> result = qm.quarantine(Path("evil.csv"), reason="SQL injection detected", severity="critical")
    >>> result.quarantine_id
    "q-abc123"
    """

    def __init__(self):
        self._ensure_storage_dirs()
        self._manifest_path = QUARANTINE_DIR / QUARANTINE_MANIFEST_FILE

    def _ensure_storage_dirs(self) -> None:
        """Create all required storage directories if they don't exist."""
        for dir_path in UPLOAD_STORAGE_DIRS:
            dir_path.mkdir(parents=True, exist_ok=True)
        logger.debug("Storage directories confirmed.")

    # ── Public routing API ────────────────────────────────────────────────────

    def route(
        self,
        file_path : Path,
        action    : str,
        reason    : str           = "",
        severity  : str           = UploadSeverity.LOW,
        metadata  : dict          = None,
    ) -> StorageResult:
        """
        Route a file to the appropriate storage location based on action.

        Parameters
        ----------
        file_path : Path — source file to route
        action    : str  — "approve" | "reject" | "quarantine"
        reason    : str  — reason for the action (logged and stored)
        severity  : str  — UploadSeverity value
        metadata  : dict — optional metadata to attach (for approved files)

        Returns
        -------
        StorageResult

        Example
        -------
        >>> qm.route(Path("data.csv"), action="approve")
        >>> qm.route(Path("evil.csv"), action="quarantine", reason="SQL injection found")
        """
        action = action.strip().lower()
        if action in ("approve", "approved"):
            return self.approve(file_path, metadata=metadata or {})
        elif action in ("reject", "rejected"):
            return self.reject(file_path, reason=reason, severity=severity)
        elif action in ("quarantine", "quarantined"):
            return self.quarantine(file_path, reason=reason, severity=severity)
        else:
            return StorageResult(
                success=False, action=action,
                destination=file_path, original_name=file_path.name,
                stored_name=file_path.name, reason=f"Unknown action: '{action}'",
                severity=UploadSeverity.MEDIUM,
                timestamp=self._now(),
            )

    def approve(self, file_path: Path, metadata: dict = None) -> StorageResult:
        """
        Move a file to the approved storage directory.

        Approved files are safe to pass to the analytics pipeline.

        Parameters
        ----------
        file_path : Path — source file
        metadata  : dict — optional metadata (ignored in filesystem storage)

        Returns
        -------
        StorageResult
        """
        file_path = Path(file_path)
        dest      = APPROVED_DIR / file_path.name
        timestamp = self._now()

        try:
            dest = self._safe_dest(APPROVED_DIR, file_path.name)
            shutil.copy2(str(file_path), str(dest))
            _log_storage_event(
                f"APPROVED: file='{file_path.name}' → '{dest}'",
                severity="INFO",
            )
            return StorageResult(
                success=True, action="approved",
                destination=dest, original_name=file_path.name,
                stored_name=dest.name, reason="All validation checks passed.",
                severity=UploadSeverity.LOW, timestamp=timestamp,
            )
        except Exception as e:
            _log_storage_event(
                f"APPROVE ERROR: file='{file_path.name}' — {e}",
                severity="ERROR",
            )
            return StorageResult(
                success=False, action="approved",
                destination=APPROVED_DIR, original_name=file_path.name,
                stored_name=file_path.name, reason=f"File move failed: {e}",
                severity=UploadSeverity.MEDIUM, timestamp=timestamp,
            )

    def reject(
        self,
        file_path : Path,
        reason    : str = "",
        severity  : str = UploadSeverity.MEDIUM,
    ) -> StorageResult:
        """
        Move a file to the rejected storage directory.

        Rejected files failed objective validation (bad extension, oversized, etc.).
        They are not suspicious — they are simply invalid.

        Parameters
        ----------
        file_path : Path — source file
        reason    : str  — why it was rejected
        severity  : str  — UploadSeverity value

        Returns
        -------
        StorageResult
        """
        file_path = Path(file_path)
        timestamp = self._now()

        try:
            dest = self._safe_dest(REJECTED_DIR, file_path.name)
            shutil.copy2(str(file_path), str(dest))
            _log_storage_event(
                f"REJECTED: file='{file_path.name}' reason='{reason[:80]}' → '{dest}'",
                severity="WARNING",
            )
            return StorageResult(
                success=True, action="rejected",
                destination=dest, original_name=file_path.name,
                stored_name=dest.name, reason=reason,
                severity=severity, timestamp=timestamp,
            )
        except Exception as e:
            _log_storage_event(
                f"REJECT ERROR: file='{file_path.name}' — {e}",
                severity="ERROR",
            )
            return StorageResult(
                success=False, action="rejected",
                destination=REJECTED_DIR, original_name=file_path.name,
                stored_name=file_path.name, reason=f"File move failed: {e}",
                severity=UploadSeverity.MEDIUM, timestamp=timestamp,
            )

    def quarantine(
        self,
        file_path : Path,
        reason    : str = "",
        severity  : str = UploadSeverity.HIGH,
    ) -> StorageResult:
        """
        Move a suspicious file to the quarantine directory and log it.

        Quarantined files are NOT deleted — they are preserved for:
          - Security team review and threat analysis
          - Incident investigation evidence
          - False-positive review

        Each quarantined file gets:
          - A unique quarantine ID (UUID-based)
          - A renamed filename with the quarantine ID prefix
          - An entry in quarantine_manifest.json

        Parameters
        ----------
        file_path : Path — source file
        reason    : str  — why it was quarantined (detailed)
        severity  : str  — UploadSeverity value

        Returns
        -------
        StorageResult
        """
        file_path    = Path(file_path)
        timestamp    = self._now()
        quarantine_id = f"q-{uuid.uuid4().hex[:8]}"

        # Rename with quarantine ID to avoid conflicts and aid identification
        safe_name = f"{quarantine_id}_{file_path.name}"
        dest = self._safe_dest(QUARANTINE_DIR, safe_name)

        try:
            shutil.copy2(str(file_path), str(dest))

            # Write to manifest
            self._append_manifest({
                "quarantine_id"     : quarantine_id,
                "original_filename" : file_path.name,
                "quarantine_filename": dest.name,
                "reason"            : reason,
                "severity"          : severity,
                "timestamp"         : timestamp,
                "destination"       : str(dest),
            })

            _log_storage_event(
                f"QUARANTINED: id={quarantine_id} file='{file_path.name}' "
                f"severity={severity} reason='{reason[:100]}'",
                severity="CRITICAL",
            )
            return StorageResult(
                success=True, action="quarantined",
                destination=dest, original_name=file_path.name,
                stored_name=dest.name, reason=reason,
                severity=severity, quarantine_id=quarantine_id,
                timestamp=timestamp,
            )
        except Exception as e:
            _log_storage_event(
                f"QUARANTINE ERROR: file='{file_path.name}' — {e}",
                severity="ERROR",
            )
            return StorageResult(
                success=False, action="quarantined",
                destination=QUARANTINE_DIR, original_name=file_path.name,
                stored_name=file_path.name, reason=f"Quarantine move failed: {e}",
                severity=severity, quarantine_id=quarantine_id,
                timestamp=timestamp,
            )

    # ── Manifest Management ────────────────────────────────────────────────────

    def _append_manifest(self, record: dict) -> None:
        """
        Append a quarantine record to the quarantine_manifest.json file.

        The manifest is a JSON array — we load it, append, and write back.
        Thread safety note: for production use, file locking should be added.
        """
        try:
            if self._manifest_path.exists():
                try:
                    existing = json.loads(self._manifest_path.read_text(encoding="utf-8"))
                    if not isinstance(existing, list):
                        existing = []
                except (json.JSONDecodeError, IOError):
                    existing = []
            else:
                existing = []

            existing.append(record)
            self._manifest_path.write_text(
                json.dumps(existing, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception as e:
            logger.error(f"Failed to update quarantine manifest: {e}")

    def get_manifest(self) -> List[dict]:
        """
        Return all quarantine records from the manifest file.

        Returns
        -------
        list[dict] — quarantine records, newest appended last
        """
        if not self._manifest_path.exists():
            return []
        try:
            data = json.loads(self._manifest_path.read_text(encoding="utf-8"))
            return data if isinstance(data, list) else []
        except Exception:
            return []

    def get_quarantine_stats(self) -> dict:
        """
        Return summary statistics about the quarantine.

        Returns
        -------
        dict with total, by_severity, most_recent_timestamp
        """
        records = self.get_manifest()
        by_severity = {}
        for r in records:
            sev = r.get("severity", "unknown")
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_quarantined" : len(records),
            "by_severity"       : by_severity,
            "most_recent"       : records[-1].get("timestamp", "") if records else "",
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    def _safe_dest(self, directory: Path, filename: str) -> Path:
        """
        Return a safe destination path, appending a counter if file already exists.

        Prevents overwriting existing files in storage.
        """
        dest = directory / filename
        if not dest.exists():
            return dest
        stem  = Path(filename).stem
        ext   = Path(filename).suffix
        count = 1
        while dest.exists():
            dest = directory / f"{stem}_{count}{ext}"
            count += 1
        return dest

    def _now(self) -> str:
        """Return current UTC time as ISO 8601 string."""
        return datetime.now(timezone.utc).isoformat()


# ── Module-level singleton + convenience ──────────────────────────────────────

_qm_instance: Optional[QuarantineManager] = None


def get_quarantine_manager() -> QuarantineManager:
    """Return the module-level singleton QuarantineManager."""
    global _qm_instance
    if _qm_instance is None:
        _qm_instance = QuarantineManager()
    return _qm_instance


def get_quarantine_manifest() -> List[dict]:
    """Convenience: return all quarantine records."""
    return get_quarantine_manager().get_manifest()
