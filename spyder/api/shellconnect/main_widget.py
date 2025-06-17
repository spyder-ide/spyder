# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Main widget to use in plugins that show content that comes from the IPython
console, such as the Variable Explorer or Plots.
"""

# Third party imports
from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.widgets.emptymessage import EmptyMessageWidget


class _ErroredMessageWidget(EmptyMessageWidget):
    """Widget to show when the kernel's shell failed to start."""

    def __init__(self, parent, shellwidget):
        # Initialize EmptyMessageWidget with the content we want to show for
        # errors
        super().__init__(
            parent,
            icon_filename=(
                "console-remote-off"
                if shellwidget.is_remote()
                else "console-off"
            ),
            text=_("No connected console"),
            description=_(
                "The current console has no active kernel, so there is no "
                "content to show here"
            ),
            adjust_on_resize=True,
        )

        # This is necessary to show this widget in case ShellConnectMainWidget
        # shows an empty message.
        self.is_empty = False


class ShellConnectMainWidget(PluginMainWidget):
    """
    Main widget to use in a plugin that shows console-specific content.

    Notes
    -----
    * This is composed of a QStackedWidget to stack widgets associated to each
      shell widget in the console and only show one of them at a time.
    * The current widget in the stack will display the content associated to
      the console with focus.
    """
    def __init__(self, *args, set_layout=True, **kwargs):
        super().__init__(*args, **kwargs)

        # Widgets
        if not (
            self.SHOW_MESSAGE_WHEN_EMPTY
            and self.get_conf(
                "show_message_when_panes_are_empty", section="main"
            )
        ):
            self._stack = QStackedWidget(self)

            if set_layout:
                layout = QVBoxLayout()
                layout.addWidget(self._stack)
                self.setLayout(layout)

        self._shellwidgets = {}

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def current_widget(self):
        """
        Return the current widget in the stack.

        Returns
        -------
        QWidget
            The current widget.
        """
        return self._content_widget

    def get_focus_widget(self):
        return self._stack.currentWidget()

    # ---- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def update_style(self):
        self._stack.setStyleSheet("QStackedWidget {padding: 0px; border: 0px}")

    # ---- Stack accesors
    # ------------------------------------------------------------------------
    def count(self):
        """
        Return the number of widgets in the stack.

        Returns
        -------
        int
            The number of widgets in the stack.
        """
        return self._stack.count()

    def get_widget_for_shellwidget(self, shellwidget):
        """return widget corresponding to shellwidget."""
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            return self._shellwidgets[shellwidget_id]
        return None

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """Create a new widget in the stack and associate it to shellwidget."""
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            widget = self.create_new_widget(shellwidget)
            self._stack.addWidget(widget)
            self._shellwidgets[shellwidget_id] = widget

            # Add all actions to new widget for shortcuts to work.
            for __, action in self.get_actions().items():
                if action:
                    widget_actions = widget.actions()
                    if action not in widget_actions:
                        widget.addAction(action)

            self.set_shellwidget(shellwidget)

    def remove_shellwidget(self, shellwidget):
        """Remove widget associated to shellwidget."""
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            widget = self._shellwidgets.pop(shellwidget_id)

            # If `widget` is an empty pane, we don't need to remove it from the
            # stack (because it's the one we need to show since the console is
            # showing an error) nor try to close it (because it makes no
            # sense).
            if not isinstance(widget, EmptyMessageWidget):
                self._stack.removeWidget(widget)
                self.close_widget(widget)

            self.update_actions()

    def set_shellwidget(self, shellwidget):
        """Set widget associated with shellwidget as the current widget."""
        old_widget = self.current_widget()
        widget = self.get_widget_for_shellwidget(shellwidget)
        if widget is None:
            return

        self.set_content_widget(widget, add_to_stack=False)
        if (
            self.SHOW_MESSAGE_WHEN_EMPTY
            and self.get_conf(
                "show_message_when_panes_are_empty", section="main"
            )
            and widget.is_empty
        ):
            self.show_empty_message()
        else:
            self.show_content_widget()

        self.switch_widget(widget, old_widget)
        self.update_actions()

    def add_errored_shellwidget(self, shellwidget):
        """
        Create a new _ErroredMessageWidget in the stack and associate it to
        shellwidget.

        This is necessary to show a meaningful message when switching to
        consoles with dead kernels.
        """
        shellwidget_id = id(shellwidget)

        # This can happen if the kernel started without issues but something is
        # printed to its stderr stream, which we display as an error in the
        # console. In that case, we need to remove the current widget
        # associated to shellwidget and replace it by an empty one.
        if shellwidget_id in self._shellwidgets:
            self._shellwidgets.pop(shellwidget_id)

        widget = _ErroredMessageWidget(self, shellwidget)
        widget.set_visibility(self.is_visible)
        if self.dockwidget is not None:
            self.dockwidget.visibilityChanged.connect(widget.set_visibility)

        self.set_content_widget(widget)
        self._shellwidgets[shellwidget_id] = widget
        self.set_shellwidget(shellwidget)

    def create_new_widget(self, shellwidget):
        """Create a widget to communicate with shellwidget."""
        raise NotImplementedError

    def close_widget(self, widget):
        """Close the widget."""
        raise NotImplementedError

    def switch_widget(self, widget, old_widget):
        """Switch the current widget."""
        raise NotImplementedError

    def refresh(self):
        """Refresh widgets."""
        if self.count():
            widget = self.current_widget()
            widget.refresh()

    def is_current_widget_error_message(self):
        """Check if the current widget is showing an error message."""
        return isinstance(self.current_widget(), _ErroredMessageWidget)

    def switch_empty_message(self, value: bool):
        """Switch between the empty message widget or the one with content."""
        if value:
            self.show_empty_message()
        else:
            self.show_content_widget()
