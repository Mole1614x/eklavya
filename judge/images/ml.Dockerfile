FROM python:3.12-slim
RUN pip install --no-cache-dir numpy==2.3.4 scikit-learn==1.7.2
USER 65534:65534
