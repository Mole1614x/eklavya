FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DOCKER_API_VERSION=1.43
WORKDIR /opt/eklavya

# Use the CLI version confirmed to work with the local Docker Desktop 24.0.6 daemon.
COPY --from=docker:24.0.6-cli /usr/local/bin/docker /usr/local/bin/docker

COPY backend/requirements.txt backend/requirements.txt
COPY judge/requirements.txt judge/requirements.txt
RUN pip install --no-cache-dir -r judge/requirements.txt
COPY backend/ backend/
COPY judge/ judge/
COPY challenges/ challenges/
RUN useradd --create-home judge && chown -R judge:judge /opt/eklavya
USER judge
CMD ["celery", "-A", "judge.celery_app:app", "worker", "--loglevel=INFO", "--concurrency=2"]
