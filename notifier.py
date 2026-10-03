"""Telegram notification module"""
import os
import requests
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class TelegramNotifier:
    def __init__(self, config: dict):
        # Prefer env vars, fall back to config.yaml
        self.bot_token = os.environ.get("TELEGRAM_BOT_TOKEN") or config.get("telegram", {}).get("bot_token", "") or config.get("telegram", {}).get("token", "")
        self.chat_id = os.environ.get("TELEGRAM_CHAT_ID") or config.get("telegram", {}).get("chat_id", "")
        self.max_items = config.get("notify", {}).get("max_items", 10)

    def send(self, recommendations: List[Dict[str, Any]]):
        """Send recommended-item notification"""
        if not recommendations:
            logger.info("No recommendations, skipping notification")
            return

        top_items = recommendations[:self.max_items]
        message = self._format_message(top_items)

        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": message,
            # "parse_mode": "HTML",
            "disable_web_page_preview": False,
        }

        try:
            r = requests.post(url, json=payload, timeout=15)
            if r.status_code == 200 and r.json().get("ok"):
                logger.info(f"Telegram notification sent ({len(top_items)} items)")
            else:
                logger.error(f"Telegram send failed: {r.json()}")
        except Exception as e:
            logger.error(f"Telegram send error: {e}")

    def send_new(self, new_products: List[Dict[str, Any]]):
        """Send new-listing notification (batched)"""
        if not new_products:
            return

        # Telegram message limit is 4096 chars; send in batches
        batch_size = self.max_items
        for i in range(0, len(new_products), batch_size):
            batch = new_products[i:i+batch_size]
            title = f"🆕 New listings ({i+1}~{i+len(batch)}/{len(new_products)})"
            message = self._format_message(batch, title=title)

            url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": message,
                # "parse_mode": "HTML",
            }

            try:
                r = requests.post(url, json=payload, timeout=15)
                if r.status_code == 200 and r.json().get("ok"):
                    logger.info(f"Telegram sent successfully ({i+1}~{i+len(batch)}/{len(new_products)})")
                else:
                    logger.error(f"Telegram send failed: {r.json()}")
            except Exception as e:
                logger.error(f"Telegram send error: {e}")

    def _format_message(self, items: List[Dict[str, Any]], title: str = "🔥 Low-price deals") -> str:
        """Format message (plain text)"""
        lines = [
            f"{title}",
            f"{len(items)} items\n",
        ]

        for i, item in enumerate(items, 1):
            source_emoji = {"ptt": "📌", "ruten": "🛒"}.get(item.get("source", ""), "📦")
            score = item.get("ai_score", 0)
            price = item.get("price", 0)
            price_str = f"${price:,.0f}" if price > 0 else "no price"
            reason = item.get("ai_reason", "")
            title_text = item.get("title", "")[:60]
            url = item.get("url", "")
            cond = {"new": "new", "used": "used"}.get(item.get("condition", ""), "")

            lines.append(f"{source_emoji} {title_text}")
            lines.append(f"   💰 {price_str} {f'| {cond}' if cond else ''}")
            if score >= 7:
                lines.append(f"   ⭐ Score: {score}/10 — {reason}")
            if url:
                lines.append(f"   🔗 {url}")
            lines.append("")

        return "\n".join(lines)

    def send_test(self):
        """Send a test message"""
        url = f"https://api.telegram.org/bot{self.bot_token}/sendMessage"
        payload = {
            "chat_id": self.chat_id,
            "text": "✅ Crawler test — Telegram notification is working!",
            # "parse_mode": "HTML",
        }
        try:
            r = requests.post(url, json=payload, timeout=10)
            return r.status_code == 200 and r.json().get("ok")
        except Exception:
            return False
