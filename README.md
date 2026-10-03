# Product Crawler

Multi-platform product crawler: fetches listings from **Ruten（露天）** and **PTT (HardwareSale)**, filters out overpriced items, and sends **Telegram** notifications.

## Features

- **Ruten crawler** — search by category, new/used filter
- **PTT crawler** — scrape PTT HardwareSale board posts, parse listing info
- **AI analysis (optional)** — score value-for-money via the OpenRouter API
- **Telegram notifications** — instant alerts for new listings / low prices
- **CPU temperature logging** — append to a JSONL log

## Install

```bash
pip install -r requirements.txt
```

## Usage

### Run the crawler

```bash
python crawler.py
```

### Dry run (no notifications)

```bash
python crawler.py --dry-run
```

### Custom config file

```bash
python crawler.py --config /path/to/config.yaml
```

### Connectivity test

```bash
python test_connection.py
```

### CPU temperature logging

```bash
python check_cpu_temp.py
```

## Config

Edit `config.yaml`:

| Parameter | Description |
|------|------|
| `notify.max_items` | Max items per notification |
| `notify.condition` | Condition filter (all / new / used) |
| `max_price` | Price cap |
| `telegram` | Telegram bot token and chat ID |
| `ptt` | PTT boards, keywords, max pages |
| `ruten` | Ruten category IDs, new/used filter |
| `openrouter` | (optional) AI analysis API settings |

## Project layout

```
crawler/
├── config.yaml            # config
├── crawler.py             # main program
├── analyzer.py            # AI price analysis
├── notifier.py            # Telegram notification
├── check_cpu_temp.py      # CPU temperature logger
├── test_connection.py     # connectivity test
├── requirements.txt
└── sites/
    ├── ptt.py             # PTT crawler
    └── ruten.py           # Ruten crawler
```
