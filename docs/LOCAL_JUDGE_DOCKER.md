# EKLAVYA judge on Docker Desktop (local development only)

The web application runs independently of the optional judge profile.
The judge Dockerfile uses Docker CLI 24.0.6, matching Docker Desktop Engine
24.0.6. The judge runner sends source files over stdin as a tar archive,
so Docker does not need to bind-mount paths from inside the judge container.

## Run on the Mac

In the repository root, ensure Docker Desktop is running.

```sh
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge up -d --build
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge ps
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge exec judge docker info
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge logs --tail=60 judge
```

The local Compose override deliberately runs the judge as root to access
Docker Desktop's root-owned Docker socket (mode 0755 in the reported setup).
**Do not use the override on a shared, internet-facing or production host.**
Docker socket access is equivalent to Docker host administrative access.
The judge's container limits do not make socket delegation safe.

For local changes, use `git status` before pulling and preserve any uncommitted
modifications. The local override is intentionally separate from the base
Compose file; never enable it in a production deployment.

Frontend: http://localhost:3000
Backend health: http://localhost:8001/api/v1/health/ready

## Smoke tests

```sh
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge exec judge python -c 'from judge.executor import execute; print(execute("python", "print(2+2)", ""))'
docker compose -f docker-compose.yml -f docker-compose.judge-local.yml --profile judge exec judge python -c 'from judge.executor import execute; print(execute("java", "public class Main { public static void main(String[] args) { System.out.println(4); }}", ""))'
```

Expect `Execution(verdict='COMPLETED', output='4\\n', ...)` for both smoke tests.
Full API submission, evaluator verdicts and security hardening require separate validation.

Note: the Docker daemon in the reported local environment warns that its
default seccomp profile is disabled. Review Docker Desktop security settings
before running code from anyone besides yourself.
