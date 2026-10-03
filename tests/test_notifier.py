from notifier import TelegramNotifier


def _notifier():
    return TelegramNotifier({"telegram": {"bot_token": "t", "chat_id": "c"}, "notify": {"max_items": 10}})


def test_format_message_contains_title_and_price():
    items = [{
        "source": "ruten", "title": "RTX 4070", "price": 15000,
        "url": "http://x", "condition": "new", "ai_score": 0, "ai_reason": "",
    }]
    msg = _notifier()._format_message(items, title="New")
    assert "New" in msg
    assert "RTX 4070" in msg
    assert "$15,000" in msg
    assert "http://x" in msg


def test_format_message_no_price():
    items = [{"source": "ptt", "title": "t", "price": 0, "url": "", "condition": "used"}]
    msg = _notifier()._format_message(items)
    assert "no price" in msg


def test_format_message_high_score_shows_reason():
    items = [{"source": "ptt", "title": "t", "price": 100, "url": "", "condition": "new", "ai_score": 9, "ai_reason": "great"}]
    msg = _notifier()._format_message(items)
    assert "Score: 9/10" in msg
    assert "great" in msg


def test_env_overrides_config(monkeypatch):
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "env_token")
    monkeypatch.setenv("TELEGRAM_CHAT_ID", "env_chat")
    n = TelegramNotifier({"telegram": {"bot_token": "cfg", "chat_id": "cfg"}})
    assert n.bot_token == "env_token"
    assert n.chat_id == "env_chat"
