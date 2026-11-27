from unittest.mock import Mock

from spyder.plugins.ipythonconsole.utils import kernel_handler
from spyder.plugins.ipythonconsole.utils.kernel_handler import KernelHandler


def test_closing_stops_client_channels_before_kernel_shutdown(monkeypatch):
    """Client streams stop before their kernel manager destroys sockets."""
    events = []
    handler = Mock()
    handler.kernel_client.channels_running = True
    handler.close_comm.side_effect = lambda: events.append("close_comm")
    handler.kernel_client.stop_channels.side_effect = (
        lambda: events.append("stop_channels")
    )
    handler.kernel_manager.stop_restarter.side_effect = (
        lambda: events.append("stop_restarter")
    )
    handler.disconnect_std_pipes.side_effect = (
        lambda: events.append("disconnect_std_pipes")
    )
    handler.kernel_manager.shutdown_kernel.side_effect = (
        lambda **kwargs: events.append("shutdown_kernel")
    )
    handler.after_shutdown.side_effect = (
        lambda: events.append("after_shutdown")
    )
    monkeypatch.setattr(kernel_handler, "running_under_pytest", lambda: True)

    KernelHandler.close(handler)

    assert events.index("stop_channels") < events.index("shutdown_kernel")


def test_waiting_for_shutdown_keeps_handler_until_std_threads_finish(
    monkeypatch,
):
    """Standard stream threads finish before shutdown owners are released."""
    events = []
    handler = Mock()
    shutdown_thread = Mock()
    shutdown_thread.isRunning.return_value = True
    handler.kernel_manager._kill_kernel.side_effect = (
        lambda: events.append("kill_kernel")
    )
    shutdown_thread.quit.side_effect = lambda: events.append("quit")
    shutdown_thread.wait.side_effect = lambda: events.append("wait")
    handler.close_std_threads.side_effect = (
        lambda: events.append("close_std_threads")
    )
    monkeypatch.setattr(
        KernelHandler,
        "_shutdown_thread_list",
        [(shutdown_thread, handler)],
    )

    KernelHandler.wait_all_shutdown_threads()

    assert events == ["kill_kernel", "quit", "wait", "close_std_threads"]
    assert KernelHandler._shutdown_thread_list == []
