# ─────────────────────────────────────────────────────────────────────────────
# tests/test_token_validation.py
#
# Full test suite for the Token Validator and Auth Utilities.
#
# Covers:
#   Group 1  — validate_token()           : valid, expired, bad signature, edge cases
#   Group 2  — Bearer prefix handling     : auto-strip "Bearer <token>"
#   Group 3  — is_token_expired()         : expired vs live, no-secret check
#   Group 4  — extract_claims()           : no secret required, expired tokens
#   Group 5  — require_role()             : hierarchy enforcement, all combos
#   Group 6  — get_user_role()            : role extraction from validated token
#   Group 7  — get_user_identity()        : identity dict shape and values
#   Group 8  — authenticate_user()        : full login flow, success, failure
#   Group 9  — validate_request_token()   : full middleware flow, role guard
#   Group 10 — build_auth_response()      : response shape validation
#   Group 11 — build_error_response()     : error response shape validation
#   Group 12 — register_user()            : hash + validation + audit
#   Group 13 — generate_user_payload()    : payload builder validation
#   Group 14 — Audit log integration      : no exception from audit logger
#
# Run:
#   cd security
#   python tests/test_token_validation.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
import time
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set test secret BEFORE importing anything that touches jwt_handler
TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
os.environ["JWT_SECRET_KEY"] = TEST_SECRET

from auth.jwt_handler import create_access_token
from auth.password_hashing import hash_password
from auth.token_validator import (
    validate_token, is_token_expired, extract_claims,
    require_role, get_user_role, get_user_identity,
)
from auth.auth_utils import (
    authenticate_user, validate_request_token, register_user,
    build_auth_response, build_error_response, generate_user_payload,
    logout_user, validate_credentials, get_current_timestamp,
)
from auth.auth_exceptions import (
    TokenExpiredError, InvalidTokenError, UnauthorizedAccessError,
    InvalidCredentialsError, WeakSecretError,
)
from configs.security_settings import AuthConfig


# ── Token factory helpers ─────────────────────────────────────────────────────

def _make_token(user_id=1, username="arslan", role="analyst", exp_minutes=30):
    payload = {"user_id": user_id, "username": username, "role": role}
    return create_access_token(payload, expires_minutes=exp_minutes, secret=TEST_SECRET)

def _expired_token(role="analyst"):
    p = {"user_id": 1, "username": "arslan", "role": role}
    t = create_access_token(p, expires_minutes=-1, secret=TEST_SECRET)
    time.sleep(0.1)
    return t


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
    print("       TOKEN VALIDATION & AUTH UTILS — FULL TEST SUITE")
    print("       validate | roles | login | middleware | responses")
    print("=" * 68)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — validate_token()
    # ══════════════════════════════════════════════════════════════════════════

    valid   = _make_token()
    expired = _expired_token()

    payload = validate_token(valid, secret=TEST_SECRET)
    check("validate_token()",
          "Valid token returns dict payload",
          isinstance(payload, dict))

    check("validate_token()",
          "Returned payload contains all required claims",
          all(k in payload for k in ["user_id", "username", "role", "iat", "exp"]))

    check("validate_token()",
          "username in payload matches original",
          payload["username"] == "arslan")

    # Expired
    try:
        validate_token(expired, secret=TEST_SECRET)
        check("validate_token()", "Expired token raises TokenExpiredError", False)
    except TokenExpiredError:
        check("validate_token()", "Expired token raises TokenExpiredError", True)

    # Wrong signature
    try:
        validate_token(valid, secret="totally_wrong_key_minimum_32_chars_x")
        check("validate_token()", "Wrong signature raises InvalidTokenError", False)
    except InvalidTokenError:
        check("validate_token()", "Wrong signature raises InvalidTokenError", True)

    # None / empty / int
    for bad, label in [(None, "None"), ("", "empty"), (0, "int")]:
        try:
            validate_token(bad, secret=TEST_SECRET)
            check("validate_token()", f"{label} input raises InvalidTokenError", False)
        except InvalidTokenError:
            check("validate_token()", f"{label} input raises InvalidTokenError", True)

    # Malformed
    try:
        validate_token("this.is.not.real", secret=TEST_SECRET)
        check("validate_token()", "Garbage token raises InvalidTokenError", False)
    except InvalidTokenError:
        check("validate_token()", "Garbage token raises InvalidTokenError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — Bearer prefix handling
    # ══════════════════════════════════════════════════════════════════════════

    bearer_variants = [
        f"Bearer {valid}",
        f"bearer {valid}",
        f"BEARER {valid}",
        f"  Bearer  {valid}  ",
    ]
    for variant in bearer_variants:
        p = validate_token(variant, secret=TEST_SECRET)
        check("Bearer Prefix",
              f"'{variant[:14].strip()}...' is handled correctly",
              p["username"] == "arslan")

    # Token without Bearer prefix still works
    p_plain = validate_token(valid, secret=TEST_SECRET)
    check("Bearer Prefix",
          "Plain token (no Bearer prefix) still validates",
          p_plain["username"] == "arslan")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — is_token_expired()
    # ══════════════════════════════════════════════════════════════════════════

    check("is_token_expired()",
          "Live 30-minute token returns False",
          is_token_expired(valid) is False)

    check("is_token_expired()",
          "Already-expired token returns True",
          is_token_expired(expired) is True)

    check("is_token_expired()",
          "Random garbage string returns True (safe default)",
          is_token_expired("garbage.string.here") is True)

    check("is_token_expired()",
          "Empty string returns True (safe default)",
          is_token_expired("") is True)

    # Works without secret (no signature verification)
    check("is_token_expired()",
          "Expired token detected without needing the secret key",
          is_token_expired(expired) is True)  # no secret=TEST_SECRET needed


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — extract_claims() (no verification)
    # ══════════════════════════════════════════════════════════════════════════

    claims = extract_claims(valid)
    check("extract_claims()",
          "Returns a dict with username claim",
          claims.get("username") == "arslan")

    # Works on expired token (for audit logging)
    claims_expired = extract_claims(expired)
    check("extract_claims()",
          "Extracts claims from expired token (for logging purposes)",
          claims_expired.get("username") == "arslan")

    # Non-JWT returns empty dict
    claims_bad = extract_claims("not_a_jwt")
    check("extract_claims()",
          "Non-JWT string returns empty dict (not an exception)",
          isinstance(claims_bad, dict) and len(claims_bad) == 0)

    claims_none = extract_claims(None)
    check("extract_claims()",
          "None returns empty dict",
          isinstance(claims_none, dict) and len(claims_none) == 0)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — require_role() — hierarchy enforcement
    # ══════════════════════════════════════════════════════════════════════════

    admin_t   = _make_token(role="admin")
    analyst_t = _make_token(role="analyst")
    viewer_t  = _make_token(role="viewer")

    # Admin can access all levels
    for required in ["viewer", "analyst", "admin"]:
        p = require_role(admin_t, required, secret=TEST_SECRET)
        check("require_role()",
              f"admin passes '{required}' requirement",
              p["role"] == "admin")

    # Analyst can access viewer and analyst, but NOT admin
    for required in ["viewer", "analyst"]:
        p = require_role(analyst_t, required, secret=TEST_SECRET)
        check("require_role()",
              f"analyst passes '{required}' requirement",
              p["role"] == "analyst")

    try:
        require_role(analyst_t, "admin", resource="admin_panel", secret=TEST_SECRET)
        check("require_role()", "analyst CANNOT access 'admin' resource", False)
    except UnauthorizedAccessError as e:
        check("require_role()", "analyst blocked from 'admin' resource", True)
        check("require_role()",
              "UnauthorizedAccessError has correct required_role",
              e.required_role == "admin")
        check("require_role()",
              "UnauthorizedAccessError has correct actual_role",
              e.actual_role == "analyst")

    # Viewer can only access viewer
    p_v = require_role(viewer_t, "viewer", secret=TEST_SECRET)
    check("require_role()", "viewer passes 'viewer' requirement", p_v["role"] == "viewer")

    for higher in ["analyst", "admin"]:
        try:
            require_role(viewer_t, higher, resource="dashboard", secret=TEST_SECRET)
            check("require_role()", f"viewer blocked from '{higher}'", False)
        except UnauthorizedAccessError:
            check("require_role()", f"viewer correctly blocked from '{higher}'", True)

    # require_role with expired token
    exp_analyst = _expired_token(role="analyst")
    try:
        require_role(exp_analyst, "viewer", secret=TEST_SECRET)
        check("require_role()", "Expired token raises TokenExpiredError in require_role", False)
    except TokenExpiredError:
        check("require_role()", "Expired token raises TokenExpiredError in require_role", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — get_user_role()
    # ══════════════════════════════════════════════════════════════════════════

    for role in ["admin", "analyst", "viewer"]:
        t    = _make_token(role=role)
        got  = get_user_role(t, secret=TEST_SECRET)
        check("get_user_role()",
              f"get_user_role() returns '{role}' for {role} token",
              got == role)

    try:
        get_user_role(expired, secret=TEST_SECRET)
        check("get_user_role()", "Expired token raises TokenExpiredError", False)
    except TokenExpiredError:
        check("get_user_role()", "Expired token raises TokenExpiredError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 7 — get_user_identity()
    # ══════════════════════════════════════════════════════════════════════════

    identity = get_user_identity(valid, secret=TEST_SECRET)
    check("get_user_identity()",
          "Returns a dict",
          isinstance(identity, dict))

    check("get_user_identity()",
          "Dict has exactly keys: user_id, username, role",
          set(identity.keys()) == {"user_id", "username", "role"},
          f"keys={set(identity.keys())}")

    check("get_user_identity()",
          "user_id value is correct",
          identity["user_id"] == 1)

    check("get_user_identity()",
          "username value is 'arslan'",
          identity["username"] == "arslan")

    check("get_user_identity()",
          "role value is 'analyst'",
          identity["role"] == "analyst")

    try:
        get_user_identity(expired, secret=TEST_SECRET)
        check("get_user_identity()", "Expired token raises TokenExpiredError", False)
    except TokenExpiredError:
        check("get_user_identity()", "Expired token raises TokenExpiredError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 8 — authenticate_user() — full login flow
    # ══════════════════════════════════════════════════════════════════════════

    stored_hash = hash_password("SecureP@ss123")

    # Successful login
    auth_resp = authenticate_user(
        username="arslan", stored_hash=stored_hash,
        plain_password="SecureP@ss123", user_id=42, role="analyst",
        expires_minutes=30, secret=TEST_SECRET,
    )
    check("authenticate_user()",
          "Returns dict with success=True",
          auth_resp.get("success") is True)

    check("authenticate_user()",
          "Response contains 'access_token'",
          "access_token" in auth_resp)

    check("authenticate_user()",
          "token_type is 'bearer'",
          auth_resp.get("token_type") == "bearer")

    check("authenticate_user()",
          "expires_in is 1800 (30 minutes × 60 seconds)",
          auth_resp.get("expires_in") == 1800)

    check("authenticate_user()",
          "username is 'arslan' in response",
          auth_resp.get("username") == "arslan")

    check("authenticate_user()",
          "role is 'analyst' in response",
          auth_resp.get("role") == "analyst")

    # The returned token is actually valid
    returned_token = auth_resp["access_token"]
    decoded        = validate_token(returned_token, secret=TEST_SECRET)
    check("authenticate_user()",
          "Returned access_token decodes to correct username",
          decoded["username"] == "arslan")

    # Wrong password
    try:
        authenticate_user(
            username="arslan", stored_hash=stored_hash,
            plain_password="WRONG_PASSWORD", user_id=42, role="analyst",
            secret=TEST_SECRET,
        )
        check("authenticate_user()", "Wrong password raises InvalidCredentialsError", False)
    except InvalidCredentialsError:
        check("authenticate_user()", "Wrong password raises InvalidCredentialsError", True)

    # Empty username
    try:
        authenticate_user(
            username="", stored_hash=stored_hash,
            plain_password="SecureP@ss123", user_id=42, role="analyst",
            secret=TEST_SECRET,
        )
        check("authenticate_user()", "Empty username raises InvalidCredentialsError", False)
    except InvalidCredentialsError:
        check("authenticate_user()", "Empty username raises InvalidCredentialsError", True)

    # Empty password
    try:
        authenticate_user(
            username="arslan", stored_hash=stored_hash,
            plain_password="", user_id=42, role="analyst",
            secret=TEST_SECRET,
        )
        check("authenticate_user()", "Empty password raises InvalidCredentialsError", False)
    except InvalidCredentialsError:
        check("authenticate_user()", "Empty password raises InvalidCredentialsError", True)

    # Multiple wrong attempts — all rejected
    for i in range(3):
        try:
            authenticate_user(
                username="arslan", stored_hash=stored_hash,
                plain_password=f"wrong_attempt_{i}", user_id=42, role="analyst",
                secret=TEST_SECRET,
            )
            check("authenticate_user()", f"Wrong attempt #{i+1} raises InvalidCredentialsError", False)
        except InvalidCredentialsError:
            check("authenticate_user()", f"Wrong attempt #{i+1} correctly rejected", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 9 — validate_request_token() — full middleware flow
    # ══════════════════════════════════════════════════════════════════════════

    analyst_token = _make_token(role="analyst")
    admin_token   = _make_token(role="admin")
    viewer_token  = _make_token(role="viewer")

    # Analyst accessing analyst resource
    identity = validate_request_token(
        analyst_token, required_role="analyst",
        resource="analytics_dashboard", secret=TEST_SECRET,
    )
    check("validate_request_token()",
          "analyst accesses 'analyst' resource → returns identity dict",
          identity["role"] == "analyst")

    # Admin accessing analyst resource (higher role)
    identity2 = validate_request_token(
        admin_token, required_role="analyst",
        resource="analytics_dashboard", secret=TEST_SECRET,
    )
    check("validate_request_token()",
          "admin accesses 'analyst' resource → allowed by hierarchy",
          identity2["role"] == "admin")

    # Viewer blocked from analyst resource
    try:
        validate_request_token(
            viewer_token, required_role="analyst",
            resource="analytics_dashboard", secret=TEST_SECRET,
        )
        check("validate_request_token()", "viewer blocked from 'analyst' resource", False)
    except UnauthorizedAccessError:
        check("validate_request_token()", "viewer blocked from 'analyst' resource", True)

    # Expired token in middleware
    try:
        validate_request_token(
            _expired_token(), required_role="viewer",
            resource="any_resource", secret=TEST_SECRET,
        )
        check("validate_request_token()", "Expired token raises TokenExpiredError", False)
    except TokenExpiredError:
        check("validate_request_token()", "Expired token raises TokenExpiredError in middleware", True)

    # Invalid token in middleware
    try:
        validate_request_token(
            "not.a.jwt", required_role="viewer",
            resource="any_resource", secret=TEST_SECRET,
        )
        check("validate_request_token()", "Invalid token raises InvalidTokenError", False)
    except InvalidTokenError:
        check("validate_request_token()", "Invalid token raises InvalidTokenError in middleware", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 10 — build_auth_response()
    # ══════════════════════════════════════════════════════════════════════════

    resp = build_auth_response("fake.jwt.token", 1800, "arslan", "analyst")
    check("build_auth_response()",
          "success is True",
          resp["success"] is True)

    check("build_auth_response()",
          "access_token is the token string",
          resp["access_token"] == "fake.jwt.token")

    check("build_auth_response()",
          "token_type is 'bearer'",
          resp["token_type"] == "bearer")

    check("build_auth_response()",
          "expires_in is 1800",
          resp["expires_in"] == 1800)

    check("build_auth_response()",
          "username is included when provided",
          resp.get("username") == "arslan")

    check("build_auth_response()",
          "role is included when provided",
          resp.get("role") == "analyst")

    # Without optional fields
    resp_min = build_auth_response("tok", 900)
    check("build_auth_response()",
          "Minimal call (no username/role) returns valid dict",
          resp_min["success"] is True and "username" not in resp_min)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 11 — build_error_response()
    # ══════════════════════════════════════════════════════════════════════════

    err = build_error_response("Invalid credentials")
    check("build_error_response()",
          "success is False",
          err["success"] is False)

    check("build_error_response()",
          "message matches input",
          err["message"] == "Invalid credentials")

    check("build_error_response()",
          "No error_code key when not provided",
          "error_code" not in err)

    err2 = build_error_response("Session expired", error_code="token_expired")
    check("build_error_response()",
          "error_code present when provided",
          err2.get("error_code") == "token_expired")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 12 — register_user()
    # ══════════════════════════════════════════════════════════════════════════

    reg = register_user("new_user", "ValidPass1")
    check("register_user()",
          "Returns dict with hashed_password",
          "hashed_password" in reg)

    check("register_user()",
          "hashed_password is a valid bcrypt hash",
          reg["hashed_password"].startswith("$2b$"))

    check("register_user()",
          "username in returned dict",
          reg.get("username") == "new_user")

    check("register_user()",
          "created_at timestamp is present and is an int",
          isinstance(reg.get("created_at"), int))

    # Weak password
    try:
        register_user("user2", "weak")
        check("register_user()", "Weak password raises ValueError", False)
    except ValueError:
        check("register_user()", "Weak password (too short) raises ValueError", True)

    # Password without digits
    try:
        register_user("user3", "NoDigitsHere")
        check("register_user()", "Password without digits raises ValueError", False)
    except ValueError:
        check("register_user()", "Password without digits raises ValueError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 13 — generate_user_payload()
    # ══════════════════════════════════════════════════════════════════════════

    p = generate_user_payload(42, "arslan", "analyst")
    check("generate_user_payload()",
          "Returns correct dict",
          p == {"user_id": 42, "username": "arslan", "role": "analyst"})

    # Invalid user_id
    try:
        generate_user_payload(0, "u", "viewer")
        check("generate_user_payload()", "user_id=0 raises ValueError", False)
    except ValueError:
        check("generate_user_payload()", "user_id=0 raises ValueError", True)

    # Negative user_id
    try:
        generate_user_payload(-5, "u", "viewer")
        check("generate_user_payload()", "Negative user_id raises ValueError", False)
    except ValueError:
        check("generate_user_payload()", "Negative user_id raises ValueError", True)

    # Invalid role
    try:
        generate_user_payload(1, "u", "godmode")
        check("generate_user_payload()", "Invalid role 'godmode' raises ValueError", False)
    except ValueError:
        check("generate_user_payload()", "Invalid role 'godmode' raises ValueError", True)

    # All three valid roles
    for role in ["admin", "analyst", "viewer"]:
        p2 = generate_user_payload(1, "u", role)
        check("generate_user_payload()",
              f"Role '{role}' accepted",
              p2["role"] == role)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 14 — Audit log integration
    # ══════════════════════════════════════════════════════════════════════════

    # Run a complete login flow — no exceptions from logging
    try:
        h = hash_password("AuditTest1")
        r = authenticate_user(
            "audit_user", h, "AuditTest1", user_id=99, role="viewer",
            expires_minutes=1, secret=TEST_SECRET,
        )
        check("Audit Integration",
              "authenticate_user() completes without audit-related exceptions",
              r["success"] is True)
    except Exception as e:
        check("Audit Integration",
              "authenticate_user() completes without audit-related exceptions",
              False, str(e))

    # Failed login — no exceptions from logging
    try:
        authenticate_user("audit_user", h, "WRONG", user_id=99,
                          role="viewer", secret=TEST_SECRET)
    except InvalidCredentialsError:
        check("Audit Integration",
              "Failed login logs correctly (no logging exception on failure)",
              True)
    except Exception as e:
        check("Audit Integration",
              "Failed login logs correctly (no logging exception on failure)",
              False, str(e))

    # Unauthorised access — audit log on role rejection
    try:
        validate_request_token(viewer_token, required_role="admin",
                               resource="admin_panel", secret=TEST_SECRET)
    except UnauthorizedAccessError:
        check("Audit Integration",
              "UnauthorizedAccess is logged without exception from logger",
              True)
    except Exception as e:
        check("Audit Integration",
              "UnauthorizedAccess logging doesn't raise",
              False, str(e))

    # logout_user
    logout_resp = logout_user(valid, secret=TEST_SECRET)
    check("Audit Integration",
          "logout_user() returns success=True and logs without exception",
          logout_resp["success"] is True)


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
