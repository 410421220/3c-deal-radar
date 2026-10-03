"""
AI price-analysis module
Uses the OpenRouter API to judge whether items are underpriced
"""
import requests
import json
import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class PriceAnalyzer:
    def __init__(self, config: dict):
        self.api_key = config.get("openrouter", {}).get("api_key", "")
        self.model = config.get("openrouter", {}).get("model", "openrouter/auto")
        self.base_url = config.get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1")
        self.max_price = config.get("max_price", 999999)
        self.min_score = config.get("notify", {}).get("min_score", 7)

    def analyze(self, products: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Analyze product list, mark recommended ones"""
        if not products:
            return []

        # Drop overpriced or price-less items
        candidates = [p for p in products if 0 < p.get("price", 0) <= self.max_price]

        if not candidates:
            logger.info("No products within the price range")
            return []

        # Batch to AI (10 per batch)
        batch_size = 10
        for i in range(0, len(candidates), batch_size):
            batch = candidates[i:i + batch_size]
            self._analyze_batch(batch)

        # Keep recommended ones
        recommendations = [p for p in candidates if p.get("ai_score", 0) >= self.min_score]
        recommendations.sort(key=lambda x: x.get("ai_score", 0), reverse=True)

        logger.info(f"AI analysis done: {len(recommendations)} recommended out of {len(candidates)}")
        return recommendations

    def _analyze_batch(self, batch: List[Dict[str, Any]]):
        """Send one batch of products to AI for analysis"""
        items_text = []
        for i, p in enumerate(batch, 1):
            price_str = f"${p['price']:,.0f}" if p['price'] > 0 else "no price"
            source = p.get("source", "?")
            title = p.get("title", "")[:80]
            cond = p.get("condition", "unknown")
            cond_str = {"new": "new", "used": "used", "unknown": "unknown"}.get(cond, cond)
            items_text.append(f"{i}. [{source}] {title} | price: {price_str} | condition: {cond_str}")

        prompt = f"""Below are items scraped from PTT, Ruten, etc. Analyze which are underpriced and worth buying.

Items:
{chr(10).join(items_text)}

Tasks:
1. Give each item a score (1-10): 10 = strongly recommend (well below market price), 1 = do not recommend
2. Brief reason (under 15 words)
3. Format: JSON array, each item has index, score, reason

Notes:
- Consider brand, specs, condition, and market price
- Suspiciously cheap items may be scams or defective — deduct points
- Return only the JSON array, no other text"""

        try:
            r = requests.post(
                f"{self.base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [{"role": "user", "content": prompt}],
                    "max_tokens": 1000,
                },
                timeout=60,
            )

            if r.status_code != 200:
                logger.error(f"AI API error: HTTP {r.status_code} — {r.text[:200]}")
                return

            data = r.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")

            # Parse the JSON in the AI reply
            results = self._parse_ai_response(reply)
            score_map = {r["index"]: r for r in results}

            for p in batch:
                idx = batch.index(p) + 1
                if idx in score_map:
                    p["ai_score"] = score_map[idx].get("score", 0)
                    p["ai_reason"] = score_map[idx].get("reason", "")
                else:
                    p["ai_score"] = 0
                    p["ai_reason"] = ""

        except requests.exceptions.Timeout:
            logger.error("AI API timeout")
        except Exception as e:
            logger.error(f"AI analysis failed: {e}")

    def _parse_ai_response(self, text: str) -> list:
        """Parse the JSON array from the AI reply"""
        try:
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                return json.loads(text[start:end])
        except json.JSONDecodeError:
            pass

        # fallback: parse line by line
        results = []
        for line in text.split("\n"):
            line = line.strip()
            if '"index"' in line and '"score"' in line:
                try:
                    obj = json.loads(line.rstrip(","))
                    results.append(obj)
                except json.JSONDecodeError:
                    pass
        return results
