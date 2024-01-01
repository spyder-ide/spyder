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
from superqt.utils import signals_blocked

# Spyder imports
from spyder.api.translations import _
from spyder.api.widgets.main_container import PluginMainContainer
from spyder.plugins.switcher.api import SwitcherActions
from spyder.plugins.switcher.widgets.switcher import Switcher
from spyder.utils.stylesheet import APP_TOOLBAR_STYLESHEET


class SwitcherContainer(PluginMainContainer):

    # ---- PluginMainContainer API
    # -------------------------------------------------------------------------
    def setup(self):
        self.switcher = Switcher(self._plugin.get_main())

        # Switcher shortcuts
        self.create_action(
            SwitcherActions.FileSwitcherAction,
            _('File switcher...'),
            icon=self._plugin.get_icon(),
            tip=_('Fast switch between files'),
            triggered=self.open_switcher,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )

        self.create_action(
            SwitcherActions.SymbolFinderAction,
            _('Symbol finder...'),
            icon=self.create_icon('symbol_find'),
            tip=_('Fast symbol search in file'),
            triggered=self.open_symbolfinder,
            register_shortcut=True,
            context=Qt.ApplicationShortcut
        )

    def update_actions(self):
        pass

    # ---- Public API
    # -------------------------------------------------------------------------
    def open_switcher(self, symbol=False):
        """Open switcher dialog."""
        switcher = self.switcher
        if switcher is not None and switcher.isVisible():
            switcher.clear()
            switcher.hide()
            return

        # Set mode and setup
        if symbol:
            # Avoid emitting sig_search_text_available
            with signals_blocked(switcher.edit):
                switcher.set_search_text('@')

            # Manually set mode and emit sig_mode_selected so that symbols are
            # shown instantly.
            switcher._mode_on = "@"
            switcher.sig_mode_selected.emit("@")
        else:
            switcher.set_search_text('')

        # Setup
        switcher.setup()

        # Set position
        mainwindow = self._plugin.get_main()

        # Note: The +3 pixels makes it vertically align with the main menu or
        # main menu + toolbar
        default_top_without_toolbar = (
            mainwindow.menuBar().geometry().height()
            + 3
        )

        default_top_with_toolbar = (
            int(APP_TOOLBAR_STYLESHEET.BUTTON_HEIGHT.split("px")[0])
            + default_top_without_toolbar
        )

        current_window = QApplication.activeWindow()
        if current_window == mainwindow:
            if self.get_conf('toolbars_visible', section='toolbar'):
                delta_top = default_top_with_toolbar
            else:
                delta_top = default_top_without_toolbar
        else:
            delta_top = default_top_with_toolbar

        switcher.set_position(delta_top, current_window)
        switcher.show()

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_switcher(symbol=True)
