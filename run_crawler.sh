#!/bin/bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
CRAWLER_DIR="${CRAWLER_DIR:-$SCRIPT_DIR}"
cd "$CRAWLER_DIR"
# Load environment variables from .env if exists
if [ -f "$CRAWLER_DIR/.env" ]; then
    set -a
    source "$CRAWLER_DIR/.env"
    set +a
fi

LOG="/tmp/crawler_cron.log"
RESULT="/tmp/crawler_result.flag"

rm -f "$RESULT"

python3 -u -c "
import sys, logging, os
sys.path.insert(0, '$CRAWLER_DIR')
os.chdir('$CRAWLER_DIR')

log_file = '$LOG'
start_pos = os.path.getsize(log_file) if os.path.exists(log_file) else 0

logging.basicConfig(level=logging.INFO, handlers=[
    logging.FileHandler(log_file, encoding='utf-8'),
])

from crawler import load_config, run
# Load config from $CRAWLER_DIR
cfg = load_config('$CRAWLER_DIR/config.yaml')
cfg['data']['log_file'] = log_file
cfg['data']['products_file'] = '/tmp/crawler_products.json'
run(cfg, dry_run=False)

with open(log_file, 'r') as f:
    f.seek(start_pos)
    new_output = f.read()
    if 'Telegram sent' in new_output or 'Telegram notification sent' in new_output:
        with open('$RESULT', 'w') as out:
            out.write('has_result')
" 2>>/tmp/crawler_cron_err.log

if [ -f "$RESULT" ]; then
    echo "CRAWLER_DONE"
fi