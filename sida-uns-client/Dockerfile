# ---- Stage 1: fetch vendored browser bundles (no build step, just pull dists)
FROM node:20-alpine AS vendor
WORKDIR /vendor
# Pin versions of the two allowed runtime libs: mqtt.js (MQTT over WebSocket)
# and protobufjs (Sparkplug B / Protobuf decoding). Nothing else is bundled.
RUN npm install --no-save --no-audit --no-fund mqtt@5.10.1 protobufjs@7.4.0

# ---- Stage 2: static server
FROM nginx:1.27-alpine
# Copy the application static files.
COPY src/ /usr/share/nginx/html/
# Copy the two vendored browser bundles next to index.html.
COPY --from=vendor /vendor/node_modules/mqtt/dist/mqtt.min.js /usr/share/nginx/html/vendor/mqtt.min.js
COPY --from=vendor /vendor/node_modules/protobufjs/dist/protobuf.min.js /usr/share/nginx/html/vendor/protobuf.min.js
# nginx site + entrypoint that injects BROKER_WS_URL into config.js at startup.
COPY nginx.conf /etc/nginx/conf.d/default.conf
COPY docker-entrypoint.sh /docker-entrypoint.d/40-sida-config.sh
RUN chmod +x /docker-entrypoint.d/40-sida-config.sh
EXPOSE 80
