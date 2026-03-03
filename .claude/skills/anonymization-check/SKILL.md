---
name: anonymization-check
description: Scan the codebase for personal and sensitive data (PII, secrets, credentials, hardcoded emails/names/tokens). Use when the user asks to check for privacy issues, data leaks, or sensitive data exposure.
allowed-tools: Read, Grep, Glob
---

Scan this project for personal and sensitive data. Cover **all** of the following locations:

- `src/` — Python source code
- `tests/` — test files (hardcoded fixtures, sample data)
- `config.yaml` — configuration file (may contain real URLs, emails, calendar IDs)
- `.env`, `*.env` files if present
- `state/` directory
- Any `*.json`, `*.yaml`, `*.yml`, `*.toml`, `*.ini` files at root level

## What to look for

### High severity
- Passwords, secrets, tokens, API keys (look for patterns like `key=`, `token=`, `secret=`, `password=`, `Bearer `)
- Private key material (`-----BEGIN`, `-----END`)
- Google service account JSON content (hardcoded in source instead of referenced by path)
- Database connection strings with credentials

### Medium severity
- Real email addresses (not example.com / placeholder domains)
- Real full names of individuals
- Phone numbers
- National/personal ID numbers
- Real Google Calendar IDs (format: `xxx@group.calendar.google.com`) hardcoded in source or config
- Real URLs pointing to internal/private systems

### Low severity
- Internal server hostnames or IP addresses
- Usernames that look real (not `admin`, `test`, `user`)
- Comments referencing real people or internal systems

## How to scan

1. Use Grep to search for common patterns across the codebase
2. Read `config.yaml` and any `.env` files in full
3. Read test fixture files — look for hardcoded sample data that might be real

## Output format

Report findings as a structured list:

```
[SEVERITY] Type of data
  File: path/to/file.py:LINE
  Found: <redacted preview, show only enough to identify the issue>
  Fix: <concrete suggestion>
```

End with a summary:
- Total findings by severity
- Overall risk assessment (Clean / Low Risk / Needs Review / High Risk)
- Top recommended action if any findings exist

If nothing is found, confirm the codebase looks clean and state what was checked.
