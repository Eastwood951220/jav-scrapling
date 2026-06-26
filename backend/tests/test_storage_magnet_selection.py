from app.modules.storage.tasks.router import _select_best_magnet


def test_select_best_magnet_prefers_chinese_subtitle_over_larger_non_subtitle():
    selected = _select_best_magnet(
        [
            {
                "magnet": "magnet:?xt=urn:btih:large",
                "name": "SSIS-889-4k.torrent",
                "size": 29573.12,
                "size_text": "28.88GB",
                "tags": ["高清"],
                "has_chinese_sub": False,
            },
            {
                "magnet": "magnet:?xt=urn:btih:sub",
                "name": "SSIS-889-C.torrent",
                "size": 8960.0,
                "size_text": "8.75GB",
                "tags": ["高清", "字幕"],
                "has_chinese_sub": True,
            },
        ]
    )

    assert selected["magnet"] == "magnet:?xt=urn:btih:sub"


def test_select_best_magnet_supports_legacy_string_size_and_magnet_url_field():
    selected = _select_best_magnet(
        [
            {
                "magnet_url": "magnet:?xt=urn:btih:small",
                "title": "small",
                "size": "900MB",
            },
            {
                "magnet_url": "magnet:?xt=urn:btih:big",
                "title": "big",
                "size": "2.5GB",
            },
        ]
    )

    assert selected["magnet_url"] == "magnet:?xt=urn:btih:big"
