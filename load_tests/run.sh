#!/bin/bash
# ==============================================================================
# TourneyPro k6 Load Test Runner
# ==============================================================================

set -e

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
K6_BIN=$(which k6 || echo "/opt/homebrew/bin/k6")

if [ ! -x "$K6_BIN" ]; then
    echo "❌ k6 binary not found! Please run: brew install k6"
    exit 1
fi

SCENARIO="${1:-smoke}"
PORT="${2:-5001}"
BASE_URL="${BASE_URL:-http://localhost:${PORT}}"

# Optional Web Dashboard support
# Usage: DASHBOARD=true ./load_tests/run.sh combined
# or pass 'dashboard' as 3rd arg: ./load_tests/run.sh combined 5001 --dashboard
K6_FLAGS=()
if [ "$3" == "--dashboard" ] || [ "$DASHBOARD" == "true" ] || [ "$K6_WEB_DASHBOARD" == "true" ]; then
    export K6_WEB_DASHBOARD=true
    export K6_WEB_DASHBOARD_OPEN=${K6_WEB_DASHBOARD_OPEN:-true}
    export K6_WEB_DASHBOARD_PORT=${K6_WEB_DASHBOARD_PORT:-5665}
    echo "📊 Live Web Dashboard enabled at: http://127.0.0.1:${K6_WEB_DASHBOARD_PORT}"
fi

# Optional HTML export report: EXPORT_HTML=report.html ./load_tests/run.sh combined
if [ -n "$EXPORT_HTML" ]; then
    export K6_WEB_DASHBOARD=true
    export K6_WEB_DASHBOARD_EXPORT="$EXPORT_HTML"
    echo "💾 HTML Summary report will be saved to: $EXPORT_HTML"
fi

echo "========================================================"
echo "  TourneyPro k6 Load Testing Suite"
echo "  Target URL : ${BASE_URL}"
echo "  Scenario   : ${SCENARIO}"
echo "========================================================"

# Health check
echo "🔍 Checking if target server is running at ${BASE_URL}..."
if ! curl -s -f -m 3 "${BASE_URL}/api/v1/tournaments" > /dev/null; then
    echo "⚠️ Warning: Could not reach ${BASE_URL}/api/v1/tournaments."
    echo "Make sure your Flask server is running before executing load tests."
    echo "To start your server:"
    echo "  python run.py"
    echo "or for realistic multi-worker concurrency:"
    echo "  ./venv/bin/gunicorn -w 4 -b 0.0.0.0:${PORT} run:app"
    echo ""
    read -p "Do you want to continue anyway? [y/N] " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

case "$SCENARIO" in
    smoke)
        echo "🚀 Running Smoke Test (1 VU, verification)..."
        "$K6_BIN" run "${K6_FLAGS[@]}" -e BASE_URL="$BASE_URL" "$DIR/scenarios/smoke.js"
        ;;
    browse|public)
        echo "🚀 Running Public Browsing Load Test (up to 50 VUs)..."
        "$K6_BIN" run "${K6_FLAGS[@]}" -e BASE_URL="$BASE_URL" "$DIR/scenarios/public-browse.js"
        ;;
    auth|authenticated)
        echo "🚀 Running Authenticated User Load Test (up to 40 VUs)..."
        "$K6_BIN" run "${K6_FLAGS[@]}" -e BASE_URL="$BASE_URL" "$DIR/scenarios/authenticated-user.js"
        ;;
    combined)
        echo "🚀 Running Combined Multi-Scenario Load Test (Public + Authenticated)..."
        "$K6_BIN" run "${K6_FLAGS[@]}" -e BASE_URL="$BASE_URL" "$DIR/scenarios/combined-load.js"
        ;;
    spike)
        echo "🚀 Running Spike / Rush Load Test (rapid spike to 100 VUs)..."
        "$K6_BIN" run "${K6_FLAGS[@]}" -e BASE_URL="$BASE_URL" "$DIR/scenarios/stress-spike.js"
        ;;
    *)
        echo "❌ Unknown scenario: $SCENARIO"
        echo "Available scenarios: smoke, browse, auth, combined, spike"
        exit 1
        ;;
esac
