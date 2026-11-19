FROM python:3.12-slim
RUN pip install --no-cache-dir pandas==2.3.3 numpy==2.3.4
USER 65534:65534
