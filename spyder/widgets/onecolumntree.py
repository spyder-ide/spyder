# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Third party imports
from qtpy.QtCore import Slot
from qtpy.QtWidgets import QTreeWidget, QMenu

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (add_actions, create_action,
                                    get_item_user_text)


class OneColumnTree(QTreeWidget):
    """One-column tree widget with context menu, ..."""
    def __init__(self, parent):
        QTreeWidget.__init__(self, parent)
        self.setItemsExpandable(True)
        self.setColumnCount(1)
        self.itemActivated.connect(self.activated)
        self.itemClicked.connect(self.clicked)
        # Setup context menu
        self.menu = QMenu(self)
        self.collapse_all_action = None
        self.collapse_selection_action = None
        self.expand_all_action = None
        self.expand_selection_action = None
        self.common_actions = self.setup_common_actions()

        self.__expanded_state = None

        self.itemSelectionChanged.connect(self.item_selection_changed)
        self.item_selection_changed()

    def activated(self, item):
        """Double-click event"""
        raise NotImplementedError

    def clicked(self, item):
        pass

    def set_title(self, title):
        self.setHeaderLabels([title])

    def setup_common_actions(self):
        """Setup context menu common actions"""
        self.collapse_all_action = create_action(self,
                                     text=_('Collapse all'),
                                     icon=ima.icon('collapse'),
                                     triggered=self.collapseAll)
        self.expand_all_action = create_action(self,
                                     text=_('Expand all'),
                                     icon=ima.icon('expand'),
                                     triggered=self.expandAll)
        self.restore_action = create_action(self,
                                     text=_('Restore'),
                                     tip=_('Restore original tree layout'),
                                     icon=ima.icon('restore'),
                                     triggered=self.restore)
        self.collapse_selection_action = create_action(
            self,
            text=_('Collapse section'),
            icon=ima.icon('collapse_selection'),
            triggered=self.collapse_selection
        )
        self.expand_selection_action = create_action(
            self,
            text=_('Expand section'),
            icon=ima.icon('expand_selection'),
            triggered=self.expand_selection
        )
        return [self.collapse_all_action, self.expand_all_action, None,
                self.collapse_selection_action, self.expand_selection_action]

    def get_menu_actions(self):
        """Returns a list of menu actions"""
        items = self.selectedItems()
        actions = self.get_actions_from_items(items)
        if actions:
            actions.append(None)
        actions += self.common_actions
        return actions

    def update_menu(self):
        self.menu.clear()
        actions = self.get_menu_actions()
        add_actions(self.menu, actions)

    def get_actions_from_items(self, items):
        # Right here: add other actions if necessary
        # (reimplement this method)
        return []

    @Slot()
    def restore(self):
        self.collapseAll()
        for item in self.get_top_level_items():
            self.expandItem(item)

    def is_item_expandable(self, item):
        """To be reimplemented in child class
        See example in project explorer widget"""
        return True

    def __expand_item(self, item):
        if self.is_item_expandable(item):
            self.expandItem(item)
            for index in range(item.childCount()):
                child = item.child(index)
                self.__expand_item(child)

    @Slot()
    def expand_selection(self):
        items = self.selectedItems()
        if not items:
            items = self.get_top_level_items()
        for item in items:
            self.__expand_item(item)
        if items:
            self.scrollToItem(items[0])

    def __collapse_item(self, item):
        self.collapseItem(item)
        for index in range(item.childCount()):
            child = item.child(index)
            self.__collapse_item(child)

    @Slot()
    def collapse_selection(self):
        items = self.selectedItems()
        if not items:
            items = self.get_top_level_items()
        for item in items:
            self.__collapse_item(item)
        if items:
            self.scrollToItem(items[0])

    def item_selection_changed(self):
        """Item selection has changed"""
        is_selection = len(self.selectedItems()) > 0
        self.expand_selection_action.setEnabled(is_selection)
        self.collapse_selection_action.setEnabled(is_selection)

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
            user_text = get_item_user_text(item)
            self.__expanded_state[hash(user_text)] = item.isExpanded()
        def browse_children(item):
            add_to_state(item)
            for index in range(item.childCount()):
                citem = item.child(index)
                user_text = get_item_user_text(citem)
                self.__expanded_state[hash(user_text)] = citem.isExpanded()
                browse_children(citem)
        for tlitem in self.get_top_level_items():
            browse_children(tlitem)

    def restore_expanded_state(self):
        """Restore all items expanded state"""
        if self.__expanded_state is None:
            return
        for item in self.get_items()+self.get_top_level_items():
            user_text = get_item_user_text(item)
            is_expanded = self.__expanded_state.get(hash(user_text))
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
