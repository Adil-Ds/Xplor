# ─────────────────────────────────────────────────────────────────────────────
# tests/test_rbac.py
#
# Full test suite for the RBAC Authorization System.
#
# Covers:
#   Group 1  — RoleManager: load, role_exists, validate_role
#   Group 2  — RoleManager: get_permissions content
#   Group 3  — RoleManager: get_all_roles, get_all_permissions, descriptions
#   Group 4  — PermissionManager: has_permission (grants)
#   Group 5  — PermissionManager: has_permission (denials)
#   Group 6  — PermissionManager: admin full access
#   Group 7  — PermissionManager: analyst restrictions
#   Group 8  — PermissionManager: viewer restrictions
#   Group 9  — PermissionManager: batch checks
#   Group 10 — AuthorizationEngine: authorize_role (grants + denials + logging)
#   Group 11 — AuthorizationEngine: authorize_or_raise exceptions
#   Group 12 — AuthorizationEngine: InvalidRoleError propagation
#   Group 13 — AuthorizationEngine: protect_resource hierarchy
#   Group 14 — Guard factories: require_permission, require_role, protect_resource
#   Group 15 — JWT integration: extract_role_from_token, authorize_from_token
#   Group 16 — AuthorizationResult: bool, to_dict, fields
#   Group 17 — Exception hierarchy: type, code, attributes
#   Group 18 — Audit integration: no exceptions from logging
#
# Run:
#   cd security
#   python tests/test_rbac.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
import os
import io
from pathlib import Path

# Force UTF-8 output on Windows
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

# Set JWT secret before JWT imports
TEST_SECRET = "test_secret_key_minimum_32_chars_xxxx"
os.environ["JWT_SECRET_KEY"] = TEST_SECRET

from auth.rbac import RoleManager, get_role_manager
from auth.permission_manager import PermissionManager, get_permission_manager
from auth.authorization import (
    AuthorizationEngine, AuthorizationResult,
    authorize, authorize_or_raise, has_permission as authz_has_permission,
    authorize_from_token, require_permission, require_role, protect_resource,
)
from auth.authorization_exceptions import (
    AuthorizationError, PermissionDeniedError, InvalidRoleError, ResourceProtectedError,
)


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
    print("       RBAC AUTHORIZATION SYSTEM — FULL TEST SUITE")
    print("       roles | permissions | engine | JWT | guards | exceptions")
    print("=" * 68)

    rm     = RoleManager()
    pm     = PermissionManager(rm)
    engine = AuthorizationEngine(pm)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 1 — RoleManager: loading and role existence
    # ══════════════════════════════════════════════════════════════════════════

    check("RoleManager Loading",
          "RoleManager initializes without error",
          rm is not None)

    check("RoleManager Loading",
          "role_exists('admin') is True",
          rm.role_exists("admin") is True)

    check("RoleManager Loading",
          "role_exists('analyst') is True",
          rm.role_exists("analyst") is True)

    check("RoleManager Loading",
          "role_exists('viewer') is True",
          rm.role_exists("viewer") is True)

    check("RoleManager Loading",
          "role_exists('superadmin') is False",
          rm.role_exists("superadmin") is False)

    check("RoleManager Loading",
          "role_exists('') is False",
          rm.role_exists("") is False)

    check("RoleManager Loading",
          "role_exists(None) is False",
          rm.role_exists(None) is False)

    check("RoleManager Loading",
          "role_exists('ADMIN') is False (case-sensitive)",
          rm.role_exists("ADMIN") is False)

    # validate_role — success
    validated = rm.validate_role("admin")
    check("RoleManager Loading",
          "validate_role('admin') returns 'admin'",
          validated == "admin")

    # validate_role — failure
    try:
        rm.validate_role("hacker")
        check("RoleManager Loading", "validate_role('hacker') raises InvalidRoleError", False)
    except InvalidRoleError as e:
        check("RoleManager Loading", "validate_role('hacker') raises InvalidRoleError", True)
        check("RoleManager Loading",
              "InvalidRoleError contains valid_roles set",
              "admin" in e.valid_roles and "analyst" in e.valid_roles)

    try:
        rm.validate_role("")
        check("RoleManager Loading", "validate_role('') raises InvalidRoleError", False)
    except InvalidRoleError:
        check("RoleManager Loading", "validate_role('') raises InvalidRoleError", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 2 — RoleManager: permission content
    # ══════════════════════════════════════════════════════════════════════════

    admin_perms   = rm.get_permissions("admin")
    analyst_perms = rm.get_permissions("analyst")
    viewer_perms  = rm.get_permissions("viewer")

    check("Permissions Content",
          "admin has 'manage_users'",
          "manage_users" in admin_perms)

    check("Permissions Content",
          "admin has 'delete_dataset'",
          "delete_dataset" in admin_perms)

    check("Permissions Content",
          "admin has 'manage_roles'",
          "manage_roles" in admin_perms)

    check("Permissions Content",
          "admin has 'configure_system'",
          "configure_system" in admin_perms)

    check("Permissions Content",
          "admin has 'view_logs'",
          "view_logs" in admin_perms)

    check("Permissions Content",
          "analyst has 'upload_dataset'",
          "upload_dataset" in analyst_perms)

    check("Permissions Content",
          "analyst has 'analyze_data'",
          "analyze_data" in analyst_perms)

    check("Permissions Content",
          "analyst has 'export_reports'",
          "export_reports" in analyst_perms)

    check("Permissions Content",
          "analyst does NOT have 'manage_users'",
          "manage_users" not in analyst_perms)

    check("Permissions Content",
          "analyst does NOT have 'delete_dataset'",
          "delete_dataset" not in analyst_perms)

    check("Permissions Content",
          "analyst does NOT have 'manage_roles'",
          "manage_roles" not in analyst_perms)

    check("Permissions Content",
          "viewer has 'view_reports'",
          "view_reports" in viewer_perms)

    check("Permissions Content",
          "viewer has 'view_dashboards'",
          "view_dashboards" in viewer_perms)

    check("Permissions Content",
          "viewer does NOT have 'export_reports'",
          "export_reports" not in viewer_perms)

    check("Permissions Content",
          "viewer does NOT have 'upload_dataset'",
          "upload_dataset" not in viewer_perms)

    check("Permissions Content",
          "viewer does NOT have 'analyze_data'",
          "analyze_data" not in viewer_perms)

    check("Permissions Content",
          "viewer does NOT have 'manage_users'",
          "manage_users" not in viewer_perms)

    check("Permissions Content",
          "admin has more permissions than analyst",
          len(admin_perms) > len(analyst_perms))

    check("Permissions Content",
          "analyst has more permissions than viewer",
          len(analyst_perms) > len(viewer_perms))

    check("Permissions Content",
          "get_permissions returns frozenset",
          isinstance(admin_perms, frozenset))


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 3 — RoleManager: utility functions
    # ══════════════════════════════════════════════════════════════════════════

    all_roles = rm.get_all_roles()
    check("RoleManager Utilities",
          "get_all_roles() returns list",
          isinstance(all_roles, list))

    check("RoleManager Utilities",
          "get_all_roles() contains admin, analyst, viewer",
          set(all_roles) == {"admin", "analyst", "viewer"},
          f"got: {all_roles}")

    check("RoleManager Utilities",
          "get_all_roles() is sorted",
          all_roles == sorted(all_roles))

    all_perms = rm.get_all_permissions()
    check("RoleManager Utilities",
          "get_all_permissions() returns frozenset",
          isinstance(all_perms, frozenset))

    check("RoleManager Utilities",
          "get_all_permissions() includes 'manage_users'",
          "manage_users" in all_perms)

    check("RoleManager Utilities",
          "get_all_permissions() includes all 10 expected permissions",
          len(all_perms) >= 10,
          f"count={len(all_perms)}")

    check("RoleManager Utilities",
          "permission_exists('delete_dataset') is True",
          rm.permission_exists("delete_dataset") is True)

    check("RoleManager Utilities",
          "permission_exists('fly') is False",
          rm.permission_exists("fly") is False)

    check("RoleManager Utilities",
          "permission_exists('') is False",
          rm.permission_exists("") is False)

    desc = rm.get_permission_description("delete_dataset")
    check("RoleManager Utilities",
          "get_permission_description('delete_dataset') returns non-empty string",
          isinstance(desc, str) and len(desc) > 0,
          f"desc='{desc}'")

    summary = rm.get_role_summary("analyst")
    check("RoleManager Utilities",
          "get_role_summary returns dict with 'role' and 'permissions' keys",
          "role" in summary and "permissions" in summary)

    check("RoleManager Utilities",
          "get_role_summary('analyst') role field is 'analyst'",
          summary["role"] == "analyst")

    check("RoleManager Utilities",
          "get_role_summary permissions list is sorted",
          summary["permissions"] == sorted(summary["permissions"]))


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 4 — PermissionManager: has_permission — GRANTED cases
    # ══════════════════════════════════════════════════════════════════════════

    GRANT_CASES = [
        ("admin",   "manage_users"),
        ("admin",   "delete_dataset"),
        ("admin",   "configure_system"),
        ("admin",   "view_logs"),
        ("admin",   "manage_roles"),
        ("admin",   "upload_dataset"),
        ("admin",   "analyze_data"),
        ("admin",   "export_reports"),
        ("admin",   "view_reports"),
        ("admin",   "view_dashboards"),
        ("analyst", "upload_dataset"),
        ("analyst", "analyze_data"),
        ("analyst", "export_reports"),
        ("analyst", "view_reports"),
        ("analyst", "view_dashboards"),
        ("viewer",  "view_reports"),
        ("viewer",  "view_dashboards"),
    ]

    for role, perm in GRANT_CASES:
        check("has_permission (Grants)",
              f"{role:8s} → {perm}",
              pm.has_permission(role, perm) is True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 5 — PermissionManager: has_permission — DENIED cases
    # ══════════════════════════════════════════════════════════════════════════

    DENY_CASES = [
        ("viewer",  "manage_users",    "viewer cannot manage users"),
        ("viewer",  "upload_dataset",  "viewer cannot upload datasets"),
        ("viewer",  "delete_dataset",  "viewer cannot delete datasets"),
        ("viewer",  "analyze_data",    "viewer cannot run analysis"),
        ("viewer",  "export_reports",  "viewer cannot export reports"),
        ("viewer",  "view_logs",       "viewer cannot view logs"),
        ("viewer",  "manage_roles",    "viewer cannot manage roles"),
        ("viewer",  "configure_system","viewer cannot configure system"),
        ("analyst", "manage_users",    "analyst cannot manage users"),
        ("analyst", "delete_dataset",  "analyst cannot delete datasets"),
        ("analyst", "view_logs",       "analyst cannot view logs"),
        ("analyst", "manage_roles",    "analyst cannot manage roles"),
        ("analyst", "configure_system","analyst cannot configure system"),
    ]

    for role, perm, reason in DENY_CASES:
        check("has_permission (Denials)",
              f"{role:8s} ✗ {perm}  ({reason})",
              pm.has_permission(role, perm) is False)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 6 — Admin full access
    # ══════════════════════════════════════════════════════════════════════════

    all_platform_perms = rm.get_all_permissions()
    for perm in sorted(all_platform_perms):
        check("Admin Full Access",
              f"admin has '{perm}'",
              pm.has_permission("admin", perm) is True)

    check("Admin Full Access",
          f"admin has ALL {len(all_platform_perms)} platform permissions",
          all(pm.has_permission("admin", p) for p in all_platform_perms),
          f"total={len(all_platform_perms)}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 7 — Analyst restrictions
    # ══════════════════════════════════════════════════════════════════════════

    analyst_cannot = [
        "manage_users", "delete_dataset", "view_logs",
        "manage_roles", "configure_system",
    ]
    for perm in analyst_cannot:
        check("Analyst Restrictions",
              f"analyst CANNOT '{perm}'",
              pm.has_permission("analyst", perm) is False)

    analyst_can = ["upload_dataset", "analyze_data", "export_reports",
                   "view_reports", "view_dashboards"]
    for perm in analyst_can:
        check("Analyst Restrictions",
              f"analyst CAN '{perm}'",
              pm.has_permission("analyst", perm) is True)

    # Denied set
    denied = pm.get_denied_permissions("analyst")
    check("Analyst Restrictions",
          "get_denied_permissions('analyst') includes 'manage_users'",
          "manage_users" in denied)

    check("Analyst Restrictions",
          "get_denied_permissions('analyst') does NOT include 'analyze_data'",
          "analyze_data" not in denied)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 8 — Viewer restrictions
    # ══════════════════════════════════════════════════════════════════════════

    viewer_cannot = [
        "manage_users", "upload_dataset", "delete_dataset",
        "analyze_data", "export_reports", "view_logs",
        "manage_roles", "configure_system",
    ]
    for perm in viewer_cannot:
        check("Viewer Restrictions",
              f"viewer CANNOT '{perm}'",
              pm.has_permission("viewer", perm) is False)

    viewer_can = ["view_reports", "view_dashboards"]
    for perm in viewer_can:
        check("Viewer Restrictions",
              f"viewer CAN '{perm}'",
              pm.has_permission("viewer", perm) is True)

    viewer_denied = pm.get_denied_permissions("viewer")
    check("Viewer Restrictions",
          f"viewer denied {len(viewer_denied)} permissions",
          len(viewer_denied) >= 8,
          f"denied_count={len(viewer_denied)}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 9 — Batch checks
    # ══════════════════════════════════════════════════════════════════════════

    result = pm.check_permissions("analyst", ["analyze_data", "manage_users", "export_reports"])
    check("Batch Checks",
          "check_permissions returns dict",
          isinstance(result, dict))

    check("Batch Checks",
          "analyze_data → True for analyst",
          result["analyze_data"] is True)

    check("Batch Checks",
          "manage_users → False for analyst",
          result["manage_users"] is False)

    check("Batch Checks",
          "export_reports → True for analyst",
          result["export_reports"] is True)

    # has_any_permission
    check("Batch Checks",
          "has_any_permission: analyst has any of [view_logs, export_reports]",
          pm.has_any_permission("analyst", ["view_logs", "export_reports"]) is True)

    check("Batch Checks",
          "has_any_permission: viewer has NONE of [view_logs, manage_users]",
          pm.has_any_permission("viewer", ["view_logs", "manage_users"]) is False)

    # has_all_permissions
    check("Batch Checks",
          "has_all_permissions: analyst has all of [analyze_data, export_reports]",
          pm.has_all_permissions("analyst", ["analyze_data", "export_reports"]) is True)

    check("Batch Checks",
          "has_all_permissions: analyst does NOT have all of [analyze_data, manage_users]",
          pm.has_all_permissions("analyst", ["analyze_data", "manage_users"]) is False)

    # Permission matrix
    matrix = pm.get_permission_matrix()
    check("Batch Checks",
          "get_permission_matrix() contains 3 roles",
          set(matrix.keys()) == {"admin", "analyst", "viewer"})

    check("Batch Checks",
          "matrix['admin']['manage_users'] is True",
          matrix["admin"]["manage_users"] is True)

    check("Batch Checks",
          "matrix['viewer']['delete_dataset'] is False",
          matrix["viewer"]["delete_dataset"] is False)

    # Display list
    display = pm.get_role_permissions_for_display("analyst")
    check("Batch Checks",
          "get_role_permissions_for_display returns list of dicts",
          isinstance(display, list) and "permission" in display[0])

    check("Batch Checks",
          "Display list contains both granted and denied entries",
          any(d["granted"] for d in display) and any(not d["granted"] for d in display))


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 10 — AuthorizationEngine: authorize_role
    # ══════════════════════════════════════════════════════════════════════════

    # Granted
    r = engine.authorize_role("admin", "manage_users", username="admin_user")
    check("AuthorizationEngine.authorize_role",
          "admin → manage_users: granted=True",
          r.granted is True)

    check("AuthorizationEngine.authorize_role",
          "Result role field matches",
          r.role == "admin")

    check("AuthorizationEngine.authorize_role",
          "Result permission field matches",
          r.permission == "manage_users")

    check("AuthorizationEngine.authorize_role",
          "Result username field matches",
          r.username == "admin_user")

    # Denied
    r2 = engine.authorize_role("viewer", "delete_dataset", username="viewer_user")
    check("AuthorizationEngine.authorize_role",
          "viewer → delete_dataset: granted=False",
          r2.granted is False)

    check("AuthorizationEngine.authorize_role",
          "Denied result has non-empty reason",
          len(r2.reason) > 0,
          f"reason='{r2.reason[:50]}...'")

    check("AuthorizationEngine.authorize_role",
          "Denied result role is 'viewer'",
          r2.role == "viewer")

    # All three roles for view_reports
    for role in ["admin", "analyst", "viewer"]:
        r_view = engine.authorize_role(role, "view_reports", username=f"{role}_user")
        check("AuthorizationEngine.authorize_role",
              f"{role} → view_reports: granted",
              r_view.granted is True)

    # Only admin for manage_users
    r_admin = engine.authorize_role("admin", "manage_users")
    r_analyst = engine.authorize_role("analyst", "manage_users")
    r_viewer  = engine.authorize_role("viewer",  "manage_users")
    check("AuthorizationEngine.authorize_role",
          "Only admin can manage_users",
          r_admin.granted and not r_analyst.granted and not r_viewer.granted)

    # Module-level convenience
    r3 = authorize("analyst", "analyze_data", username="arslan")
    check("AuthorizationEngine.authorize_role",
          "Module-level authorize() works",
          r3.granted is True)

    check("AuthorizationEngine.authorize_role",
          "Module-level has_permission() works",
          authz_has_permission("admin", "configure_system") is True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 11 — authorize_or_raise exceptions
    # ══════════════════════════════════════════════════════════════════════════

    # Should raise
    for role, perm in [("viewer", "delete_dataset"), ("analyst", "manage_users"),
                       ("viewer", "configure_system"), ("analyst", "manage_roles")]:
        try:
            engine.authorize_or_raise(role, perm, username="user")
            check("authorize_or_raise", f"{role} ✗ {perm} raises PermissionDeniedError", False)
        except PermissionDeniedError:
            check("authorize_or_raise", f"{role} ✗ {perm} raises PermissionDeniedError", True)

    # Should NOT raise
    for role, perm in [("admin", "manage_users"), ("analyst", "analyze_data"),
                       ("viewer", "view_reports")]:
        try:
            r = engine.authorize_or_raise(role, perm, username="user")
            check("authorize_or_raise", f"{role} ✓ {perm} does NOT raise", r.granted is True)
        except PermissionDeniedError:
            check("authorize_or_raise", f"{role} ✓ {perm} does NOT raise", False)

    # Module-level
    try:
        authorize_or_raise("viewer", "upload_dataset")
        check("authorize_or_raise", "Module-level authorize_or_raise raises for viewer", False)
    except PermissionDeniedError:
        check("authorize_or_raise", "Module-level authorize_or_raise raises for viewer", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 12 — InvalidRoleError propagation
    # ══════════════════════════════════════════════════════════════════════════

    for bad_role in ["superadmin", "god", "root", "", "ADMIN", "Analyst", "123"]:
        try:
            engine.authorize_role(bad_role, "view_reports")
            check("InvalidRoleError", f"'{bad_role}' raises InvalidRoleError", False)
        except InvalidRoleError as e:
            check("InvalidRoleError", f"'{bad_role}' raises InvalidRoleError", True)
            check("InvalidRoleError",
                  f"  InvalidRoleError.code is 'invalid_role'",
                  e.code == "invalid_role")

    # PermissionManager propagates too
    try:
        pm.has_permission("wizard", "view_reports")
        check("InvalidRoleError", "PermissionManager propagates InvalidRoleError", False)
    except InvalidRoleError:
        check("InvalidRoleError", "PermissionManager propagates InvalidRoleError", True)

    # Unknown permission returns False (not an error)
    check("InvalidRoleError",
          "Unknown permission returns False (not error)",
          pm.has_permission("admin", "nonexistent_permission") is False)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 13 — protect_resource hierarchy
    # ══════════════════════════════════════════════════════════════════════════

    # admin can access admin resource
    r = engine.protect_resource("admin_panel", "admin", "admin", username="superuser")
    check("protect_resource",
          "admin accesses admin_panel → granted",
          r.granted is True)

    # admin can access analyst resource (higher level)
    r2 = engine.protect_resource("dashboard", "analyst", "admin", username="superuser")
    check("protect_resource",
          "admin accesses analyst-level resource → granted",
          r2.granted is True)

    # analyst can access analyst resource
    r3 = engine.protect_resource("dashboard", "analyst", "analyst", username="arslan")
    check("protect_resource",
          "analyst accesses analyst-level resource → granted",
          r3.granted is True)

    # analyst CANNOT access admin resource
    try:
        engine.protect_resource("admin_panel", "admin", "analyst", username="arslan")
        check("protect_resource", "analyst blocked from admin_panel", False)
    except ResourceProtectedError as e:
        check("protect_resource", "analyst blocked from admin_panel → ResourceProtectedError", True)
        check("protect_resource",
              "ResourceProtectedError.required_role is 'admin'",
              e.required_role == "admin")
        check("protect_resource",
              "ResourceProtectedError.resource is 'admin_panel'",
              e.resource == "admin_panel")

    # viewer CANNOT access analyst or admin resources
    for req in ["analyst", "admin"]:
        try:
            engine.protect_resource(f"{req}_resource", req, "viewer", username="viewer_user")
            check("protect_resource", f"viewer blocked from {req}_resource", False)
        except ResourceProtectedError:
            check("protect_resource", f"viewer blocked from {req}_resource", True)

    # viewer CAN access viewer resource
    r_v = engine.protect_resource("public_dashboard", "viewer", "viewer", username="viewer_user")
    check("protect_resource",
          "viewer accesses viewer-level resource → granted",
          r_v.granted is True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 14 — Guard factories
    # ══════════════════════════════════════════════════════════════════════════

    # require_permission
    export_guard = require_permission("export_reports")

    for role in ["admin", "analyst"]:
        r = export_guard(role, username=f"{role}_user")
        check("Guard Factories",
              f"require_permission('export_reports'): {role} passes",
              r.granted is True)

    try:
        export_guard("viewer", username="viewer_user")
        check("Guard Factories", "require_permission('export_reports'): viewer blocked", False)
    except PermissionDeniedError:
        check("Guard Factories", "require_permission('export_reports'): viewer blocked", True)

    # require_role
    admin_guard = require_role("admin", resource="admin_panel")

    r_admin_ok = admin_guard("admin", username="superuser")
    check("Guard Factories",
          "require_role('admin'): admin passes",
          r_admin_ok.granted is True)

    for blocked_role in ["analyst", "viewer"]:
        try:
            admin_guard(blocked_role, username="user")
            check("Guard Factories", f"require_role('admin'): {blocked_role} blocked", False)
        except ResourceProtectedError:
            check("Guard Factories", f"require_role('admin'): {blocked_role} blocked", True)

    # require_role analyst level
    analyst_guard = require_role("analyst", resource="analytics")
    analyst_guard("admin", username="superuser")   # admin passes
    analyst_guard("analyst", username="arslan")     # analyst passes
    check("Guard Factories",
          "require_role('analyst'): admin and analyst pass",
          True)

    try:
        analyst_guard("viewer", username="viewer_user")
        check("Guard Factories", "require_role('analyst'): viewer blocked", False)
    except ResourceProtectedError:
        check("Guard Factories", "require_role('analyst'): viewer blocked", True)

    # protect_resource factory
    dataset_guard = protect_resource("datasets_endpoint", "upload_dataset")

    for role in ["admin", "analyst"]:
        r = dataset_guard(role, username=f"{role}_user")
        check("Guard Factories",
              f"protect_resource('upload_dataset'): {role} passes",
              r.granted is True)

    try:
        dataset_guard("viewer", username="viewer_user")
        check("Guard Factories", "protect_resource('upload_dataset'): viewer blocked", False)
    except PermissionDeniedError:
        check("Guard Factories", "protect_resource('upload_dataset'): viewer blocked", True)


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 15 — JWT integration
    # ══════════════════════════════════════════════════════════════════════════

    from auth.jwt_handler import create_access_token

    analyst_token = create_access_token(
        {"user_id": 42, "username": "arslan", "role": "analyst"},
        expires_minutes=30, secret=TEST_SECRET
    )
    admin_token = create_access_token(
        {"user_id": 1, "username": "admin_user", "role": "admin"},
        expires_minutes=30, secret=TEST_SECRET
    )
    viewer_token = create_access_token(
        {"user_id": 3, "username": "viewer_user", "role": "viewer"},
        expires_minutes=30, secret=TEST_SECRET
    )

    # extract_role_from_token
    role, username, user_id = engine.extract_role_from_token(analyst_token, secret=TEST_SECRET)
    check("JWT Integration",
          "extract_role_from_token: role='analyst'",
          role == "analyst")

    check("JWT Integration",
          "extract_role_from_token: username='arslan'",
          username == "arslan")

    check("JWT Integration",
          "extract_role_from_token: user_id=42",
          user_id == 42)

    # authorize_from_token — granted
    r = engine.authorize_from_token(analyst_token, "analyze_data",
                                    resource="dataset_1", secret=TEST_SECRET)
    check("JWT Integration",
          "authorize_from_token: analyst token → analyze_data: granted",
          r.granted is True)

    check("JWT Integration",
          "Result has correct username",
          r.username == "arslan")

    check("JWT Integration",
          "Result has correct role",
          r.role == "analyst")

    check("JWT Integration",
          "Result has correct user_id",
          r.user_id == 42)

    # authorize_from_token — denied
    r2 = engine.authorize_from_token(analyst_token, "manage_users",
                                     resource="user_mgmt", secret=TEST_SECRET)
    check("JWT Integration",
          "authorize_from_token: analyst token → manage_users: denied",
          r2.granted is False)

    # Admin full access via token
    r3 = engine.authorize_from_token(admin_token, "manage_users", secret=TEST_SECRET)
    check("JWT Integration",
          "authorize_from_token: admin token → manage_users: granted",
          r3.granted is True)

    # Viewer limited access via token
    for perm in ["view_reports", "view_dashboards"]:
        r4 = engine.authorize_from_token(viewer_token, perm, secret=TEST_SECRET)
        check("JWT Integration",
              f"authorize_from_token: viewer token → {perm}: granted",
              r4.granted is True)

    for perm in ["delete_dataset", "export_reports", "manage_users"]:
        r5 = engine.authorize_from_token(viewer_token, perm, secret=TEST_SECRET)
        check("JWT Integration",
              f"authorize_from_token: viewer token → {perm}: denied",
              r5.granted is False)

    # Module-level authorize_from_token
    r6 = authorize_from_token(admin_token, "configure_system", secret=TEST_SECRET)
    check("JWT Integration",
          "Module-level authorize_from_token: admin → configure_system: granted",
          r6.granted is True)

    # authorize_from_token_or_raise
    try:
        engine.authorize_from_token_or_raise(viewer_token, "delete_dataset", secret=TEST_SECRET)
        check("JWT Integration", "authorize_from_token_or_raise raises for viewer", False)
    except PermissionDeniedError:
        check("JWT Integration", "authorize_from_token_or_raise raises for viewer", True)

    # Invalid role in JWT (manually craft a token with bad role)
    import jwt as _jwt_lib
    from datetime import datetime, timezone, timedelta
    bad_role_payload = {
        "user_id": 99, "username": "hacker", "role": "godmode",
        "iat": int(datetime.now(timezone.utc).timestamp()),
        "exp": int((datetime.now(timezone.utc) + timedelta(minutes=30)).timestamp()),
    }
    bad_role_token = _jwt_lib.encode(bad_role_payload, TEST_SECRET, algorithm="HS256")
    try:
        engine.extract_role_from_token(bad_role_token, secret=TEST_SECRET)
        check("JWT Integration", "Invalid role in token raises InvalidRoleError", False)
    except Exception as e:
        check("JWT Integration",
              "Invalid role in token raises InvalidTokenError or InvalidRoleError",
              True, f"got: {type(e).__name__}")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 16 — AuthorizationResult
    # ══════════════════════════════════════════════════════════════════════════

    r_ok  = AuthorizationResult(granted=True,  role="admin",  permission="manage_users",
                                 username="superuser", user_id=1)
    r_bad = AuthorizationResult(granted=False, role="viewer", permission="delete_dataset",
                                 username="bob",  reason="Permission denied", user_id=3)

    check("AuthorizationResult",
          "bool(AuthorizationResult(granted=True)) is True",
          bool(r_ok) is True)

    check("AuthorizationResult",
          "bool(AuthorizationResult(granted=False)) is False",
          bool(r_bad) is False)

    check("AuthorizationResult",
          "'if result:' works as shorthand for 'if result.granted:'",
          (True if r_ok else False) is True)

    d = r_ok.to_dict()
    check("AuthorizationResult",
          "to_dict() returns dict with 'granted', 'role', 'permission', 'username'",
          all(k in d for k in ["granted", "role", "permission", "username", "user_id"]))

    check("AuthorizationResult",
          "to_dict() granted value matches",
          d["granted"] is True)

    check("AuthorizationResult",
          "Denied result has non-empty reason",
          len(r_bad.reason) > 0)

    check("AuthorizationResult",
          "Granted result has empty reason by default",
          r_ok.reason == "")


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 17 — Exception hierarchy
    # ══════════════════════════════════════════════════════════════════════════

    pde = PermissionDeniedError(role="viewer", action="delete_dataset", resource="dataset_1")
    check("Exception Hierarchy",
          "PermissionDeniedError is subclass of AuthorizationError",
          isinstance(pde, AuthorizationError))

    check("Exception Hierarchy",
          "PermissionDeniedError.code is 'permission_denied'",
          pde.code == "permission_denied")

    check("Exception Hierarchy",
          "PermissionDeniedError.role is 'viewer'",
          pde.role == "viewer")

    check("Exception Hierarchy",
          "PermissionDeniedError.action is 'delete_dataset'",
          pde.action == "delete_dataset")

    check("Exception Hierarchy",
          "PermissionDeniedError.resource is 'dataset_1'",
          pde.resource == "dataset_1")

    ire = InvalidRoleError(role="godmode", valid_roles={"admin", "analyst", "viewer"})
    check("Exception Hierarchy",
          "InvalidRoleError is subclass of AuthorizationError",
          isinstance(ire, AuthorizationError))

    check("Exception Hierarchy",
          "InvalidRoleError.code is 'invalid_role'",
          ire.code == "invalid_role")

    check("Exception Hierarchy",
          "InvalidRoleError.valid_roles contains 'admin'",
          "admin" in ire.valid_roles)

    rpe = ResourceProtectedError(resource="admin_panel", role="analyst", required_role="admin")
    check("Exception Hierarchy",
          "ResourceProtectedError is subclass of AuthorizationError",
          isinstance(rpe, AuthorizationError))

    check("Exception Hierarchy",
          "ResourceProtectedError.code is 'resource_protected'",
          rpe.code == "resource_protected")

    check("Exception Hierarchy",
          "ResourceProtectedError.resource is 'admin_panel'",
          rpe.resource == "admin_panel")

    check("Exception Hierarchy",
          "ResourceProtectedError.required_role is 'admin'",
          rpe.required_role == "admin")

    # All are catchable as AuthorizationError
    for exc in [pde, ire, rpe]:
        check("Exception Hierarchy",
              f"{type(exc).__name__} is catchable as AuthorizationError",
              isinstance(exc, AuthorizationError))

    # str() representation
    check("Exception Hierarchy",
          "str(PermissionDeniedError) contains code",
          "[permission_denied]" in str(pde))


    # ══════════════════════════════════════════════════════════════════════════
    # GROUP 18 — Audit integration
    # ══════════════════════════════════════════════════════════════════════════

    # All these should complete without any exception from the audit logger

    try:
        r = engine.authorize_role("analyst", "analyze_data", username="audit_test_user")
        check("Audit Integration",
              "Granted event logged without exception",
              r.granted is True)
    except Exception as e:
        check("Audit Integration", "Granted event logged without exception", False, str(e))

    try:
        r = engine.authorize_role("viewer", "delete_dataset", username="audit_test_viewer")
        check("Audit Integration",
              "Denied event logged without exception",
              r.granted is False)
    except Exception as e:
        check("Audit Integration", "Denied event logged without exception", False, str(e))

    try:
        engine.authorize_or_raise("viewer", "manage_users", username="audit_test_raise")
    except PermissionDeniedError:
        check("Audit Integration",
              "PermissionDeniedError raised + logged without logger exception",
              True)
    except Exception as e:
        check("Audit Integration",
              "PermissionDeniedError raised + logged without logger exception",
              False, str(e))

    try:
        engine.protect_resource("admin_panel", "admin", "analyst", username="audit_protect")
    except ResourceProtectedError:
        check("Audit Integration",
              "ResourceProtectedError raised + logged without logger exception",
              True)
    except Exception as e:
        check("Audit Integration",
              "ResourceProtectedError raised + logged without logger exception",
              False, str(e))


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
