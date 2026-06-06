# ─────────────────────────────────────────────────────────────────────────────
# tests/test_file_encryptor.py
#
# Full test suite for the File Encryptor and Secure Storage Orchestrator.
#
# Covers:
#   Group 1 — encrypt_file()     : CSV, JSON, binary, naming, size, secure_delete
#   Group 2 — decrypt_file()     : round-trips, wrong key, missing file, corrupt
#   Group 3 — Storage routing    : datasets/, reports/, temporary/ directories
#   Group 4 — list utilities     : list_encrypted_files(), list_temp_files()
#   Group 5 — SecureStorage class: store_dataset, retrieve_dataset, store_report,
#                                  retrieve_report, list_stored, cleanup_temp_files,
#                                  verify_integrity
#   Group 6 — cleanup            : max_age filter, delete count, temp dir state
#
# Run:
#   cd security
#   python tests/test_file_encryptor.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
import json
import time
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from encryption.key_manager import generate_key
from encryption.file_encryptor import (
    encrypt_file, decrypt_file,
    list_encrypted_files, list_temp_files,
    get_encrypted_dir,
    FileEncryptionError, FileDecryptionError,
)
from encryption.secure_storage import SecureStorage
from encryption.integrity import validate_encrypted_file, is_encrypted_file
from configs.security_settings import EncryptionConfig

import encryption.file_encryptor as _fe   # for directory overriding in tests


def _make_storage(tmp_path: Path, key: bytes) -> tuple:
    """
    Create a SecureStorage instance wired to temp directories.
    Returns (storage, enc_datasets, enc_reports, enc_temp, dec_temp).
    """
    enc_ds  = tmp_path / "enc" / "datasets"
    enc_rp  = tmp_path / "enc" / "reports"
    enc_tmp = tmp_path / "enc" / "temporary"
    dec_tmp = tmp_path / "decrypted_temp"

    # Patch module-level directory constants
    import encryption.secure_storage as _ss
    _fe.ENCRYPTED_DATASETS  = enc_ds
    _fe.ENCRYPTED_REPORTS   = enc_rp
    _fe.ENCRYPTED_TEMPORARY = enc_tmp
    _fe.DECRYPTED_TEMP_DIR  = dec_tmp
    _ss.DECRYPTED_TEMP_DIR  = dec_tmp

    # Update routing table in file_encryptor
    _fe._CATEGORY_TO_DIR = {
        "dataset"  : enc_ds,
        "datasets" : enc_ds,
        "report"   : enc_rp,
        "reports"  : enc_rp,
        "temporary": enc_tmp,
        "temp"     : enc_tmp,
    }

    storage = SecureStorage(key=key)
    return storage, enc_ds, enc_rp, enc_tmp, dec_tmp


# ── Test runner helpers ───────────────────────────────────────────────────────

def run_tests():

    passed = 0
    failed = 0
    last_group = None

    def check(group: str, description: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed, last_group
        if group != last_group:
            last_group = group
            header = f"  ── {group} "
            print(header + "─" * max(0, 64 - len(header)))
        ok     = bool(condition)
        status = "✅ PASS" if ok else "❌ FAIL"
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        print(f"  {status}  {description}")
        if detail:
            print(f"         {detail}")

    print("\n" + "=" * 68)
    print("       FILE ENCRYPTOR & SECURE STORAGE — FULL TEST SUITE")
    print("       Covers: files | routing | listing | SecureStorage | cleanup")
    print("=" * 68)


    KEY = generate_key()


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — encrypt_file()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        enc_dir  = tmp_path / "encrypted"

        # CSV file
        csv = tmp_path / "sales_q3.csv"
        csv.write_bytes(b"product,revenue\nWidget A,150000\nWidget B,220000")
        enc_csv = encrypt_file(csv, KEY, dest_dir=enc_dir)

        check("encrypt_file()",
              "Returns a Path object",
              isinstance(enc_csv, Path))

        check("encrypt_file()",
              ".enc file is created on disk",
              enc_csv.exists())

        check("encrypt_file()",
              "Encrypted filename has .enc extension",
              enc_csv.name == csv.name + EncryptionConfig.ENCRYPTED_EXT,
              f"enc_name={enc_csv.name}")

        check("encrypt_file()",
              "Encrypted file is larger than plaintext (overhead = IV + TAG = 28 bytes)",
              enc_csv.stat().st_size > csv.stat().st_size)

        check("encrypt_file()",
              "Encrypted file does not contain plaintext (not readable as CSV)",
              b"product,revenue" not in enc_csv.read_bytes())

        # JSON file
        json_file = tmp_path / "report.json"
        json_data = json.dumps({"quarter": "Q3", "revenue": 4200000}).encode()
        json_file.write_bytes(json_data)
        enc_json = encrypt_file(json_file, KEY, dest_dir=enc_dir)
        check("encrypt_file()",
              "JSON file: .enc created and does not expose JSON content",
              enc_json.exists() and json_data not in enc_json.read_bytes())

        # Binary file (simulated AI model weights)
        bin_file = tmp_path / "model_weights.bin"
        bin_data = os.urandom(4096)
        bin_file.write_bytes(bin_data)
        enc_bin = encrypt_file(bin_file, KEY, dest_dir=enc_dir)
        check("encrypt_file()",
              "Binary file (4 KB random): .enc created successfully",
              enc_bin.exists())

        # Validate it looks like a real encrypted file
        check("encrypt_file()",
              "Encrypted payload passes validate_encrypted_file() structural check",
              validate_encrypted_file(enc_csv.read_bytes()))

        # secure_delete: source is removed after encryption
        del_file = tmp_path / "delete_me.csv"
        del_file.write_bytes(b"temporary data")
        encrypt_file(del_file, KEY, dest_dir=enc_dir, secure_delete=True)
        check("encrypt_file()",
              "secure_delete=True removes the source plaintext file",
              not del_file.exists())

        # Missing source file
        try:
            encrypt_file(tmp_path / "ghost.csv", KEY, dest_dir=enc_dir)
            check("encrypt_file()", "Missing source raises FileEncryptionError", False)
        except (FileEncryptionError, FileNotFoundError):
            check("encrypt_file()", "Missing source raises error (FileEncryptionError or FileNotFoundError)", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — decrypt_file()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        enc_dir  = tmp_path / "encrypted"
        dec_dir  = tmp_path / "decrypted_temp"

        # Round-trips
        for name, content in [
            ("revenue.csv",  b"product,revenue\nAlpha,500000"),
            ("report.json",  b'{"q":"Q3","total":4200000}'),
            ("binary.bin",   os.urandom(2048)),
        ]:
            src = tmp_path / name
            src.write_bytes(content)
            enc = encrypt_file(src, KEY, dest_dir=enc_dir)
            dec_path = decrypt_file(enc, KEY, dest_dir=dec_dir)
            check("decrypt_file()",
                  f"{name}: decrypted content matches original",
                  dec_path.read_bytes() == content)

        # Decrypted file has correct name (without .enc)
        csv_src = tmp_path / "named_check.csv"
        csv_src.write_bytes(b"a,b,c")
        enc_named = encrypt_file(csv_src, KEY, dest_dir=enc_dir)
        dec_named = decrypt_file(enc_named, KEY, dest_dir=dec_dir)
        check("decrypt_file()",
              "Decrypted filename matches original (no .enc extension)",
              dec_named.name == "named_check.csv",
              f"decrypted_name={dec_named.name}")

        # Wrong key
        wrong_key = generate_key()
        csv_src2  = tmp_path / "wrong_key_test.csv"
        csv_src2.write_bytes(b"sensitive,data")
        enc_wk = encrypt_file(csv_src2, KEY, dest_dir=enc_dir)
        try:
            decrypt_file(enc_wk, wrong_key, dest_dir=dec_dir)
            check("decrypt_file()", "Wrong key raises FileDecryptionError", False)
        except FileDecryptionError:
            check("decrypt_file()", "Wrong key raises FileDecryptionError", True)

        # Missing .enc file
        try:
            decrypt_file(tmp_path / "ghost.enc", KEY, dest_dir=dec_dir)
            check("decrypt_file()", "Missing .enc file raises FileDecryptionError", False)
        except FileDecryptionError:
            check("decrypt_file()", "Missing .enc file raises FileDecryptionError", True)

        # Corrupted ciphertext (random bytes, valid length)
        corrupt_file = enc_dir / "corrupt.csv.enc"
        corrupt_file.parent.mkdir(parents=True, exist_ok=True)
        corrupt_file.write_bytes(os.urandom(100))
        try:
            decrypt_file(corrupt_file, KEY, dest_dir=dec_dir)
            check("decrypt_file()", "Corrupted ciphertext raises FileDecryptionError", False)
        except FileDecryptionError:
            check("decrypt_file()", "Corrupted ciphertext raises FileDecryptionError", True)

        # Tampered ciphertext (bit-flip in ciphertext region)
        tamper_src = tmp_path / "tamper_test.csv"
        tamper_src.write_bytes(b"original content here")
        enc_tamper = encrypt_file(tamper_src, KEY, dest_dir=enc_dir)
        raw = bytearray(enc_tamper.read_bytes())
        raw[30] ^= 0xFF    # flip a bit in the ciphertext region
        enc_tamper.write_bytes(bytes(raw))
        try:
            decrypt_file(enc_tamper, KEY, dest_dir=dec_dir)
            check("decrypt_file()", "Tampered ciphertext raises FileDecryptionError", False)
        except FileDecryptionError:
            check("decrypt_file()", "Tampered ciphertext (bit-flip) raises FileDecryptionError", True)

        # Too-small file (below IV + TAG minimum)
        tiny_file = enc_dir / "tiny.csv.enc"
        tiny_file.write_bytes(b"tiny")
        try:
            decrypt_file(tiny_file, KEY, dest_dir=dec_dir)
            check("decrypt_file()", "Too-small .enc file raises FileDecryptionError", False)
        except FileDecryptionError:
            check("decrypt_file()", "Too-small .enc file raises FileDecryptionError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — Storage routing
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        storage, enc_ds, enc_rp, enc_tmp, dec_tmp = _make_storage(tmp_path, KEY)

        # Dataset category
        ds_file = tmp_path / "dataset.csv"
        ds_file.write_bytes(b"col1,col2\n1,2")
        enc_ds_path = encrypt_file(ds_file, KEY, category="dataset")
        check("Storage Routing",
              "category='dataset' routes to datasets/ directory",
              enc_ds_path.parent == enc_ds,
              f"parent={enc_ds_path.parent.name}")

        # Report category
        rp_file = tmp_path / "report.json"
        rp_file.write_bytes(b'{"type":"report"}')
        enc_rp_path = encrypt_file(rp_file, KEY, category="report")
        check("Storage Routing",
              "category='report' routes to reports/ directory",
              enc_rp_path.parent == enc_rp,
              f"parent={enc_rp_path.parent.name}")

        # Temporary category
        tmp_file = tmp_path / "temp_process.json"
        tmp_file.write_bytes(b'{"batch":"001"}')
        enc_tmp_path = encrypt_file(tmp_file, KEY, category="temporary")
        check("Storage Routing",
              "category='temporary' routes to temporary/ directory",
              enc_tmp_path.parent == enc_tmp,
              f"parent={enc_tmp_path.parent.name}")

        # Default (no category) → datasets
        default_file = tmp_path / "default.csv"
        default_file.write_bytes(b"a,b")
        enc_default = encrypt_file(default_file, KEY)
        check("Storage Routing",
              "No category defaults to datasets/ directory",
              enc_default.parent == enc_ds,
              f"parent={enc_default.parent.name}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — list utilities
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        storage, enc_ds, enc_rp, enc_tmp, dec_tmp = _make_storage(tmp_path, KEY)

        # Create 3 datasets
        for i in range(3):
            f = tmp_path / f"data_{i}.csv"
            f.write_bytes(f"col,val\n{i},{i*100}".encode())
            encrypt_file(f, KEY, category="dataset")

        listed = list_encrypted_files("dataset")
        check("List Utilities",
              "list_encrypted_files('dataset') returns list of Paths",
              isinstance(listed, list) and all(isinstance(p, Path) for p in listed))

        check("List Utilities",
              "list_encrypted_files('dataset') finds all 3 encrypted files",
              len(listed) == 3,
              f"found={len(listed)}")

        check("List Utilities",
              "All listed files have .enc extension",
              all(p.suffix == ".enc" for p in listed))

        # Empty category
        empty_list = list_encrypted_files("report")
        check("List Utilities",
              "list_encrypted_files() returns empty list for empty category",
              empty_list == [])

        # Temp files after decryption
        dec_dir_used = dec_tmp
        for enc_f in listed[:2]:
            decrypt_file(enc_f, KEY, dest_dir=dec_dir_used)

        temp_files = list_temp_files()
        check("List Utilities",
              "list_temp_files() finds decrypted temp files",
              len(temp_files) >= 2,
              f"found={len(temp_files)}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — SecureStorage class
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        storage, enc_ds, enc_rp, enc_tmp, dec_tmp = _make_storage(tmp_path, KEY)

        # Create test files
        csv_path  = tmp_path / "revenue_q3.csv"
        json_path = tmp_path / "analysis_q3.json"
        csv_path.write_bytes(b"product,revenue\nAlpha,150000")
        json_path.write_bytes(b'{"quarter":"Q3","revenue":4200000}')

        # store_dataset
        enc_ds_path = storage.store_dataset(csv_path)
        check("SecureStorage",
              "store_dataset() returns a Path",
              isinstance(enc_ds_path, Path))

        check("SecureStorage",
              "store_dataset() .enc file exists",
              enc_ds_path.exists())

        # retrieve_dataset
        dec_ds_path = storage.retrieve_dataset(enc_ds_path)
        check("SecureStorage",
              "retrieve_dataset() decrypted content matches original CSV",
              dec_ds_path.read_bytes() == csv_path.read_bytes())

        # store_report
        enc_rp_path = storage.store_report(json_path)
        check("SecureStorage",
              "store_report() .enc file exists",
              enc_rp_path.exists())

        # retrieve_report
        dec_rp_path = storage.retrieve_report(enc_rp_path)
        check("SecureStorage",
              "retrieve_report() decrypted content matches original JSON",
              dec_rp_path.read_bytes() == json_path.read_bytes())

        # verify_integrity
        check("SecureStorage",
              "verify_integrity() returns True for valid .enc file",
              storage.verify_integrity(enc_ds_path) is True)

        # Integrity check on too-small file
        tiny = tmp_path / "tiny.csv.enc"
        tiny.write_bytes(b"tiny")
        try:
            storage.verify_integrity(tiny)
            check("SecureStorage",
                  "verify_integrity() raises IntegrityError for too-small file", False)
        except Exception:
            check("SecureStorage",
                  "verify_integrity() raises error for too-small .enc file", True)

        # list_stored
        listed_ds = storage.list_stored("dataset")
        check("SecureStorage",
              "list_stored('dataset') returns list of dicts",
              isinstance(listed_ds, list) and all(isinstance(d, dict) for d in listed_ds))

        check("SecureStorage",
              "list_stored() dict contains required keys: name, size_bytes, modified_at, path",
              all(
                  all(k in item for k in ["name", "size_bytes", "modified_at", "path"])
                  for item in listed_ds
              ))

        # store_dataset with wrong key scenario
        wrong_key = generate_key()
        bad_storage = SecureStorage(key=wrong_key)
        try:
            bad_storage.retrieve_dataset(enc_ds_path)
            check("SecureStorage",
                  "retrieve_dataset() with wrong key raises FileDecryptionError", False)
        except FileDecryptionError:
            check("SecureStorage",
                  "retrieve_dataset() with wrong key raises FileDecryptionError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — cleanup_temp_files()
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        storage, enc_ds, enc_rp, enc_tmp, dec_tmp = _make_storage(tmp_path, KEY)

        # Create several files and decrypt them to populate decrypted_temp
        for i in range(4):
            f = tmp_path / f"cleanup_test_{i}.csv"
            f.write_bytes(f"idx,val\n{i},{i*50}".encode())
            enc = storage.store_dataset(f)
            storage.retrieve_dataset(enc)

        temp_before = list_temp_files()
        check("cleanup_temp_files()",
              "temp directory contains 4 decrypted files before cleanup",
              len(temp_before) == 4,
              f"count={len(temp_before)}")

        # Cleanup with max_age=0 (delete all regardless of age)
        deleted = storage.cleanup_temp_files(max_age_seconds=0)
        check("cleanup_temp_files()",
              "cleanup_temp_files(0) deletes all temp files",
              deleted == 4,
              f"deleted={deleted}")

        temp_after = list_temp_files()
        check("cleanup_temp_files()",
              "temp directory is empty after cleanup",
              len(temp_after) == 0,
              f"remaining={len(temp_after)}")

        # Cleanup with max_age large enough that nothing is deleted
        f_new = tmp_path / "fresh.csv"
        f_new.write_bytes(b"fresh data")
        enc_new = storage.store_dataset(f_new)
        storage.retrieve_dataset(enc_new)

        deleted_none = storage.cleanup_temp_files(max_age_seconds=99999)
        check("cleanup_temp_files()",
              "cleanup_temp_files(large_age) deletes 0 files (nothing is old enough)",
              deleted_none == 0,
              f"deleted={deleted_none}")

        check("cleanup_temp_files()",
              "Temp file still exists after age-limited cleanup",
              len(list_temp_files()) == 1)


    # ══════════════════════════════════════════════════════════════════════════
    # FINAL SUMMARY
    # ══════════════════════════════════════════════════════════════════════════

    total   = passed + failed
    overall = "ALL TESTS PASSED ✅" if failed == 0 else f"{failed} TEST(S) FAILED ❌"

    print("\n" + "=" * 68)
    print(f"  {passed} passed  |  {failed} failed  |  {total} total")
    print(f"  {overall}")
    print("=" * 68 + "\n")


if __name__ == "__main__":
    run_tests()
