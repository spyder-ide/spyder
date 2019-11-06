# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.panes
==================

Here, 'panes' are Qt main windows that should be used to encapsulate the
main interface of Spyder plugins.
"""

# ---- Standard library imports
import uuid

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QToolBar

# ---- Local imports
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import create_toolbar_stretcher


class SpyderPaneToolbar(QToolBar):
    """
    Spyder pane toolbar class.

    A toolbar class that is used by the spyder pane widget class.
    """

    def __init__(self, parent=None, areas=Qt.TopToolBarArea,
                 corner_widget=None):
        super().__init__(parent)
        self._set_corner_widget(corner_widget)
        self.setObjectName("pane_toolbar_{}".format(str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setAllowedAreas(areas)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self._set_style()

    def addWidget(self, widget):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new widget in this toolbar.
        """
        if self._corner_widget is not None:
            super().insertWidget(self._corner_separator_action, widget)
        else:
            super().addWidget(widget)

    def addAction(self, action):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new action in this toolbar.
        """
        if self._corner_widget is not None:
            super().insertAction(self._corner_separator_action, action)
        else:
            super().addAction(action)

    def _set_corner_widget(self, corner_widget):
        """
        Add the given corner widget to this toolbar.

        A stretcher widget is added before the corner widget so that
        its position is forced to the right side of the toolbar when the
        toolbar is resized.
        """
        self._corner_widget = corner_widget
        if corner_widget is not None:
            self._corner_separator_action = super().addWidget(
                create_toolbar_stretcher())
            super().addWidget(self._corner_widget)
        else:
            self._corner_separator_action = None

    def _set_style(self):
        """
        Set the style of this toolbar with a stylesheet.
        """
        if is_dark_interface():
            self.setStyleSheet(
                "QToolButton {background-color: transparent;} "
                "QToolButton:!hover:!pressed {border-color: transparent} "
                "QToolBar {border: 0px;  background: rgb(25, 35, 45);}")
        else:
            self.setStyleSheet("QToolBar {border: 0px;}")


class SpyderPaneWidget(QMainWindow):
    """
    Spyder pane widget class.

    All Spyder plugins that need to add a pane to the Spyder mainwindow
    *must* use a Spyder pane widget to encapsulate their main interface.

    A Spyder pane widget is a Qt main window that consists of a central
    widget and a set of toolbars that are stacked above or below the central
    widget. The toolbars are not moveable nor floatable and must occupy
    the entire horizontal space available for the pane, i.e. that toolbars
    must be stacked vertically and cannot be placed horizontally
    next to each others.
    """

    def __init__(self, parent=None, options_button=None):
        super().__init__(parent)
        self.setWindowFlags(Qt.Widget)

        self._main_toolbar = SpyderPaneToolbar(corner_widget=options_button)
        self.addToolBar(self._main_toolbar)
        self._aux_toolbars = {Qt.TopToolBarArea: [], Qt.BottomToolBarArea: []}

    # ---- Public methods
    def create_auxialiary_toolbar(self, where='above'):
        """
        Add to this pane an auxiliary toolbar above or below this
        pane central widget.

        Parameters
        ----------
        where: str
            A string whose value is used to determine where to add the
            toolbar in the pane. The toolbar is added above the pane's central
            widget when the value of 'where' is 'above', while it is added
            below the central widget when it is 'below'.

        Returns
        -------
        QToolBar
            The toolbar that was created and added as an auxiliary toolbar
            to this pane.
        """
        where = (Qt.BottomToolBarArea if where == 'below'
                 else Qt.TopToolBarArea)
        toolbar = SpyderPaneToolbar(areas=where)

        if (where == Qt.TopToolBarArea or
                where == Qt.BottomToolBarArea and self._aux_toolbars[where]):
            self.addToolBarBreak(where)
        self.addToolBar(toolbar)
        self._aux_toolbars[where].append(toolbar)

        return toolbar

    def get_main_toolbar(self):
        """
        Return the main toolbar of this pane.

        Returns
        -------
        QToolBar
            The main toolbar of this pane.
        """
        return self._main_toolbar

    def get_central_widget(self):
        """
        Return the central widget of this pane.

        Returns
        -------
        (QWidget, None)
            The central widget of this pane or None if the central widget has
            not been set.
        """
        return self.centralWidget()

    def set_central_widget(self, widget):
        """
        Set the given widget to be the central widget of this pane.

        Parameters
        ----------
        widget: QWidget
            Widget to set as the central widget of this pane.
        """
        self.setCentralWidget(widget)

    def set_iconsize(self, iconsize):
        """
        Set the icon size of this pane toolbars.

        Parameters
        ----------
        iconsize: int
            An integer corresponding to the size in pixels to which the icons
            of this pane toolbars need to be set.
        """
        pass
