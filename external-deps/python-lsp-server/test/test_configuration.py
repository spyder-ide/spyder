# Copyright 2021- Python Language Server Contributors.

from unittest.mock import patch

import pytest

from pylsp import IS_WIN
from test.test_notebook_document import wait_for_condition
from test.test_utils import send_initialize_request

INITIALIZATION_OPTIONS = {
    "pylsp": {
        "plugins": {
            "flake8": {"enabled": True},
            "pycodestyle": {"enabled": False},
            "pyflakes": {"enabled": False},
        },
    }
}


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_set_flake8_using_init_opts(client_server_pair) -> None:
    client, server = client_server_pair
    send_initialize_request(client, INITIALIZATION_OPTIONS)
    for key, value in INITIALIZATION_OPTIONS["pylsp"]["plugins"].items():
        assert server.workspace._config.settings().get("plugins").get(key).get(
            "enabled"
        ) == value.get("enabled")


@pytest.mark.skipif(IS_WIN, reason="Flaky on Windows")
def test_set_flake8_using_workspace_did_change_configuration(
    client_server_pair,
) -> None:
    client, server = client_server_pair
    send_initialize_request(client, None)
    assert (
        server.workspace._config.settings().get("plugins").get("flake8").get("enabled")
        is False
    )

    with patch.object(server.workspace, "update_config") as mock_update_config:
        client._endpoint.notify(
            "workspace/didChangeConfiguration",
            {"settings": INITIALIZATION_OPTIONS},
        )
        wait_for_condition(lambda: mock_update_config.call_count >= 1)

        for key, value in INITIALIZATION_OPTIONS["pylsp"]["plugins"].items():
            assert server.workspace._config.settings().get("plugins").get(key).get(
                "enabled"
            ) == value.get("enabled")
