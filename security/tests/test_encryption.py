# ─────────────────────────────────────────────────────────────────────────────
# tests/test_encryption.py
#
# Full test suite for AES-256-GCM Engine and Integrity Utilities.
#
# Covers:
#   Group 1 — encrypt_bytes / decrypt_bytes  : round-trips, binary safety
#   Group 2 — encrypt_text / decrypt_text    : string round-trips, encoding
#   Group 3 — IV uniqueness                  : never same IV twice
#   Group 4 — Wire format                    : correct IV‖TAG‖CIPHERTEXT layout
#   Group 5 — Tamper detection               : bit-flips in IV, TAG, ciphertext
#   Group 6 — Wrong key rejection            : every wrong key fails
#   Group 7 — Input validation               : bad key lengths, wrong types
#   Group 8 — integrity.py                   : hash_bytes, hash_file, sidecar,
#                                              validate_encrypted_file, is_encrypted_file
#   Group 9 — encrypt_file / decrypt_file    : file-level round-trips
#
# Run:
#   cd security
#   python tests/test_encryption.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import json
import tempfile
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from encryption.aes import (
    encrypt_bytes, decrypt_bytes,
    encrypt_text, decrypt_text,
    encrypt_file, decrypt_file,
    EncryptionError, DecryptionError,
)
from encryption.key_manager import generate_key
from encryption.integrity import (
    hash_bytes, hash_file, verify_file_hash,
    save_hash_file, load_and_verify_hash,
    validate_encrypted_file, is_encrypted_file,
    IntegrityError,
)
from configs.security_settings import EncryptionConfig


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
    print("       AES-256-GCM ENGINE & INTEGRITY — FULL TEST SUITE")
    print("       Covers: encrypt/decrypt | tamper | keys | integrity")
    print("=" * 68)

    # ─── Shared key for this test run ──────────────────────────────────────
    KEY = generate_key()


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — encrypt_bytes / decrypt_bytes
    # ══════════════════════════════════════════════════════════════════════════

    plain_bytes = b"Hello, Xplor! Sensitive analytics data."

    enc = encrypt_bytes(plain_bytes, KEY)
    dec = decrypt_bytes(enc, KEY)

    check("encrypt_bytes / decrypt_bytes",
          "Round-trip: decrypted bytes match original",
          dec == plain_bytes,
          f"original_len={len(plain_bytes)}  enc_len={len(enc)}")

    check("encrypt_bytes / decrypt_bytes",
          "Encrypted bytes are different from plaintext",
          enc != plain_bytes)

    check("encrypt_bytes / decrypt_bytes",
          "Encrypted output is longer than input (IV + TAG overhead)",
          len(enc) == len(plain_bytes) + EncryptionConfig.IV_SIZE_BYTES + EncryptionConfig.TAG_SIZE_BYTES,
          f"enc_len={len(enc)}  expected={len(plain_bytes) + 28}")

    # Binary data (random bytes — simulates a real file)
    binary = os.urandom(4096)
    enc_bin = encrypt_bytes(binary, KEY)
    dec_bin = decrypt_bytes(enc_bin, KEY)
    check("encrypt_bytes / decrypt_bytes",
          "Binary data (4096 random bytes) round-trips correctly",
          dec_bin == binary)

    # Empty input
    enc_empty = encrypt_bytes(b"", KEY)
    dec_empty = decrypt_bytes(enc_empty, KEY)
    check("encrypt_bytes / decrypt_bytes",
          "Empty bytes encrypt and decrypt correctly",
          dec_empty == b"",
          f"enc_len={len(enc_empty)}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — encrypt_text / decrypt_text
    # ══════════════════════════════════════════════════════════════════════════

    text = "Revenue Q3 2026: $4,200,000 (confidential)"
    enc_t = encrypt_text(text, KEY)
    dec_t = decrypt_text(enc_t, KEY)

    check("encrypt_text / decrypt_text",
          "String round-trip: decrypted text matches original",
          dec_t == text,
          f"original='{text[:40]}'")

    # Unicode
    unicode_text = "数据分析平台 — Analyse de données — Datenanalyse"
    enc_u = encrypt_text(unicode_text, KEY)
    dec_u = decrypt_text(enc_u, KEY)
    check("encrypt_text / decrypt_text",
          "Unicode text round-trips correctly",
          dec_u == unicode_text)

    # Type error
    try:
        encrypt_text(12345, KEY)
        check("encrypt_text / decrypt_text",
              "Non-string input raises EncryptionError", False,
              "FAIL: no exception raised")
    except EncryptionError:
        check("encrypt_text / decrypt_text",
              "Non-string input raises EncryptionError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — IV uniqueness
    # ══════════════════════════════════════════════════════════════════════════

    # Same plaintext encrypted 100 times must produce 100 different ciphertexts
    sample = b"same plaintext every time"
    ciphertexts = [encrypt_bytes(sample, KEY) for _ in range(100)]
    unique_count = len(set(ciphertexts))

    check("IV Uniqueness",
          "100 encryptions of identical plaintext produce 100 unique ciphertexts",
          unique_count == 100,
          f"unique={unique_count}/100")

    # IV portion (first 12 bytes) is always different
    ivs = [c[:EncryptionConfig.IV_SIZE_BYTES] for c in ciphertexts]
    unique_ivs = len(set(ivs))
    check("IV Uniqueness",
          "All 100 IVs are unique (no IV reuse)",
          unique_ivs == 100,
          f"unique_ivs={unique_ivs}/100")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — Wire format
    # ══════════════════════════════════════════════════════════════════════════

    test_plain = b"wire format test"
    test_enc   = encrypt_bytes(test_plain, KEY)
    iv_len     = EncryptionConfig.IV_SIZE_BYTES
    tag_len    = EncryptionConfig.TAG_SIZE_BYTES

    check("Wire Format",
          "First 12 bytes are the IV (extraction position correct)",
          len(test_enc[:iv_len]) == iv_len,
          f"iv={test_enc[:iv_len].hex()[:24]}...")

    check("Wire Format",
          "Bytes 12-28 are the GCM tag (extraction position correct)",
          len(test_enc[iv_len : iv_len + tag_len]) == tag_len)

    check("Wire Format",
          "Ciphertext region length equals plaintext length",
          len(test_enc[iv_len + tag_len:]) == len(test_plain),
          f"ciphertext_region={len(test_enc[iv_len + tag_len:])}  plaintext={len(test_plain)}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — Tamper detection
    # ══════════════════════════════════════════════════════════════════════════

    original_enc = encrypt_bytes(b"tamper detection test", KEY)

    def tamper_byte(data: bytes, pos: int) -> bytes:
        arr = bytearray(data)
        arr[pos] ^= 0xFF
        return bytes(arr)

    # Tamper IV region
    try:
        decrypt_bytes(tamper_byte(original_enc, 5), KEY)
        check("Tamper Detection", "Tampered IV is rejected", False, "FAIL: decryption succeeded")
    except DecryptionError:
        check("Tamper Detection", "Tampered IV is rejected (DecryptionError raised)", True)

    # Tamper TAG region
    try:
        decrypt_bytes(tamper_byte(original_enc, iv_len + 5), KEY)
        check("Tamper Detection", "Tampered GCM tag is rejected", False, "FAIL: decryption succeeded")
    except DecryptionError:
        check("Tamper Detection", "Tampered GCM tag is rejected (DecryptionError raised)", True)

    # Tamper ciphertext region
    try:
        decrypt_bytes(tamper_byte(original_enc, iv_len + tag_len + 2), KEY)
        check("Tamper Detection", "Tampered ciphertext is rejected", False, "FAIL: decryption succeeded")
    except DecryptionError:
        check("Tamper Detection", "Tampered ciphertext is rejected (DecryptionError raised)", True)

    # Truncated payload
    try:
        decrypt_bytes(original_enc[:10], KEY)
        check("Tamper Detection", "Truncated payload is rejected", False, "FAIL: accepted truncated data")
    except DecryptionError:
        check("Tamper Detection", "Truncated payload raises DecryptionError", True)

    # Completely random bytes
    try:
        decrypt_bytes(os.urandom(100), KEY)
        check("Tamper Detection", "Random bytes are rejected", False, "FAIL: accepted random data")
    except DecryptionError:
        check("Tamper Detection", "Completely random bytes raise DecryptionError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — Wrong key rejection
    # ══════════════════════════════════════════════════════════════════════════

    original_plain = b"very sensitive analytics payload"
    original_enc2  = encrypt_bytes(original_plain, KEY)

    for i in range(5):
        wrong_key = generate_key()
        try:
            decrypt_bytes(original_enc2, wrong_key)
            check("Wrong Key Rejection",
                  f"Wrong key #{i+1} is rejected", False,
                  "FAIL: wrong key was accepted")
        except DecryptionError:
            check("Wrong Key Rejection",
                  f"Wrong key #{i+1} is correctly rejected", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 7 — Input validation
    # ══════════════════════════════════════════════════════════════════════════

    # Short key
    try:
        encrypt_bytes(b"test", b"too_short")
        check("Input Validation", "16-byte key raises EncryptionError", False)
    except EncryptionError:
        check("Input Validation", "16-byte key raises EncryptionError", True)

    # Wrong key type (string)
    try:
        encrypt_bytes(b"test", "not_bytes_key")
        check("Input Validation", "String key raises EncryptionError", False)
    except EncryptionError:
        check("Input Validation", "String key (str) raises EncryptionError", True)

    # Wrong key type (int)
    try:
        encrypt_bytes(b"test", 12345)
        check("Input Validation", "Integer key raises EncryptionError", False)
    except EncryptionError:
        check("Input Validation", "Integer key raises EncryptionError", True)

    # 31-byte key (one byte too short)
    try:
        encrypt_bytes(b"test", os.urandom(31))
        check("Input Validation", "31-byte key raises EncryptionError", False)
    except EncryptionError:
        check("Input Validation", "31-byte key raises EncryptionError (must be exactly 32)", True)

    # 33-byte key (one byte too long)
    try:
        encrypt_bytes(b"test", os.urandom(33))
        check("Input Validation", "33-byte key raises EncryptionError", False)
    except EncryptionError:
        check("Input Validation", "33-byte key raises EncryptionError (must be exactly 32)", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 8 — integrity.py
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # hash_bytes
        digest = hash_bytes(b"hello world")
        check("Integrity",
              "hash_bytes() returns 64-char hex string",
              len(digest) == 64 and all(c in "0123456789abcdef" for c in digest),
              f"digest={digest[:32]}...")

        check("Integrity",
              "hash_bytes() is deterministic (same input → same hash)",
              hash_bytes(b"hello") == hash_bytes(b"hello"))

        check("Integrity",
              "hash_bytes() avalanche: different input → completely different hash",
              hash_bytes(b"hello") != hash_bytes(b"Hello"))

        # hash_file
        test_file = tmp_path / "data.csv"
        test_file.write_bytes(b"name,revenue\nAlice,150000")
        file_hash = hash_file(test_file)
        check("Integrity",
              "hash_file() returns 64-char hex digest",
              len(file_hash) == 64,
              f"digest={file_hash[:32]}...")

        # verify_file_hash: match
        check("Integrity",
              "verify_file_hash() returns True for matching hash",
              verify_file_hash(test_file, file_hash) is True)

        # verify_file_hash: mismatch
        check("Integrity",
              "verify_file_hash() returns False for wrong hash",
              verify_file_hash(test_file, "a" * 64) is False)

        # Sidecar save/load round-trip
        sidecar = save_hash_file(test_file)
        check("Integrity",
              "save_hash_file() creates a .sha256 sidecar file",
              sidecar.exists() and sidecar.name.endswith(".sha256"),
              f"sidecar={sidecar.name}")

        check("Integrity",
              "load_and_verify_hash() returns True for unmodified file",
              load_and_verify_hash(test_file) is True)

        # Detect modified file
        test_file.write_bytes(b"name,revenue\nAlice,999999")  # tampered!
        check("Integrity",
              "load_and_verify_hash() returns False after file is modified",
              load_and_verify_hash(test_file) is False)

        # validate_encrypted_file: too small
        check("Integrity",
              "validate_encrypted_file() returns False for 4-byte payload",
              validate_encrypted_file(b"tiny") is False)

        # validate_encrypted_file: valid minimum size
        check("Integrity",
              "validate_encrypted_file() returns True for 28+ byte payload",
              validate_encrypted_file(os.urandom(64)) is True)

        # validate_encrypted_file: exactly minimum (28 bytes)
        check("Integrity",
              "validate_encrypted_file() accepts exactly 28 bytes (minimum valid)",
              validate_encrypted_file(os.urandom(28)) is True)

        # validate_encrypted_file: 27 bytes (one too short)
        check("Integrity",
              "validate_encrypted_file() rejects 27 bytes (one byte below minimum)",
              validate_encrypted_file(os.urandom(27)) is False)

        # is_encrypted_file
        enc_file = tmp_path / "sales.csv.enc"
        enc_file.write_bytes(os.urandom(64))
        check("Integrity",
              "is_encrypted_file() returns True for valid .enc file",
              is_encrypted_file(enc_file) is True)

        plain_file = tmp_path / "sales.csv"
        plain_file.write_bytes(b"sales data")
        check("Integrity",
              "is_encrypted_file() returns False for non-.enc file",
              is_encrypted_file(plain_file) is False)

        tiny_enc = tmp_path / "tiny.enc"
        tiny_enc.write_bytes(b"tiny")
        check("Integrity",
              "is_encrypted_file() returns False for too-small .enc file",
              is_encrypted_file(tiny_enc) is False)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 9 — encrypt_file / decrypt_file (AES module functions)
    # ══════════════════════════════════════════════════════════════════════════

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # CSV file
        csv = tmp_path / "revenue.csv"
        csv.write_bytes(b"product,q3_revenue\nAnalytics Pro,2100000")
        enc_csv = encrypt_file(csv, KEY)
        dec_csv = decrypt_file(enc_csv, KEY)
        check("encrypt_file / decrypt_file",
              "CSV file: decrypted bytes match original",
              dec_csv == csv.read_bytes())

        check("encrypt_file / decrypt_file",
              "CSV file: .enc payload is longer than plaintext",
              len(enc_csv) > len(csv.read_bytes()))

        # JSON file
        json_file = tmp_path / "export.json"
        json_data = json.dumps({"quarter": "Q3", "revenue": 4200000}).encode()
        json_file.write_bytes(json_data)
        enc_json = encrypt_file(json_file, KEY)
        dec_json = decrypt_file(enc_json, KEY)
        check("encrypt_file / decrypt_file",
              "JSON file: decrypted bytes match original",
              dec_json == json_data)

        # Missing source file
        try:
            encrypt_file(tmp_path / "nonexistent.csv", KEY)
            check("encrypt_file / decrypt_file",
                  "Missing source file raises FileNotFoundError", False)
        except FileNotFoundError:
            check("encrypt_file / decrypt_file",
                  "Missing source file raises FileNotFoundError", True)

        # Binary file (simulated model weights)
        bin_file = tmp_path / "model.bin"
        bin_data = os.urandom(8192)
        bin_file.write_bytes(bin_data)
        enc_bin = encrypt_file(bin_file, KEY)
        dec_bin = decrypt_file(enc_bin, KEY)
        check("encrypt_file / decrypt_file",
              "Binary file (8 KB random): round-trip verified",
              dec_bin == bin_data)


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
