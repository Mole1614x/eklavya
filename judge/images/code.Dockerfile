# syntax=docker/dockerfile:1.7
FROM alpine:3.21
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then cp /etc/ssl/certs/ca-certificates.crt /tmp/ca-certificates.crt && cat /run/secrets/build_ca >> /etc/ssl/certs/ca-certificates.crt; fi \
    && apk add --no-cache gcc g++ musl-dev \
    && if [ -f /tmp/ca-certificates.crt ]; then mv /tmp/ca-certificates.crt /etc/ssl/certs/ca-certificates.crt; fi
USER 65534:65534
