from sites.ruten import RutenCrawler


def _crawler():
    return RutenCrawler({"ruten": {}, "notify": {}})


def test_parse_product_basic():
    p = {
        "ProdName": "RTX 4070 全新",
        "PriceRange": [15000, 16000],
        "ProdId": "abc123",
        "SellerId": "seller1",
        "Image": "img",
        "SoldQty": 3,
        "StockQty": 5,
        "PostTime": "2026/10/01 10:00:00",
    }
    parsed = _crawler()._parse_product(p, "00110031")
    assert parsed["source"] == "ruten"
    assert parsed["price"] == 15000
    assert parsed["price_max"] == 16000
    assert parsed["condition"] == "new"
    assert parsed["prod_id"] == "abc123"


def test_parse_product_used_keyword():
    p = {"ProdName": "二手 iPhone 13", "PriceRange": [10000, 10000], "ProdId": "x"}
    parsed = _crawler()._parse_product(p, "00110013")
    assert parsed["condition"] == "used"


def test_parse_product_skips_invalid():
    assert _crawler()._parse_product({"ProdName": "", "PriceRange": [100]}, "x") is None
    assert _crawler()._parse_product({"ProdName": "t", "PriceRange": [0, 0]}, "x") is None


def test_condition_filter_used_only():
    c = RutenCrawler({"ruten": {"categories": []}, "notify": {"condition": "used"}})
    assert c.condition == "used"
