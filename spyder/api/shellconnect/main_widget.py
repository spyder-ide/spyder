# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Main widget for plugins showing content from the IPython Console.

Used in, for example, the :guilabel:`Variable Explorer`, :guilabel:`Plots`,
:guilabel:`Debugger` and :guilabel:`Profiler` plugins.
"""

from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING, Any

# Third party imports
from qtpy.QtWidgets import QStackedWidget, QVBoxLayout

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.widgets.emptymessage import EmptyMessageWidget

if TYPE_CHECKING:
    from qtpy.QtWidgets import QWidget

    import spyder.plugins.ipythonconsole.widgets


class _ErroredMessageWidget(EmptyMessageWidget):
    """Widget to show when the kernel's shell failed to start."""

    def __init__(
        self,
        parent: ShellConnectMainWidget,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Initialize :class:`EmptyMessageWidget` with content to show for errors.

        Parameters
        ----------
        parent : ShellConnectMainWidget
            The parent widget of this one.
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that failed to launch.

        Returns
        -------
        None
        """
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

        self.is_empty: bool = False
        """
        If the current widget has no content to show.

        Used to show this widget if :class:`ShellConnectMainWidget` has an
        empty message.
        """


class ShellConnectMainWidget(PluginMainWidget):
    """
    Main widget to use in a plugin that shows different content per-console.

    It is composed of a :class:`QStackedWidget` to stack the widget associated
    to each console shell widget, and only show one of them at a time.
    The current widget in the stack displays the content corresponding to
    the console with focus.

    Used in the :guilabel:`Variable Explorer` and :guilabel:`Plots` plugins,
    for example, to show the variables and plots of the current console.
    """

    def __init__(
        self, *args: Any, set_layout: bool = True, **kwargs: Any
    ) -> None:
        """
        Create a new main widget to show console-specific content.

        Parameters
        ----------
        *args : Any
            Positional arguments to pass to
            :meth:`PluginMainWidget.__init__() <spyder.api.widgets.main_widget.PluginMainWidget.__init__>`.
        set_layout : bool, optional
            Whether to add the created widget to a layout, ``True`` by default.
        **kwargs : Any
            Keyword arguments to pass to
            :meth:`PluginMainWidget.__init__() <spyder.api.widgets.main_widget.PluginMainWidget.__init__>`.

        Returns
        -------
        None
        """
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
    def current_widget(self) -> QWidget:
        """
        Get the currently displayed widget (either the stack or error widget).

        Returns
        -------
        QWidget
            The currently displayed widget, either the active widget in the
            stack associated with the current
            :class:`~spyder.plugins.ipythonconsole.widgets.ShellWidget`
            (i.e. :guilabel:`IPython Console` tab),
            or if that kernel failed with an error, the error message widget.
        """
        return self._content_widget

    def get_focus_widget(self) -> QWidget:
        """
        Get the stack widget associated to the currently active shell widget.

        Used by
        :meth:`~spyder.api.widgets.main_widget.PluginMainWidget.change_visibility`
        when switching to the plugin.

        Returns
        -------
        QWidget
            The current widget in the stack, associated with the active
            :class:`~spyder.plugins.ipythonconsole.widgets.ShellWidget`
            (i.e. :guilabel:`IPython Console` tab), to give focus to.
        """
        return self._stack.currentWidget()

    # ---- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    def update_style(self) -> None:
        """
        Update the stylesheet and style of the stack widget.

        .. caution::

            If overriding this method, :class:`super` must be called
            for this widget to display correctly in the Spyder UI.

        Returns
        -------
        None
        """
        self._stack.setStyleSheet("QStackedWidget {padding: 0px; border: 0px}")

    # ---- Stack accesors
    # ------------------------------------------------------------------------
    def count(self) -> int:
        """
        Get the number of widgets in the stack.

        Returns
        -------
        int
            The number of widgets in the stack.
        """
        return self._stack.count()

    def get_widget_for_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> QWidget | None:
        """
        Retrieve the stacked widget corresponding to the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to return the associated widget of.

        Returns
        -------
        QWidget | None
            The widget in the stack associated with ``shellwidget``,
            or ``None`` if not found.
        """
        shellwidget_id = id(shellwidget)
        if shellwidget_id in self._shellwidgets:
            return self._shellwidgets[shellwidget_id]
        return None

    # ---- Public API
    # ------------------------------------------------------------------------
    def add_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Create a new widget in the stack associated to a given shell widget.

        This method registers a new widget to display the content that
        is associated with the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate the new widget to.

        Returns
        -------
        None
        """
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

    def remove_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Remove the stacked widget associated to a given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to remove the associated widget of.

        Returns
        -------
        None
        """
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

    def set_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Set as active the stack widget associated with the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget that corresponds to the stacked widget to set
            as currently active.

        Returns
        -------
        None
        """
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

    def add_errored_shellwidget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> None:
        """
        Add an error widget for a shell widget whose kernel failed to start.

        This is necessary to show a meaningful message when switching to
        consoles with dead kernels.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to associate with a new error widget.

        Returns
        -------
        None
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

    def create_new_widget(
        self,
        shellwidget: spyder.plugins.ipythonconsole.widgets.ShellWidget,
    ) -> QWidget:
        """
        Create a new widget to communicate with the given shell widget.

        Parameters
        ----------
        shellwidget : spyder.plugins.ipythonconsole.widgets.ShellWidget
            The shell widget to create a new associated widget for.

        Returns
        -------
        QWidget
            The newly-created widget associated with ``shellwidget``.
        """
        raise NotImplementedError

    def close_widget(self, widget: QWidget) -> None:
        """
        Close the given stacked widget.

        Parameters
        ----------
        widget : QWidget
            The widget to close.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def switch_widget(self, widget: QWidget, old_widget: QWidget) -> None:
        """
        Switch the given stacked widget.

        Parameters
        ----------
        widget : QWidget
            The widget to switch to.
        old_widget : QWidget
            The previously-active widget.

        Returns
        -------
        None
        """
        raise NotImplementedError

    def refresh(self) -> None:
        """
        Refresh the current stacked widget.

        Returns
        -------
        None
        """
        if self.count():
            widget = self.current_widget()
            widget.refresh()

    def is_current_widget_error_message(self) -> bool:
        """
        Check if the current widget is showing an error message.

        Returns
        -------
        bool
            ``True`` if the current widget is showing an error message,
            ``False`` if not.
        """
        return isinstance(self.current_widget(), _ErroredMessageWidget)

    def switch_empty_message(self, value: bool) -> None:
        """
        Switch between the empty message widget or the one with content.

        Parameters
        ----------
        value : bool
            If ``True``, switch to the empty widget; if ``False``, switch
            to the content widget.

        Returns
        -------
        None
        """
        if value:
            self.show_empty_message()
        else:
            self.show_content_widget()
