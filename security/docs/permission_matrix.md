# Permission Matrix

## Complete Permission Matrix — All Roles × All Permissions

| Permission | admin | analyst | viewer | Description |
|---|:---:|:---:|:---:|---|
| `manage_users` | ✅ | ❌ | ❌ | Create, edit, deactivate platform user accounts |
| `upload_dataset` | ✅ | ✅ | ❌ | Upload CSV or JSON datasets to the analytics platform |
| `delete_dataset` | ✅ | ❌ | ❌ | Permanently delete datasets from the platform |
| `analyze_data` | ✅ | ✅ | ❌ | Run AI models and analytics pipelines on datasets |
| `export_reports` | ✅ | ✅ | ❌ | Export analytics results to PDF, CSV, or external systems |
| `view_reports` | ✅ | ✅ | ✅ | View existing analytics reports and visualizations |
| `view_dashboards` | ✅ | ✅ | ✅ | Access read-only platform dashboards |
| `view_logs` | ✅ | ❌ | ❌ | Access security and audit logs |
| `manage_roles` | ✅ | ❌ | ❌ | Assign and revoke roles for other users |
| `configure_system` | ✅ | ❌ | ❌ | Modify platform-wide settings and configurations |
| **Total** | **10/10** | **5/10** | **2/10** | |

---

## Permission Counts by Role

| Role | Granted | Denied | Access Level |
|---|---|---|---|
| `admin` | 10 | 0 | Full platform access |
| `analyst` | 5 | 5 | Analytics + reporting |
| `viewer` | 2 | 8 | Read-only |

---

## What Each Role Can and Cannot Do

### admin
**Can do everything.**

| Action | Result |
|---|---|
| Create/edit user accounts | ✅ `manage_users` |
| Upload datasets | ✅ `upload_dataset` |
| Delete datasets | ✅ `delete_dataset` |
| Run AI analysis | ✅ `analyze_data` |
| Export reports | ✅ `export_reports` |
| View reports | ✅ `view_reports` |
| View dashboards | ✅ `view_dashboards` |
| View security logs | ✅ `view_logs` |
| Assign roles to users | ✅ `manage_roles` |
| Change system settings | ✅ `configure_system` |

---

### analyst
**Can work with data. Cannot manage the platform.**

| Action | Result | Reason |
|---|---|---|
| Upload datasets | ✅ `upload_dataset` | Core analytics work |
| Run AI analysis | ✅ `analyze_data` | Core analytics work |
| Export reports | ✅ `export_reports` | Core analytics work |
| View reports | ✅ `view_reports` | Included in analytics |
| View dashboards | ✅ `view_dashboards` | Included in analytics |
| Create/edit users | ❌ `manage_users` | Admin-only operation |
| Delete datasets | ❌ `delete_dataset` | Destructive — admin only |
| View security logs | ❌ `view_logs` | Sensitive — admin only |
| Assign roles | ❌ `manage_roles` | Privilege escalation risk |
| Change settings | ❌ `configure_system` | Admin-only operation |

**Why can't analysts delete datasets?**
Deletion is irreversible. Even if an analyst uploaded a dataset, deletion should require an admin to approve, preventing accidental data loss and giving admins visibility over what's being removed.

**Why can't analysts view logs?**
Audit logs may contain information about other users' activities, security events, and access patterns. This information should only be accessible to administrators.

---

### viewer
**Read-only. No write operations.**

| Action | Result | Reason |
|---|---|---|
| View reports | ✅ `view_reports` | Core viewer function |
| View dashboards | ✅ `view_dashboards` | Core viewer function |
| Upload datasets | ❌ `upload_dataset` | Write operation |
| Run AI analysis | ❌ `analyze_data` | Compute-intensive write |
| Export reports | ❌ `export_reports` | Prevents data exfiltration |
| Delete datasets | ❌ `delete_dataset` | Destructive operation |
| Create/edit users | ❌ `manage_users` | Admin-only |
| View security logs | ❌ `view_logs` | Sensitive |
| Assign roles | ❌ `manage_roles` | Admin-only |
| Change settings | ❌ `configure_system` | Admin-only |

**Why can't viewers export reports?**
Export is a data exfiltration risk. Viewers are stakeholders who should read information within the platform. If they need an export, an analyst or admin should provide it — this keeps an audit trail of what data leaves the platform.

---

## Permissions by Sensitivity

| Sensitivity | Permissions | Rationale |
|---|---|---|
| 🔴 **Admin only** | `manage_users`, `delete_dataset`, `view_logs`, `manage_roles`, `configure_system` | Destructive, sensitive, or privilege-escalation risk |
| 🟡 **Analyst+** | `upload_dataset`, `analyze_data`, `export_reports` | Data processing — requires training + accountability |
| 🟢 **All roles** | `view_reports`, `view_dashboards` | Read-only — safe for any authenticated user |

---

## Role Hierarchy for Resource Protection

Beyond per-permission checks, the RBAC system supports role-level hierarchy enforcement via `protect_resource()`:

```
Level 3: admin   → passes admin, analyst, viewer resource checks
Level 2: analyst → passes analyst, viewer resource checks
Level 1: viewer  → passes only viewer resource checks
```

| Resource Requires | admin | analyst | viewer |
|---|:---:|:---:|:---:|
| `admin` | ✅ | ❌ | ❌ |
| `analyst` | ✅ | ✅ | ❌ |
| `viewer` | ✅ | ✅ | ✅ |

---

## Extending Permissions

To add a new permission or role, edit `configs/roles.json` only:

```json
{
  "roles": {
    "analyst": {
      "permissions": [
        "upload_dataset",
        "analyze_data",
        "export_reports",
        "view_reports",
        "view_dashboards",
        "schedule_reports"   ← add here
      ]
    }
  },
  "all_permissions": [
    "...",
    "schedule_reports"       ← add here too
  ],
  "_permission_descriptions": {
    "schedule_reports": "Schedule automated report generation"  ← add here
  }
}
```

Then call `get_role_manager().reload()` — no code changes needed anywhere else.

---

## Denied Permission Summary

### What viewer CANNOT do (8 permissions)
`manage_users`, `upload_dataset`, `delete_dataset`, `analyze_data`, `export_reports`, `view_logs`, `manage_roles`, `configure_system`

### What analyst CANNOT do (5 permissions)
`manage_users`, `delete_dataset`, `view_logs`, `manage_roles`, `configure_system`

### What admin CANNOT do
Nothing — admin has all 10 platform permissions.
