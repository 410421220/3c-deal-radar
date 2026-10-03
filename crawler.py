"""
Product crawler main program v4
- Ruten: uses config.ruten.categories + isnew parameter
- PTT: requires config.ptt.keywords to fetch
- Notify on newly listed products
"""
import sys, os, json, logging
from datetime import datetime, timedelta
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sites.ruten import RutenCrawler
from sites.ptt import PTTCrawler
from notifier import TelegramNotifier


def load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)


def setup_logging(config):
    log_file = config.get("data", {}).get("log_file", "logs/crawler.log")
    os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=[logging.FileHandler(log_file, encoding="utf-8"), logging.StreamHandler()],
    )


def _normalize_time(time_str):
    """Normalize various time formats to ISO format"""
    if not time_str:
        return None
    # Try Ruten format: 2026/05/24 01:49:54
    try:
        dt = datetime.strptime(time_str, "%Y/%m/%d %H:%M:%S")
        return dt.isoformat()
    except (ValueError, TypeError):
        pass
    # Try PTT format: 5/24 (assume current year)
    try:
        dt = datetime.strptime(time_str, "%m/%d")
        dt = dt.replace(year=datetime.now().year)
        return dt.isoformat()
    except (ValueError, TypeError):
        pass
    return None


def find_new_products(current_products, history_file, max_days: int = 3):
    """Dedupe by ID to detect new products; auto-clean records older than N days"""
    os.makedirs(os.path.dirname(history_file) or ".", exist_ok=True)

    # Load already-sent IDs (format: {"seen": {"id": "2026-05-24"}, ...})
    seen = {}
    if os.path.exists(history_file):
        try:
            with open(history_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                # Support both legacy (list) and new (dict) formats
                if isinstance(data, dict):
                    seen = data.get("seen", {})
                elif isinstance(data, list):
                    # Migrate legacy format: mark everything as today
                    today = datetime.now().strftime("%Y-%m-%d")
                    seen = {pid: today for pid in data}
        except (ValueError, TypeError, OSError):
            seen = {}

    # Clean records older than max_days (safe-parse; drop bad dates)
    cutoff = datetime.now() - timedelta(days=max_days)
    cleaned = {}
    for pid, date_str in seen.items():
        try:
            d = datetime.strptime(date_str, "%Y-%m-%d")
            if d >= cutoff:
                cleaned[pid] = date_str
        except (ValueError, TypeError):
            pass  # bad date format -> drop, avoid later strptime crashes
    seen = cleaned

    def make_id(p):
        source = p.get("source", "")
        # Use a stable unique key so title edits don't cause duplicates
        if source == "ruten":
            pid = p.get("prod_id", "")
            if pid:
                return f"ruten:{pid}"
        # fallback: PTT uses url, others use url+title
        url = p.get("url", "")
        title = p.get("title", "")[:50]
        return f"{source}:{url}:{title}"

    new_products = []
    today = datetime.now().strftime("%Y-%m-%d")
    for p in current_products:
        pid = make_id(p)
        if pid not in seen:
            new_products.append(p)
            seen[pid] = today

    # Persist (keep at most 5000 entries)
    if len(seen) > 5000:
        # Sort by date, keep newest
        sorted_ids = sorted(seen.items(), key=lambda x: x[1], reverse=True)
        seen = dict(sorted_ids[:5000])

    with open(history_file, "w", encoding="utf-8") as f:
        json.dump({"seen": seen}, f, ensure_ascii=False)

    return new_products


def run(config, dry_run=False):
    logger = logging.getLogger(__name__)
    max_price = config.get("max_price", 999999)
    all_products = []

    # 1. Ruten
    try:
        ruten = RutenCrawler(config)
        ruten_results = ruten.search_all()
        logger.info(f"Ruten: {len(ruten_results)} items")
        all_products.extend(ruten_results)
    except Exception as e:
        logger.error(f"Ruten failed: {e}")

    # 2. PTT (requires config.ptt.keywords)
    ptt_keywords = config.get("ptt", {}).get("keywords", [])
    if ptt_keywords:
        try:
            ptt = PTTCrawler(config)
            ptt_results = ptt.search_all(ptt_keywords)
            logger.info(f"PTT: {len(ptt_results)} posts")
            all_products.extend(ptt_results)
        except Exception as e:
            logger.error(f"PTT failed: {e}")
    else:
        logger.info("PTT: no keywords set, skipped")

    logger.info(f"Total fetched: {len(all_products)}")

    if not all_products:
        return

    # 3. Price filter (Ruten only; PTT is kept unfiltered)
    filtered = []
    for p in all_products:
        price = p.get("price", 0)
        source = p.get("source", "")
        if source == "ptt":
            # PTT is not price-filtered
            filtered.append(p)
        elif 0 < price <= max_price:
            # Ruten is price-filtered
            filtered.append(p)
    logger.info(f"After price filter: {len(filtered)}")

    # 4. New-product comparison
    history_file = config.get("data", {}).get("products_file", "data/products.json")
    new_products = find_new_products(filtered, history_file)
    logger.info(f"New products: {len(new_products)}")

    if not new_products:
        logger.info("No new products")
        return

    # 5. Send Telegram
    if not dry_run:
        try:
            notifier = TelegramNotifier(config)
            notifier.send_new(new_products)
            logger.info(f"✅ Telegram sent ({len(new_products)} items)")
        except Exception as e:
            logger.error(f"Telegram failed: {e}")
    else:
        logger.info(f"DRY RUN: {len(new_products)} new products")


def main():
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=None)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    config = load_config(args.config)
    setup_logging(config)
    run(config, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
