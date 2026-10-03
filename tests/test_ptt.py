from datetime import datetime

from sites.ptt import PTTCrawler


def test_extract_price_dollar():
    assert PTTCrawler._extract_price("[賣] RTX 4070 $15000") == 15000


def test_extract_price_with_commas():
    assert PTTCrawler._extract_price("iPhone 15, $32,000") == 32000


def test_extract_price_售字():
    assert PTTCrawler._extract_price("[出售] 筆電 售 25000") == 25000


def test_extract_price_out_of_range():
    assert PTTCrawler._extract_price("$10") == 0
    assert PTTCrawler._extract_price("no price here") == 0


def test_guess_condition():
    assert PTTCrawler._guess_condition("二手 RTX 3060") == "used"
    assert PTTCrawler._guess_condition("全新未拆 Switch") == "new"
    assert PTTCrawler._guess_condition("some title") == "unknown"


_crawler = PTTCrawler({"ptt": {}})

def test_is_recent_today():
    today = datetime.now().strftime("%-m/%-d")
    assert _crawler._is_recent(today, days=2) is True


def test_is_recent_bad_input_keeps():
    assert _crawler._is_recent("", days=2) is True
    assert _crawler._is_recent("garbage", days=2) is True


def test_extract_articles_filters_non_sale():
    html = '''
    <div class="title"><a href="/bbs/HardwareSale/M.1.html">[賣] GPU</a></div>
    <div class="date">10/01</div>
    <div class="author">user1</div>
    <div class="title"><a href="/bbs/HardwareSale/M.2.html">[公告] board rules</a></div>
    <div class="date">10/01</div>
    <div class="author">admin</div>
    <div class="title">(已被刪除)</div>
    '''
    articles = PTTCrawler({"ptt": {}})._extract_articles(html, "HardwareSale")
    assert len(articles) == 1
    assert articles[0]["title"] == "[賣] GPU"
    assert articles[0]["board"] == "HardwareSale"
