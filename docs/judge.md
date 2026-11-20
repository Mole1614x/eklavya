# Judge and evaluator operations

The API persists `QUEUED` work and sends only the submission identifier to Celery. A worker locks that row, claims a `RUNNING` lease, loads private cases in the worker, evaluates each bounded case, and persists a terminal result. Verified `SUBMIT` acceptance then awards idempotent progression in the same database workflow.

## Runtime map

| Workload | Runtime |
| --- | --- |
| Python console and MapReduce | allowlisted Python Alpine container |
| C/C++ | dedicated Alpine compiler container |
| Java | allowlisted Temurin JDK container |
| SQL | isolated SQLite database with mutation/schema operations denied |
| Pandas/NumPy | scientific data runner |
| PySpark | Spark runner |
| scikit-learn | ML runner |
| PyTorch | CPU deep-learning runner |
| Numerical/multiple choice | deterministic answer evaluator |

TensorFlow is not implemented and must not be advertised as executable.

## Isolation contract

Every learner-code container uses no network, a read-only root, dropped Linux capabilities, `no-new-privileges`, PID/CPU/memory/time/output limits, a read-only source mount, bounded tmpfs, and `--pull never`. Image names are code-controlled, not learner-controlled. The Docker socket makes the Celery service a host-security boundary: run it on dedicated capacity with access restricted to operators.

Workers use late acknowledgement, reject work lost with a worker, prefetch one task, bound retries, and database leases. Terminal deliveries are ignored. A fresh duplicate lease retries later; a stale lease is reclaimable. Learners may cancel queued work immediately and running work between bounded cases. Administrators may recover old leases from the audited admin action after confirming the original worker is unavailable.

Monitor queued/running/system-error counts, oldest queue age, lease age, execution duration, worker heartbeats, Docker disk, and runner image availability. Missing images and platform failures are `SYSTEM_ERROR`, never learner acceptance or wrong answer.
