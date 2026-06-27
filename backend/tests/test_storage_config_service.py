from unittest.mock import MagicMock


def test_storage_config_service_masks_token_on_read():
    from app.modules.storage.config.service import StorageConfigService

    repo = MagicMock()
    repo.get_default.return_value = {"api_token": "abcdef123456", "grpc_host": "localhost:9798"}
    service = StorageConfigService(config_repository=repo, provider_factory=MagicMock())

    result = service.get_config()

    assert result["api_token"] == "************3456"


def test_storage_config_service_rejects_invalid_delay_range():
    from app.modules.storage.config.service import StorageConfigService

    service = StorageConfigService(config_repository=MagicMock(), provider_factory=MagicMock())

    try:
        service.update_config({"operation_delay_min": 2, "operation_delay_max": 1})
        assert False, "Expected ValueError"
    except ValueError as exc:
        assert "operation_delay_max must be >= operation_delay_min" in str(exc)


def test_storage_config_service_connection_test_uses_factory_gateway():
    from app.modules.storage.config.service import StorageConfigService

    repo = MagicMock()
    repo.get_default.return_value = {"api_token": "token", "grpc_host": "http://localhost:9798"}
    factory = MagicMock()
    client = MagicMock()
    factory.create.return_value = client
    gateway = MagicMock()
    gateway.health_check.return_value.reachable = True
    gateway.health_check.return_value.authorized = True
    gateway.health_check.return_value.error_message = None

    service = StorageConfigService(config_repository=repo, provider_factory=factory, gateway_class=lambda created: gateway)

    result = service.test_connection()

    factory.create.assert_called_once()
    assert result.grpc_reachable is True
    assert result.api_authorized is True
