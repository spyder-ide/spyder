from unittest.mock import Mock

import pytest
from qtpy.compat import isalive
from qtpy.QtCore import QCoreApplication, QEvent

from spyder.plugins.ipythonconsole.utils.kernel_handler import (
    KernelConnectionState,
)
from spyder.plugins.ipythonconsole.widgets import ControlWidget
from spyder.plugins.ipythonconsole.widgets.shell import ShellWidget
from spyder.utils.qthelpers import qapplication

APP = qapplication()


def test_kernel_ready_is_ignored_after_control_is_deleted():
    """A queued kernel-ready callback cannot access a deleted console."""
    control = ControlWidget()
    control.deleteLater()
    QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)
    assert not isalive(control)

    shell = Mock(
        shutting_down=False,
        _control=control,
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )
    shell._show_banner.side_effect = control.textCursor

    ShellWidget.handle_kernel_is_ready(shell)

    shell.setup_spyder_kernel.assert_not_called()
    shell._show_banner.assert_not_called()
    shell.sig_kernel_is_ready.emit.assert_not_called()


@pytest.mark.parametrize("show_banner", [True, False], ids=["long", "short"])
@pytest.mark.parametrize("close_action", ["delete_control", "shutdown"])
def test_banner_processing_stops_if_console_closes(show_banner, close_action):
    """Closing during banner lookup prevents rendering and readiness."""
    control = ControlWidget()
    shell = Mock(
        shutting_down=False,
        _control=control,
        is_external_kernel=False,
        _is_banner_shown=False,
        additional_options={"show_banner": show_banner},
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )

    def close_during_banner():
        if close_action == "delete_control":
            control.deleteLater()
            QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)
            assert not isalive(control)
        else:
            shell.shutting_down = True
            assert isalive(control)
        return "Kernel banner\n"

    banner_method = shell.long_banner if show_banner else shell.short_banner
    banner_method.side_effect = close_during_banner
    shell._show_banner.side_effect = lambda: ShellWidget._show_banner(shell)

    try:
        ShellWidget.handle_kernel_is_ready(shell)

        banner_method.assert_called_once_with()
        shell._insert_plain_text.assert_not_called()
        assert not shell._is_banner_shown
        shell.sig_kernel_is_ready.emit.assert_not_called()
    finally:
        if isalive(control):
            control.deleteLater()
            QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)


@pytest.mark.parametrize("show_banner", [True, False], ids=["long", "short"])
def test_open_console_shows_banner_and_announces_readiness(show_banner):
    """Normal startup still displays either banner and announces readiness."""
    control = ControlWidget()
    shell = Mock(
        shutting_down=False,
        _control=control,
        is_external_kernel=False,
        _is_banner_shown=False,
        additional_options={"show_banner": show_banner},
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )
    shell.long_banner.return_value = "Long kernel banner\n"
    shell.short_banner.return_value = "Short kernel banner\n"
    shell._show_banner.side_effect = lambda: ShellWidget._show_banner(shell)
    shell._insert_plain_text.side_effect = (
        lambda cursor, text: cursor.insertText(text)
    )

    try:
        ShellWidget.handle_kernel_is_ready(shell)

        expected = (
            "Long kernel banner\n" if show_banner else "Short kernel banner\n"
        )
        assert control.toPlainText() == expected
        assert shell.banner == expected
        assert shell._is_banner_shown
        shell.sig_kernel_is_ready.emit.assert_called_once_with()
    finally:
        control.deleteLater()
        QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)


def test_kernel_ready_stops_when_setup_deletes_control():
    """Kernel setup cannot leave a late callback using a deleted console."""
    control = ControlWidget()

    def delete_control():
        control.deleteLater()
        QCoreApplication.sendPostedEvents(control, QEvent.DeferredDelete)

    shell = Mock(
        shutting_down=False,
        _control=control,
        kernel_handler=Mock(
            connection_state=KernelConnectionState.SpyderKernelReady,
        ),
    )
    shell.setup_spyder_kernel.side_effect = delete_control
    shell._show_banner.side_effect = control.textCursor

    ShellWidget.handle_kernel_is_ready(shell)

    shell.setup_spyder_kernel.assert_called_once_with()
    shell._show_banner.assert_not_called()
    shell.sig_kernel_is_ready.emit.assert_not_called()
