from fastapi import APIRouter, Depends, HTTPException

from app.core.dependencies import get_storage_config_service
from app.modules.storage.config.schemas import StorageConfig, StorageConfigResponse, StorageTestResult
from app.modules.storage.config.service import StorageConfigService

router = APIRouter(prefix="/api/storage/config", tags=["storage-config"])


@router.get("", response_model=StorageConfigResponse)
def get_storage_config(service: StorageConfigService = Depends(get_storage_config_service)):
    return StorageConfigResponse(**service.get_config())


@router.put("", response_model=StorageConfigResponse)
def update_storage_config(
    body: StorageConfig,
    service: StorageConfigService = Depends(get_storage_config_service),
):
    try:
        return StorageConfigResponse(**service.update_config(body))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.post("/test", response_model=StorageTestResult)
def test_storage_connection(service: StorageConfigService = Depends(get_storage_config_service)):
    return service.test_connection()
