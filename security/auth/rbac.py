# ─────────────────────────────────────────────────────────────────────────────
# auth/rbac.py
#
# Role Manager — Core RBAC Engine
#
# WHAT IS RBAC?
#   Role-Based Access Control assigns permissions to ROLES, not to individual
#   users. Users are assigned a role (e.g. "analyst"). The role determines
#   what they can do. This is simpler and more maintainable than per-user
#   permissions because:
#     - New user gets a role → inherits all permissions automatically
#     - Changing a role's permissions affects ALL users with that role at once
#     - Audit logs are easier to interpret (role names instead of permission lists)
#
# ARCHITECTURE:
#   configs/roles.json  ← single source of truth (permissions defined here)
#         │
#         ▼
#     RoleManager         ← loads and caches the role→permissions mapping
#         │
#         ├── get_permissions(role) → list of permission strings
#         ├── role_exists(role) → bool
#         ├── validate_role(role) → str (raises InvalidRoleError if invalid)
#         └── get_all_roles() → list
#
# LEAST PRIVILEGE PRINCIPLE:
#   Every role has the MINIMUM permissions it needs to do its job.
#   Viewer: view only.
#   Analyst: view + analyze + upload + export.
#   Admin: everything.
#
#   This means if an analyst account is compromised, the attacker cannot
#   delete datasets or manage users — the damage is bounded by the role.
#
# Public API:
#   RoleManager (class)  — load/query the role→permission mapping
#   get_role_manager()   — module-level singleton accessor
#
# Used by:
#   auth/permission_manager.py — uses RoleManager to check permissions
#   auth/authorization.py      — calls permission_manager
#   tests/test_rbac.py
# ─────────────────────────────────────────────────────────────────────────────

import json
import sys
from pathlib import Path
from typing import List, Optional

# ── Path setup ────────────────────────────────────────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))

from auth.authorization_exceptions import InvalidRoleError

# ── Default roles path ────────────────────────────────────────────────────────

_DEFAULT_ROLES_PATH = Path(__file__).parent.parent / "configs" / "roles.json"


# ══════════════════════════════════════════════════════════════════════════════
# ROLE MANAGER
# ══════════════════════════════════════════════════════════════════════════════

class RoleManager:
    """
    Loads and manages the role → permissions mapping from configs/roles.json.

    This is the single source of truth for all role and permission data.
    No permissions are hardcoded anywhere in the codebase — they all
    come from roles.json via this class.

    Design decisions:
        - Loads once at construction time and caches in memory
        - Provides a `reload()` method for runtime config updates
        - All permission lists are stored as frozensets for O(1) lookup
        - Invalid roles raise InvalidRoleError, never return empty/None silently

    Attributes
    ----------
    _roles_path   : Path — location of roles.json
    _role_map     : dict[str, frozenset] — role → frozenset of permission strings
    _all_perms    : frozenset — all known permission strings across all roles
    _descriptions : dict[str, str] — permission → human-readable description

    Example
    -------
    >>> rm = RoleManager()
    >>> rm.get_permissions("analyst")
    frozenset({'upload_dataset', 'analyze_data', 'export_reports', ...})
    >>> rm.role_exists("superadmin")
    False
    """

    def __init__(self, roles_path: Optional[Path] = None):
        """
        Load the role definitions from roles.json.

        Parameters
        ----------
        roles_path : Path, optional — override the default config path
                     (default: security/configs/roles.json)

        Raises
        ------
        FileNotFoundError — if roles.json does not exist
        ValueError        — if roles.json is malformed
        """
        self._roles_path = Path(roles_path) if roles_path else _DEFAULT_ROLES_PATH
        self._role_map     : dict = {}
        self._all_perms    : frozenset = frozenset()
        self._descriptions : dict = {}
        self._load()

    # ── Loading ───────────────────────────────────────────────────────────────

    def _load(self) -> None:
        """
        Parse roles.json and populate the internal permission maps.

        Called automatically at __init__. Can be called again via reload()
        to pick up config changes without restarting the application.

        Raises
        ------
        FileNotFoundError — if roles.json cannot be found
        ValueError        — if JSON structure is unexpected
        """
        if not self._roles_path.exists():
            raise FileNotFoundError(
                f"roles.json not found at: {self._roles_path}\n"
                "Create it by copying configs/roles.json from the template."
            )

        try:
            with self._roles_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"roles.json contains invalid JSON: {exc}\n"
                f"File: {self._roles_path}"
            ) from exc

        if "roles" not in data:
            raise ValueError(
                "roles.json must contain a top-level 'roles' key. "
                f"Got keys: {list(data.keys())}"
            )

        # Build role → frozenset(permissions) map
        raw_roles = data["roles"]
        self._role_map = {}
        for role_name, role_data in raw_roles.items():
            if isinstance(role_data, dict):
                # Format: {"_description": "...", "permissions": [...]}
                perms = role_data.get("permissions", [])
            elif isinstance(role_data, list):
                # Compact format: {"admin": [...permissions...]}
                perms = role_data
            else:
                raise ValueError(
                    f"Unexpected format for role '{role_name}' in roles.json. "
                    "Expected a list or dict with 'permissions' key."
                )
            self._role_map[role_name] = frozenset(perms)

        # Build all_permissions set
        if "all_permissions" in data:
            self._all_perms = frozenset(data["all_permissions"])
        else:
            # Derive from union of all role permissions
            self._all_perms = frozenset(
                p for perms in self._role_map.values() for p in perms
            )

        # Permission descriptions (optional)
        self._descriptions = data.get("_permission_descriptions", {})

    def reload(self) -> None:
        """
        Reload role definitions from disk without restarting.

        Use this when roles.json has been updated at runtime.

        Example
        -------
        >>> role_manager.reload()
        >>> role_manager.get_permissions("analyst")  # now reflects new file
        """
        self._load()

    # ── Role Queries ──────────────────────────────────────────────────────────

    def role_exists(self, role: str) -> bool:
        """
        Check whether a role name is defined in the platform.

        Parameters
        ----------
        role : str — the role name to check (e.g. "admin", "analyst", "viewer")

        Returns
        -------
        bool — True if the role exists in roles.json, False otherwise

        Example
        -------
        >>> rm.role_exists("analyst")
        True
        >>> rm.role_exists("superadmin")
        False
        """
        return isinstance(role, str) and role in self._role_map

    def validate_role(self, role: str) -> str:
        """
        Assert that a role exists and return it — raises if invalid.

        Use this when you need the role string to be valid before
        proceeding with authorization logic.

        Parameters
        ----------
        role : str — the role name to validate

        Returns
        -------
        str — the validated role name (same value as input)

        Raises
        ------
        InvalidRoleError — if the role is not in roles.json

        Example
        -------
        >>> rm.validate_role("analyst")
        'analyst'
        >>> rm.validate_role("hacker")
        # raises InvalidRoleError("Role 'hacker' is not a recognized platform role...")
        """
        if not self.role_exists(role):
            raise InvalidRoleError(
                role=str(role) if role else "",
                valid_roles=set(self._role_map.keys()),
            )
        return role

    def get_permissions(self, role: str) -> frozenset:
        """
        Return the set of permissions for a given role.

        Parameters
        ----------
        role : str — the role name (must be a valid role)

        Returns
        -------
        frozenset[str] — set of permission strings the role has

        Raises
        ------
        InvalidRoleError — if the role is not in roles.json

        Example
        -------
        >>> rm.get_permissions("viewer")
        frozenset({'view_reports', 'view_dashboards'})
        >>> rm.get_permissions("admin")
        frozenset({'manage_users', 'upload_dataset', 'delete_dataset', ...})
        """
        self.validate_role(role)
        return self._role_map[role]

    def get_all_roles(self) -> List[str]:
        """
        Return a sorted list of all defined role names.

        Returns
        -------
        list[str] — sorted list: ["admin", "analyst", "viewer"]

        Example
        -------
        >>> rm.get_all_roles()
        ['admin', 'analyst', 'viewer']
        """
        return sorted(self._role_map.keys())

    def get_all_permissions(self) -> frozenset:
        """
        Return the complete set of all permission strings in the platform.

        Useful for validating that a permission string is a known one
        before checking whether a role has it.

        Returns
        -------
        frozenset[str] — all permissions across all roles

        Example
        -------
        >>> rm.get_all_permissions()
        frozenset({'manage_users', 'upload_dataset', 'delete_dataset', ...})
        """
        return self._all_perms

    def permission_exists(self, permission: str) -> bool:
        """
        Check whether a permission string is a known platform permission.

        Parameters
        ----------
        permission : str — the permission name to check

        Returns
        -------
        bool — True if the permission is in the all_permissions list

        Example
        -------
        >>> rm.permission_exists("delete_dataset")
        True
        >>> rm.permission_exists("fly")
        False
        """
        return isinstance(permission, str) and permission in self._all_perms

    def get_permission_description(self, permission: str) -> str:
        """
        Return the human-readable description for a permission.

        Parameters
        ----------
        permission : str — the permission name

        Returns
        -------
        str — description string, or empty string if not found

        Example
        -------
        >>> rm.get_permission_description("delete_dataset")
        'Permanently delete datasets from the platform'
        """
        return self._descriptions.get(permission, "")

    def get_role_summary(self, role: str) -> dict:
        """
        Return a human-readable summary of a role's permissions.

        Useful for debug output, admin UI, and documentation.

        Parameters
        ----------
        role : str — the role name (must be valid)

        Returns
        -------
        dict — {
            "role": str,
            "permission_count": int,
            "permissions": list[str],
            "descriptions": dict[str, str]
        }

        Example
        -------
        >>> rm.get_role_summary("analyst")
        {"role": "analyst", "permission_count": 5, "permissions": [...], ...}
        """
        perms = self.get_permissions(role)
        return {
            "role"             : role,
            "permission_count" : len(perms),
            "permissions"      : sorted(perms),
            "descriptions"     : {p: self._descriptions.get(p, "") for p in sorted(perms)},
        }

    def __repr__(self) -> str:
        roles = self.get_all_roles()
        return f"RoleManager(roles={roles}, path='{self._roles_path}')"


# ══════════════════════════════════════════════════════════════════════════════
# SINGLETON ACCESSOR
# ══════════════════════════════════════════════════════════════════════════════

_role_manager_instance: Optional[RoleManager] = None


def get_role_manager(roles_path: Optional[Path] = None) -> RoleManager:
    """
    Return the module-level singleton RoleManager instance.

    Creates a new instance on first call, reuses it on subsequent calls.
    Pass `roles_path` only on the first call (or to force a reload).

    Parameters
    ----------
    roles_path : Path, optional — custom path to roles.json (first call only)

    Returns
    -------
    RoleManager — the shared instance

    Example
    -------
    >>> rm = get_role_manager()
    >>> rm.get_permissions("admin")
    frozenset({...})

    # Force reload (e.g. after editing roles.json at runtime):
    >>> get_role_manager().reload()
    """
    global _role_manager_instance
    if _role_manager_instance is None or roles_path is not None:
        _role_manager_instance = RoleManager(roles_path=roles_path)
    return _role_manager_instance


# ── Quick self-test ───────────────────────────────────────────────────────────
if __name__ == "__main__":

    print("\n" + "=" * 60)
    print("  ROLE MANAGER — SELF TEST")
    print("=" * 60)

    rm = RoleManager()
    print(f"\n  Loaded: {rm}")

    for role in rm.get_all_roles():
        summary = rm.get_role_summary(role)
        print(f"\n  Role: {role}  ({summary['permission_count']} permissions)")
        for p in summary["permissions"]:
            print(f"    ✅ {p:25s}  {summary['descriptions'].get(p, '')}")

    print(f"\n  All permissions ({len(rm.get_all_permissions())}):")
    for p in sorted(rm.get_all_permissions()):
        print(f"    • {p}")

    # Validation
    assert rm.role_exists("admin")
    assert rm.role_exists("analyst")
    assert rm.role_exists("viewer")
    assert not rm.role_exists("superadmin")
    assert not rm.role_exists("")
    assert not rm.role_exists(None)

    try:
        rm.validate_role("hacker")
    except InvalidRoleError as e:
        print(f"\n  InvalidRoleError correctly raised for 'hacker': {e.code}")

    print("\n  All assertions passed.")
    print("=" * 60 + "\n")
