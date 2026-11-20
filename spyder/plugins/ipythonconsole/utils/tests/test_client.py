from unittest.mock import Mock

from jupyter_client.threaded import IOLoopThread
from qtconsole.client import QtKernelClient

from spyder.plugins.ipythonconsole.utils.client import (
    SpyderKernelClient,
)


def test_client_closes_streams_before_teardown(monkeypatch):
    """Channel streams close before the I/O loop tears their sockets down."""
    events = []
    client = SpyderKernelClient()
    client.ioloop_thread = IOLoopThread()
    client.ioloop_thread.start()

    channel_names = ["shell", "iopub", "stdin", "control"]
    channels = []
    for channel_name in channel_names:
        channel = Mock()

        channel.close.side_effect = (
            lambda name=channel_name: events.append(f"close_{name}")
        )
        channels.append(channel)

    (
        client._shell_channel,
        client._iopub_channel,
        client._stdin_channel,
        client._control_channel,
    ) = channels
    monkeypatch.setattr(
        QtKernelClient,
        "stop_channels",
        lambda _client: events.append("teardown"),
    )

    try:
        client.stop_channels()
    finally:
        client.ioloop_thread.stop()

    for channel_name in channel_names:
        assert events.index(f"close_{channel_name}") < events.index("teardown")
