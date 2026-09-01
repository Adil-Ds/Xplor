# ─────────────────────────────────────────────────────────────
# guards/pattern_manager.py
#
# PatternManager — loads, validates, and exposes blocked_patterns.json.
#
# Responsibilities:
#   - Parse the versioned JSON config into usable structures
#   - Provide per-category metadata (severity, description, pattern IDs)
#   - Support runtime reload without restarting the application
#   - Remain the single source of truth for all pattern data
#
# Other modules (PromptInjectionDetector, AuditLogger) import from here
# instead of reading the JSON file directly.
# ─────────────────────────────────────────────────────────────

import json
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger("security.pattern_manager")


class PatternManager:
    """
    Loads and manages blocked_patterns.json.

    Supports:
      - New versioned format: {"version": "...", "categories": [...]}
      - Legacy flat format:   {"category_name": ["pattern", ...]}

    After loading, two dictionaries are populated:
      self.patterns  — {category: [pattern_str, ...]}        — for matching
      self.metadata  — {category: {severity, description, patterns: [{id, pattern}]}}
    """

    def __init__(self, path: Optional[Path] = None):
        if path is None:
            path = Path(__file__).parent.parent / "configs" / "blocked_patterns.json"
        self.path = Path(path)
        self.version  = "unknown"
        self.patterns : dict[str, list[str]]  = {}   # {category: [pattern_string]}
        self.metadata : dict[str, dict]        = {}   # {category: {severity, description, patterns}}
        self.load()

    # ── Public API ─────────────────────────────────────────────

    def load(self) -> None:
        """(Re)load patterns from disk. Safe to call at runtime."""
        raw = self._read_file()
        if raw:
            self._parse(raw)
            logger.info(
                f"PatternManager loaded {self.total_patterns()} patterns "
                f"across {len(self.patterns)} categories (v{self.version})"
            )

    def get_categories(self) -> list[str]:
        """Return all category names."""
        return list(self.patterns.keys())

    def get_patterns(self, category: str) -> list[str]:
        """Return plain pattern strings for a category."""
        return self.patterns.get(category, [])

    def get_pattern_objects(self, category: str) -> list[dict]:
        """Return [{id, pattern}] objects for a category."""
        return self.metadata.get(category, {}).get("patterns", [])

    def get_severity(self, category: str) -> str:
        """Return the severity label for a category (defaults to 'medium')."""
        return self.metadata.get(category, {}).get("severity", "medium")

    def get_description(self, category: str) -> str:
        """Return the human-readable description for a category."""
        return self.metadata.get(category, {}).get("description", "")

    def total_patterns(self) -> int:
        """Total number of patterns across all categories."""
        return sum(len(v) for v in self.patterns.values())

    def summary(self) -> dict:
        """Return a summary dict — useful for health-check endpoints."""
        return {
            "version"         : self.version,
            "total_categories": len(self.patterns),
            "total_patterns"  : self.total_patterns(),
            "categories"      : {
                cat: {
                    "count"   : len(self.patterns[cat]),
                    "severity": self.get_severity(cat),
                }
                for cat in self.patterns
            }
        }

    # ── Private Helpers ────────────────────────────────────────

    def _read_file(self) -> Optional[dict]:
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                return json.load(f)
        except FileNotFoundError:
            logger.critical(f"blocked_patterns.json not found at {self.path}. Detection DISABLED.")
            return None
        except json.JSONDecodeError as e:
            logger.critical(f"blocked_patterns.json is malformed: {e}. Detection DISABLED.")
            return None

    def _parse(self, raw: dict) -> None:
        """
        Handle both format versions:

        New (versioned):
            {"version": "1.0", "categories": [{"category": "...", "patterns": [{"id": "...", "pattern": "..."}]}]}

        Legacy (flat):
            {"category_name": ["pattern_string", ...]}
        """
        if "categories" in raw:
            self._parse_versioned(raw)
        else:
            self._parse_legacy(raw)

    def _parse_versioned(self, raw: dict) -> None:
        self.version = raw.get("version", "1.0")
        self.patterns = {}
        self.metadata = {}

        for entry in raw.get("categories", []):
            category    = entry.get("category", "unknown")
            severity    = entry.get("severity", "medium")
            description = entry.get("description", "")
            raw_pats    = entry.get("patterns", [])

            # Each item can be {"id": "...", "pattern": "..."} or a plain string
            pattern_objects = []
            pattern_strings = []

            for idx, item in enumerate(raw_pats):
                if isinstance(item, dict):
                    pat_str = item.get("pattern", "")
                    pat_id  = item.get("id", f"{category[:2].upper()}-{idx+1:03d}")
                else:
                    pat_str = str(item)
                    pat_id  = f"{category[:2].upper()}-{idx+1:03d}"

                if pat_str:
                    pattern_objects.append({"id": pat_id, "pattern": pat_str})
                    pattern_strings.append(pat_str)

            self.patterns[category] = pattern_strings
            self.metadata[category] = {
                "severity"   : severity,
                "description": description,
                "patterns"   : pattern_objects,
            }

    def _parse_legacy(self, raw: dict) -> None:
        """
        Support the old flat {category: [strings]} format so existing
        deployments keep working after a config upgrade.
        """
        self.version  = "legacy"
        self.patterns = {}
        self.metadata = {}

        for category, items in raw.items():
            if not isinstance(items, list):
                continue
            pattern_objects = [
                {"id": f"{category[:2].upper()}-{i+1:03d}", "pattern": p}
                for i, p in enumerate(items) if isinstance(p, str)
            ]
            self.patterns[category] = [obj["pattern"] for obj in pattern_objects]
            self.metadata[category] = {
                "severity"   : "medium",
                "description": f"Legacy category: {category}",
                "patterns"   : pattern_objects,
            }


# ── Module-level singleton ─────────────────────────────────────
# Imported by PromptInjectionDetector so patterns are loaded once.
_default_manager: Optional[PatternManager] = None


def get_default_manager() -> PatternManager:
    global _default_manager
    if _default_manager is None:
        _default_manager = PatternManager()
    return _default_manager
