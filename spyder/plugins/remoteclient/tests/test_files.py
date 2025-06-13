# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the remote files API."""
import io
import zipfile

# Third party imports
import pytest

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.remoteclient.api.modules.file_services import RemoteOSError
from spyder.plugins.remoteclient.tests.conftest import mark_remote_test


@mark_remote_test
class TestRemoteFilesAPI:
    remote_temp_dir = "/tmp/spyder-remote-tests"

    @AsyncDispatcher(early_return=False)
    async def test_create_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be created on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.mkdir(self.remote_temp_dir) == {
                "success": True
            }

    @AsyncDispatcher(early_return=False)
    async def test_write_file(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a file can be written to the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            async with await file_api.open(
                self.remote_temp_dir + "/test.txt", "w+"
            ) as f:
                await f.write("Hello, world!")
                await f.flush()
                await f.seek(0)
                assert await f.read() == "Hello, world!"

    @AsyncDispatcher(early_return=False)
    async def test_list_directories(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be listed on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            async for ls_content in file_api.ls(self.remote_temp_dir):
                assert ls_content["name"] == self.remote_temp_dir + "/test.txt"
                assert ls_content["size"] == 13
                assert ls_content["type"] == "file"
                assert not ls_content["islink"]
                assert ls_content["created"] > 0
                assert ls_content["mode"] == 0o100644
                assert ls_content["uid"] > 0
                assert ls_content["gid"] >= 0
                assert ls_content["mtime"] > 0
                assert ls_content["ino"] > 0
                assert ls_content["nlink"] == 1

    @AsyncDispatcher(early_return=False)
    async def test_copy_file(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a file can be copied on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.copy(
                self.remote_temp_dir + "/test.txt",
                self.remote_temp_dir + "/test2.txt",
            ) == {"success": True}

        async with file_api_class() as file_api:
            ls_content = [
                ls_file async for ls_file in file_api.ls(self.remote_temp_dir)
            ]
            assert len(ls_content) == 2
            idx = [
                item["name"] for item in ls_content
            ].index(self.remote_temp_dir + "/test.txt")
            assert (
                ls_content[not idx]["name"]
                == self.remote_temp_dir + "/test2.txt"
            )
            assert ls_content[0]["size"] == ls_content[1]["size"]

    @AsyncDispatcher(early_return=False)
    async def test_zip_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be zipped on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        buffer = io.BytesIO()
        async with file_api_class() as file_api:
            async for chunk in file_api.zip_directory(self.remote_temp_dir):
                buffer.write(chunk)
            assert buffer.tell() > 0

        buffer.seek(0)
        with zipfile.ZipFile(buffer, "r") as zip_file:
            assert zip_file.testzip() is None
            zip_file_contents = zip_file.namelist()
            assert len(zip_file_contents) == 2
            with zip_file.open(
                "test.txt"
            ) as file:
                assert file.read() == b"Hello, world!"
            with zip_file.open(
                "test2.txt"
            ) as file:
                assert file.read() == b"Hello, world!"

    @AsyncDispatcher(early_return=False)
    async def test_rm_file(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a file can be removed from the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.unlink(
                self.remote_temp_dir + "/test.txt"
            ) == {"success": True}
            assert await file_api.unlink(
                self.remote_temp_dir + "/test2.txt"
            ) == {"success": True}

    @AsyncDispatcher(early_return=False)
    async def test_rm_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be removed from the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.rmdir(self.remote_temp_dir) == {
                "success": True
            }

    @AsyncDispatcher(early_return=False)
    async def test_ls_nonexistent_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that listing a nonexistent directory raises an error."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            with pytest.raises(RemoteOSError) as exc_info:
                async for ls_file in file_api.ls(self.remote_temp_dir):
                    ...

        assert exc_info.value.errno == 2  # ENOENT: No such file or directory


if __name__ == "__main__":
    pytest.main()
