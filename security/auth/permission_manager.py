# ─────────────────────────────────────────────────────────────────────────────
# auth/permission_manager.py
#
# Permission Manager — Centralized Permission Validation Layer
#
# WHY A SEPARATE PERMISSION MANAGER?
#   RoleManager answers: "What permissions does a role have?"
#   PermissionManager answers: "Does THIS user/role have THIS permission?"
#
#   The separation allows:
#     - RoleManager  → data layer  (loads/caches roles.json)
#     - PermissionManager → logic layer (checks, validates, logs)
#     - Authorization → policy layer  (combines check + response)
#
# PERMISSION CHECK FLOW:
#   has_permission(role, permission)
#         │
#         ├── 1. Validate role exists (via RoleManager)
#         ├── 2. Validate permission is a known platform permission
#         ├── 3. Check if role's frozenset contains the permission
#         └── 4. Return True / False
#
# Public API:
#   has_permission(role, permission) → bool
#   get_permissions(role) → frozenset
#   get_role_permissions_for_display(role) → list[dict]
#   check_permissions(role, permissions) → dict[str, bool]
#   get_denied_permissions(role) → frozenset
#
# Used by:
#   auth/authorization.py  — calls has_permission() for every access check
#   tests/test_rbac.py
# ─────────────────────────────────────────────────────────────────────────────

import sys
from pathlib import Path
from typing import Iterable, List

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.rbac import get_role_manager, RoleManager
from auth.authorization_exceptions import InvalidRoleError


# ══════════════════════════════════════════════════════════════════════════════
# PERMISSION MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class PermissionManager:
    """
    Centralized permission validation layer.

    Wraps RoleManager to provide higher-level permission checking methods.
    All permission decisions flow through this class — never directly
    through RoleManager from authorization code.

    Responsibilities:
        - Check whether a role has a specific permission
        - Batch-check multiple permissions at once
        - Return denied permissions for a role
        - Provide display-friendly permission data

    The PermissionManager itself does NOT raise exceptions for denied
    permissions — it returns True/False. The Authorization layer
    (authorization.py) raises exceptions when needed.

    Attributes
    ----------
    _role_manager : RoleManager — the underlying data source

    Example
    -------
    >>> pm = PermissionManager()
    >>> pm.has_permission("analyst", "analyze_data")
    True
    >>> pm.has_permission("viewer", "delete_dataset")
    False
    """

    def __init__(self, role_manager: RoleManager = None):
        """
        Initialize with an optional custom RoleManager.

        Parameters
        ----------
        role_manager : RoleManager, optional
                       Uses the global singleton if not provided.
        """
        self._rm = role_manager or get_role_manager()

    # ── Primary Check ─────────────────────────────────────────────────────────

    def has_permission(self, role: str, permission: str) -> bool:
        """
        Check whether a role has a specific permission.

        This is the PRIMARY function for permission decisions.
        Returns True if the role has the permission, False otherwise.
        Never raises for denied permissions — only raises for invalid roles.

        Parameters
        ----------
        role       : str — the user's role (e.g. "analyst")
        permission : str — the permission to check (e.g. "delete_dataset")

        Returns
        -------
        bool — True if the role has the permission, False otherwise

        Raises
        ------
        InvalidRoleError — if the role is not a defined platform role

        Example
        -------
        >>> pm.has_permission("admin", "manage_users")
        True
        >>> pm.has_permission("viewer", "delete_dataset")
        False
        >>> pm.has_permission("analyst", "analyze_data")
        True

        Security note:
            We still validate the role even when the permission is unknown.
            This prevents attackers from probing the system by using invented
            permission strings (the role error fires first, giving no info
            about which permissions exist).
        """
        # Step 1: Validate role (raises InvalidRoleError if bad)
        self._rm.validate_role(role)

        # Step 2: Unknown permission strings always return False
        # (not an error — the caller may be checking an old/renamed permission)
        if not self._rm.permission_exists(permission):
            return False

        # Step 3: Check membership in the role's frozenset (O(1) hash lookup)
        return permission in self._rm.get_permissions(role)

    def has_any_permission(self, role: str, permissions: Iterable[str]) -> bool:
        """
        Check whether a role has ANY of the listed permissions.

        Useful for "OR" conditions: allow if the user can do at least one
        of the listed things (e.g. "can view OR can export").

        Parameters
        ----------
        role        : str — the user's role
        permissions : iterable[str] — permissions to check

        Returns
        -------
        bool — True if the role has at least one of the permissions

        Raises
        ------
        InvalidRoleError — if the role is not valid

        Example
        -------
        >>> pm.has_any_permission("analyst", ["view_logs", "export_reports"])
        True   # analyst has export_reports
        """
        return any(self.has_permission(role, p) for p in permissions)

    def has_all_permissions(self, role: str, permissions: Iterable[str]) -> bool:
        """
        Check whether a role has ALL of the listed permissions.

        Useful for "AND" conditions: allow only if the user can do all
        the listed things (e.g. "must be able to analyze AND export").

        Parameters
        ----------
        role        : str — the user's role
        permissions : iterable[str] — all permissions required

        Returns
        -------
        bool — True if the role has every listed permission

        Raises
        ------
        InvalidRoleError — if the role is not valid

        Example
        -------
        >>> pm.has_all_permissions("analyst", ["analyze_data", "export_reports"])
        True
        >>> pm.has_all_permissions("viewer", ["view_reports", "export_reports"])
        False  # viewer lacks export_reports
        """
        return all(self.has_permission(role, p) for p in permissions)

    # ── Bulk Queries ──────────────────────────────────────────────────────────

    def get_permissions(self, role: str) -> frozenset:
        """
        Return the frozenset of permissions for a role.

        Delegates to RoleManager. Raises InvalidRoleError for bad roles.

        Parameters
        ----------
        role : str — the role name

        Returns
        -------
        frozenset[str] — the role's permissions

        Example
        -------
        >>> pm.get_permissions("analyst")
        frozenset({'upload_dataset', 'analyze_data', 'export_reports', ...})
        """
        return self._rm.get_permissions(role)

    def check_permissions(self, role: str, permissions: Iterable[str]) -> dict:
        """
        Batch-check a list of permissions for a role.

        Returns a dict mapping each permission to True/False.
        Useful for building "what can this user do?" summaries.

        Parameters
        ----------
        role        : str — the role name
        permissions : iterable[str] — permissions to evaluate

        Returns
        -------
        dict[str, bool] — {permission: True/False}

        Raises
        ------
        InvalidRoleError — if the role is not valid

        Example
        -------
        >>> pm.check_permissions("analyst", ["analyze_data", "manage_users", "export_reports"])
        {"analyze_data": True, "manage_users": False, "export_reports": True}
        """
        return {p: self.has_permission(role, p) for p in permissions}

    def get_denied_permissions(self, role: str) -> frozenset:
        """
        Return all platform permissions that this role does NOT have.

        Useful for admin UIs showing what a role is blocked from,
        and for audit reports.

        Parameters
        ----------
        role : str — the role name

        Returns
        -------
        frozenset[str] — permissions NOT granted to this role

        Raises
        ------
        InvalidRoleError — if the role is not valid

        Example
        -------
        >>> pm.get_denied_permissions("viewer")
        frozenset({'manage_users', 'upload_dataset', 'delete_dataset', ...})
        """
        self._rm.validate_role(role)
        role_perms = self._rm.get_permissions(role)
        all_perms  = self._rm.get_all_permissions()
        return all_perms - role_perms

    def get_role_permissions_for_display(self, role: str) -> List[dict]:
        """
        Return a display-friendly list of all permissions with granted/denied status.

        Useful for admin UIs, documentation generation, and permission matrices.

        Parameters
        ----------
        role : str — the role name

        Returns
        -------
        list[dict] — sorted list of:
            {
                "permission" : str,
                "granted"    : bool,
                "description": str
            }

        Raises
        ------
        InvalidRoleError — if the role is not valid

        Example
        -------
        >>> pm.get_role_permissions_for_display("analyst")
        [
            {"permission": "analyze_data",   "granted": True,  "description": "..."},
            {"permission": "configure_system","granted": False, "description": "..."},
            ...
        ]
        """
        self._rm.validate_role(role)
        role_perms = self._rm.get_permissions(role)
        all_perms  = sorted(self._rm.get_all_permissions())

        return [
            {
                "permission" : p,
                "granted"    : p in role_perms,
                "description": self._rm.get_permission_description(p),
            }
            for p in all_perms
        ]

    def get_permission_matrix(self) -> dict:
        """
        Return the full permission matrix for all roles.

        Returns a nested dict: {role → {permission → bool}}.
        Useful for generating the permission_matrix.md documentation.

        Returns
        -------
        dict[str, dict[str, bool]] — full matrix

        Example
        -------
        >>> matrix = pm.get_permission_matrix()
        >>> matrix["admin"]["manage_users"]
        True
        >>> matrix["viewer"]["delete_dataset"]
        False
        """
        all_perms = sorted(self._rm.get_all_permissions())
        all_roles = self._rm.get_all_roles()
        return {
            role: {p: p in self._rm.get_permissions(role) for p in all_perms}
            for role in all_roles
        }

    def __repr__(self) -> str:
        roles = self._rm.get_all_roles()
        return f"PermissionManager(roles={roles})"


# ══════════════════════════════════════════════════════════════════════════════
# MODULE-LEVEL SINGLETON
# ══════════════════════════════════════════════════════════════════════════════

_pm_instance: PermissionManager = None


def get_permission_manager() -> PermissionManager:
    """
    Return the module-level singleton PermissionManager.

    Creates a new instance on first call, reuses it on subsequent calls.

    Returns
    -------
    PermissionManager — the shared instance

    Example
    -------
    >>> pm = get_permission_manager()
    >>> pm.has_permission("analyst", "analyze_data")
    True
    """
    global _pm_instance
    if _pm_instance is None:
        _pm_instance = PermissionManager()
    return _pm_instance


# ── Convenience module-level functions ────────────────────────────────────────
# These let callers use: from auth.permission_manager import has_permission
# without needing to instantiate PermissionManager explicitly.

def has_permission(role: str, permission: str) -> bool:
    """Module-level convenience: get_permission_manager().has_permission(role, permission)."""
    return get_permission_manager().has_permission(role, permission)


def get_permissions(role: str) -> frozenset:
    """Module-level convenience: get_permission_manager().get_permissions(role)."""
    return get_permission_manager().get_permissions(role)


def check_permissions(role: str, permissions: Iterable[str]) -> dict:
    """Module-level convenience: get_permission_manager().check_permissions(role, permissions)."""
    return get_permission_manager().check_permissions(role, permissions)


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  PERMISSION MANAGER — SELF TEST")
    print("=" * 60)

    pm = PermissionManager()

    # Print permission matrix
    matrix = pm.get_permission_matrix()
    all_perms = sorted(list(list(matrix.values())[0].keys()))
    roles     = sorted(matrix.keys())

    header = f"  {'Permission':<25}" + "".join(f" {r:^10}" for r in roles)
    print(f"\n{header}")
    print("  " + "─" * (25 + 11 * len(roles)))
    for p in all_perms:
        row = f"  {p:<25}"
        for r in roles:
            val = "✅" if matrix[r][p] else "❌"
            row += f" {val:^10}"
        print(row)

    # Core checks
    assert pm.has_permission("admin",   "manage_users")    is True
    assert pm.has_permission("analyst", "analyze_data")    is True
    assert pm.has_permission("viewer",  "view_reports")    is True
    assert pm.has_permission("viewer",  "delete_dataset")  is False
    assert pm.has_permission("analyst", "manage_users")    is False

    print(f"\n  Core assertions passed  ✅")

    # Denied permissions
    viewer_denied = pm.get_denied_permissions("viewer")
    assert "delete_dataset" in viewer_denied
    assert "manage_users"   in viewer_denied
    print(f"  viewer denied {len(viewer_denied)} permissions  ✅")

    print("=" * 60 + "\n")
