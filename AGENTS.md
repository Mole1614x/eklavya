# EKLAVYA engineering notes

- Keep work scoped to the phase in the issue or brief. Develop on feature branches and verify changes before proposing a PR.
- Use the Next.js App Router for UI, FastAPI and Pydantic for the versioned API, and SQLAlchemy plus Alembic for database changes. Keep API response schemas explicit.
- Store representative public challenge data in `challenges/catalog.json`. Preserve challenge slugs and whitespace in examples. Never include private test cases in public catalog data or API responses.
- Keep execution outside the API process. Phase 1 has no judge. The editor must report unavailable execution and submissions without generating verdicts.
- Run backend tests and migration checks, then run frontend type checking, the production build, and Playwright with the seeded backend running. See README for commands.
