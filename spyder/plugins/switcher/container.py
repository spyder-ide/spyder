# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Switcher Main Container."""

# Third-party imports
from qtpy.QtCore import Qt

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

        if symbol:
            switcher.set_search_text('@')
        else:
            switcher.set_search_text('')
            switcher.setup()

        switcher.show()

        # Note: The +8 pixel on the top makes it look better
        # FIXME: Why is this using the toolbars menu? A: To not be on top of
        # the toolbars.
        # Probably toolbars should be taken into account for this 'delta' only
        # when are visible
        mainwindow = self._plugin.get_main()
        delta_top = (mainwindow.toolbar.toolbars_menu.geometry().height() +
                     mainwindow.menuBar().geometry().height() + 8)

        switcher.set_position(delta_top)

    def open_symbolfinder(self):
        """Open symbol list management dialog box."""
        self.open_switcher(symbol=True)
