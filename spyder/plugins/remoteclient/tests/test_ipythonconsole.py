# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""IPython console and Spyder Remote Client integration tests."""

# Standard library imports

# Local imports
from spyder.plugins.remoteclient.tests.conftest import await_future


def test_shutdown_kernel(ipyconsole, remote_client, remote_client_id, qtbot):
    """Starts and stops a kernel on the remote server."""
    remote_client.create_ipyclient_for_server(remote_client_id)
    shell = ipyconsole.get_current_shellwidget()

    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=180000,  # longer timeout for installation
    )

    ipyconsole.get_widget().close_client()

    assert (
        await_future(remote_client.get_kernels(remote_client_id), timeout=10)
        == []
    )


def test_restart_kernel(ipyconsole, remote_client, remote_client_id, qtbot):
    """Test that kernel is restarted correctly."""
    remote_client.create_ipyclient_for_server(remote_client_id)
    shell = ipyconsole.get_current_shellwidget()

    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=180000,
    )

    # Do an assignment to verify that it's not there after restarting
    with qtbot.waitSignal(shell.executed):
        shell.execute("a = 10")

    # Restart kernel and wait until it's up again.
    # NOTE: We trigger the restart_action instead of calling `restart_kernel`
    # directly to also check that that action is working as expected and avoid
    # regressions such as spyder-ide/spyder#22084.
    shell._prompt_html = None
    ipyconsole.get_widget().restart_action.trigger()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=4000,
    )

    assert not shell.is_defined("a")

    with qtbot.waitSignal(shell.executed):
        shell.execute("b = 10")

    # Make sure that kernel is responsive after restart
    qtbot.waitUntil(lambda: shell.is_defined("b"), timeout=2000)

    ipyconsole.get_widget().close_client()


def test_kernel_kill(ipyconsole, remote_client, remote_client_id, qtbot):
    """Test that the kernel correctly restarts after a kill."""
    crash_string = "import os, signal; os.kill(os.getpid(), signal.SIGTERM)"

    remote_client.create_ipyclient_for_server(remote_client_id)
    shell = ipyconsole.get_current_shellwidget()
    qtbot.waitUntil(
        lambda: shell.spyder_kernel_ready and shell._prompt_html is not None,
        timeout=180000,
    )

    # Since the heartbeat and the tunnels are running in separate threads, we
    # need to make sure that the heartbeat thread has "higher" priority than
    # the tunnel thread, otherwise the kernel will be restarted and the tunnels
    # recreated before the heartbeat can detect the kernel is dead.
    # In the test enviroment, the heartbeat needs to be set to a lower value
    # because there are fewer threads running.
    shell.kernel_handler.set_time_to_dead(0.2)

    shell._prompt_html = None
    with qtbot.waitSignal(shell.sig_prompt_ready, timeout=30000):
        shell.execute(crash_string)

    assert "The kernel died, restarting..." in shell._control.toPlainText()

    with qtbot.waitSignal(shell.executed):
        shell.execute("b = 10")

    # Make sure that kernel is responsive after restart
    qtbot.waitUntil(lambda: shell.is_defined("b"), timeout=2000)

    ipyconsole.get_widget().close_client()
