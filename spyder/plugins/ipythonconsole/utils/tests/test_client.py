from unittest.mock import Mock

from jupyter_client.threaded import IOLoopThread
from qtconsole.client import QtKernelClient

from spyder.plugins.ipythonconsole.utils.client import (
    SpyderKernelClient,
    _detach_channels,
)


def test_detach_channels_drains_pending_events():
    """Channel receivers detach before pending I/O loop events are drained."""
    events = []
    ioloop_thread = IOLoopThread()
    ioloop_thread.start()
    channels = []

    for channel_name in ["shell", "iopub", "stdin", "control"]:
        channel = Mock()

        def stop_receiving(_callback, name=channel_name):
            events.append(f"stop_receiving_{name}")
            ioloop_thread.ioloop.add_callback(
                lambda name=name: events.append(f"pending_event_{name}")
            )

        channel.stream.on_recv.side_effect = stop_receiving
        channels.append(channel)

    try:
        _detach_channels(ioloop_thread.ioloop, channels)
        events.append("detached")
    finally:
        ioloop_thread.stop()

    for channel_name in ["shell", "iopub", "stdin", "control"]:
        assert events.index(f"stop_receiving_{channel_name}") < events.index(
            f"pending_event_{channel_name}"
        )
        assert events.index(f"pending_event_{channel_name}") < events.index(
            "detached"
        )


def test_client_quiesces_drains_and_closes_streams_before_teardown(
    monkeypatch,
):
    """Channel streams close before the I/O loop tears their sockets down."""
    events = []
    client = SpyderKernelClient()
    client.ioloop_thread = IOLoopThread()
    client.ioloop_thread.start()

    channel_names = ["shell", "iopub", "stdin", "control"]
    channels = []
    for channel_name in channel_names:
        channel = Mock()

        def stop_receiving(_callback, name=channel_name):
            events.append(f"stop_receiving_{name}")
            client.ioloop.add_callback(
                lambda name=name: events.append(f"pending_event_{name}")
            )

        channel.stream.on_recv.side_effect = stop_receiving
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
        assert events.index(f"stop_receiving_{channel_name}") < events.index(
            f"pending_event_{channel_name}"
        )
        assert events.index(f"pending_event_{channel_name}") < events.index(
            f"close_{channel_name}"
        )
        assert events.index(f"close_{channel_name}") < events.index("teardown")
