import json
import os
from datetime import datetime, timedelta

from crawler import find_new_products, _normalize_time


def _history(tmp_path, seen):
    p = tmp_path / "products.json"
    p.write_text(json.dumps({"seen": seen}), encoding="utf-8")
    return str(p)


def test_normalize_time_ruten_format():
    assert _normalize_time("2026/05/24 01:49:54") == "2026-05-24T01:49:54"


def test_normalize_time_ptt_format():
    out = _normalize_time("5/24")
    assert out is not None and out.endswith("T00:00:00")


def test_normalize_time_garbage():
    assert _normalize_time("not a time") is None
    assert _normalize_time("") is None
    assert _normalize_time(None) is None


def test_find_new_products_detects_new(tmp_path):
    today = datetime.now().strftime("%Y-%m-%d")
    history = _history(tmp_path, {"ruten:123": today})
    products = [
        {"source": "ruten", "prod_id": "123", "title": "old", "url": "u1"},
        {"source": "ruten", "prod_id": "456", "title": "new", "url": "u2"},
    ]
    new = find_new_products(products, history)
    assert [p["prod_id"] for p in new] == ["456"]


def test_find_new_products_updates_history(tmp_path):
    history = _history(tmp_path, {})
    products = [{"source": "ptt", "url": "https://x/1", "title": "t"}]
    find_new_products(products, history)
    data = json.loads(open(history, encoding="utf-8").read())
    assert len(data["seen"]) == 1


def test_find_new_products_cleans_old(tmp_path):
    old_date = (datetime.now() - timedelta(days=10)).strftime("%Y-%m-%d")
    history = _history(tmp_path, {"ruten:123": old_date})
    products = [{"source": "ruten", "prod_id": "123", "title": "t", "url": "u"}]
    # old record was cleaned, so the product counts as new again
    new = find_new_products(products, history)
    assert len(new) == 1


def test_find_new_products_bad_history_recovers(tmp_path):
    p = tmp_path / "products.json"
    p.write_text("{not json", encoding="utf-8")
    products = [{"source": "ruten", "prod_id": "1", "title": "t", "url": "u"}]
    new = find_new_products(products, str(p))
    assert len(new) == 1


def test_find_new_products_legacy_list_format(tmp_path):
    p = tmp_path / "products.json"
    p.write_text(json.dumps(["ruten:123"]), encoding="utf-8")
    products = [{"source": "ruten", "prod_id": "123", "title": "t", "url": "u"}]
    new = find_new_products(products, str(p))
    assert new == []
