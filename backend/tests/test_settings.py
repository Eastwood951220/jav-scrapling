def test_batch_save_size_in_settings_keys():
    from app.api.settings import SETTING_KEYS
    assert "BATCH_SAVE_SIZE" in SETTING_KEYS


def test_batch_save_size_in_setting_update():
    from app.models.setting import SettingUpdate
    s = SettingUpdate(BATCH_SAVE_SIZE=25)
    assert s.BATCH_SAVE_SIZE == 25


def test_batch_save_size_defaults_to_none():
    from app.models.setting import SettingUpdate
    s = SettingUpdate()
    assert s.BATCH_SAVE_SIZE is None
