from scraper.core.security import is_security_check_page


class FakePage:
    text = "Verify you are human"


def test_is_security_check_page():
    assert is_security_check_page(FakePage()) is True


def test_is_security_check_page_false():
    class NormalPage:
        text = "normal movie page"

    assert is_security_check_page(NormalPage()) is False
