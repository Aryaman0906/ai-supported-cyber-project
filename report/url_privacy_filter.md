# Third-Party URL Privacy Filter

## Purpose

Optional URL reputation checks can be useful, but they may disclose the submitted URL to an external provider. This project now uses a local sensitive URL filter before any external reputation provider is called.

The filter does not stop local/offline URL analysis. It only controls whether a URL is safe enough to submit to third-party services.

## Flow

```text
User URL
  ↓
Offline URL feature extraction and model analysis
  ↓
External checks requested?
  ↓
Sensitive URL filter
  ↓
If safe: provider checks may run
If blocked: no provider request is made
```

## Blocked URL categories

The filter blocks third-party submission when a URL appears to contain or target:

| Category | Example risk |
|---|---|
| Unsupported scheme | `file://`, `data:`, or other non-http/non-https inputs |
| Local/private/internal host | localhost, private IP ranges, single-label intranet names, `.local`, `.internal`, `.lan` |
| Private service link | mailbox, personal document, account, or identity-provider links |
| Embedded user-info | URLs containing user-info material before the host |
| Sensitive query parameter names | session, auth, reset, invite, verification, one-time codes, or similar parameter names |
| Account-flow path | login/reset/callback/invite/verification style path combined with a query or token-like path |
| Token-like path value | long high-entropy path segments |
| Personal identifier | email-like identifiers inside the URL |

## User-facing behavior

When external checks are disabled, the result says `submitted: false` and no providers are called.

When external checks are enabled but the URL is blocked, the result includes:

```json
{
  "enabled": true,
  "submitted": false,
  "sensitive_url_filter": {
    "status": "blocked",
    "safe_to_submit": false,
    "categories": ["sensitive_query_parameters"]
  },
  "providers": [
    {"provider": "virustotal", "status": "skipped"},
    {"provider": "phishtank", "status": "skipped"}
  ]
}
```

The important part is `submitted: false`: the URL was not sent to any third-party provider.

## Safe usage rule

External checks should only be enabled for public, non-sensitive URLs that the user has permission to submit. For private URLs, tokenized URLs, mailbox links, document links, or internal hosts, rely on the local/offline analysis result instead.

## Validation

The tests in `tests/test_external_checks.py` verify that:

- external checks stay disabled by default;
- sensitive query URLs are blocked before provider calls;
- internal hosts are blocked before provider calls;
- private service links are blocked;
- safe public URLs still reach the configured provider functions;
- token-like path values are blocked.
