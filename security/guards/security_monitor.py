# ─────────────────────────────────────────────────────────────────────────────
# guards/security_monitor.py
#
# SecurityMonitor — lightweight in-process security monitoring engine.
#
# Responsibility:
#   Track security event patterns over time, maintain live counters,
#   detect repeated attacks, and generate aggregated summary reports.
#
# What this module does:
#   - Count events by severity, event_type, action_taken, and category
#   - Keep a rolling in-memory buffer of recent security events
#   - Detect when the same attack category fires multiple times in a window
#   - Generate structured summary reports for dashboards / demos
#   - Delegate actual file writing to AuditLogger (separation of concerns)
#
# What this module does NOT do:
#   - Write to log files  → that is AuditLogger's job
#   - Build log entries   → that is EventFormatter's job
#
# Threading:
#   All state mutations are protected by a single threading.Lock() so
#   this monitor is safe to use from multiple concurrent request threads.
#
# Persistence:
#   All counters are in-memory only. On restart they reset to zero.
#   For persistent counters, integrate with a database in a future version.
# ─────────────────────────────────────────────────────────────────────────────

import threading
from collections import defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional


# ── Graceful settings import ──────────────────────────────────────────────────

try:
    import sys, os
    sys.path.insert(0, str(Path(__file__).parent.parent))
    from configs.security_settings import MonitoringConfig, EventType
    from guards.event_formatter import EventFormatter, SecurityEvent, get_formatter
    from guards.audit_logger import AuditLogger, get_audit_logger
    _HAS_SETTINGS = True
except ImportError:
    _HAS_SETTINGS = False

    class MonitoringConfig:
        REPEATED_ATTACK_THRESHOLD      = 3
        REPEATED_ATTACK_WINDOW_SECONDS = 300   # 5 minutes
        ESCALATION_SCORE_THRESHOLD     = 0.8
        RECENT_EVENTS_BUFFER_SIZE      = 500

    class EventType:
        SAFE_INPUT = "safe_input"


# ══════════════════════════════════════════════════════════════════════════════
# SECURITY MONITOR CLASS
# ══════════════════════════════════════════════════════════════════════════════

class SecurityMonitor:
    """
    Lightweight in-process security monitoring for the AI Security Guardrail System.

    The SecurityMonitor sits above the AuditLogger. When you call record(),
    it both updates its internal counters AND forwards the event to the
    AuditLogger for persistent file storage.

    This dual responsibility makes it the single call-point for the full
    pipeline: detect → score → record → log.

    Tracked metrics:
        _total_events     — running count of all events recorded
        _by_severity      — counts grouped by INFO / WARNING / CRITICAL
        _by_event_type    — counts grouped by event type (prompt_injection etc.)
        _by_action        — counts grouped by action taken (blocked / allowed etc.)
        _by_category      — counts grouped by attack category
        _attack_times     — timestamps of recent attacks per category
        _recent           — rolling buffer of last N SecurityEvent objects

    Reporting methods:
        get_summary()          — aggregated stats dict for dashboards
        get_repeated_attacks() — categories exceeding repeat threshold
        get_recent_events()    — last N events as dicts
        get_attack_frequency() — category counts sorted by frequency

    Usage:
        monitor = SecurityMonitor()
        result  = detector.check("Ignore previous instructions")
        monitor.record(result)              # track + log in one call
        print(monitor.get_summary())        # see aggregated stats
        print(monitor.get_repeated_attacks()) # see persistent attackers
    """

    def __init__(
        self,
        formatter    : Optional["EventFormatter"] = None,
        audit_logger : Optional["AuditLogger"]    = None,
    ):
        """
        Parameters
        ----------
        formatter    : EventFormatter, optional
            Inject a custom formatter (useful in tests for predictable IDs).
        audit_logger : AuditLogger, optional
            Inject a custom audit logger (useful in tests to redirect log output).
        """
        self._fmt   = formatter    if formatter    is not None else get_formatter()
        self._audit = audit_logger if audit_logger is not None else get_audit_logger()
        self._lock  = threading.Lock()   # protects all mutable state below

        # ── Event counters ────────────────────────────────────────────────────
        self._total_events  : int            = 0
        self._by_severity   : dict[str, int] = defaultdict(int)
        self._by_event_type : dict[str, int] = defaultdict(int)
        self._by_action     : dict[str, int] = defaultdict(int)
        self._by_category   : dict[str, int] = defaultdict(int)

        # ── Repeated attack tracking ──────────────────────────────────────────
        # Stores UTC timestamps (as floats) for each attack category.
        # Using a bounded deque avoids unbounded memory growth.
        max_stored = MonitoringConfig.REPEATED_ATTACK_THRESHOLD * 10
        self._attack_times: dict[str, deque] = defaultdict(
            lambda: deque(maxlen=max_stored)
        )

        # ── Recent events ring buffer ─────────────────────────────────────────
        # Keeps the last N SecurityEvent objects in memory for quick retrieval.
        self._recent: deque["SecurityEvent"] = deque(
            maxlen=MonitoringConfig.RECENT_EVENTS_BUFFER_SIZE
        )

    # ══ Primary recording methods ═════════════════════════════════════════════

    def record(
        self,
        result,
        module_name: str = "PromptInjectionDetector",
    ) -> "SecurityEvent":
        """
        Record an InjectionCheckResult with the monitor AND the audit logger.

        This is the recommended single call-point for the full security pipeline:
            1. EventFormatter builds a structured SecurityEvent
            2. Internal counters are updated (_track)
            3. AuditLogger writes the event to the appropriate log file(s)

        Parameters
        ----------
        result      : InjectionCheckResult or dict — the detection result
        module_name : str — which module produced the result

        Returns
        -------
        SecurityEvent — the structured event, useful for inspection
        """
        event = self._fmt.from_injection_result(result, module_name=module_name)
        self._track(event)
        self._audit.log_event(result, module_name=module_name)
        return event

    def record_dataset_finding(
        self,
        row_index   : int,
        location    : str,
        value       : str,
        risk_score  : float,
        category    : str,
        pattern_ids : list,
        module_name : str = "DatasetScanner",
    ) -> "SecurityEvent":
        """
        Record and log a suspicious dataset cell finding.

        Called by DatasetScanner after it flags a cell or column name.
        Updates counters AND writes to suspicious_activity.log.

        Parameters
        ----------
        row_index   : int   — row number in dataset
        location    : str   — which column or field was flagged
        value       : str   — the suspicious cell content
        risk_score  : float — detection risk score
        category    : str   — matched attack category
        pattern_ids : list  — matched pattern IDs
        module_name : str   — calling module

        Returns
        -------
        SecurityEvent
        """
        event = self._fmt.from_dataset_finding(
            row_index, location, value, risk_score, category, pattern_ids, module_name
        )
        self._track(event)
        self._audit.log_dataset_finding(
            row_index, location, value, risk_score, category, pattern_ids, module_name
        )
        return event

    def record_sanitization(
        self,
        original      : str,
        sanitized     : str,
        removed_count : int,
        module_name   : str = "SentenceSanitizer",
    ) -> "SecurityEvent":
        """
        Record and log a sanitization action.

        Called by SentenceSanitizer after removing dangerous sentences.
        Updates counters AND writes to suspicious_activity.log.

        Parameters
        ----------
        original      : str — raw input before sanitization
        sanitized     : str — cleaned output
        removed_count : int — number of sentences removed
        module_name   : str — calling module

        Returns
        -------
        SecurityEvent
        """
        event = self._fmt.from_sanitization(
            original, sanitized, removed_count, module_name
        )
        self._track(event)
        self._audit.log_sanitization(
            original, sanitized, removed_count, module_name
        )
        return event

    # ══ Reporting / query methods ═════════════════════════════════════════════

    def get_summary(self) -> dict:
        """
        Return an aggregated summary of all recorded security events.

        This is the primary reporting method for dashboards, health-check
        endpoints, and evaluation demonstrations.

        Returns
        -------
        dict with fields:
            total_events   : int
            by_severity    : {INFO: int, WARNING: int, CRITICAL: int}
            by_event_type  : {prompt_injection: int, ...}
            by_action      : {blocked: int, allowed: int, ...}
            by_category    : {jailbreaking: int, override_attempts: int, ...}
            threat_level   : NONE | LOW | MEDIUM | HIGH
            generated_at   : ISO 8601 UTC timestamp

        Threat level algorithm:
            HIGH   — >= 50% of all events are CRITICAL
            MEDIUM — >= 30% of all events are WARNING
            LOW    — some events, but mostly safe
            NONE   — no events recorded yet

        Example output:
            {
              "total_events": 42,
              "by_severity": {"CRITICAL": 15, "WARNING": 20, "INFO": 7},
              "by_event_type": {"prompt_injection": 10, "jailbreak_attempt": 5},
              "by_action": {"blocked": 15, "warning_only": 20, "allowed": 7},
              "by_category": {"override_attempts": 8, "jailbreaking": 5},
              "threat_level": "HIGH",
              "generated_at": "2026-05-23T08:30:00Z"
            }
        """
        with self._lock:
            total    = self._total_events
            critical = self._by_severity.get("CRITICAL", 0)
            warning  = self._by_severity.get("WARNING",  0)

            # Compute overall threat level
            if total == 0:
                threat_level = "NONE"
            elif critical / max(total, 1) >= 0.5:
                threat_level = "HIGH"
            elif warning / max(total, 1) >= 0.3:
                threat_level = "MEDIUM"
            else:
                threat_level = "LOW"

            return {
                "total_events"  : total,
                "by_severity"   : dict(self._by_severity),
                "by_event_type" : dict(self._by_event_type),
                "by_action"     : dict(self._by_action),
                "by_category"   : dict(self._by_category),
                "threat_level"  : threat_level,
                "generated_at"  : self._utc_now(),
            }

    def get_repeated_attacks(self) -> list:
        """
        Return attack categories that have exceeded the repeat threshold.

        An attack is considered "repeated" if the same category fires
        REPEATED_ATTACK_THRESHOLD or more times within
        REPEATED_ATTACK_WINDOW_SECONDS seconds.

        This is used to detect persistent attackers or automated attack tools
        that are probing the system repeatedly.

        Returns
        -------
        list of dicts, each with:
            category        : str   — attack category name
            count           : int   — number of attacks in the window
            window_seconds  : int   — the time window that was checked
            first_seen      : str   — ISO 8601 timestamp of first attack in window
            last_seen       : str   — ISO 8601 timestamp of most recent attack

        Sorted by count descending (most frequent attacks first).
        """
        now     = datetime.now(timezone.utc).timestamp()
        window  = MonitoringConfig.REPEATED_ATTACK_WINDOW_SECONDS
        thresh  = MonitoringConfig.REPEATED_ATTACK_THRESHOLD
        results = []

        with self._lock:
            for category, timestamps in self._attack_times.items():
                # Filter to only attacks within the time window
                recent_times = [t for t in timestamps if (now - t) <= window]
                if len(recent_times) >= thresh:
                    results.append({
                        "category"      : category,
                        "count"         : len(recent_times),
                        "window_seconds": window,
                        "first_seen"    : datetime.fromtimestamp(
                            min(recent_times), tz=timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                        "last_seen"     : datetime.fromtimestamp(
                            max(recent_times), tz=timezone.utc
                        ).strftime("%Y-%m-%dT%H:%M:%SZ"),
                    })

        # Most frequent attacks first
        return sorted(results, key=lambda x: x["count"], reverse=True)

    def get_recent_events(self, limit: int = 20) -> list:
        """
        Return the most recent security events from the in-memory buffer.

        The buffer holds up to RECENT_EVENTS_BUFFER_SIZE events (default 500).
        Events are returned as plain dicts for easy serialisation.

        Parameters
        ----------
        limit : int — maximum number of events to return (default 20)

        Returns
        -------
        list of dicts — each dict is a SecurityEvent.to_dict() snapshot
        """
        with self._lock:
            all_recent = list(self._recent)

        # Return the last 'limit' events (most recent)
        return [e.to_dict() for e in all_recent[-limit:]]

    def get_attack_frequency(self) -> dict:
        """
        Return attack counts per category, sorted by frequency (descending).

        Useful for identifying the most common attack vectors against the system.

        Returns
        -------
        dict — {category: count} sorted highest-count first

        Example:
            {"override_attempts": 12, "jailbreaking": 8, "role_hijacking": 3}
        """
        with self._lock:
            categories = dict(self._by_category)

        return dict(
            sorted(categories.items(), key=lambda item: item[1], reverse=True)
        )

    def get_severity_breakdown(self) -> dict:
        """
        Return event counts by severity with percentages.

        Useful for quick threat assessment in demonstrations.

        Returns
        -------
        dict with fields:
            counts      : {INFO: int, WARNING: int, CRITICAL: int}
            percentages : {INFO: float, WARNING: float, CRITICAL: float}
            total       : int
        """
        with self._lock:
            total     = self._total_events
            by_sev    = dict(self._by_severity)

        percentages = {}
        for level, count in by_sev.items():
            percentages[level] = round((count / max(total, 1)) * 100, 1)

        return {
            "counts"     : by_sev,
            "percentages": percentages,
            "total"      : total,
        }

    def reset(self) -> None:
        """
        Reset all counters and buffers to zero.

        WARNING: Only use this in tests. In production, resetting the monitor
        destroys event history and breaks repeated-attack detection.
        """
        with self._lock:
            self._total_events  = 0
            self._by_severity   = defaultdict(int)
            self._by_event_type = defaultdict(int)
            self._by_action     = defaultdict(int)
            self._by_category   = defaultdict(int)
            max_stored = MonitoringConfig.REPEATED_ATTACK_THRESHOLD * 10
            self._attack_times  = defaultdict(lambda: deque(maxlen=max_stored))
            self._recent.clear()

    # ══ Private helpers ═══════════════════════════════════════════════════════

    def _track(self, event: "SecurityEvent") -> None:
        """
        Update all internal counters and the recent-events buffer.

        Called after every recorded event. Protected by _lock for thread safety.

        Attack timestamps are stored for repeat-detection but only for
        WARNING and CRITICAL events — safe (INFO) events don't count as attacks.
        """
        now = datetime.now(timezone.utc).timestamp()

        with self._lock:
            # Update running totals
            self._total_events                      += 1
            self._by_severity[event.severity]        += 1
            self._by_event_type[event.event_type]    += 1
            self._by_action[event.action_taken]      += 1

            # Track per-category counts
            for category in event.matched_categories:
                self._by_category[category] += 1

            # Store attack timestamps only for non-safe events
            if event.severity in ("CRITICAL", "WARNING"):
                for category in event.matched_categories:
                    self._attack_times[category].append(now)

            # Add to rolling recent-events buffer
            self._recent.append(event)

    @staticmethod
    def _utc_now() -> str:
        """Return the current UTC time as an ISO 8601 string."""
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


# ── Module-level singleton ────────────────────────────────────────────────────

_default_monitor: Optional[SecurityMonitor] = None


def get_security_monitor() -> SecurityMonitor:
    """
    Return the shared SecurityMonitor singleton.

    Creates the instance on first call and reuses it subsequently.
    Use this in production code to ensure all modules share one monitor.
    """
    global _default_monitor
    if _default_monitor is None:
        _default_monitor = SecurityMonitor()
    return _default_monitor


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  SECURITY MONITOR — SELF TEST")
    print("=" * 60)

    # Use a no-op audit logger so the self-test doesn't create log files
    import logging
    from guards.event_formatter import EventFormatter, EventIDGenerator
    import tempfile
    from pathlib import Path

    with tempfile.TemporaryDirectory() as tmp:
        gen = EventIDGenerator(Path(tmp) / ".event_counter")
        fmt = EventFormatter(id_generator=gen)

        from guards.audit_logger import AuditLogger
        noop = logging.getLogger("noop.monitor_selftest")
        noop.addHandler(logging.NullHandler())
        noop.propagate = False
        audit = AuditLogger(formatter=fmt)
        audit._security_log = audit._blocked_log = audit._suspicious_log = audit._system_log = noop

        monitor = SecurityMonitor(formatter=fmt, audit_logger=audit)
        monitor.reset()

        # Record some events
        blocked   = {"is_safe": False, "risk_score": 0.91, "action_taken": "blocked",
                     "confidence_level": "high", "detection_layer": "rule_based",
                     "matched_categories": ["jailbreaking"], "matched_patterns": ["JB-009"],
                     "original_input": "Enable developer mode"}
        suspicious = {"is_safe": True, "risk_score": 0.42, "action_taken": "warning_only",
                      "confidence_level": "medium", "detection_layer": "rule_based",
                      "matched_categories": ["indirect_injection"], "matched_patterns": ["IN-001"],
                      "original_input": "Hypothetically speaking..."}

        monitor.record(blocked)
        monitor.record(blocked)
        monitor.record(suspicious)

        summary = monitor.get_summary()
        print(f"\n  Total events  : {summary['total_events']}")
        print(f"  By severity   : {summary['by_severity']}")
        print(f"  By action     : {summary['by_action']}")
        print(f"  Threat level  : {summary['threat_level']}")

        freq = monitor.get_attack_frequency()
        print(f"\n  Attack freq   : {freq}")

        recent = monitor.get_recent_events(limit=2)
        print(f"  Recent events : {len(recent)} returned")

    print("\n" + "=" * 60 + "\n")
