import json

from cookies.cookie_manager import CookieManager


def test_cookie_manager_load_dict(tmp_path, monkeypatch):
    cookie_dir = tmp_path / "cookies"
    cookie_dir.mkdir()

    filepath = cookie_dir / "test.json"
    filepath.write_text(
        json.dumps({"a": "1"}, ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr("cookies.cookie_manager.COOKIE_DIR", cookie_dir)

    manager = CookieManager("test.json")

    assert manager.load() == {"a": "1"}


def test_cookie_manager_load_list(tmp_path, monkeypatch):
    cookie_dir = tmp_path / "cookies"
    cookie_dir.mkdir()

    filepath = cookie_dir / "test.json"
    filepath.write_text(
        json.dumps([{"name": "a", "value": "1"}], ensure_ascii=False),
        encoding="utf-8",
    )

    monkeypatch.setattr("cookies.cookie_manager.COOKIE_DIR", cookie_dir)

    manager = CookieManager("test.json")

    assert manager.load() == {"a": "1"}
