#!/usr/bin/env bash
# simulate_failure.sh
# --------------------
# Breaks the sample-app so you can watch the self-healing monitor detect it
# and trigger an automatic restart. Use this to demo the project live.
#
# Usage:
#   ./scripts/simulate_failure.sh          # break the app
#   ./scripts/simulate_failure.sh --fix    # manually restore it (healer does this automatically)
#   ./scripts/simulate_failure.sh --watch  # stream healer logs while you wait

set -euo pipefail

APP_URL="http://localhost:8080"
HEALER_CONTAINER="healer"

log()  { echo -e "\033[1;34m[INFO]\033[0m  $*"; }
warn() { echo -e "\033[1;33m[WARN]\033[0m  $*"; }
ok()   { echo -e "\033[1;32m[ OK ]\033[0m  $*"; }

# ── Parse arguments ───────────────────────────────────────────────────────────
ACTION="${1:-break}"

case "$ACTION" in
  --fix)
    log "Manually restoring sample-app to healthy state..."
    curl -s -X POST "$APP_URL/fix" | python3 -m json.tool
    ok "App is healthy again."
    exit 0
    ;;

  --watch)
    log "Streaming healer logs (Ctrl+C to stop)..."
    docker logs -f "$HEALER_CONTAINER"
    exit 0
    ;;

  --status)
    log "Current health status:"
    curl -s "$APP_URL/health" | python3 -m json.tool
    exit 0
    ;;

  break|--break|"")
    # Fall through to the main demo flow below
    ;;

  *)
    echo "Usage: $0 [--fix | --watch | --status]"
    exit 1
    ;;
esac

# ── Main demo: break the app and watch recovery ───────────────────────────────
log "=== Self-Healing Demo ==="
echo ""

# Step 1: confirm app is up
log "Checking app health before breaking it..."
STATUS=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/health" || echo "000")
if [[ "$STATUS" != "200" ]]; then
  warn "App returned HTTP $STATUS — make sure 'docker compose up' is running first."
  exit 1
fi
ok "App is currently healthy (HTTP 200)"
echo ""

# Step 2: break the app
log "Sending /break signal to sample-app..."
curl -s -X POST "$APP_URL/break" | python3 -m json.tool
echo ""
warn "App is now returning HTTP 503 on /health"
echo ""

# Step 3: watch healer respond
log "Streaming healer logs — watch for the restart event..."
log "(The healer polls every 15s and restarts after 3 consecutive failures — expect ~45s)"
echo ""
echo "─────────────────────────────────────────────────────"
timeout 90 docker logs -f "$HEALER_CONTAINER" 2>&1 | grep --line-buffered -E "(unhealthy|Restarting|restarted|recovered|ERROR)" || true
echo "─────────────────────────────────────────────────────"
echo ""

# Step 4: confirm recovery
log "Checking health after recovery..."
sleep 3
FINAL=$(curl -s -o /dev/null -w "%{http_code}" "$APP_URL/health" || echo "000")
if [[ "$FINAL" == "200" ]]; then
  ok "✅  Recovery confirmed — app is healthy again (HTTP 200)"
else
  warn "App returned HTTP $FINAL after recovery window. Check healer logs."
fi
