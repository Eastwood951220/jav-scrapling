from unittest.mock import MagicMock

import grpc


def test_factory_normalizes_host_protocol_and_trailing_slash():
    from shared.integrations.storage_providers.clouddrive2.factory import CloudDriveClientFactory

    factory = CloudDriveClientFactory()

    assert factory.normalize_host("localhost:19798") == "localhost:19798"
    assert factory.normalize_host("http://localhost:19798") == "localhost:19798"
    assert factory.normalize_host("https://localhost:19798/") == "localhost:19798"


def test_mapper_converts_cloud_file_to_remote_file():
    from shared.integrations.storage_providers.clouddrive2.mapper import map_remote_file

    proto_file = MagicMock()
    proto_file.name = "video.mp4"
    proto_file.fullPathName = "/Downloads/video.mp4"
    proto_file.size = 123
    proto_file.isDirectory = False

    result = map_remote_file(proto_file)

    assert result.name == "video.mp4"
    assert result.full_path == "/Downloads/video.mp4"
    assert result.size == 123
    assert result.is_directory is False


def test_mapper_maps_authentication_error():
    from shared.integrations.storage_providers.clouddrive2.exceptions import CloudDriveAuthenticationError
    from shared.integrations.storage_providers.clouddrive2.mapper import map_grpc_error

    error = grpc.RpcError()
    error.code = lambda: grpc.StatusCode.UNAUTHENTICATED
    error.details = lambda: "bad token"

    mapped = map_grpc_error(error)

    assert isinstance(mapped, CloudDriveAuthenticationError)
    assert "bad token" in str(mapped)


def test_gateway_returns_internal_models_only():
    from shared.integrations.storage_providers.clouddrive2.gateway import CloudDrive2Gateway
    from shared.integrations.storage_providers.clouddrive2.models import RemoteFile

    client = MagicMock()
    proto_file = MagicMock()
    proto_file.name = "movie.mkv"
    proto_file.fullPathName = "/Downloads/movie.mkv"
    proto_file.size = 456
    proto_file.isDirectory = False
    client.list_sub_files.return_value = [proto_file]

    gateway = CloudDrive2Gateway(client)

    files = gateway.list_files("/Downloads")

    assert files == [RemoteFile(name="movie.mkv", full_path="/Downloads/movie.mkv", size=456, is_directory=False)]
