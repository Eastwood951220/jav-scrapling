from shared.database.repositories import (
    MagnetRepository,
    MovieRepository,
    StorageConfigRepository,
    StorageTaskRepository,
)
from shared.integrations.storage_providers.clouddrive2.factory import CloudDriveClientFactory
from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway

from app.modules.storage.config.service import StorageConfigService
from app.modules.storage.tasks.service import StorageTaskService


def get_storage_task_repository() -> StorageTaskRepository:
    return StorageTaskRepository()


def get_storage_config_repository() -> StorageConfigRepository:
    return StorageConfigRepository()


def get_movie_repository() -> MovieRepository:
    return MovieRepository()


def get_magnet_repository() -> MagnetRepository:
    return MagnetRepository()


def get_clouddrive_client_factory() -> CloudDriveClientFactory:
    return CloudDriveClientFactory()


def get_clouddrive_gateway():
    config = get_storage_config_repository().get_default()
    client = get_clouddrive_client_factory().create(config)
    return CloudDrive2Gateway(client)


def get_storage_config_service() -> StorageConfigService:
    return StorageConfigService(
        config_repository=get_storage_config_repository(),
        provider_factory=get_clouddrive_client_factory(),
    )


def get_storage_task_service() -> StorageTaskService:
    return StorageTaskService(
        task_repository=get_storage_task_repository(),
        movie_repository=get_movie_repository(),
        magnet_repository=get_magnet_repository(),
    )
