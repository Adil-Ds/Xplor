# Contributing Guide

## Workflow

1. **Never push directly to `main` or `dev`.**  
2. Work only on your feature branch.
3. When done → open a Pull Request into `dev`.
4. At least **one other team member** must review & approve.
5. `dev` → `main` merges are done by the group leader only after testing.

## Branch Naming

```
feature/<your-name>/<short-description>
fix/<your-name>/<short-description>
docs/<your-name>/<short-description>
```

**Examples:**
```
feature/mareeha/anomaly-detection-model
fix/laiba/file-upload-bug
docs/nabiha/dashboard-readme
```

## Commit Message Format

```
<type>(<scope>): <short description>
```

| Type | When to use |
|---|---|
| `feat` | New feature |
| `fix` | Bug fix |
| `docs` | Documentation only |
| `train` | ML model training update |
| `test` | Adding/fixing tests |
| `style` | Formatting, no logic change |
| `refactor` | Code restructure |
| `security` | Security-related changes |

**Examples:**
```
feat(backend): add CSV file upload endpoint
train(ai-models): retrain distilBERT with new dirty rows
fix(frontend): fix dashboard chart not re-rendering
security(auth): add MFA TOTP endpoint
```

## Pull Request Rules

- Fill in the PR template completely.
- Link the related GitHub Issue (e.g., `Closes #12`).
- Add screenshots for UI changes.
- All CI checks must pass.
- No PR with unresolved comments will be merged.

## Code Style

- **Python:** Follow PEP 8. Run `black .` and `flake8` before committing.
- **JavaScript/React:** Follow ESLint config. Run `npm run lint`.
- **Notebooks:** Clear all outputs before committing.
