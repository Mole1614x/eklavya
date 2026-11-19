# EKLAVYA engineering notes

- Preserve the layered Next.js BFF, FastAPI, PostgreSQL/Alembic, Redis/Celery, and isolated-runner architecture.
- Use the Next.js App Router, explicit Pydantic response schemas, SQLAlchemy models, and reversible Alembic migrations. Run `alembic check` after every model change.
- Store representative public challenge data in `challenges/catalog.json`. Preserve challenge slugs and sample whitespace. Private test cases must never enter public catalog records or API responses.
- Never execute submissions in the API or judge worker process. Keep all runner images allowlisted and retain the network, filesystem, capability, PID, CPU, memory, time, and output controls.
- Never log access, refresh, verification, or password-reset tokens. Production secrets belong in environment-backed secret stores.
- Keep administrator authority database-backed, provision accounts only through the trusted CLI, and audit every administrative mutation. Never add passwords, password hashes, tokens, hidden expected output, or dataset storage paths to admin responses.
- Keep evaluation datasets outside public routes. Validate size, name, type, and content before private storage; multi-host deployments must use private object storage rather than a shared public filesystem.
- Keep feature work scoped, preserve existing changes, and run backend/judge tests, migration cycles, frontend typecheck/build, and relevant Playwright flows before proposing a PR.
- Treat the Docker socket as a critical infrastructure boundary and document any change to the sandbox threat model.
