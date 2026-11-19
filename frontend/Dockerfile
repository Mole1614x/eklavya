# syntax=docker/dockerfile:1.7
FROM node:24-bookworm-slim AS build
WORKDIR /app
ENV NEXT_TELEMETRY_DISABLED=1
COPY . .
RUN --mount=type=secret,id=build_ca,required=false \
    if [ -f /run/secrets/build_ca ]; then export NODE_EXTRA_CA_CERTS=/run/secrets/build_ca; fi \
    && npm ci --no-audit --no-fund \
    && npm run build \
    && rm -rf node_modules .next/cache /root/.npm

FROM node:24-bookworm-slim
WORKDIR /app
ENV NODE_ENV=production NEXT_TELEMETRY_DISABLED=1
COPY --from=build --chown=node:node /app/.next/standalone ./
USER node
EXPOSE 3000
CMD ["node", "server.js"]
