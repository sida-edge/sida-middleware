// This file is OVERWRITTEN at container startup by docker-entrypoint.sh,
// which injects the BROKER_WS_URL environment variable. The value below is a
// development fallback only and is never persisted with credentials.
window.__SIDA_CONFIG__ = window.__SIDA_CONFIG__ || {
  BROKER_WS_URL: "ws://localhost:9001",
  HISTORY_MAX_POINTS: 300
};
