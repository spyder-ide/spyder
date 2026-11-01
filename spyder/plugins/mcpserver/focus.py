# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Keep keyboard focus where the user has it while agents use tools.

Some plugin methods give focus to their widgets (e.g. the Editor when it
opens a file, or the console when the debugger stops), which is right when
users trigger them but not when an agent does: the user's next keystrokes
would go to a different widget, e.g. their code. So tool calls restore the
focus when they finish, unless the user moved it in the meantime.
"""

# Standard library imports
from __future__ import annotations

from collections.abc import Callable
import time

# Third-party imports
from qtpy.QtCore import QEvent, QObject, Qt, QTimer
from qtpy.QtWidgets import QApplication, QWidget

# Local imports
from spyder.plugins.mcpserver.api import Content, MCPTool, ToolCall

# Focus changes this soon after a click or a key press are made by the user.
USER_FOCUS_WINDOW = 0.5

MOUSE_EVENTS = {
    QEvent.MouseButtonPress,
    QEvent.MouseButtonDblClick,
    QEvent.TouchBegin,
}


def _is_alive(obj: QObject | None) -> bool:
    if obj is None:
        return False
    try:
        obj.objectName()
    except RuntimeError:
        # The C++ object was deleted
        return False
    return True


class FocusGuard(QObject):
    """
    Restore the focus after a tool call, following the focus changes the
    user makes during the call.
    """

    # Keep a reference to guards until they stop
    _active_guards: set[FocusGuard] = set()

    def __init__(self) -> None:
        super().__init__()
        self._active_guards.add(self)
        self._widget: QWidget | None = QApplication.focusWidget()
        self._window: QWidget | None = QApplication.activeWindow()
        self._last_key_press = 0.0
        self._last_click = 0.0
        self._clicked: QWidget | None = None
        self._active = True

        app = QApplication.instance()
        app.installEventFilter(self)
        app.focusChanged.connect(self._on_focus_changed)

    def eventFilter(self, obj, event) -> bool:
        if event.type() == QEvent.KeyPress:
            self._last_key_press = time.monotonic()
        elif event.type() in MOUSE_EVENTS and isinstance(obj, QWidget):
            self._last_click = time.monotonic()
            self._clicked = obj
        return False

    def finish(self) -> None:
        """Restore the focus now and after pending events, then stop."""
        if not self._active:
            return
        self._active = False
        self.restore()
        QTimer.singleShot(0, self._restore_and_stop)

    def _on_focus_changed(self, old: QWidget, new: QWidget) -> None:
        if not self._active or new is None:
            return
        if self._is_user_change(new):
            # The user moved the focus, so keep it there
            self._widget = new
            self._window = new.window()

    def _is_user_change(self, new: QWidget) -> bool:
        # Qt moves the focus on mouse presses before the event filters see
        # them, but the button is already down
        if QApplication.mouseButtons() != Qt.NoButton:
            return True

        now = time.monotonic()

        # Clicking a widget focuses it or one of its parents or children
        clicked = self._clicked
        if now - self._last_click < USER_FOCUS_WINDOW and _is_alive(clicked):
            if (
                clicked is new
                or new.isAncestorOf(clicked)
                or clicked.isAncestorOf(new)
            ):
                return True

        # Keyboard shortcuts and Tab can focus any widget
        return now - self._last_key_press < USER_FOCUS_WINDOW

    def restore(self) -> None:
        """Give the focus back to the widget the user had it in."""
        widget = self._get_target()
        if widget is None:
            return

        window = self._window
        if (
            _is_alive(window)
            and window.isVisible()
            and QApplication.activeWindow() is not window
        ):
            window.activateWindow()

        if QApplication.focusWidget() is not widget:
            widget.setFocus(Qt.OtherFocusReason)

    def _get_target(self) -> QWidget | None:
        """
        Widget to give the focus to: the one the user had it in or, if it
        was hidden (e.g. the Editor switched to another file), the active
        widget of the same area.
        """
        widget = self._widget
        if not _is_alive(widget):
            return None
        if widget.isVisible():
            return widget

        parent = widget.parentWidget()
        while parent is not None and not parent.isVisible():
            parent = parent.parentWidget()
        if parent is None:
            return None

        # The child of that area that last had the focus
        child = parent.focusWidget()
        if _is_alive(child) and child.isVisible():
            return child
        return parent if parent.focusPolicy() != Qt.NoFocus else None

    def _restore_and_stop(self) -> None:
        self.restore()
        app = QApplication.instance()
        app.removeEventFilter(self)
        try:
            app.focusChanged.disconnect(self._on_focus_changed)
        except (TypeError, RuntimeError):
            pass
        self._active_guards.discard(self)
        self.deleteLater()


def call_tool_keeping_focus(
    tool: MCPTool,
    arguments: dict,
    on_done: Callable[[list[Content], bool], None],
) -> None:
    """
    Call ``tool`` in the main Qt thread, keeping the keyboard focus where the
    user has it.
    """
    guard = FocusGuard()

    def finish(content: list[Content], is_error: bool) -> None:
        guard.finish()
        on_done(content, is_error)

    tool.call(ToolCall(arguments, finish))

    # Restore the focus taken while the tool started, even if it keeps
    # running (e.g. code in a console), but keep guarding until it finishes
    guard.restore()
