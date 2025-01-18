# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""IPython console and Spyder Remote Client integration tests."""

# Third party imports
import pytest


from spyder.plugins.remoteclient.plugin import RemoteClient


class TestRemoteFilesAPI:
    remote_temp_dir = "/tmp/spyder-remote-tests"

    @pytest.mark.asyncio
    async def test_create_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be created on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.mkdir(self.remote_temp_dir) == {"success": True}

    @pytest.mark.asyncio
    async def test_list_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be listed on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.ls(self.remote_temp_dir) == []

    @pytest.mark.asyncio
    async def test_write_file(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a file can be written to the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            async with await file_api.open(self.remote_temp_dir + "/test.txt", "w+") as f:
                await f.write("Hello, world!")
                await f.flush()
                await f.seek(0)
                assert await f.read() == "Hello, world!"
    
    @pytest.mark.asyncio
    async def test_list_directories(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be listed on the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            ls_content = await file_api.ls(self.remote_temp_dir)
            assert len(ls_content) == 1
            assert ls_content[0]["name"] == self.remote_temp_dir + "/test.txt"
            assert ls_content[0]["size"] == 13
            assert ls_content[0]["type"] == "file"
            assert not ls_content[0]["islink"]
            assert ls_content[0]["created"] > 0
            assert ls_content[0]["mode"] == 0o100644
            assert ls_content[0]["uid"] > 0
            assert ls_content[0]["gid"] >= 0
            assert ls_content[0]["mtime"] > 0
            assert ls_content[0]["ino"] > 0
            assert ls_content[0]["nlink"] == 1

    @pytest.mark.asyncio
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
            ls_content = await file_api.ls(self.remote_temp_dir)
            assert len(ls_content) == 2
            assert ls_content[0]["name"] == self.remote_temp_dir + "/test.txt"
            assert ls_content[1]["name"] == self.remote_temp_dir + "/test2.txt"
            assert ls_content[0]["size"] == ls_content[1]["size"]

    @pytest.mark.asyncio
    async def test_rm_file(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a file can be removed from the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.unlink(self.remote_temp_dir + "/test.txt") == {"success": True}
            assert await file_api.unlink(self.remote_temp_dir + "/test2.txt") == {"success": True}
    
    @pytest.mark.asyncio
    async def test_rm_dir(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """Test that a directory can be removed from the remote server."""
        file_api_class = remote_client.get_file_api(remote_client_id)
        assert file_api_class is not None

        async with file_api_class() as file_api:
            assert await file_api.rmdir(self.remote_temp_dir) == {"success": True}


if __name__ == "__main__":
    pytest.main()
