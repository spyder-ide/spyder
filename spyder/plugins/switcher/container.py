# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Main Container."""

# Third-party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QApplication

# Spyder imports
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.switcher.widgets.switcher import Switcher


class SwitcherContainer(PluginMainContainer):

    # --- PluginMainContainer API
    # ------------------------------------------------------------------------
    def setup(self):
        self.switcher = Switcher(self._plugin.get_main())

        # Switcher shortcuts
        self.create_action(
            'file switcher',
            _('File switcher...'),
            icon=self._plugin.get_icon(),
            tip=_('Fast switch between files'),
            triggered=self.open_switcher,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )

        self.create_action(
            'symbol finder',
            _('Symbol finder...'),
            icon=self.create_icon('symbol_find'),
            tip=_('Fast symbol search in file'),
            triggered=self.open_symbolfinder,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )

    def update_actions(self):
        pass

    # --- Public API
    # ------------------------------------------------------------------------
    def open_switcher(self, symbol=False):
        """Open switcher dialog."""
        switcher = self.switcher
        if switcher is not None and switcher.isVisible():
            switcher.clear()
            switcher.hide()
            return

        # Set mode and setup
        if symbol:
            switcher.set_search_text('@')
        else:
            switcher.set_search_text('')

        # Setup
        switcher.setup()

        # Set position
        mainwindow = self._plugin.get_main()

        # Note: The +8 pixel on the top makes it look better
        default_top = (mainwindow.toolbar.toolbars_menu.geometry().height() +
                       mainwindow.menuBar().geometry().height() + 8)

        current_window = QApplication.activeWindow()
        if current_window == mainwindow:
            if self.get_conf('toolbars_visible', section='toolbar'):
                delta_top = default_top
            else:
                delta_top = mainwindow.menuBar().geometry().height() + 8
        else:
            delta_top = default_top

        switcher.set_position(delta_top, current_window)
        switcher.show()

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_switcher(symbol=True)
