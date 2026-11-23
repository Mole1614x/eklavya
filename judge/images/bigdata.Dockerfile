# syntax=docker/dockerfile:1.7
FROM python:3.12-slim-bookworm
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then cp /run/secrets/build_ca /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi \
    && apt-get update \
    && apt-get install -y --no-install-recommends openjdk-17-jre-headless procps \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir pyspark==3.5.3 \
    && if [ -f /usr/local/share/ca-certificates/build-ca.crt ]; then rm /usr/local/share/ca-certificates/build-ca.crt && update-ca-certificates; fi
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 \
    PYSPARK_PYTHON=python \
    SPARK_LOCAL_IP=127.0.0.1 \
    SPARK_LOCAL_HOSTNAME=localhost
USER 65534:65534
