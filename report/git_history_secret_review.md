# Git History Secret Review

This document records the remaining secret-exposure verification work for the project.

## Why this exists

`.gitignore` protects future commits, but it does not prove that older commits are clean. A normal pull request can remove sensitive values from current tracked files, but it cannot erase sensitive values already present in Git history.

Because this project uses local Gmail OAuth files, optional Google Drive uploads, generated reports, and local environment variables, history checks must be run before final submission.

## What to check

Run the helper script from the repository root:

```powershell
.\tools\check_git_history_secrets.ps1
```

The script checks:

- tracked sensitive runtime files
- ignored local secret files
- current files for secret-like strings
- current files for Drive folder URLs
- Git history for sensitive file names
- Git history for common token/API key patterns

## If findings appear

Do not paste raw secrets into issues, PRs, reports, screenshots, or chat.

Use this response plan:

1. Revoke or rotate exposed OAuth/API credentials.
2. Recreate any exposed Drive folder if the old folder URL or folder identifier appeared in history.
3. Put new private values only in `.env`, `.env.local`, Windows environment variables, or another ignored local config.
4. Confirm current tracked files no longer contain real private values.
5. Add only redacted proof to the final report.

## Expected clean current-state result

For current tracked files, the old Drive folder example should no longer appear after the placeholder cleanup PR. The history scan may still show old commits. That does not mean the current files are still dirty; it means operational rotation is required.

## Important limitation

This project should prefer operational rotation over Git history rewriting. Rewriting public Git history requires force-push coordination and can break clones, forks, and pull requests. For this college/demo project, the safer recommendation is:

- remove sensitive values from current files
- rotate or recreate exposed resources
- document the review with redacted proof
