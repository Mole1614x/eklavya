# Production architecture

EKLAVYA keeps browser sessions, application data, queueing, and untrusted execution in separate trust zones.

```text
Browser -> HTTPS edge -> unprivileged Nginx -> Next.js BFF -> FastAPI/Uvicorn
                                                        |-> PostgreSQL
                                                        `-> Redis <- Celery judge
                                                                       `-> one no-network container per case
Prometheus ----------------------- private scrape --------------------^ metrics
Administrator ------------------- private dataset volume/object store
```

## Components and boundaries

- Nginx is the only host-published production service. The default production override binds its HTTP listener to loopback for a managed TLS edge; the optional TLS override publishes 443 with operator-supplied certificate files.
- Next.js renders the product and proxies authenticated browser calls. Access and refresh tokens remain HttpOnly cookies; unsafe BFF routes enforce same-origin browser metadata.
- FastAPI/Uvicorn owns validation, authentication, authorization, business rules, and public API schemas. It never executes submitted code.
- PostgreSQL is authoritative for users, catalog, submissions, progression, contests, administration, audit records, and dataset metadata.
- Redis is an authenticated, persistent Celery broker, shared rate-limit store, and short public-response cache. Correctness does not depend on cache hits.
- Celery workers claim database leases and create a fresh allowlisted runner container for each evaluated case. Workers require Docker access and belong on dedicated, patched capacity; they are not placed on the application network.
- Private datasets use a non-public mounted volume in the single-host topology. Multi-host installations must replace it with private object storage and short-lived authorized retrieval.
- Prometheus scrapes FastAPI only on the private application network. Alert routing, host/database exporters, centralized logs, and durable dashboards belong to the deployment platform.

Production Compose uses `edge`, `application`, and `data` networks. PostgreSQL and Redis exist only on `data`; the judge shares only `data`; the frontend shares only `application`; the proxy joins `edge` and `application`; FastAPI bridges `application` and `data`. Child judge containers always use `--network none`.

## Scaling

Frontend and API replicas are stateless. Keep the sum of per-replica SQLAlchemy pools below the PostgreSQL connection budget. Scale judge workers independently, with Celery prefetch one and concurrency aligned to the CPU/memory needed by child containers. Dataset storage must become shared private object storage before scaling admin or judge services across hosts.
