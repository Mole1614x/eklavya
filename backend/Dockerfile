# syntax=docker/dockerfile:1.7
FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /opt/eklavya/backend
COPY backend/requirements.txt .
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then cp /run/secrets/build_ca /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi \
    && pip install --no-cache-dir -r requirements.txt \
    && useradd --create-home eklavya \
    && if [ -f /usr/local/share/ca-certificates/build-ca.crt ]; then rm /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi
COPY --chown=eklavya:eklavya backend/ .
COPY --chown=eklavya:eklavya challenges/ ../challenges/
USER eklavya
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--proxy-headers", "--forwarded-allow-ips=*", "--no-access-log"]
