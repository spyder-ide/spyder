# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.widgets
==================

Here, 'plugin central widgets' are Qt main windows that should be used
to encapsulate the main interface of Spyder plugins.
"""

# ---- Standard library imports
import uuid

# ---- Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMainWindow, QToolBar

# ---- Local imports
from spyder.config.gui import is_dark_interface
from spyder.utils.qthelpers import create_toolbar_stretcher


class SpyderPluginToolbar(QToolBar):
    """
    Spyder plugin toolbar class.

    A toolbar used in Spyder plugins to add internal toolbars
    to their interface.
    """

    def __init__(self, parent=None, areas=Qt.TopToolBarArea,
                 corner_widget=None):
        super(SpyderPluginToolbar, self).__init__(parent)
        self._set_corner_widget(corner_widget)
        self.setObjectName("plugin_toolbar_{}".format(str(uuid.uuid4())[:8]))
        self.setFloatable(False)
        self.setMovable(False)
        self.setAllowedAreas(areas)
        self.setContextMenuPolicy(Qt.PreventContextMenu)
        self._setup_style()

    def addWidget(self, widget):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new widget in this toolbar.
        """
        if self._corner_widget is not None:
            super(SpyderPluginToolbar, self).insertWidget(
                self._corner_separator_action, widget)
        else:
            super(SpyderPluginToolbar, self).addWidget(widget)

    def addAction(self, action):
        """
        Override Qt method to take into account the existence of a corner
        widget when adding a new action in this toolbar.
        """
        if self._corner_widget is not None:
            super(SpyderPluginToolbar, self).insertAction(
                self._corner_separator_action, action)
        else:
            super(SpyderPluginToolbar, self).addAction(action)

    def _set_corner_widget(self, corner_widget):
        """
        Add the given corner widget to this toolbar.

        A stretcher widget is added before the corner widget so that
        its position is forced to the right side of the toolbar when the
        toolbar is resized.
        """
        self._corner_widget = corner_widget
        if corner_widget is not None:
            stretcher = create_toolbar_stretcher()
            self._corner_separator_action = (
                super(SpyderPluginToolbar, self).addWidget(stretcher))
            super(SpyderPluginToolbar, self).addWidget(self._corner_widget)
        else:
            self._corner_separator_action = None

    def _setup_style(self):
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


class PluginCentralWidget(QMainWindow):
    """
    Spyder plugin central widget class.

    Spyder plugins that need to add one or more toolbars to their
    interface should use this class to encapsulate their main interface.

    A Spyder plugin central widget is a Qt main window that consists of
    a single widget and a set of toolbars that are stacked above or below
    that widget. The toolbars are not moveable nor floatable and must
    occupy the entire horizontal space available for the plugin, i.e. that
    toolbars must be stacked vertically and cannot be placed horizontally
    next to each others.
    """

    def __init__(self, parent=None, options_button=None):
        super(PluginCentralWidget, self).__init__(parent)
        self.setWindowFlags(Qt.Widget)

        # Setup the main toolbar of the plugin.
        self._main_toolbar = SpyderPluginToolbar(corner_widget=options_button)
        self.addToolBar(self._main_toolbar)

        # Setup the a dictionary in which pointers to additional toolbars
        # added to the plugin interface are going to be saved.
        self._aux_toolbars = {Qt.TopToolBarArea: [], Qt.BottomToolBarArea: []}

    # ---- Public methods
    def create_auxialiary_toolbar(self, where='top'):
        """
        Create and add an auxiliary toolbar at the top or at the bottom
        of the plugin.

        Parameters
        ----------
        where: str
            A string whose value is used to determine where to add the
            toolbar in the plugin interface. The toolbar can be added either
            at the 'top' or at the 'bottom' of the plugin.

        Returns
        -------
        SpyderPluginToolbar
            The auxiliary toolbar that was created and added to the plugin
            interface.
        """
        toolbar = SpyderPluginToolbar()
        self.add_auxialiary_toolbar(toolbar, where)
        return toolbar

    def add_auxialiary_toolbar(self, toolbar, where='top'):
        """
        Add the given toolbar at the top or at the bottom of the plugin.

        Parameters
        ----------
        toolbar: QToolBar
            The SpyderPluginToolbar that needs to be added to the plugin
            interface.
        where: str
            A string whose value is used to determine where to add the given
            toolbar in the plugin interface. The toolbar can be added either
            at the 'top' or at the 'bottom' of the plugin.
        """
        if where == 'top' or (where == 'bottom' and self._aux_toolbars[where]):
            self.addToolBarBreak(where)

        toolbar.setAllowedAreas(
            Qt.BottomToolBarArea if where == 'bottom' else Qt.TopToolBarArea)
        self.addToolBar(toolbar)
        self._aux_toolbars[where].append(toolbar)

    def get_main_toolbar(self):
        """
        Return the main toolbar of the plugin.

        Returns
        -------
        QToolBar
            The main toolbar of the plugin that contains the options button.
        """
        return self._main_toolbar

    def get_widget(self):
        """
        Return the central widget of the plugin.

        Returns
        -------
        (QWidget, None)
            The central widget of the plugin or None if the widget has
            not been set.
        """
        return self.centralWidget()

    def set_widget(self, widget):
        """
        Set the given widget as the central widget of the plugin.

        Parameters
        ----------
        widget: QWidget
            Widget to be set as the central widget of the plugin.
        """
        self.setCentralWidget(widget)

    def set_iconsize(self, iconsize):
        """
        Set the icon size of the plugin's toolbars.

        Parameters
        ----------
        iconsize: int
            An integer corresponding to the size in pixels to which the icons
            of the plugin's toolbars need to be set.
        """
        pass
