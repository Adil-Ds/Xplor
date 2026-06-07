# Quarantine System

## What Is the Quarantine?

The quarantine is a **holding area for suspicious uploads** that passed enough checks to be saved but contain content flagged as potentially dangerous.

**Key principle: suspicious files are NEVER silently deleted.**

Reasons:
- Security teams need to inspect them for threat intelligence
- They may contain evidence for incident investigations
- False positives need human review before permanent removal
- Deletion audit trails are required in many compliance frameworks

---

## Storage Layout

```
storage/
└── uploads/
    ├── approved/        ← clean files — safe for analytics pipeline
    │   └── data.csv
    │
    ├── rejected/        ← invalid files — bad extension, oversized, corrupted
    │   └── malware.exe
    │
    └── quarantine/      ← suspicious files — awaiting human review
        ├── quarantine_manifest.json
        ├── q-a1b2c3d4_evil.csv
        └── q-e5f6g7h8_inject.json
```

---

## Routing Decision Table

| Condition | Storage | Action |
|---|---|---|
| All 5 layers pass | `approved/` | Ready for analytics |
| Bad extension (`.exe`, `.bat`, etc.) | `rejected/` | HTTP 400 |
| Oversized file | `rejected/` | HTTP 413 |
| Corrupted CSV/JSON/XLSX | `rejected/` | HTTP 422 |
| MIME mismatch (critical) | `quarantine/` | HTTP 400 + quarantine |
| SQL injection in cells | `quarantine/` | HTTP 400 + quarantine |
| Script injection (`<script>`) | `quarantine/` | HTTP 400 + quarantine |
| Code execution (`eval()`) | `quarantine/` | HTTP 400 + quarantine |
| Prompt injection in dataset | `quarantine/` | HTTP 400 + quarantine |

---

## Quarantine ID System

Every quarantined file receives a unique quarantine ID:

```
q-a1b2c3d4
```

Format: `q-` + 8 random hex characters (from UUID4).

The file is renamed:
```
original name:     evil_data.csv
quarantined name:  q-a1b2c3d4_evil_data.csv
```

This prevents:
- Filename collisions (multiple uploads of the same malicious file)
- Ambiguity when reviewing quarantine contents

---

## Quarantine Manifest

Every quarantined file is indexed in `quarantine_manifest.json`:

```json
[
  {
    "quarantine_id": "q-a1b2c3d4",
    "original_filename": "evil.csv",
    "quarantine_filename": "q-a1b2c3d4_evil.csv",
    "reason": "SQL injection payload detected: 'drop table' at row 3, column 'query'.",
    "severity": "critical",
    "timestamp": "2026-06-07T12:34:56.789012+00:00",
    "destination": "security/storage/uploads/quarantine/q-a1b2c3d4_evil.csv"
  }
]
```

The manifest is an **append-only JSON array** — records are never deleted, only added.

---

## Quarantine Review Process

For a production system, the quarantine review workflow would be:

```
1. Security alert fires (email / n8n webhook / SIEM)
       │
       ▼
2. Analyst opens quarantine_manifest.json
       │
       ▼
3. Review quarantine_id entry:
   - reason (what triggered quarantine)
   - severity (low / medium / high / critical)
   - timestamp (when it arrived)
   - original_filename (what the uploader called it)
       │
       ▼
4. Open the quarantined file in an isolated environment
       │
       ├── Confirmed malicious → permanently delete + document in incident log
       ├── False positive → move to approved/ and whitelist
       └── Uncertain → escalate to security team
```

---

## Severity Levels

| Severity | Examples | Typical Action |
|---|---|---|
| `critical` | SQL `DROP TABLE`, `<script>`, `eval()`, MIME mismatch | Immediate review |
| `high` | Path traversal, formula injection (`=cmd\|`), deep JSON | Review within 24h |
| `medium` | Unusual patterns, oversized MIME mismatch | Review within 72h |
| `low` | Minor structure warnings (retained in quarantine) | Periodic review |

---

## API Reference

```python
from guards.quarantine_manager import QuarantineManager

qm = QuarantineManager()

# Route a file
result = qm.route(file_path, action="quarantine", reason="SQL detected", severity="critical")

# Direct actions
qm.approve(file_path)
qm.reject(file_path, reason="Bad extension")
qm.quarantine(file_path, reason="Injection payload", severity="critical")

# Inspect quarantine
manifest = qm.get_manifest()         # all quarantine records
stats    = qm.get_quarantine_stats() # counts by severity
```

---

## Security Notes

- Files in `quarantine/` are **never executed or parsed again** without explicit analyst action
- Quarantine directory permissions should be restricted to security team only
- The manifest file should be monitored for tampering (checksum verification in production)
- For production: integrate with SIEM or n8n webhook to alert on new quarantine entries
