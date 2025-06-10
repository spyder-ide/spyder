# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""Tests for the remote files API."""

# Third party imports
import pytest

from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.remoteclient.tests.conftest import mark_remote_test


@mark_remote_test
class TestRemoteEnvironAPI:
    test_key = "TEST_VAR"
    test_value = "test_value"

    @AsyncDispatcher(early_return=False)
    async def test_set_var(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """
        Test that an environment variable can be set on the remote server.
        """
        environ_api_class = remote_client.get_environ_api(remote_client_id)
        assert environ_api_class is not None

        async with environ_api_class() as environ_api:
            await environ_api.set(self.test_key, self.test_value)
            value = await environ_api.get(self.test_key)

        assert value == self.test_value

    @AsyncDispatcher(early_return=False)
    async def test_list_environ(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """
        Test that environment variables can be listed on the remote server.
        """
        environ_api_class = remote_client.get_environ_api(remote_client_id)
        assert environ_api_class is not None

        async with environ_api_class() as environ_api:
            env_vars = await environ_api.to_dict()
            assert isinstance(env_vars, dict)
            assert self.test_key in env_vars
            assert env_vars[self.test_key] == self.test_value

    @AsyncDispatcher(early_return=False)
    async def test_get_non_existent_var(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """
        Test that getting a non-existent environment variable returns None.
        """
        environ_api_class = remote_client.get_environ_api(remote_client_id)
        assert environ_api_class is not None

        async with environ_api_class() as environ_api:
            value = await environ_api.get("NON_EXISTENT_VAR")
            assert value is None

    @AsyncDispatcher(early_return=False)
    async def test_delete_var(
        self,
        remote_client: RemoteClient,
        remote_client_id: str,
    ):
        """
        Test that an environment variable can be deleted on the remote server.
        """
        environ_api_class = remote_client.get_environ_api(remote_client_id)
        assert environ_api_class is not None

        async with environ_api_class() as environ_api:
            await environ_api.delete(self.test_key)
            value = await environ_api.get(self.test_key)

        assert value is None


if __name__ == "__main__":
    pytest.main()
