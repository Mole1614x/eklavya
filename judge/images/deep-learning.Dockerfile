# syntax=docker/dockerfile:1.7
FROM python:3.12-slim
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then cp /run/secrets/build_ca /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi \
    && pip install --no-cache-dir --index-url https://download.pytorch.org/whl/cpu torch==2.5.1 \
    && if [ -f /usr/local/share/ca-certificates/build-ca.crt ]; then rm /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi
USER 65534:65534
