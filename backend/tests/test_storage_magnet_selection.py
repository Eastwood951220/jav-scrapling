from app.modules.storage.tasks.router import _select_best_magnet


def test_select_best_magnet_accepts_parser_shaped_numeric_size():
    parser_magnets = [
        {
            "magnet": "magnet:?xt=urn:btih:small",
            "name": "SSIS-889-small.torrent",
            "size": 8960.0,
            "size_text": "8.75GB",
            "has_chinese_sub": False,
        },
        {
            "magnet": "magnet:?xt=urn:btih:subtitle",
            "name": "SSIS-889-C.torrent",
            "size": 2816.0,
            "size_text": "2.75GB",
            "has_chinese_sub": True,
        },
    ]

    assert _select_best_magnet(parser_magnets) == parser_magnets[1]


def test_select_best_magnet_keeps_legacy_string_size_behavior():
    legacy_magnets = [
        {
            "magnet": "magnet:?xt=urn:btih:small",
            "name": "SSIS-889-small.torrent",
            "size": "900 MB",
            "has_chinese_sub": False,
        },
        {
            "magnet": "magnet:?xt=urn:btih:large",
            "name": "SSIS-889-large.torrent",
            "size": "2.5 GB",
            "has_chinese_sub": False,
        },
    ]

    assert _select_best_magnet(legacy_magnets) == legacy_magnets[1]
