# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
spyderlib.widgets
=================

Widgets defined in this module may be used in any other PyQt4-based application

They are also used in Spyder through the Plugin interface
(see spyderlib.plugins)
"""

from PyQt4.QtGui import QTreeWidget, QMenu
from PyQt4.QtCore import SIGNAL

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import create_action, add_actions, translate

class OneColumnTree(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*,int)'),
                     self.activated)
        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()
                     
    def activated(self):
        raise NotImplementedError
                     
    def set_title(self, title):
        self.setHeaderLabels([title])
                     
    def setup_common_actions(self):
        """Setup context menu common actions"""
        collapse_act = create_action(self,
                    text=translate('OneColumnTree', 'Collapse all'),
                    icon=get_icon('collapse.png'),
                    triggered=self.collapseAll)
        expand_act = create_action(self,
                    text=translate('OneColumnTree', 'Expand all'),
                    icon=get_icon('expand.png'),
                    triggered=self.expandAll)
        return [collapse_act, expand_act]
                     
    def update_menu(self):
        self.menu.clear()
        items = self.selectedItems()
        actions = self.get_actions_from_items(items)
        if actions:
            actions.append(None)
        actions += self.common_actions
        add_actions(self.menu, actions)
        
    def get_actions_from_items(self, items):
        # Right here: add other actions if necessary
        # (reimplement this method)
        return []
                     
    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())
        
