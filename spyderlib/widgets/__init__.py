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
from PyQt4.QtCore import SIGNAL, Qt, QVariant

# Local imports
from spyderlib.config import get_icon
from spyderlib.utils.qthelpers import (create_action, add_actions, translate,
                                       get_item_user_text)

class OneColumnTree(QTreeWidget):
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.connect(self, SIGNAL('itemActivated(QTreeWidgetItem*,int)'),
                     self.activated)
        self.connect(self, SIGNAL('itemClicked(QTreeWidgetItem*,int)'),
                     self.clicked)
        # Setup context menu
        self.menu = QMenu(self)
        self.common_actions = self.setup_common_actions()
        
        self.__expanded_state = None
                     
    def activated(self):
        raise NotImplementedError
        
    def clicked(self):
        pass
                     
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
    
    def get_top_level_items(self):
        """Iterate over top level items"""
        return [self.topLevelItem(_i) for _i in range(self.topLevelItemCount())]
    
    def get_items(self):
        """Return items (excluding top level items)"""
        itemlist = []
        def add_to_itemlist(item):
            for index in range(item.childCount()):
                citem = item.child(index)
                itemlist.append(citem)
                add_to_itemlist(citem)
        for tlitem in self.get_top_level_items():
            add_to_itemlist(tlitem)
        return itemlist
    
    def get_scrollbar_position(self):
        return (self.horizontalScrollBar().value(),
                self.verticalScrollBar().value())
        
    def set_scrollbar_position(self, position):
        hor, ver = position
        self.horizontalScrollBar().setValue(hor)
        self.verticalScrollBar().setValue(ver)
        
    def get_expanded_state(self):
        self.save_expanded_state()
        return self.__expanded_state
    
    def set_expanded_state(self, state):
        self.__expanded_state = state
        self.restore_expanded_state()
    
    def save_expanded_state(self):
        """Save all items expanded state"""
        self.__expanded_state = {}
        def add_to_state(item):
            for index in range(item.childCount()):
                citem = item.child(index)
                user_text = get_item_user_text(citem)
                self.__expanded_state[user_text] = citem.isExpanded()
                add_to_state(citem)
        for tlitem in self.get_top_level_items():
            add_to_state(tlitem)
    
    def restore_expanded_state(self):
        """Restore all items expanded state"""
        if self.__expanded_state is None:
            return
        for item in self.get_items():
            user_text = get_item_user_text(item)
            is_expanded = self.__expanded_state.get(user_text)
            if is_expanded is not None:
                item.setExpanded(is_expanded)

    def sort_top_level_items(self, key):
        """Sorting tree wrt top level items"""
        self.save_expanded_state()
        items = sorted([self.takeTopLevelItem(0)
                        for index in range(self.topLevelItemCount())], key=key)
        for index, item in enumerate(items):
            self.insertTopLevelItem(index, item)
        self.restore_expanded_state()
                     
    def contextMenuEvent(self, event):
        """Override Qt method"""
        self.update_menu()
        self.menu.popup(event.globalPos())
        
