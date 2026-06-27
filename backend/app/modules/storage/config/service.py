from __future__ import annotations

from app.modules.storage.config.schemas import StorageConfig, StorageTestResult
from shared.database.repositories.storage_config_repository import mask_token
from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway


class StorageConfigService:
    def __init__(self, config_repository, provider_factory, gateway_class=CloudDrive2Gateway) -> None:
        self.config_repository = config_repository
        self.provider_factory = provider_factory
        self.gateway_class = gateway_class

    def get_config(self) -> dict:
        config = StorageConfig().model_dump()
        config.update(self.config_repository.get_default())
        config["api_token"] = mask_token(config.get("api_token", ""))
        return config

    def update_config(self, body: StorageConfig | dict) -> dict:
        data = StorageConfig().model_dump()
        incoming = body.model_dump() if hasattr(body, "model_dump") else dict(body)
        data.update(incoming)
        self._validate_ranges(data)
        saved = self.config_repository.save_default(data)
        response = dict(saved)
        response["api_token"] = mask_token(response.get("api_token", ""))
        return response

    def test_connection(self) -> StorageTestResult:
        config = StorageConfig().model_dump()
        config.update(self.config_repository.get_default())
        client = self.provider_factory.create(config)
        try:
            gateway = self.gateway_class(client)
            health = gateway.health_check()
            result = StorageTestResult(
                grpc_reachable=health.reachable,
                grpc_error=None if health.reachable else health.error_message,
                api_authorized=health.authorized,
                api_error=None if health.authorized else health.error_message,
            )
            if health.reachable and health.authorized:
                result.download_root_exists = gateway.find_file(config["download_root_folder"]) is not None
                result.target_folder_accessible = gateway.find_file(config["target_folder"]) is not None
            return result
        finally:
            close = getattr(client, "close", None)
            if callable(close):
                close()

    def _validate_ranges(self, data: dict) -> None:
        checks = [
            ("operation_delay_min", "operation_delay_max"),
            ("download_poll_interval_min", "download_poll_interval_max"),
            ("retry_delay_min", "retry_delay_max"),
        ]
        for minimum, maximum in checks:
            if data[maximum] < data[minimum]:
                raise ValueError(f"{maximum} must be >= {minimum}")
