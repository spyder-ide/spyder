# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""IPython console and Spyder Remote Client integration tests."""

# Third party imports
from flaky import flaky
import pytest

# Local imports
from spyder.api.asyncdispatcher import AsyncDispatcher
from spyder.plugins.remoteclient.tests.conftest import (
    await_future,
    mark_remote_test,
)


@AsyncDispatcher(loop="test")
async def list_kernels(remote_client_plugin, server_id):
    async with remote_client_plugin.get_jupyter_api(server_id) as jupyter_api:
        return await jupyter_api.list_kernels()


@mark_remote_test
class TestIpythonConsole:
    def test_start_stop_kernel(
        self, ipyconsole, remote_client, remote_client_id, qtbot
    ):
        """Starts and stops a kernel on the remote server."""
        ipyconsole.get_widget().create_ipyclient_for_server(remote_client_id)
        shell = ipyconsole.get_current_shellwidget()

        qtbot.waitUntil(
            lambda: shell.spyder_kernel_ready
            and shell._prompt_html is not None,
            timeout=180000,  # longer timeout for installation
        )

        ipyconsole.get_widget().close_client()

        assert await_future(
            list_kernels(remote_client, remote_client_id),
            timeout=5
        ) == []

    def test_restart_kernel(self, remote_shell, ipyconsole, qtbot):
        """Test that kernel is restarted correctly."""
        # Do an assignment to verify that it's not there after restarting
        with qtbot.waitSignal(remote_shell.executed):
            remote_shell.execute("a = 10")

        with qtbot.waitSignal(
            remote_shell.sig_kernel_is_ready,
            timeout=4000
        ):
            ipyconsole.get_widget().restart_action.trigger()

        assert not remote_shell.is_defined("a")

        with qtbot.waitSignal(remote_shell.executed):
            remote_shell.execute("b = 10")

        # Make sure that kernel is responsive after restart
        qtbot.waitUntil(lambda: remote_shell.is_defined("b"), timeout=2000)

    def test_interrupt_kernel(self, remote_shell, qtbot):
        """Test that the kernel correctly interrupts."""
        loop_string = "while True: pass"

        with qtbot.waitSignal(remote_shell.executed):
            remote_shell.execute("b = 10")

        remote_shell.execute(loop_string)

        qtbot.wait(500)

        remote_shell.interrupt_kernel()

        qtbot.wait(1000)

        # Make sure that kernel didn't die
        assert remote_shell.get_value("b") == 10

    def test_kernel_kill(self, remote_shell, qtbot):
        """Test that the kernel correctly restarts after a kill."""
        crash_string = (
            "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"
        )

        with qtbot.waitSignal(remote_shell.sig_prompt_ready, timeout=30000):
            remote_shell.execute(crash_string)

        assert "The kernel died, restarting..." in remote_shell._control.toPlainText()

        with qtbot.waitSignal(remote_shell.executed):
            remote_shell.execute("b = 10")

        # Make sure that kernel is responsive after restart
        qtbot.waitUntil(lambda: remote_shell.is_defined("b"), timeout=2000)


if __name__ == "__main__":
    pytest.main()
