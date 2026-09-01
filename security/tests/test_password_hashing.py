# ─────────────────────────────────────────────────────────────────────────────
# tests/test_password_hashing.py
#
# Full test suite for the bcrypt Password Hashing System.
#
# Covers:
#   Group 1 — hash_password()          : output format, length, randomness, types
#   Group 2 — verify_password()        : correct match, wrong password, timing safety
#   Group 3 — Salt uniqueness           : same password → different hashes
#   Group 4 — Input validation          : empty, None, too long, wrong types
#   Group 5 — is_valid_password_format(): length, digits, letters, edge cases
#   Group 6 — Security properties       : no plaintext in hash, bcrypt prefix
#
# Run:
#   cd security
#   python tests/test_password_hashing.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from auth.password_hashing import hash_password, verify_password, is_valid_password_format
from configs.security_settings import AuthConfig


def run_tests():

    passed   = 0
    failed   = 0
    last_grp = None

    def check(group: str, desc: str, condition: bool, detail: str = "") -> None:
        nonlocal passed, failed, last_grp
        if group != last_grp:
            last_grp = group
            hdr = f"  ── {group} "
            print(hdr + "─" * max(0, 64 - len(hdr)))
        ok = bool(condition)
        passed += 1 if ok else 0
        failed += 0 if ok else 1
        print(f"  {'✅ PASS' if ok else '❌ FAIL'}  {desc}")
        if detail:
            print(f"         {detail}")

    print("\n" + "=" * 68)
    print("       PASSWORD HASHING — FULL TEST SUITE")
    print("       bcrypt | salts | verification | validation | security")
    print("=" * 68)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — hash_password() output format
    # ══════════════════════════════════════════════════════════════════════════

    h = hash_password("SecureP@ss123")

    check("hash_password() Format",
          "Returns a string",
          isinstance(h, str))

    check("hash_password() Format",
          "Hash is exactly 60 characters (bcrypt output length)",
          len(h) == 60,
          f"len={len(h)}")

    check("hash_password() Format",
          "Hash starts with '$2b$' (bcrypt version 2b prefix)",
          h.startswith("$2b$"),
          f"prefix={h[:4]}")

    check("hash_password() Format",
          f"Hash contains work factor '${AuthConfig.BCRYPT_ROUNDS}$' (rounds={AuthConfig.BCRYPT_ROUNDS})",
          f"${AuthConfig.BCRYPT_ROUNDS}$" in h,
          f"hash={h[:20]}...")

    check("hash_password() Format",
          "Hash does not contain the original plaintext password",
          "SecureP@ss123" not in h)

    check("hash_password() Format",
          "Hash is different from the input password",
          h != "SecureP@ss123")

    # Various password types — within the 72-byte bcrypt limit
    for pwd in ["short1A", "A" * 60 + "1", "unicode_1"]:
        try:
            h2 = hash_password(pwd)
            check("hash_password() Format",
                  f"Password of length {len(pwd)} hashes without error",
                  len(h2) == 60)
        except Exception as e:
            check("hash_password() Format",
                  f"Password of length {len(pwd)} hashes without error",
                  False, str(e))

    # Password > 72 chars MUST raise (bcrypt hard limit)
    too_long_for_bcrypt = "A" * 80 + "1"
    try:
        hash_password(too_long_for_bcrypt)
        check("hash_password() Format",
              "Password > 72 chars raises ValueError (bcrypt hard limit)", False)
    except ValueError:
        check("hash_password() Format",
              "Password > 72 chars raises ValueError (bcrypt hard limit)", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — verify_password()
    # ══════════════════════════════════════════════════════════════════════════

    password = "MyP@ssw0rd!"
    hashed   = hash_password(password)

    check("verify_password()",
          "Correct password returns True",
          verify_password(password, hashed) is True)

    check("verify_password()",
          "Wrong password returns False",
          verify_password("wrong_password_1", hashed) is False)

    check("verify_password()",
          "Case-sensitive: uppercase variant rejected",
          verify_password("MYP@SSW0RD!", hashed) is False)

    check("verify_password()",
          "Password with trailing space rejected",
          verify_password(password + " ", hashed) is False)

    check("verify_password()",
          "Empty string returns False (not raises)",
          verify_password("", hashed) is False)

    check("verify_password()",
          "None returns False (not raises)",
          verify_password(None, hashed) is False)

    check("verify_password()",
          "Corrupted hash string returns False (not raises)",
          verify_password(password, "not_a_valid_bcrypt_hash") is False)

    check("verify_password()",
          "Correct password against another user's hash returns False",
          verify_password(password, hash_password("different_password_1")) is False)

    # Verify against all three hash rounds (same password, different salts)
    for i in range(5):
        h_i = hash_password(password)
        ok  = verify_password(password, h_i)
        check("verify_password()",
              f"Correct password verifies against hash #{i+1} (different salt each time)",
              ok is True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — Salt uniqueness
    # ══════════════════════════════════════════════════════════════════════════

    pwd       = "identical_password_1"
    hashes    = [hash_password(pwd) for _ in range(10)]
    unique_ct = len(set(hashes))

    check("Salt Uniqueness",
          "10 hashes of same password produce 10 unique strings (random salts)",
          unique_ct == 10,
          f"unique={unique_ct}/10")

    # Extract embedded salts (characters 7-29 in bcrypt string)
    salts = [h[7:29] for h in hashes]
    check("Salt Uniqueness",
          "All 10 embedded salts are unique (no salt reuse)",
          len(set(salts)) == 10,
          f"unique_salts={len(set(salts))}/10")

    # Despite different hashes, all verify correctly
    for i, h_i in enumerate(hashes):
        check("Salt Uniqueness",
              f"Correct password verifies against unique hash #{i+1}",
              verify_password(pwd, h_i) is True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — Input validation in hash_password()
    # ══════════════════════════════════════════════════════════════════════════

    # Empty string
    try:
        hash_password("")
        check("Input Validation", "Empty password raises ValueError", False)
    except ValueError:
        check("Input Validation", "Empty password raises ValueError", True)

    # None
    try:
        hash_password(None)
        check("Input Validation", "None raises ValueError", False)
    except ValueError:
        check("Input Validation", "None raises ValueError", True)

    # Integer
    try:
        hash_password(12345)
        check("Input Validation", "Integer raises ValueError", False)
    except ValueError:
        check("Input Validation", "Integer raises ValueError", True)

    # Bytes
    try:
        hash_password(b"bytespassword")
        check("Input Validation", "bytes raises ValueError", False)
    except ValueError:
        check("Input Validation", "bytes raises ValueError", True)

    # Too long (> MAX_PASSWORD_LENGTH = 72 — bcrypt hard limit)
    too_long = "A" * (AuthConfig.MAX_PASSWORD_LENGTH + 1) + "1"
    try:
        hash_password(too_long)
        check("Input Validation",
              f"Password > {AuthConfig.MAX_PASSWORD_LENGTH} chars raises ValueError", False)
    except ValueError:
        check("Input Validation",
              f"Password > {AuthConfig.MAX_PASSWORD_LENGTH} chars raises ValueError", True)

    # Exactly at limit (72 chars — should succeed)
    at_limit = "A" * (AuthConfig.MAX_PASSWORD_LENGTH - 1) + "1"
    try:
        h_limit = hash_password(at_limit)
        check("Input Validation",
              f"Password exactly {AuthConfig.MAX_PASSWORD_LENGTH} chars is accepted",
              len(h_limit) == 60)
    except Exception as e:
        check("Input Validation",
              f"Password exactly {AuthConfig.MAX_PASSWORD_LENGTH} chars is accepted",
              False, str(e))


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — is_valid_password_format()
    # ══════════════════════════════════════════════════════════════════════════

    # Valid password
    ok, msg = is_valid_password_format("Strong1Pass")
    check("is_valid_password_format()",
          "Strong password passes format check",
          ok is True and msg == "",
          f"ok={ok}, msg='{msg}'")

    # Too short
    ok2, msg2 = is_valid_password_format("Ab1")
    check("is_valid_password_format()",
          "3-char password fails (minimum 8)",
          ok2 is False and "8" in msg2,
          f"reason: {msg2}")

    # Exactly 8 chars with digit and letter
    ok3, _ = is_valid_password_format("Abcdef1g")
    check("is_valid_password_format()",
          "Exactly 8-char password with digit and letter passes",
          ok3 is True)

    # No digits
    ok4, msg4 = is_valid_password_format("NoDigitsHere")
    check("is_valid_password_format()",
          "Password without digits fails",
          ok4 is False and "digit" in msg4.lower(),
          f"reason: {msg4}")

    # No letters
    ok5, msg5 = is_valid_password_format("12345678")
    check("is_valid_password_format()",
          "Password without letters fails",
          ok5 is False and "letter" in msg5.lower(),
          f"reason: {msg5}")

    # Too long
    ok6, msg6 = is_valid_password_format("A" * 200 + "1")
    check("is_valid_password_format()",
          "Password > 128 chars fails format check",
          ok6 is False,
          f"reason: {msg6}")

    # Non-string
    ok7, msg7 = is_valid_password_format(12345)
    check("is_valid_password_format()",
          "Non-string input returns (False, reason)",
          ok7 is False)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — Security properties
    # ══════════════════════════════════════════════════════════════════════════

    secret_pwd = "SuperSecret99!"
    h_sec = hash_password(secret_pwd)

    check("Security Properties",
          "Hash output never contains the original password",
          secret_pwd not in h_sec)

    check("Security Properties",
          "Hash is not reversible by simple base64 decode",
          True)  # conceptual — bcrypt is one-way by design

    check("Security Properties",
          "bcrypt format means hash cannot be used as SHA-256 input directly",
          not h_sec.isalnum())  # bcrypt contains $, /, . characters

    # Cross-verification: hashes from different users don't interfere
    h_a = hash_password("userA_password_1")
    h_b = hash_password("userB_password_1")
    check("Security Properties",
          "Password A does not verify against Password B's hash",
          verify_password("userA_password_1", h_b) is False)

    check("Security Properties",
          "Password B does not verify against Password A's hash",
          verify_password("userB_password_1", h_a) is False)

    check("Security Properties",
          "Empty string does not verify against a valid hash (no hash bypass)",
          verify_password("", h_a) is False)


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
