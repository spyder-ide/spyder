from unittest.mock import Mock, patch

import pytest

from spyder.plugins.ipythonconsole.widgets.main_widget import (
    IPythonConsoleWidget,
)


def test_pending_client_setup_is_ignored_during_mainwindow_close():
    """A late environment result cannot start kernels during shutdown."""
    widget = Mock(mainwindow_close=True)
    client = Mock()
    future = Mock()
    future.result.return_value = {}

    IPythonConsoleWidget._connect_new_client_to_kernel(
        widget,
        cache=True,
        path_to_custom_interpreter=None,
        client=client,
        future=future,
    )

    widget.get_cached_kernel.assert_not_called()
    client.connect_kernel.assert_not_called()


@pytest.mark.parametrize("environment_error", [False, True])
def test_removed_client_ignores_delayed_environment_result(environment_error):
    """Closing a console discards its pending startup result or error."""
    widget = Mock(mainwindow_close=False, clients=[Mock()])
    client = Mock()
    future = Mock()
    if environment_error:
        future.result.side_effect = RuntimeError("Environment lookup failed")
    else:
        future.result.return_value = {"TEST_ENV": "value"}

    with patch(
        "spyder.plugins.ipythonconsole.widgets.main_widget.SpyderKernelSpec"
    ) as kernel_spec:
        IPythonConsoleWidget._connect_new_client_to_kernel(
            widget, True, None, client, future
        )

    kernel_spec.assert_not_called()
    widget.get_cached_kernel.assert_not_called()
    client.connect_kernel.assert_not_called()
    client.show_kernel_error.assert_not_called()


def test_registered_client_receives_kernel_after_environment_lookup():
    """An open console still receives the kernel for its environment."""
    client = Mock()
    widget = Mock(mainwindow_close=False, clients=[client])
    future = Mock()
    future.result.return_value = {"TEST_ENV": "value"}

    with patch(
        "spyder.plugins.ipythonconsole.widgets.main_widget.SpyderKernelSpec"
    ) as kernel_spec:
        IPythonConsoleWidget._connect_new_client_to_kernel(
            widget, True, None, client, future
        )

    assert kernel_spec.return_value.env == {"TEST_ENV": "value"}
    widget.get_cached_kernel.assert_called_once_with(
        kernel_spec.return_value, cache=True
    )
    client.connect_kernel.assert_called_once_with(
        widget.get_cached_kernel.return_value
    )
    client.show_kernel_error.assert_not_called()


def test_registered_client_shows_environment_lookup_error():
    """An open console still reports an environment-discovery failure."""
    client = Mock()
    widget = Mock(mainwindow_close=False, clients=[client])
    future = Mock()
    error = RuntimeError("Environment lookup failed")
    future.result.side_effect = error

    with patch(
        "spyder.plugins.ipythonconsole.widgets.main_widget.SpyderKernelSpec"
    ):
        IPythonConsoleWidget._connect_new_client_to_kernel(
            widget, True, None, client, future
        )

    widget.get_cached_kernel.assert_not_called()
    client.connect_kernel.assert_not_called()
    client.show_kernel_error.assert_called_once_with(error)
