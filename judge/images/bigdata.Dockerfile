FROM python:3.12-slim-bookworm
RUN apt-get update && apt-get install -y --no-install-recommends openjdk-17-jre-headless && rm -rf /var/lib/apt/lists/* && pip install --no-cache-dir pyspark==3.5.3
ENV JAVA_HOME=/usr/lib/jvm/java-17-openjdk-amd64 PYSPARK_PYTHON=python
USER 65534:65534
