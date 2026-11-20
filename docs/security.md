# Security model and verification

This document describes implemented controls and their verified limits. Vulnerability reporting instructions are in the repository [security policy](../SECURITY.md).

## Controls

- Argon2 password hashes; generic authentication/reset responses; short access tokens; hashed, one-time refresh/verification/reset tokens; session revocation on reset and logout.
- Database-backed active-account and administrator checks. Public registration cannot select a role, and administrative changes are audited.
- Explicit production HTTPS origin and trusted-host allowlists, secure HttpOnly cookies, `SameSite` protection, same-origin checks for unsafe browser BFF routes, and restrictive browser security headers.
- Redis-backed limits for authentication and submission mutations. Production mutations fail closed when the protection store is unavailable.
- SQLAlchemy parameterization and validated filters; SQLite evaluator authorizers deny SQL mutations, attachments, pragmas, and schema changes.
- Private datasets are administrator-only, size-bounded, filename-normalized, extension/MIME allowlisted, parsed or signature checked, stored with restrictive permissions, and never served by a public route.
- Learner code executes only in allowlisted, per-case containers under the isolation contract in [judge.md](judge.md).
- Structured logs include request IDs, method, path, status, and latency but exclude bodies, credentials, source code, private cases, and dataset contents.

## Verification evidence

Automated tests cover malformed/expired tokens, forged role claims, inactive users, cross-user access, refresh rotation/revocation, admin denial, dataset traversal/type checks, hidden-output concealment, SQL mutation denial, isolation flags, headers, trusted hosts, production configuration, and CSRF rejection in the real browser/BFF flow. CI runs Python and npm dependency audits; repository secret-pattern review is part of release verification.

## Outstanding risk

- The judge owns Docker access; a worker compromise must be treated as host compromise. Dedicated sandbox nodes or an external sandbox are required for hostile public traffic.
- The project has no independent penetration test, WAF policy, host intrusion telemetry, or multi-host network-partition exercise.
- Audit records are append-only through the application, not cryptographically tamper-proof. Export them to retained centralized storage.
- Direct TLS files and all application/database/Redis credentials remain operator responsibilities and must come from a managed secret store.
