#!/bin/sh
# Trusted local Docker Desktop only; intentionally uses docker-compose.judge-local.yml.
set -eu
cd "$(dirname "$0")/.."

echo "Building and starting EKLAVYA judge..."
docker compose -p eklavya \
  -f docker-compose.yml -f docker-compose.judge-local.yml \
  --profile judge up -d --no-deps --build --force-recreate judge

echo "Checking Docker daemon access inside judge..."
docker compose -p eklavya \
  -f docker-compose.yml -f docker-compose.judge-local.yml \
  --profile judge exec -T judge docker info >/dev/null

echo "Running full local judge smoke checks..."
docker compose -p eklavya \
  -f docker-compose.yml -f docker-compose.judge-local.yml \
  --profile judge exec -T judge python -m judge.smoke

echo "Judge smoke tests passed. This does NOT establish production sandbox safety."
