FROM python:3.12-slim
WORKDIR /opt/eklavya
COPY backend/requirements.txt backend/requirements.txt
COPY judge/requirements.txt judge/requirements.txt
RUN apt-get update && apt-get install -y --no-install-recommends docker.io && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir -r judge/requirements.txt
COPY backend/ backend/
COPY judge/ judge/
COPY challenges/ challenges/
RUN useradd --create-home judge && chown -R judge:judge /opt/eklavya
USER judge
CMD ["celery", "-A", "judge.celery_app:app", "worker", "--loglevel=INFO", "--concurrency=2"]
