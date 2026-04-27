# Security Policy

## ⚠️ NEVER Commit Secrets

The following must NEVER be committed to this repository:

- Firebase API keys or service account JSON files
- `.env` files containing real credentials
- Private keys (`.pem`, `.key`)
- Model weights that contain private training data
- Any real user data or PII

## If You Accidentally Push a Secret

1. **Immediately** contact the group leader.
2. The secret must be rotated/revoked at the source.
3. Use `git filter-branch` or BFG Repo Cleaner to scrub history.
4. Notify all team members to re-clone.

## Reporting Vulnerabilities

Report security issues privately via GitHub's "Security Advisories" tab or directly to the group leader.
