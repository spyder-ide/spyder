# -----------------------------------------------------------------------------
# Copyright (c) 2020- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Spyder API auxiliary widgets.
"""

from __future__ import annotations

# Standard library imports
from typing import TYPE_CHECKING

# Third party imports
from qtpy.QtCore import QEvent, QSize, Signal
from qtpy.QtWidgets import QMainWindow, QSizePolicy, QToolBar, QWidget

# Local imports
from spyder.api.exceptions import SpyderAPIError
from spyder.api.widgets import PluginMainWidgetWidgets
from spyder.api.widgets.mixins import SpyderMainWindowMixin
from spyder.utils.stylesheet import APP_STYLESHEET

if TYPE_CHECKING:
    from qtpy.QtGui import QCloseEvent

    import spyder.utils.qthelpers  # For SpyderAction
    from spyder.api.widgets.main_widget import PluginMainWidget


class SpyderWindowWidget(QMainWindow, SpyderMainWindowMixin):
    """
    An undocked window for a :class:`~spyder.api.plugins.SpyderDockablePlugin`.
    """

    # ---- Signals
    # ------------------------------------------------------------------------
    sig_closed: Signal = Signal()
    """Signal emitted when the close event is fired."""

    sig_window_state_changed: Signal = Signal(object)
    """
    Signal is emitted when this window's state has changed.

    For instance, if the window changed between maximized and minimized state.

    Parameters
    ----------
    window_state: Qt.WindowStates
        The new window state that was changed to.
    """

    def __init__(self, widget: PluginMainWidget) -> None:
        """
        Create a window for a :class:`~spyder.api.plugins.SpyderDockablePlugin`.

        Parameters
        ----------
        widget : PluginMainWidget
            The main widget of this window's corresponding
            :class:`~spyder.api.plugins.SpyderDockablePlugin`.

        Returns
        -------
        None
        """
        super().__init__()

        self.widget: PluginMainWidget = widget
        """The main widget of this window's corresponding dockable plugin."""

        self.is_window_widget: bool = True
        """Distinguish these windows from the main Spyder one."""

        # Set interface theme
        self.setStyleSheet(str(APP_STYLESHEET))

    def closeEvent(self, event: QCloseEvent) -> None:
        """
        Event handler for when the window is closed.

        Overrides the default :meth:`QWidget.closeEvent` method to emit
        a custom :attr:`sig_closed` signal.
        """
        super().closeEvent(event)
        self.sig_closed.emit()

    def changeEvent(self, event: QEvent) -> None:
        """
        Event handler for when the window state is changed (e.g. minimized).

        Overrides the default :meth:`QWidget.changeEvent` method to emit
        a custom :attr:`sig_window_state_changed` signal.
        """
        if event.type() == QEvent.WindowStateChange:
            self.sig_window_state_changed.emit(self.windowState())
        super().changeEvent(event)


class MainCornerWidget(QToolBar):
    """
    Toolbar widget displayed in the top right hand corner of dockable plugins.

    It is used to display the options (hamburger) menu, progress spinner
    and additional toolbar items to the right of the main toolbar.
    """

    def __init__(self, parent: PluginMainWidget, name: str) -> None:
        """
        Create a new corner widget for a plugin's toolbar.

        Parameters
        ----------
        widget : PluginMainWidget
            The main widget of this window's corresponding
            :class:`~spyder.api.plugins.SpyderDockablePlugin`.
        name : str
            Name of this corner widget, nominally
            :attr:`spyder.api.widgets.PluginMainWidgetWidgets.CornerWidget`.

        Returns
        -------
        None
        """
        super().__init__(parent)
        self._icon_size = QSize(16, 16)
        self.setIconSize(self._icon_size)

        self._widgets = {}
        self._actions = []
        self.setObjectName(name)

        # We add an strut widget here so that there is a spacing
        # between the first item of the corner widget and the last
        # item of the MainWidgetToolbar.
        self._strut = QWidget()
        self._strut.setFixedWidth(0)
        self._strut.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.addWidget(self._strut)

    def add_widget(
        self,
        widget: spyder.utils.qthelpers.SpyderAction | QWidget,
        before: spyder.utils.qthelpers.SpyderAction | QWidget | None = None,
    ) -> None:
        """
        Add a widget to the corner toolbar.

        By default, widgets are added to the left of the last toolbar item.
        Corner widgets provide an options menu button and a spinner so any
        additional widgets will be placed the left of the spinner, if visible
        (unless ``before`` is set).

        Parameters
        ----------
        widget : spyder.utils.qthelpers.SpyderAction | QWidget
            The action or widget to add to the toolbar.
        before : spyder.utils.qthelpers.SpyderAction | QWidget | None, optional
            The action or widget to add ``widget`` before (to the right of).
            If ``None`` (the default), the widget will be added to the left
            of the left-most widget.

        Returns
        -------
        None

        Raises
        ------
        SpyderAPIError
            If either ``widget`` or ``before`` lacks a ``name`` attribute;
            a widget with the same ``name`` as ``widget`` was already added;
            a widget with ``before.name`` has not been added previously; or
            the first widget added is not the options (hamburger) menu widget.
        """
        if not hasattr(widget, "name") or (
            before is not None and not hasattr(before, "name")
        ):
            raise SpyderAPIError(
                f"Widget {widget} or {before} doesn't have a name, which must "
                f"be provided by the attribute `name`"
            )

        if widget.name in self._widgets:
            raise SpyderAPIError(
                'Widget with name "{}" already added. Current names are: {}'
                "".format(widget.name, list(self._widgets.keys()))
            )

        if before is not None and before.name not in self._widgets:
            raise SpyderAPIError(
                f"Widget with name '{before.name}' not in this corner widget"
            )

        if (
            not self._widgets
            and widget.name != PluginMainWidgetWidgets.OptionsToolButton
        ):
            raise SpyderAPIError(
                "The options button must be the first one to be added to the "
                "corner widget of dockable plugins."
            )

        if widget.name == PluginMainWidgetWidgets.OptionsToolButton:
            # This is only necessary for the options button because it's the
            # first one to be added
            action = self.addWidget(widget)
        else:
            if before is not None:
                before_action = self.get_action(before.name)
            else:
                # By default other buttons are added to the left of the last
                # one
                before_action = self._actions[-1]

            # Allow to add either widgets or actions
            if isinstance(widget, QWidget):
                action = self.insertWidget(before_action, widget)
            else:
                action = widget
                self.insertAction(before_action, action)
                widget = self.widgetForAction(action)
                widget.name = action.name

        self._widgets[widget.name] = (widget, action)
        self._actions.append(action)

    def get_widget(self, widget_id: str) -> QWidget | None:
        """
        Return a widget by its unique ID (i.e. its ``name`` attribute).

        Parameters
        ----------
        widget_id : str
            The ``name`` attribute of the widget to return.

        Returns
        -------
        QWidget | None
            The widget object corresponding to ``widget_id``, or ``None``
            if a widget with that ``name`` does not exist.
        """
        if widget_id in self._widgets:
            return self._widgets[widget_id][0]
        return None

    def get_action(
        self, widget_id: str
    ) -> spyder.utils.qthelpers.SpyderAction | None:
        """
        Return an action by its unique ID (i.e. its ``name`` attribute).

        Parameters
        ----------
        widget_id : str
            The ``name`` attribute of the action to return.

        Returns
        -------
        spyder.utils.qthelpers.SpyderAction | None
            The action object corresponding to ``widget_id``, or ``None``
            if an action with that ``name`` does not exist.
        """
        if widget_id in self._widgets:
            return self._widgets[widget_id][1]
        return None
