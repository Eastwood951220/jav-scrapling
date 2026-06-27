"""Tests for CloudDriveGrpcClient."""

from unittest.mock import MagicMock

from clouddrive.clouddrive_grpc_client import CloudDriveGrpcClient


def test_copy_file_calls_grpc_stub():
    """copy_file should invoke stub.CopyFile with CopyFileRequest."""
    client = CloudDriveGrpcClient(host="localhost:19798", token="test")
    mock_stub = MagicMock()
    client._stub = mock_stub

    client.copy_file(["/src/file1.mp4", "/src/file2.mp4"], "/dest")

    mock_stub.CopyFile.assert_called_once()
    call_args = mock_stub.CopyFile.call_args
    request = call_args[0][0]
    assert list(request.theFilePaths) == ["/src/file1.mp4", "/src/file2.mp4"]
    assert request.destPath == "/dest"
