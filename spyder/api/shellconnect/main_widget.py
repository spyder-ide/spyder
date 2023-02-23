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
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Widgets
        self._stack = QStackedWidget(self)
        self._shellwidgets = {}

        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(0)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._stack)
        self.setLayout(layout)

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

    def current_widget(self):
        """
        Return the current figure browser widget in the stack.

        Returns
        -------
        QWidget
            The current widget.
        """
        return self._stack.currentWidget()

    def get_focus_widget(self):
        return self.current_widget()

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(self, shellwidget):
        """
        Create a new widget in the stack and associate it to
        shellwidget.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id not in self._shellwidgets:
            widget = self.create_new_widget(shellwidget)
            self._stack.addWidget(widget)
            self._shellwidgets[shellwidget_id] = widget
            self.set_shellwidget(shellwidget)
            self.update_actions()

    def remove_shellwidget(self, shellwidget):
        """Remove widget associated to shellwidget."""
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            widget = self._shellwidgets.pop(shellwidget_id)
            self._stack.removeWidget(widget)
            self.close_widget(widget)

    def set_shellwidget(self, shellwidget):
        """
        Set widget associated with shellwidget as the current widget.
        """
        shellwidget_id = id(shellwidget)
        old_widget = self.current_widget()
        if shellwidget_id in self._shellwidgets:
            widget = self._shellwidgets[shellwidget_id]
            self.switch_widget(widget, old_widget)
            self._stack.setCurrentWidget(widget)

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

    def update_actions(self):
        """Update the actions."""
        widget = self.current_widget()

        for __, action in self.get_actions().items():
            if action:
                # IMPORTANT: Since we are defining the main actions in here
                # and the context is WidgetWithChildrenShortcut we need to
                # assign the same actions to the children widgets in order
                # for shortcuts to work
                if widget:
                    widget_actions = widget.actions()
                    if action not in widget_actions:
                        widget.addAction(action)
