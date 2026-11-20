# Changelog

All notable EKLAVYA changes are documented here. The project follows semantic versioning after the first reviewed production release.

## [1.0.0] - 2026-11-20

### Added

- Integrated programming, SQL, data, statistics, big-data, ML, AI, daily-learning, contest, ranking, path, insight, and administration journeys.
- Database-authorized administration, validated private datasets, append-only audit history, and trusted administrator provisioning.
- Bounded public caching, indexed and paginated hot paths, submission cancellation, stale-job recovery, load tools, and lifecycle metrics.
- Production environment template, segmented Compose networks, resource/log limits, authenticated Redis, optional direct TLS, Prometheus rules, and guarded backup/restore scripts.
- Same-origin enforcement for browser mutations and expanded production configuration validation.

### Security

- HttpOnly rotating sessions, Argon2 password hashes, strict authorization, explicit CORS/host allowlists, security headers, shared rate limits, and isolated no-network judge containers.
- CI dependency audits, migration/reversibility checks, browser integration, container-definition checks, and production configuration rendering.

### Known limitations

- Transactional email delivery requires an operator-selected provider.
- TensorFlow evaluation is not implemented.
- Live Phase 16 PySpark, Pandas/NumPy, scikit-learn, PyTorch, and Java concurrency reruns were storage-blocked in the 7.9 GB verification workspace; prior functional evidence and automated contracts are identified in the final report.
- No independent penetration test or multi-host soak test has been completed.
