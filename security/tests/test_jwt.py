# ─────────────────────────────────────────────────────────────────────────────
# tests/test_jwt.py
#
# Full test suite for the JWT Token Generation and Decoding Engine.
#
# Covers:
#   Group 1 — create_access_token() : structure, claims, types, role validation
#   Group 2 — decode_token()        : successful decode, payload content
#   Group 3 — Expiration             : expired token rejection, exp claim value
#   Group 4 — Wrong secret           : signature verification failure
#   Group 5 — Malformed tokens       : not-a-JWT, truncated, empty, None, bytes
#   Group 6 — Missing claims          : tokens without required claims rejected
#   Group 7 — Role claim             : all three roles encode correctly
#   Group 8 — verify_token()         : True/False convenience wrapper
#   Group 9 — WeakSecretError        : short and missing secrets rejected
#   Group 10 — get_token_expiry()    : extracts expiry without secret
#
# Run:
#   cd security
#   python tests/test_jwt.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
import time
from datetime import datetime, timezone
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test secret BEFORE importing jwt_handler so _load_secret() works
TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
os.environ["JWT_SECRET_KEY"] = TEST_SECRET

from auth.jwt_handler import (
    create_access_token, decode_token, verify_token,
    get_token_expiry, _load_secret,
)
from auth.auth_exceptions import (
    TokenExpiredError, InvalidTokenError, WeakSecretError,
)
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
    print("       JWT ENGINE — FULL TEST SUITE")
    print("       create | decode | expiry | signature | malformed | claims")
    print("=" * 68)

    BASE_PAYLOAD = {"user_id": 42, "username": "arslan", "role": "analyst"}


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — create_access_token()
    # ══════════════════════════════════════════════════════════════════════════

    token = create_access_token(BASE_PAYLOAD, expires_minutes=30, secret=TEST_SECRET)

    check("create_access_token()",
          "Returns a string",
          isinstance(token, str))

    check("create_access_token()",
          "Token has exactly 3 dot-separated segments (HEADER.PAYLOAD.SIGNATURE)",
          token.count(".") == 2,
          f"parts={token.count('.') + 1}")

    check("create_access_token()",
          "Token is not empty",
          len(token) > 0)

    # Two tokens with DIFFERENT payloads are different
    payload2 = {"user_id": 99, "username": "other_user", "role": "admin"}
    token2   = create_access_token(payload2, expires_minutes=30, secret=TEST_SECRET)
    check("create_access_token()",
          "Tokens for different users (user_id 42 vs 99) are different",
          token != token2)

    # Two tokens for same payload but small sleep → different iat
    time.sleep(1.1)
    token_later = create_access_token(BASE_PAYLOAD, expires_minutes=30, secret=TEST_SECRET)
    check("create_access_token()",
          "Two tokens 1s apart for same payload are different (iat differs)",
          token != token_later)

    # Missing required fields
    for missing_field in ["user_id", "username", "role"]:
        bad_payload = {k: v for k, v in BASE_PAYLOAD.items() if k != missing_field}
        try:
            create_access_token(bad_payload, secret=TEST_SECRET)
            check("create_access_token()",
                  f"Missing '{missing_field}' raises InvalidTokenError", False)
        except InvalidTokenError:
            check("create_access_token()",
                  f"Missing '{missing_field}' raises InvalidTokenError", True)

    # Invalid role
    try:
        create_access_token(
            {"user_id": 1, "username": "u", "role": "superadmin"},
            secret=TEST_SECRET,
        )
        check("create_access_token()", "Invalid role 'superadmin' raises InvalidTokenError", False)
    except InvalidTokenError:
        check("create_access_token()", "Invalid role 'superadmin' raises InvalidTokenError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — decode_token() — successful decode
    # ══════════════════════════════════════════════════════════════════════════

    decoded = decode_token(token, secret=TEST_SECRET)

    check("decode_token()",
          "Returns a dict",
          isinstance(decoded, dict))

    check("decode_token()",
          "user_id claim matches input (42)",
          decoded.get("user_id") == 42,
          f"user_id={decoded.get('user_id')}")

    check("decode_token()",
          "username claim matches input ('arslan')",
          decoded.get("username") == "arslan",
          f"username={decoded.get('username')}")

    check("decode_token()",
          "role claim matches input ('analyst')",
          decoded.get("role") == "analyst",
          f"role={decoded.get('role')}")

    check("decode_token()",
          "iat (issued at) claim is present and is an integer",
          isinstance(decoded.get("iat"), int),
          f"iat={decoded.get('iat')}")

    check("decode_token()",
          "exp (expiration) claim is present and is an integer",
          isinstance(decoded.get("exp"), int),
          f"exp={decoded.get('exp')}")

    check("decode_token()",
          "exp > iat (expiry is in the future relative to issue time)",
          decoded.get("exp", 0) > decoded.get("iat", 0))

    check("decode_token()",
          "exp - iat ≈ 30 minutes (1800 seconds, within ±10s tolerance)",
          abs((decoded["exp"] - decoded["iat"]) - 1800) < 10,
          f"diff={decoded['exp'] - decoded['iat']}s")

    check("decode_token()",
          "iat is approximately now (within ±5 seconds of current time)",
          abs(decoded["iat"] - int(datetime.now(timezone.utc).timestamp())) < 5,
          f"iat_age={int(datetime.now(timezone.utc).timestamp()) - decoded['iat']}s")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — Expiration handling
    # ══════════════════════════════════════════════════════════════════════════

    expired_token = create_access_token(
        BASE_PAYLOAD, expires_minutes=-1, secret=TEST_SECRET
    )
    time.sleep(0.1)  # ensure at least 0.1s passes

    try:
        decode_token(expired_token, secret=TEST_SECRET)
        check("Expiration", "Expired token raises TokenExpiredError", False,
              "FAIL: expired token was accepted")
    except TokenExpiredError as e:
        check("Expiration", "Expired token raises TokenExpiredError", True)
        check("Expiration",
              "TokenExpiredError has expired_at attribute",
              hasattr(e, "expired_at") and e.expired_at,
              f"expired_at='{e.expired_at}'")

    check("Expiration",
          "verify_token() returns False for expired token",
          verify_token(expired_token, secret=TEST_SECRET) is False)

    # Custom expiry values
    for exp_mins in [1, 15, 60, 120]:
        t = create_access_token(BASE_PAYLOAD, expires_minutes=exp_mins, secret=TEST_SECRET)
        d = decode_token(t, secret=TEST_SECRET)
        expected_diff = exp_mins * 60
        actual_diff   = d["exp"] - d["iat"]
        check("Expiration",
              f"expires_minutes={exp_mins} → exp-iat≈{expected_diff}s",
              abs(actual_diff - expected_diff) < 5,
              f"actual_diff={actual_diff}s")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — Wrong secret / signature failure
    # ══════════════════════════════════════════════════════════════════════════

    for i, wrong_secret in enumerate([
        "wrong_secret_key_minimum_32_chars_aa",
        "completely_different_secret_key_xxxx",
        "another_wrong_secret_key_32chars_bbbb",
        "totally_different_again_32chars_cccc_",
        "last_wrong_secret_key_minimum_32chars",
    ]):
        try:
            decode_token(token, secret=wrong_secret)
            check("Wrong Secret", f"Wrong secret #{i+1} raises InvalidTokenError", False,
                  f"FAIL: wrong secret '{wrong_secret[:20]}...' was accepted")
        except InvalidTokenError:
            check("Wrong Secret", f"Wrong secret #{i+1} raises InvalidTokenError", True)

    # Tampered token (flip a char in the signature)
    parts = token.split(".")
    tampered = parts[0] + "." + parts[1] + "." + parts[2][:-2] + "XX"
    try:
        decode_token(tampered, secret=TEST_SECRET)
        check("Wrong Secret", "Tampered signature raises InvalidTokenError", False)
    except InvalidTokenError:
        check("Wrong Secret", "Tampered signature (last 2 chars flipped) raises InvalidTokenError", True)

    # Tampered payload (flip a char in payload segment)
    payload_tampered = parts[0] + "." + parts[1][:-2] + "XX" + "." + parts[2]
    try:
        decode_token(payload_tampered, secret=TEST_SECRET)
        check("Wrong Secret", "Tampered payload raises InvalidTokenError", False)
    except InvalidTokenError:
        check("Wrong Secret", "Tampered payload (payload segment modified) raises InvalidTokenError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — Malformed tokens
    # ══════════════════════════════════════════════════════════════════════════

    malformed_cases = [
        ("not.a.jwt",         "Random 3-segment string"),
        ("",                  "Empty string"),
        ("single_segment",    "Single segment (no dots)"),
        ("only.two",          "Two segments only"),
        ("a.b.c.d",           "Four segments (too many)"),
        ("aaa.bbb.",          "Trailing dot with empty signature"),
        (".bbb.ccc",          "Leading dot with empty header"),
    ]

    for bad_token, desc in malformed_cases:
        try:
            decode_token(bad_token, secret=TEST_SECRET)
            check("Malformed Tokens", f"{desc} raises InvalidTokenError", False,
                  f"FAIL: '{bad_token}' was accepted")
        except InvalidTokenError:
            check("Malformed Tokens", f"{desc} raises InvalidTokenError", True)

    # None
    try:
        decode_token(None, secret=TEST_SECRET)
        check("Malformed Tokens", "None raises InvalidTokenError", False)
    except InvalidTokenError:
        check("Malformed Tokens", "None raises InvalidTokenError", True)

    # bytes
    try:
        decode_token(b"bytes.token.here", secret=TEST_SECRET)
        check("Malformed Tokens", "bytes raises InvalidTokenError", False)
    except InvalidTokenError:
        check("Malformed Tokens", "bytes raises InvalidTokenError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — Missing claims (custom tokens without required fields)
    # ══════════════════════════════════════════════════════════════════════════

    import jwt as _jwt

    for missing_claim in ["user_id", "username", "role"]:
        payload_no_claim = {
            k: v for k, v in {
                "user_id": 1, "username": "u", "role": "viewer",
                "iat": int(datetime.now(timezone.utc).timestamp()),
                "exp": int(datetime.now(timezone.utc).timestamp()) + 1800,
            }.items() if k != missing_claim
        }
        raw = _jwt.encode(payload_no_claim, TEST_SECRET, algorithm="HS256")
        try:
            decode_token(raw, secret=TEST_SECRET)
            check("Missing Claims",
                  f"Token without '{missing_claim}' raises InvalidTokenError", False)
        except InvalidTokenError:
            check("Missing Claims",
                  f"Token without '{missing_claim}' raises InvalidTokenError", True)

    # Token with invalid role value
    bad_role_payload = {
        "user_id": 1, "username": "u", "role": "godmode",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int(datetime.now(timezone.utc).timestamp()) + 1800,
    }
    raw_bad_role = _jwt.encode(bad_role_payload, TEST_SECRET, algorithm="HS256")
    try:
        decode_token(raw_bad_role, secret=TEST_SECRET)
        check("Missing Claims", "Invalid role 'godmode' raises InvalidTokenError", False)
    except InvalidTokenError:
        check("Missing Claims", "Invalid role 'godmode' raises InvalidTokenError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 7 — Role claim encoding
    # ══════════════════════════════════════════════════════════════════════════

    for role in ["admin", "analyst", "viewer"]:
        t = create_access_token(
            {"user_id": 1, "username": "user", "role": role},
            expires_minutes=30, secret=TEST_SECRET,
        )
        d = decode_token(t, secret=TEST_SECRET)
        check("Role Claims",
              f"Role '{role}' is correctly encoded and decoded",
              d.get("role") == role,
              f"encoded={role}  decoded={d.get('role')}")

    # All three roles in one batch — cross check
    tokens = {
        role: create_access_token(
            {"user_id": i+1, "username": f"{role}_user", "role": role},
            secret=TEST_SECRET,
        )
        for i, role in enumerate(["admin", "analyst", "viewer"])
    }
    for role, t in tokens.items():
        d = decode_token(t, secret=TEST_SECRET)
        check("Role Claims",
              f"Cross-check: '{role}' token decodes to correct role",
              d["role"] == role)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 8 — verify_token()
    # ══════════════════════════════════════════════════════════════════════════

    valid_token = create_access_token(BASE_PAYLOAD, expires_minutes=30, secret=TEST_SECRET)

    check("verify_token()",
          "Valid token returns True",
          verify_token(valid_token, secret=TEST_SECRET) is True)

    check("verify_token()",
          "Expired token returns False",
          verify_token(expired_token, secret=TEST_SECRET) is False)

    check("verify_token()",
          "Wrong secret returns False",
          verify_token(valid_token, secret="wrong_secret_key_minimum_32_chars_aa") is False)

    check("verify_token()",
          "Empty string returns False",
          verify_token("", secret=TEST_SECRET) is False)

    check("verify_token()",
          "None returns False",
          verify_token(None, secret=TEST_SECRET) is False)

    check("verify_token()",
          "Random string returns False",
          verify_token("this.is.garbage", secret=TEST_SECRET) is False)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 9 — WeakSecretError
    # ══════════════════════════════════════════════════════════════════════════

    orig_secret = os.environ.get("JWT_SECRET_KEY", TEST_SECRET)

    # Short secret
    os.environ["JWT_SECRET_KEY"] = "short"
    try:
        _load_secret()
        check("WeakSecretError", "Secret shorter than 32 chars raises WeakSecretError", False)
    except WeakSecretError as e:
        check("WeakSecretError", "Secret shorter than 32 chars raises WeakSecretError", True)
        check("WeakSecretError",
              "WeakSecretError reports actual_length",
              e.actual_length == len("short"),
              f"actual_length={e.actual_length}")

    # Missing secret
    os.environ.pop("JWT_SECRET_KEY", None)
    try:
        _load_secret()
        check("WeakSecretError", "Missing JWT_SECRET_KEY raises WeakSecretError", False)
    except WeakSecretError as e:
        check("WeakSecretError", "Missing JWT_SECRET_KEY raises WeakSecretError", True)
        check("WeakSecretError",
              "WeakSecretError.actual_length is 0 for missing key",
              e.actual_length == 0,
              f"actual_length={e.actual_length}")

    # Exactly 32 chars (minimum — should pass)
    min_secret = "A" * 32
    os.environ["JWT_SECRET_KEY"] = min_secret
    try:
        loaded = _load_secret()
        check("WeakSecretError",
              "Secret of exactly 32 chars is accepted",
              loaded == min_secret)
    except WeakSecretError:
        check("WeakSecretError", "Secret of exactly 32 chars is accepted", False)

    # Restore
    os.environ["JWT_SECRET_KEY"] = orig_secret


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 10 — get_token_expiry()
    # ══════════════════════════════════════════════════════════════════════════

    exp_token = create_access_token(BASE_PAYLOAD, expires_minutes=60, secret=TEST_SECRET)
    expiry    = get_token_expiry(exp_token)

    check("get_token_expiry()",
          "Returns a datetime object",
          isinstance(expiry, datetime))

    check("get_token_expiry()",
          "Expiry is timezone-aware (UTC)",
          expiry.tzinfo is not None)

    check("get_token_expiry()",
          "Expiry is approximately 60 minutes from now",
          abs((expiry - datetime.now(timezone.utc)).total_seconds() - 3600) < 30,
          f"seconds_until_expiry={int((expiry - datetime.now(timezone.utc)).total_seconds())}")

    check("get_token_expiry()",
          "Returns None for an invalid/garbage token",
          get_token_expiry("not.a.valid.jwt.at.all") is None)

    check("get_token_expiry()",
          "Works on expired token without raising (no signature check)",
          get_token_expiry(expired_token) is not None)


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
