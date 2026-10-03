"""
Connectivity test — verify PTT / Ruten / Telegram / OpenRouter are reachable
"""
import os
import sys
import json
import requests
import yaml

def load_config(path=None):
    if path is None:
        path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
    with open(path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

def test_ptt(config):
    """Test PTT connectivity"""
    print("\n=== PTT test ===")
    boards = config.get("ptt", {}).get("boards", ["BuyTogether"])
    headers = {
        "Cookie": "over18=1",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36"
    }

    for board in boards:
        url = f"https://www.ptt.cc/bbs/{board}/index.html"
        try:
            r = requests.get(url, headers=headers, timeout=15)
            print(f"  [{board}] HTTP {r.status_code} — {len(r.text)} bytes")
            if r.status_code == 200:
                # Basic check for article list
                if "r-list-container" in r.text or "title" in r.text.lower():
                    print(f"  -> page content looks normal")
                else:
                    print(f"  -> ⚠️ page structure may have changed")
            elif r.status_code == 403:
                print(f"  -> ❌ access denied (check headers)")
            elif r.status_code == 404:
                print(f"  -> ❌ board does not exist, check board name")
        except requests.exceptions.Timeout:
            print(f"  [{board}] ❌ timeout")
        except Exception as e:
            print(f"  [{board}] ❌ error: {e}")

def test_ruten(config):
    """Test Ruten connectivity"""
    print("\n=== Ruten test ===")
    keyword = config.get("keywords", ["iPhone"])[0]

    url = "https://search.ruten.com.tw/search/s000.php"
    params = {
        "q": keyword,
        "sort": "prc/ac",
    }
    headers = {
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
    }

    try:
        r = requests.get(url, params=params, headers=headers, timeout=15)
        print(f"  HTTP {r.status_code} — {len(r.text)} bytes")
        if r.status_code == 200:
            # Check for product data
            if "rt-store-gold" in r.text or "search-result" in r.text or "class=\"rt" in r.text:
                print(f"  -> ✅ page content looks normal")
            elif "item" in r.text.lower():
                print(f"  -> ✅ page has product-related content")
            else:
                print(f"  -> ⚠️ page structure may have changed, parser needs review")
        elif r.status_code == 429:
            print(f"  -> ⚠️ rate limited (429), add delay or use a proxy")
        else:
            print(f"  -> ❌ response: {r.text[:200]}")
    except requests.exceptions.Timeout:
        print(f"  ❌ timeout")
    except Exception as e:
        print(f"  ❌ error: {e}")

def test_telegram(config):
    """Test Telegram bot"""
    print("\n=== Telegram test ===")
    token = config.get("telegram", {}).get("bot_token", "")
    chat_id = config.get("telegram", {}).get("chat_id", "")

    if not token or not chat_id:
        print("  ⚠️ token or chat_id not set, skipped")
        return

    url = f"https://api.telegram.org/bot{token}/getMe"
    try:
        r = requests.get(url, timeout=10)
        data = r.json()
        if data.get("ok"):
            bot_info = data.get("result", {})
            print(f"  -> ✅ bot name: @{bot_info.get('username', '?')}")
            print(f"  -> ✅ bot ID: {bot_info.get('id', '?')}")
        else:
            print(f"  -> ❌ invalid bot token: {data}")
    except Exception as e:
        print(f"  ❌ error: {e}")

    # Test sending a message
    print("\n  sending test message...")
    send_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": "🔔 Crawler test message — if you see this, notifications work!",
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(send_url, json=payload, timeout=10)
        data = r.json()
        if data.get("ok"):
            print(f"  -> ✅ message sent! check Telegram")
        else:
            print(f"  -> ❌ send failed: {data}")
    except Exception as e:
        print(f"  ❌ error: {e}")

def test_openrouter(config):
    """Test OpenRouter API"""
    print("\n=== OpenRouter AI test ===")
    api_key = config.get("openrouter", {}).get("api_key", "")
    model = config.get("openrouter", {}).get("model", "openrouter/auto")
    base_url = config.get("openrouter", {}).get("base_url", "https://openrouter.ai/api/v1")

    if not api_key:
        print("  ⚠️ API key not set, skipped")
        return

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly: OK"}
        ],
        "max_tokens": 10,
    }

    try:
        r = requests.post(f"{base_url}/chat/completions", headers=headers, json=payload, timeout=30)
        print(f"  HTTP {r.status_code}")
        if r.status_code == 200:
            data = r.json()
            reply = data.get("choices", [{}])[0].get("message", {}).get("content", "")
            print(f"  -> ✅ AI reply: {reply}")
        else:
            print(f"  -> ❌ response: {r.text[:300]}")
    except requests.exceptions.Timeout:
        print(f"  ❌ timeout")
    except Exception as e:
        print(f"  ❌ error: {e}")

if __name__ == "__main__":
    print("🔍 Starting connectivity test...")
    config = load_config()

    test_ptt(config)
    test_ruten(config)
    test_telegram(config)
    test_openrouter(config)

    print("\n✅ Test complete!")
