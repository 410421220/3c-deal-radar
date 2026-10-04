# AGENTS.md

Product crawler: fetch Ruten/PTT listings → price filter → ID dedupe → Telegram notification. Plain Python; no tests/lint/CI.

## Common commands

```bash
pip install -r requirements.txt   # only pyyaml, requests
python crawler.py --dry-run       # fetch without sending notifications
python crawler.py                 # full run (sends Telegram)
python test_connection.py         # connectivity smoke test (hits real network)
```

No unit test framework; `test_connection.py` is a live connectivity smoke test.

## Architecture notes (non-obvious)

- `crawler.py` is the only entrypoint: `load_config` → Ruten/PTT fetch → filter → `find_new_products` dedupe → notify.
- Dedupe state and product data **share** `data.products_file` (history format `{"seen": {id: date}}`); Ruten keys by `prod_id`, others by `url+title`; 3-day cutoff, max 5000 entries.
- **PTT items skip price filtering** (`source == "ptt"` kept unconditionally); only Ruten applies `0 < price <= max_price`.
- `analyzer.py` is standalone (OpenRouter scoring); **crawler.py never imports it** — changes don't affect the main flow.
- Old backups `notifier.py.bak` / `.bak2` / `.backup` were deleted (stashed in `/tmp/opencode/3c-crawler-attic/`) — do not import them.

## Environment & config gotchas

- `config.yaml` `data.products_file` / `log_file` are relative (`data/`, `logs/`); when deploying elsewhere, override via `--config`.
- `config.yaml` contains a **plaintext Telegram token** and is **gitignored** — never commit it. Use `config.example.yaml` as the template (copy to `config.yaml` locally). In production prefer env vars `TELEGRAM_BOT_TOKEN` / `TELEGRAM_CHAT_ID` (notifier reads env first).
- PTT requires `Cookie: over18=1` for HardwareSale; Ruten API only sends the `isnew` param when it is `"0"`/`"1"` (`"2"` = omitted).
- `scripts/run_crawler.sh` is the cron/systemd wrapper: flock prevents overlap, `TIMEOUT_SECONDS` (default 300) caps runtime, `.env` is sourced, dedupe state persists at `data/products.json` via config.

## Style

- Python 3, no type checking. Network calls always use a timeout and request delay (ptt `0.5s`, ruten `1.0s`) — do not remove the delays. Comments/logs/notifications are in English; Chinese literals in parsing code (title keywords, PTT board markers) must be kept as-is since real listing data is Chinese.
