# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os

import pytest

from spyder.api.plugins.pytest import *  # noqa
from spyder.plugins.remoteclient.plugin import RemoteClient
from spyder.plugins.ipythonconsole.plugin import IPythonConsole
from spyder.plugins.remoteclient.tests.fixtures import *  # noqa


@pytest.fixture(scope="session")
def plugins_cls():
    os.environ["IPYCONSOLE_TESTING"] = "True"
    yield [("remote_client", RemoteClient),
           ("ipyconsole", IPythonConsole)]
    del os.environ["IPYCONSOLE_TESTING"]


@pytest.fixture()
def remote_shell(ipyconsole, remote_client_id, qtbot):
    """Create a new shell widget."""
    ipyconsole.get_widget().create_ipyclient_for_server(remote_client_id)
    client = ipyconsole.get_current_client()
    shell = client.shellwidget
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=180000,
    )

    yield shell

    ipyconsole.get_widget().close_client(client=client)
