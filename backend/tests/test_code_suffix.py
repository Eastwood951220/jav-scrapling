def test_derive_code_suffix_chinese_sub():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix
    assert derive_code_suffix(has_chinese_sub=True, tags=[]) == "-C"


def test_derive_code_suffix_uncensored():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix
    assert derive_code_suffix(has_chinese_sub=False, tags=["破解"]) == "-U"


def test_derive_code_suffix_both():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix
    assert derive_code_suffix(has_chinese_sub=True, tags=["破解", "中文字幕"]) == "-UC"


def test_derive_code_suffix_none():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix
    assert derive_code_suffix(has_chinese_sub=False, tags=[]) == ""


def test_derive_code_suffix_uncensored_from_tags():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix
    assert derive_code_suffix(has_chinese_sub=False, tags=["无码破解"]) == "-U"


def test_derive_code_suffix_from_filename():
    from backend.app.modules.storage.domain.filename_policy import derive_code_suffix_from_filename
    assert derive_code_suffix_from_filename("SSIS-978-C.mp4") == "-C"
    assert derive_code_suffix_from_filename("SSIS-978-U.mp4") == "-U"
    assert derive_code_suffix_from_filename("SSIS-978-UC.mp4") == "-UC"
    assert derive_code_suffix_from_filename("SSIS-978.mp4") == ""
    assert derive_code_suffix_from_filename("SSIS-978-C") == "-C"
