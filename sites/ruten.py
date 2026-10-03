"""
Ruten (露天市集) crawler module v6
- Uses the search/v4 API (supports isnew parameter)
- Uses the prod/v3 API for product details
"""
import requests
import time
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

SEARCH_URL = "https://rtapi.ruten.com.tw/api/search/v4/index.php/core/prod"
PROD_URL = "https://rtapi.ruten.com.tw/api/prod/v3/index.php/prod"


class RutenCrawler:
    def __init__(self, config: dict):
        self.limit = config.get("ruten", {}).get("limit", 50)
        self.delay = config.get("ruten", {}).get("request_delay", 1.0)
        self.categories = config.get("ruten", {}).get("categories", ["00110001"])
        # isnew: 0=all, 1=new, 2=used, ""=not specified (default all)
        self.isnew = config.get("ruten", {}).get("isnew", "2")
        self.condition = config.get("notify", {}).get("condition", "all")
        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/26.3.1 Safari/605.1.15",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "identity",
            "Referer": "https://www.ruten.com.tw/",
        })

    def _search_ids(self, cate_id: str) -> List[str]:
        """Search product IDs via search/v4"""
        params = {
            "location": "tw",
            "type": "direct",
            "cateid": cate_id,
            "sort": "new/dc",
            "offset": 1,
            "limit": min(self.limit, 100),
        }
        # Only add isnew when 0 or 1
        if self.isnew in ("0", "1"):
            params["isnew"] = self.isnew

        try:
            r = self.session.get(SEARCH_URL, params=params, timeout=15)
            if r.status_code != 200:
                logger.warning(f"search/v4 [{cate_id}] HTTP {r.status_code}")
                return []
            data = r.json()
            rows = data.get("Rows", [])
            ids = [row["Id"] for row in rows if row.get("Id")]
            logger.info(f"search/v4 [{cate_id}]: {len(ids)} IDs")
            return ids
        except Exception as e:
            logger.error(f"search/v4 [{cate_id}] failed: {e}")
            return []

    def _get_products(self, ids: List[str]) -> List[Dict[str, Any]]:
        """Fetch product details via prod/v3"""
        if not ids:
            return []

        # At most 100 per request
        all_products = []
        for i in range(0, len(ids), 100):
            batch = ids[i:i+100]
            id_str = ",".join(batch)
            params = {"id": id_str}
            if self.isnew in ("0", "1", "2"):
                params["isnew"] = self.isnew

            try:
                r = self.session.get(PROD_URL, params=params, timeout=15)
                if r.status_code != 200:
                    continue
                items = r.json()
                if isinstance(items, list):
                    all_products.extend(items)
                time.sleep(self.delay)
            except Exception as e:
                logger.error(f"prod/v3 failed: {e}")

        return all_products

    def _parse_product(self, p: dict, cate_id: str) -> Dict[str, Any]:
        name = p.get("ProdName", "")
        price_range = p.get("PriceRange", [0, 0])
        price = price_range[0] if price_range else 0
        price_max = price_range[1] if len(price_range) > 1 else price
        prod_id = p.get("ProdId", "")
        seller_id = p.get("SellerId", "")
        image = p.get("Image", "")
        sold = p.get("SoldQty", 0)
        stock = p.get("StockQty", 0)
        post_time = p.get("PostTime", "")

        if not name or price <= 0:
            return None

        # Detect used items
        is_used = any(kw in name for kw in ["二手", "二手品", "used", "USED", "9成", "8成", "7成", "中古", "舊", "讓售", "讓出"])

        return {
            "source": "ruten",
            "title": name,
            "keyword": name,
            "price": price,
            "price_max": price_max,
            "url": f"https://www.ruten.com.tw/item/show?{prod_id}" if prod_id else "",
            "prod_id": prod_id,
            "seller_id": seller_id,
            "image": image,
            "sold_count": sold,
            "stock": stock,
            "post_time": post_time,
            "cate_id": cate_id,
            "condition": "used" if is_used else "new",
        }

    def search_category(self, cate_id: str) -> List[Dict[str, Any]]:
        """Search one category"""
        ids = self._search_ids(cate_id)
        if not ids:
            return []
        raw_products = self._get_products(ids)
        results = []
        for p in raw_products:
            parsed = self._parse_product(p, cate_id)
            if parsed:
                # If notify.condition is used, keep only used items
                if self.condition == "used" and parsed["condition"] != "used":
                    continue
                results.append(parsed)
        logger.info(f"Ruten [{cate_id}]: {len(results)} items")
        return results

    def search_all(self, keywords=None) -> List[Dict[str, Any]]:
        all_items = []
        seen = set()
        for cate_id in self.categories:
            items = self.search_category(cate_id)
            for item in items:
                pid = item.get("prod_id", "")
                if pid and pid not in seen:
                    seen.add(pid)
                    all_items.append(item)
            time.sleep(self.delay)
        logger.info(f"Ruten total: {len(all_items)} items")
        return all_items


if __name__ == "__main__":
    import os, yaml
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    with open(_cfg, "r") as f:
        config = yaml.safe_load(f)
    crawler = RutenCrawler(config)
    results = crawler.search_all()
    print(f"\nRuten: {len(results)} items")
    for r in results[:10]:
        cond = "used" if r["condition"] == "used" else "new"
        print(f"  ${r['price']:>10,} | {cond} | {r['title'][:55]}")
