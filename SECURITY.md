# EKLAVYA security policy

## Reporting

Do not open a public issue for a suspected vulnerability. Send the repository owner a private GitHub security advisory with reproduction steps, affected versions, and impact. Avoid accessing other users' data or running destructive proof-of-concept code.

## Trust boundaries

- Browsers communicate with the Next.js BFF. Access and refresh tokens are HTTP-only; the refresh cookie is restricted to the auth route and uses `SameSite=Strict`.
- The FastAPI service is the authorization boundary. UI checks are never treated as authorization.
- PostgreSQL and Redis are private dependencies and are not exposed by the production Compose override.
- The judge is an infrastructure-security boundary. It can access the Docker daemon to create restricted child containers; compromise of the worker must be treated as host compromise.

## Implemented controls

- Argon2 password hashes, generic login/reset responses, short access-token lifetime, hashed refresh/account tokens, one-time refresh rotation, reset-time session revocation, and backend role checks.
- Explicit production secret, origin, and host validation; CORS allowlists; trusted-host checks; CSP, HSTS, clickjacking, MIME-sniffing, referrer, and browser-permission headers.
- Redis-backed rate limits for account entry points and submission mutations. Protected mutations fail closed if the production limit store is unavailable.
- Request IDs, structured JSON logs without credentials or account tokens, generic database errors, readiness probes, and low-cardinality Prometheus metrics.
- Per-submission containers with no network, read-only roots, all Linux capabilities dropped, `no-new-privileges`, PID/CPU/memory/time/output limits, read-only source mounts, and disposable temporary filesystems.
- Non-root application and runner images, read-only production services, profile-gated workers, and no public database or Redis ports.

## Operator responsibilities

- Generate and rotate strong secrets outside Git; use a secret manager rather than `.env` for managed deployments.
- Terminate TLS before the production proxy, keep secure cookies enabled, restrict administrative accounts, and retain audit logs.
- Run the judge on dedicated capacity, restrict access to the Docker socket, preapprove runner images, and keep Docker/kernel/base images patched.
- Back up PostgreSQL, test restoration, monitor dependency advisories, and apply supported upgrades through reviewed migrations.
- Integrate a transactional email provider without logging verification or password-reset tokens.

Supported code is the latest commit on the default branch after its required checks pass.
