#!/bin/bash
# Wrapper for cron / systemd timer.
# - prevents overlapping runs via flock
# - hard timeout so a hung run doesn't block the next one
# - sources .env if present (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID)
set -u

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRAWLER_DIR="${CRAWLER_DIR:-$(dirname "$SCRIPT_DIR")}"
cd "$CRAWLER_DIR" || exit 1

if [ -f "$CRAWLER_DIR/.env" ]; then
    set -a
    # shellcheck disable=SC1091
    source "$CRAWLER_DIR/.env"
    set +a
fi

mkdir -p "$CRAWLER_DIR/logs"
LOG="$CRAWLER_DIR/logs/cron.log"
ERR="$CRAWLER_DIR/logs/cron_err.log"
LOCK=/tmp/3c-crawler.lock
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-300}"

# Skip if a previous run is still in progress
exec 9>"$LOCK"
if ! flock -n 9; then
    echo "$(date '+%F %T') another run in progress, skipping" >> "$ERR"
    exit 0
fi

timeout "$TIMEOUT_SECONDS" python3 -u crawler.py --config "$CRAWLER_DIR/config.yaml" >> "$LOG" 2>> "$ERR"
code=$?
if [ "$code" -eq 124 ]; then
    echo "$(date '+%F %T') timed out after ${TIMEOUT_SECONDS}s" >> "$ERR"
fi
exit "$code"
