#!/bin/sh
# Injects runtime configuration into the static app at container startup.
# The BROKER_WS_URL env var is written into config.js so the browser can read
# it — credentials are NEVER injected here (they only exist in the browser tab).
set -e

TARGET="/usr/share/nginx/html/config.js"
BROKER_WS_URL="${BROKER_WS_URL:-}"
HISTORY_MAX_POINTS="${HISTORY_MAX_POINTS:-300}"

cat > "$TARGET" <<EOF
// Generated at container startup from environment variables. Do not edit.
window.__SIDA_CONFIG__ = {
  BROKER_WS_URL: "${BROKER_WS_URL}",
  HISTORY_MAX_POINTS: ${HISTORY_MAX_POINTS}
};
EOF

echo "[sida-uns-client] config.js gerado com BROKER_WS_URL='${BROKER_WS_URL}'"
