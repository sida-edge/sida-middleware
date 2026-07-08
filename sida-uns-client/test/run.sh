#!/usr/bin/env bash
# Runs the acceptance test (SDD 3.1) fully containerized: an isolated Mosquitto
# broker, the real client image, and a Playwright test-runner that publishes the
# Sparkplug B sequence and asserts the UI. Exit code = test result.
set -uo pipefail
cd "$(dirname "$0")"

COMPOSE="docker compose -f docker-compose.test.yml"

cleanup() {
  echo "--- tearing down test stack ---"
  $COMPOSE down -v >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "--- building & running acceptance stack ---"
$COMPOSE up --build --abort-on-container-exit --exit-code-from test-runner
RESULT=$?

echo "--- acceptance test exit code: $RESULT ---"
exit $RESULT
