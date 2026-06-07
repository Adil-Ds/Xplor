# Upload Security Architecture

## Overview

The Xplor Upload Protection System is a **defense-in-depth** validation pipeline that intercepts every file upload before it reaches the analytics engine. No file touches storage or processing until it passes all validation layers.

---

## The Upload Pipeline (5 Layers)

```
Uploaded File
      │
      ▼
┌─────────────────────────────────────────────────────┐
│  Layer 1 — Extension Validation                     │
│  FileUploadGuard.validate_extension()               │
│  Checks: .csv / .xlsx / .json only                  │
│  Blocks: .exe .bat .cmd .sh .js .dll .ps1 ...       │
│  Fail: STOP — return 400 (rejected immediately)     │
└────────────────────────┬────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 2 — MIME Type Validation                     │
│  MimeValidator.validate()                           │
│  Checks: actual content vs declared extension       │
│  Uses: libmagic or manual magic-byte inspection     │
│  Blocks: MZ-header in .csv, PDF in .json, etc.      │
│  Fail: STOP — quarantine (suspicious rename)        │
└────────────────────────┬────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 3 — File Size Validation                     │
│  FileUploadGuard.validate_size()                    │
│  Hard limit: 25 MB                                  │
│  Warn limit: 20 MB                                  │
│  Fail: STOP — return 413 (rejected)                 │
└────────────────────────┬────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 4 — Dataset Structure Validation             │
│  DatasetValidator.validate()                        │
│  CSV: headers, column consistency, formula inject.  │
│  JSON: syntax, depth limit, key count               │
│  XLSX: readable workbook, sheet/row limits          │
│  Fail: reject (corrupted) or quarantine (injection) │
└────────────────────────┬────────────────────────────┘
                         │ PASS
                         ▼
┌─────────────────────────────────────────────────────┐
│  Layer 5 — Content Scanning                         │
│  UploadScanner.scan_file()                          │
│  Pass A: Dangerous content (SQL, scripts, eval)     │
│  Pass B: Prompt injection (PromptInjectionDetector) │
│  Fail: QUARANTINE — preserve for review             │
└────────────────────────┬────────────────────────────┘
                         │ CLEAN
                         ▼
┌─────────────────────────────────────────────────────┐
│  QuarantineManager.approve()                        │
│  → storage/uploads/approved/                        │
│  → Analytics Pipeline                              │
└─────────────────────────────────────────────────────┘
```

---

## Fail-Fast Strategy

Layers 1–3 (extension, MIME, size) are **fail-fast**: if any fails, subsequent layers are skipped.

| Layer fails | Reason | Skip | Action |
|---|---|---|---|
| Extension | Bad type (.exe) | MIME, size, structure, scan | Reject |
| MIME | Content mismatch | Size, structure, scan | Quarantine (if critical) / Reject |
| Size | Oversized | Structure, scan | Reject |
| Structure | Corrupted CSV | Scan | Reject |
| Content | SQL / injection | — | Quarantine |

---

## Module Architecture

| Module | Layer | Responsibility |
|---|---|---|
| `configs/upload_settings.py` | Config | All constants, allowed types, limits |
| `guards/file_upload_guard.py` | 1 + 3 | Extension + size validation |
| `guards/mime_validator.py` | 2 | MIME detection + mismatch check |
| `guards/dataset_validator.py` | 4 | CSV/JSON/XLSX structure validation |
| `guards/upload_scanner.py` | 5 | Dangerous content + injection scanning |
| `guards/quarantine_manager.py` | Storage | File routing + manifest |

---

## Allowed vs Rejected File Types

### Allowed
| Extension | MIME Types | Notes |
|---|---|---|
| `.csv` | `text/csv`, `text/plain`, `application/csv` | Must be UTF-8 decodable |
| `.json` | `application/json`, `text/plain` | Must have dict or list root |
| `.xlsx` | `application/vnd.openxmlformats-officedocument.spreadsheetml.sheet`, `application/octet-stream` | Requires openpyxl |

### Blocked Extensions (sample)
`.exe` `.bat` `.cmd` `.sh` `.js` `.dll` `.msi` `.ps1` `.vbs` `.jar` `.py` `.php` `.pl` `.sql` `.zip` `.tar` `.html`

---

## Security Properties

| Property | Implementation |
|---|---|
| Defense in depth | 5 independent validation layers |
| Fail-fast | Stop immediately on obvious failures |
| Never trust extensions | MIME check always follows extension check |
| Audit trail | Every decision logged to AuditLogger |
| Quarantine, don't delete | Suspicious files preserved for review |
| Content-level scanning | SQL, scripts, eval(), injection payloads caught at Layer 5 |
| OWASP CSV Injection | Formula prefixes (=, +, -, @) caught in Layer 4 |

---

## Integration Points

- **Prompt Injection System** — `UploadScanner` calls `DatasetScanner` which calls `PromptInjectionDetector`
- **Audit Logger** — `FileUploadGuard`, `UploadScanner`, `QuarantineManager` all log to `AuditLogger`
- **Security Monitor** — future integration: repeated malicious uploads trigger alerts
- **Analytics Pipeline** — only files in `storage/uploads/approved/` enter the pipeline
