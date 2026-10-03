"""
PTT crawler module v3
Starts from index1.html, supports pagination
"""
import requests
import re
import time
import logging
from datetime import datetime
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PTTCrawler:
    BASE_URL = "https://www.ptt.cc"

    def __init__(self, config: dict):
        self.boards = config.get("ptt", {}).get("boards", ["HardwareSale"])
        self.delay = config.get("ptt", {}).get("request_delay", 0.5)
        self.max_pages = config.get("ptt", {}).get("max_pages", 3)
        self.session = requests.Session()
        self.session.headers.update({
            "Cookie": "over18=1",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-TW,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
        })

    def _fetch_page(self, board: str, page: int) -> str:
        """Fetch the HTML of the given page"""
        if page == 0:
            url = f"{self.BASE_URL}/bbs/{board}/index.html"
        else:
            url = f"{self.BASE_URL}/bbs/{board}/index{page}.html"
        try:
            r = self.session.get(url, timeout=15)
            if r.status_code == 200:
                return r.text
        except Exception as e:
            logger.debug(f"PTT [{board}] page {page} failed: {e}")
        return ""

    def _extract_articles(self, html: str, board: str) -> List[dict]:
        """Extract articles from HTML (excluding announcements)"""
        articles = []
        title_pattern = re.compile(
            r'<div class="title">\s*<a href="(/bbs/[^"]+)">([^<]+)</a>',
            re.DOTALL
        )
        date_pattern = re.compile(r'<div class="date">([^<]+)</div>')
        author_pattern = re.compile(r'<div class="author">([^<]+)</div>')

        titles = title_pattern.findall(html)
        dates = date_pattern.findall(html)
        authors = author_pattern.findall(html)

        for i, (href, title) in enumerate(titles):
            title = title.strip()
            if not title or "(已被刪除)" in title:
                continue
            # Exclude announcements, discussions, scams, apologies, questions, etc.
            skip_prefixes = ["[公告]", "[討論]", "[詐騙]", "[道歉]", "[問題]", "[建議]", "[心得]", "Re:"]
            if any(title.startswith(p) for p in skip_prefixes):
                continue
            articles.append({
                "title": title,
                "url": f"{self.BASE_URL}{href}",
                "date": dates[i].strip() if i < len(dates) else "",
                "author": authors[i].strip() if i < len(authors) else "",
                "board": board,
            })
        return articles

    def _get_next_page(self, html: str, board: str) -> int:
        """Find the previous-page index"""
        m = re.search(rf'<a[^>]*href="/bbs/{board}/index(\d+)\.html"[^>]*>‹ 上頁', html)
        if m:
            return int(m.group(1))
        return -1

    @staticmethod
    def _extract_price(title: str) -> float:
        patterns = [
            r'[\$$]\s*([\d,]+)',
            r'(?:售|讓|賣|價格|price)[\s::]*[\$$]?\s*([\d,]+)',
            r'(?:只要|僅|最低)\s*[\$$]?\s*([\d,]+)',
        ]
        for pat in patterns:
            m = re.search(pat, title, re.IGNORECASE)
            if m:
                try:
                    price = float(m.group(1).replace(",", ""))
                    if 50 <= price <= 999999:
                        return price
                except ValueError:
                    continue
        return 0

    @staticmethod
    def _guess_condition(title: str) -> str:
        t = title.lower()
        if any(k in t for k in ["二手", "used", "二手品", "9成", "8成", "7成"]):
            return "used"
        if any(k in t for k in ["全新", "new", "新品", "未開", "未使用", "未拆", "密封"]):
            return "new"
        return "unknown"

    def _is_recent(self, date_str: str, days: int = 2) -> bool:
        """Whether the article date is within the last N days (PTT date format: M/D)"""
        if not date_str:
            return True  # keep if no date
        try:
            parts = date_str.strip().split("/")
            if len(parts) != 2:
                return True
            month, day = int(parts[0]), int(parts[1])
            now = datetime.now()
            # Handle year boundary: a month later than now means last year
            if month > now.month:
                article_date = now.replace(year=now.year - 1, month=month, day=day)
            else:
                article_date = now.replace(month=month, day=day)
            delta = now - article_date
            return delta.days <= days
        except (ValueError, AttributeError):
            return True

    def search(self, keyword: str) -> List[Dict[str, Any]]:
        results = []
        kw_lower = keyword.lower()

        for board in self.boards:
            page = 0  # start from index.html (latest)
            pages_checked = 0
            empty_count = 0

            while pages_checked < self.max_pages and empty_count < 3:
                html = self._fetch_page(board, page)
                if not html:
                    empty_count += 1
                    page += 1
                    continue

                articles = self._extract_articles(html, board)
                if not articles:
                    empty_count += 1
                    page += 1
                    continue

                for art in articles:
                    # Date filter: keep only last 2 days
                    if not self._is_recent(art["date"], days=2):
                        continue
                    title = art["title"]
                    if kw_lower in title.lower():
                        price = self._extract_price(title)
                        results.append({
                            "source": "ptt",
                            "keyword": keyword,
                            "title": title,
                            "price": price,
                            "url": art["url"],
                            "author": art["author"],
                            "date": art["date"],
                            "board": board,
                            "condition": self._guess_condition(title),
                        })

                pages_checked += 1
                page += 1
                time.sleep(self.delay)

        logger.info(f"PTT [{keyword}] {len(results)} posts")
        return results

    def search_all(self, keywords: list = None) -> List[Dict[str, Any]]:
        """Search all boards. With keywords -> filter; without -> keep all (excluding announcements)"""
        all_items = []

        if keywords:
            # With keywords: filter by keyword
            for kw in keywords:
                items = self.search(kw)
                all_items.extend(items)
        else:
            # No keywords: iterate all boards, latest first
            for board in self.boards:
                page = 0  # index.html = latest page
                pages_checked = 0
                while pages_checked < self.max_pages:
                    html = self._fetch_page(board, page)
                    if not html:
                        break
                    articles = self._extract_articles(html, board)
                    if not articles:
                        break
                    # If this whole page is too old, stop paginating
                    page_has_recent = False
                    for art in articles:
                        if self._is_recent(art["date"], days=2):
                            page_has_recent = True
                        price = self._extract_price(art["title"])
                        all_items.append({
                            "source": "ptt",
                            "keyword": "",
                            "title": art["title"],
                            "price": price,
                            "url": art["url"],
                            "author": art["author"],
                            "date": art["date"],
                            "board": board,
                            "condition": self._guess_condition(art["title"]),
                        })
                    if not page_has_recent:
                        break  # whole page too old, older ones follow
                    pages_checked += 1
                    page += 1
                    time.sleep(self.delay)

        logger.info(f"PTT total: {len(all_items)} posts")
        return all_items


if __name__ == "__main__":
    import os, yaml
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    _cfg = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "config.yaml")
    with open(_cfg, "r") as f:
        config = yaml.safe_load(f)
    crawler = PTTCrawler(config)
    results = crawler.search_all(config.get("keywords", ["RTX", "iPhone"]))
    print(f"\nPTT: {len(results)} posts")
    for r in results[:10]:
        ps = f"${r['price']:,.0f}" if r['price'] > 0 else "no price"
        print(f"  {ps:>12} | {r['title'][:60]}")
