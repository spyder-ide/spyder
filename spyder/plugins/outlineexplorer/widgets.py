# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer widgets."""

# Standard library imports
import bisect
import os.path as osp
import uuid

# Third party imports
from intervaltree import IntervalTree
from qtpy.compat import from_qvariant
from qtpy.QtCore import Qt, QTimer, Signal, Slot
from qtpy.QtWidgets import (QHBoxLayout, QTreeWidgetItem,
                            QTreeWidgetItemIterator)

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.api.widgets.main_widget import PluginMainWidget
from spyder.config.base import _
from spyder.py3compat import to_text_string
from spyder.utils.icon_manager import ima
from spyder.plugins.completion.api import SymbolKind, SYMBOL_KIND_ICON
from spyder.utils.qthelpers import set_item_user_text
from spyder.widgets.onecolumntree import OneColumnTree


SYMBOL_NAME_MAP = {
    SymbolKind.FILE: _('File'),
    SymbolKind.MODULE: _('Module'),
    SymbolKind.NAMESPACE: _('Namespace'),
    SymbolKind.PACKAGE: _('Package'),
    SymbolKind.CLASS: _('Class'),
    SymbolKind.METHOD: _('Method'),
    SymbolKind.PROPERTY: _('Property'),
    SymbolKind.FIELD: _('Attribute'),
    SymbolKind.CONSTRUCTOR: _('constructor'),
    SymbolKind.ENUM: _('Enum'),
    SymbolKind.INTERFACE: _('Interface'),
    SymbolKind.FUNCTION: _('Function'),
    SymbolKind.VARIABLE: _('Variable'),
    SymbolKind.CONSTANT: _('Constant'),
    SymbolKind.STRING: _('String'),
    SymbolKind.NUMBER: _('Number'),
    SymbolKind.BOOLEAN: _('Boolean'),
    SymbolKind.ARRAY: _('Array'),
    SymbolKind.OBJECT: _('Object'),
    SymbolKind.KEY: _('Key'),
    SymbolKind.NULL: _('Null'),
    SymbolKind.ENUM_MEMBER: _('Enum member'),
    SymbolKind.STRUCT: _('Struct'),
    SymbolKind.EVENT: _('Event'),
    SymbolKind.OPERATOR: _('Operator'),
    SymbolKind.TYPE_PARAMETER: _('Type parameter'),
    SymbolKind.CELL: _('Cell'),
    SymbolKind.BLOCK_COMMENT: _('Block comment')
}

ICON_CACHE = {}


def line_span(position):
    return position[1] - position[0] + 1


class OutlineExplorerToolbuttons:
    GoToCursor = 'go_to_cursor'


class OutlineExplorerSections:
    Main = 'main_section'
    DisplayOptions = 'display_options'


class OutlineExplorerActions:
    GoToCursor = 'go_to_cursor'
    ShowFullPath = 'show_fullpath'
    ShowAllFiles = 'show_all_files'
    ShowSpecialComments = 'show_comments'
    GroupCodeCells = 'group_code_cells'
    DisplayVariables = 'display_variables'
    FollowCursor = 'follow_cursor'
    SortFiles = 'sort_files_alphabetically'


class SymbolStatus:
    def __init__(self, name, kind, position, path, node=None):
        self.name = name
        self.position = position
        self.kind = kind
        self.node = node
        self.path = path
        self.id = str(uuid.uuid4())
        self.index = None
        self.children = []
        self.status = False
        self.selected = False
        self.parent = None

    def delete(self):
        for child in self.children:
            child.parent = None

        self.children = []
        self.node.takeChildren()

        if self.parent is not None:
            self.parent.remove_node(self)
            self.parent = None

        if self.node.parent is not None:
            self.node.parent.remove_children(self.node)

    def add_node(self, node):
        if node.position == self.position:
            # The nodes should be at the same level
            self.parent.add_node(node)
        else:
            node.parent = self
            node.path = self.path
            this_node = self.node
            children_ranges = [c.position[0] for c in self.children]
            node_range = node.position[0]
            new_index = bisect.bisect_left(children_ranges, node_range)
            node.index = new_index
            for child in self.children[new_index:]:
                child.index += 1
            this_node.append_children(new_index, node.node)
            self.children.insert(new_index, node)
            for idx, next_idx in zip(self.children, self.children[1:]):
                assert idx.index < next_idx.index

    def remove_node(self, node):
        for child in self.children[node.index + 1:]:
            child.index -= 1
        self.children.pop(node.index)
        for idx, next_idx in zip(self.children, self.children[1:]):
            assert idx.index < next_idx.index

    def clone_node(self, node):
        self.id = node.id
        self.index = node.index
        self.path = node.path
        self.children = node.children
        self.status = node.status
        self.selected = node.selected
        self.node = node.node
        self.parent = node.parent
        self.node.update_info(self.name, self.kind, self.position[0] + 1,
                              self.status, self.selected)
        self.node.ref = self

        for child in self.children:
            child.parent = self

        if self.parent is not None:
            self.parent.replace_node(self.index, self)

    def refresh(self):
        self.node.update_info(self.name, self.kind, self.position[0] + 1,
                              self.status, self.selected)

    def replace_node(self, index, node):
        self.children[index] = node

    def create_node(self):
        self.node = SymbolItem(None, self, self.name, self.kind,
                               self.position[0] + 1, self.status,
                               self.selected)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '({0}, {1}, {2}, {3})'.format(
            self.position, self.name, self.id, self.status)


class BaseTreeItem(QTreeWidgetItem):
    def clear(self):
        self.takeChildren()

    def append_children(self, index, node):
        self.insertChild(index, node)
        node.parent = self

    def remove_children(self, node):
        self.removeChild(node)
        node.parent = None


class FileRootItem(BaseTreeItem):
    def __init__(self, path, ref, treewidget, is_python=True):
        QTreeWidgetItem.__init__(self, treewidget, QTreeWidgetItem.Type)
        self.path = path
        self.ref = ref
        self.setIcon(
            0, ima.icon('python') if is_python else ima.icon('TextFileIcon'))
        self.setToolTip(0, path)
        set_item_user_text(self, path)

    def set_path(self, path, fullpath):
        self.path = path
        self.set_text(fullpath)

    def set_text(self, fullpath):
        self.setText(0, self.path if fullpath else osp.basename(self.path))


class SymbolItem(BaseTreeItem):
    """Generic symbol tree item."""
    def __init__(self, parent, ref, name, kind, position, status, selected):
        QTreeWidgetItem.__init__(self, parent, QTreeWidgetItem.Type)
        self.parent = parent
        self.ref = ref
        self.num_children = 0
        self.update_info(name, kind, position, status, selected)

    def update_info(self, name, kind, position, status, selected):
        self.setIcon(0, ima.icon(SYMBOL_KIND_ICON.get(kind, 'no_match')))
        identifier = SYMBOL_NAME_MAP.get(kind, '')
        identifier = identifier.replace('_', ' ').capitalize()
        self.setToolTip(0, '{3} {2}: {0} {1}'.format(
            identifier, name, position, _('Line')))
        set_item_user_text(self, name)
        self.setText(0, name)
        self.setExpanded(status)
        self.setSelected(selected)


class TreeItem(QTreeWidgetItem):
    """Class browser item base class."""
    def __init__(self, oedata, parent, preceding):
        if preceding is None:
            QTreeWidgetItem.__init__(self, parent, QTreeWidgetItem.Type)
        else:
            if preceding is not parent:
                # Preceding must be either the same as item's parent
                # or have the same parent as item
                while preceding.parent() is not parent:
                    preceding = preceding.parent()
                    if preceding is None:
                        break
            if preceding is None:
                QTreeWidgetItem.__init__(self, parent, QTreeWidgetItem.Type)
            else:
                QTreeWidgetItem.__init__(self, parent, preceding,
                                         QTreeWidgetItem.Type)
        self.parent_item = parent
        self.oedata = oedata
        oedata.sig_update.connect(self.update)
        self.update()

    def level(self):
        """Get fold level."""
        return self.oedata.fold_level

    def get_name(self):
        """Get the item name."""
        return self.oedata.def_name

    def set_icon(self, icon):
        self.setIcon(0, icon)

    def setup(self):
        self.setToolTip(0, _("Line %s") % str(self.line))

    @property
    def line(self):
        """Get line number."""
        block_number = self.oedata.get_block_number()
        if block_number is not None:
            return block_number + 1
        return None

    def update(self):
        """Update the tree element."""
        name = self.get_name()
        self.setText(0, name)
        parent_text = from_qvariant(self.parent_item.data(0, Qt.UserRole),
                                    to_text_string)
        set_item_user_text(self, parent_text + '/' + name)
        self.setup()


class OutlineExplorerTreeWidget(OneColumnTree):
    # Used only for debug purposes
    sig_tree_updated = Signal()
    sig_display_spinner = Signal()
    sig_hide_spinner = Signal()
    sig_update_configuration = Signal()

    CONF_SECTION = 'outline_explorer'

    def __init__(self, parent):
        self.show_fullpath = self.get_conf('show_fullpath')
        self.show_all_files = self.get_conf('show_all_files')
        self.group_cells = self.get_conf('group_cells')
        self.show_comments = self.get_conf('show_comments')
        self.sort_files_alphabetically = self.get_conf(
            'sort_files_alphabetically')
        self.follow_cursor = self.get_conf('follow_cursor')
        self.display_variables = self.get_conf('display_variables')

        super().__init__(parent)

        self.freeze = False  # Freezing widget to avoid any unwanted update
        self.editor_items = {}
        self.editor_tree_cache = {}
        self.editor_ids = {}
        self.update_timers = {}
        self.editors_to_update = {}
        self.ordered_editor_ids = []
        self._current_editor = None
        self._languages = []

        self.currentItemChanged.connect(self.selection_switched)
        self.itemExpanded.connect(self.tree_item_expanded)
        self.itemCollapsed.connect(self.tree_item_collapsed)

    # ---- SpyderWidgetMixin API
    # ------------------------------------------------------------------------
    @property
    def current_editor(self):
        """Get current editor."""
        return self._current_editor

    @current_editor.setter
    def current_editor(self, value):
        """Set current editor and connect the necessary signals."""
        if self._current_editor == value:
            return
        # Disconnect previous editor
        self.connect_current_editor(False)
        self._current_editor = value
        # Connect new editor
        self.connect_current_editor(True)

    def __hide_or_show_root_items(self, item):
        """
        show_all_files option is disabled: hide all root items except *item*
        show_all_files option is enabled: do nothing
        """
        for _it in self.get_top_level_items():
            _it.setHidden(_it is not item and not self.show_all_files)

    @on_conf_change(option='show_fullpath')
    def toggle_fullpath_mode(self, state):
        self.show_fullpath = state
        self.setTextElideMode(Qt.ElideMiddle if state else Qt.ElideRight)
        for index in range(self.topLevelItemCount()):
            self.topLevelItem(index).set_text(fullpath=self.show_fullpath)

    @on_conf_change(option='show_all_files')
    def toggle_show_all_files(self, state):
        self.show_all_files = state
        if self.current_editor is not None:
            editor_id = self.editor_ids[self.current_editor]
            item = self.editor_items[editor_id].node
            self.__hide_or_show_root_items(item)
            self.__sort_toplevel_items()
            if self.show_all_files is False:
                self.root_item_selected(
                    self.editor_items[self.editor_ids[self.current_editor]])
            self.do_follow_cursor()

    @on_conf_change(option='show_comments')
    def toggle_show_comments(self, state):
        self.show_comments = state
        self.sig_update_configuration.emit()
        self.update_all_editors(reset_info=True)

    @on_conf_change(option='group_cells')
    def toggle_group_cells(self, state):
        self.group_cells = state
        self.sig_update_configuration.emit()
        self.update_all_editors(reset_info=True)

    @on_conf_change(option='display_variables')
    def toggle_variables(self, state):
        self.display_variables = state
        for editor in self.editor_ids.keys():
            self.update_editor(editor.info, editor)

    @on_conf_change(option='sort_files_alphabetically')
    def toggle_sort_files_alphabetically(self, state):
        self.sort_files_alphabetically = state
        self.__sort_toplevel_items()

    @on_conf_change(option='follow_cursor')
    def toggle_follow_cursor(self, state):
        """Follow the cursor."""
        self.follow_cursor = state
        self.do_follow_cursor()

    @Slot()
    def do_follow_cursor(self):
        """Go to cursor position."""
        if self.follow_cursor:
            self.go_to_cursor_position()

    @Slot()
    def go_to_cursor_position(self):
        if self.current_editor is not None:
            editor_id = self.editor_ids[self.current_editor]
            line = self.current_editor.get_cursor_line_number()
            tree = self.editor_tree_cache[editor_id]
            root = self.editor_items[editor_id]
            overlap = tree[line - 1]
            if len(overlap) == 0:
                item = root.node
                self.setCurrentItem(item)
                self.scrollToItem(item)
                self.expandItem(item)
            else:
                sorted_nodes = sorted(overlap)
                # The last item of the sorted elements correspond to the
                # current node if expanding, otherwise it is the first stopper
                # found
                idx = -1
                self.switch_to_node(sorted_nodes, idx)

    def switch_to_node(self, sorted_nodes, idx):
        """Given a set of tree nodes, highlight the node on index `idx`."""
        item_interval = sorted_nodes[idx]
        item_ref = item_interval.data
        item = item_ref.node
        self.setCurrentItem(item)
        self.scrollToItem(item)
        self.expandItem(item)

    def connect_current_editor(self, state):
        """Connect or disconnect the editor from signals."""
        editor = self.current_editor
        if editor is None:
            return

        # Connect syntax highlighter
        sig_update = editor.sig_outline_explorer_data_changed
        sig_move = editor.sig_cursor_position_changed
        sig_display_spinner = editor.sig_start_outline_spinner
        if state:
            sig_update.connect(self.update_editor)
            sig_move.connect(self.do_follow_cursor)
            sig_display_spinner.connect(self.sig_display_spinner)
            self.do_follow_cursor()
        else:
            try:
                sig_update.disconnect(self.update_editor)
                sig_move.disconnect(self.do_follow_cursor)
                sig_display_spinner.disconnect(self.sig_display_spinner)
            except TypeError:
                # This catches an error while performing
                # teardown in one of our tests.
                pass

    def clear(self):
        """Reimplemented Qt method"""
        self.set_title('')
        OneColumnTree.clear(self)

    def set_current_editor(self, editor, update):
        """Bind editor instance"""
        editor_id = editor.get_id()

        # Don't fail if editor doesn't exist anymore. This
        # happens when switching projects.
        try:
            item = self.editor_items[editor_id].node
        except KeyError:
            return

        if not self.freeze:
            self.scrollToItem(item)
            self.root_item_selected(item)
            self.__hide_or_show_root_items(item)
        if update:
            self.save_expanded_state()
            self.restore_expanded_state()

        self.current_editor = editor

        # Update tree with currently stored info or require symbols if
        # necessary.
        if (editor.get_language() in self._languages and
                len(self.editor_tree_cache[editor_id]) == 0):
            if editor.info is not None:
                self.update_editor(editor.info)
            elif editor.is_cloned:
                editor.request_symbols()

    def register_editor(self, editor):
        """
        Register editor attributes and create basic objects associated
        to it.
        """
        editor_id = editor.get_id()
        self.editor_ids[editor] = editor_id
        self.ordered_editor_ids.append(editor_id)

        this_root = SymbolStatus(editor.fname, None, None, editor.fname)
        self.editor_items[editor_id] = this_root

        root_item = FileRootItem(editor.fname, this_root,
                                 self, editor.is_python())
        this_root.node = root_item
        root_item.set_text(fullpath=self.show_fullpath)
        self.resizeColumnToContents(0)
        if not self.show_all_files:
            root_item.setHidden(True)

        editor_tree = IntervalTree()
        self.editor_tree_cache[editor_id] = editor_tree

        self.__sort_toplevel_items()

    def file_renamed(self, editor, new_filename):
        """File was renamed, updating outline explorer tree"""
        if editor is None:
            # This is needed when we can't find an editor to attach
            # the outline explorer to.
            # Fix spyder-ide/spyder#8813.
            return
        editor_id = editor.get_id()
        if editor_id in list(self.editor_ids.values()):
            root_item = self.editor_items[editor_id].node
            root_item.set_path(new_filename, fullpath=self.show_fullpath)
            self.__sort_toplevel_items()

    def update_editors(self, language):
        """
        Update all editors for a given language sequentially.

        This is done through a timer to avoid lags in the interface.
        """
        if self.editors_to_update.get(language):
            editor = self.editors_to_update[language][0]
            if editor.info is not None:
                # Editor could be not there anymore after switching
                # projects
                try:
                    self.update_editor(editor.info, editor)
                except KeyError:
                    pass
                self.editors_to_update[language].remove(editor)
            self.update_timers[language].start()

    def update_all_editors(self, reset_info=False):
        """Update all editors with LSP support."""
        for language in self._languages:
            self.set_editors_to_update(language, reset_info=reset_info)
            self.update_timers[language].start()

    @Slot(list)
    def update_editor(self, items, editor=None):
        """
        Update the outline explorer for `editor` preserving the tree
        state.
        """
        if items is None:
            return

        plugin_base = self.parent().parent()
        if editor is None:
            editor = self.current_editor
        editor_id = editor.get_id()
        language = editor.get_language()
        update = self.update_tree(items, editor_id, language)

        if getattr(plugin_base, "_isvisible", True) and update:
            self.save_expanded_state()
            self.restore_expanded_state()
            self.do_follow_cursor()

    def merge_interval(self, parent, node):
        """Add node into an existing tree structure."""
        match = False
        start, end = node.position
        while parent.parent is not None and not match:
            parent_start, parent_end = parent.position
            if parent_end <= start:
                parent = parent.parent
            else:
                match = True

        if node.parent is not None:
            node.parent.remove_node(node)
            node.parent = None
            if node.node.parent is not None:
                node.node.parent.remove_children(node.node)

        parent.add_node(node)
        node.refresh()
        return node

    def update_tree(self, items, editor_id, language):
        current_tree = self.editor_tree_cache[editor_id]
        tree_info = []
        for symbol in items:
            symbol_name = symbol['name']
            symbol_kind = symbol['kind']
            if language.lower() == 'python':
                if symbol_kind == SymbolKind.MODULE:
                    continue
                if (symbol_kind == SymbolKind.VARIABLE and
                        not self.display_variables):
                    continue
                if (symbol_kind == SymbolKind.FIELD and
                        not self.display_variables):
                    continue
            # NOTE: This could be also a DocumentSymbol
            symbol_range = symbol['location']['range']
            symbol_start = symbol_range['start']['line']
            symbol_end = symbol_range['end']['line']
            symbol_repr = SymbolStatus(symbol_name, symbol_kind,
                                       (symbol_start, symbol_end), None)
            tree_info.append((symbol_start, symbol_end + 1, symbol_repr))

        tree = IntervalTree.from_tuples(tree_info)
        changes = tree - current_tree
        deleted = current_tree - tree

        if len(changes) == 0 and len(deleted) == 0:
            self.sig_hide_spinner.emit()
            return False

        adding_symbols = len(changes) > len(deleted)
        deleted_iter = iter(sorted(deleted))
        changes_iter = iter(sorted(changes))

        deleted_entry = next(deleted_iter, None)
        changed_entry = next(changes_iter, None)
        non_merged = 0

        while deleted_entry is not None and changed_entry is not None:
            deleted_entry_i = deleted_entry.data
            changed_entry_i = changed_entry.data

            if deleted_entry_i.name == changed_entry_i.name:
                deleted_span = line_span(deleted_entry_i.position)
                changed_span = line_span(changed_entry_i.position)
                # Copy symbol status
                changed_entry_i.clone_node(deleted_entry_i)
                deleted_entry = next(deleted_iter, None)
                changed_entry = next(changes_iter, None)
            else:
                if adding_symbols:
                    # New symbol added
                    changed_entry_i.create_node()
                    non_merged += 1
                    changed_entry = next(changes_iter, None)
                else:
                    # Symbol removed
                    deleted_entry_i.delete()
                    non_merged += 1
                    deleted_entry = next(deleted_iter, None)

        if deleted_entry is not None:
            while deleted_entry is not None:
                # Symbol removed
                deleted_entry_i = deleted_entry.data
                deleted_entry_i.delete()
                non_merged += 1
                deleted_entry = next(deleted_iter, None)

        root = self.editor_items[editor_id]
        # tree_merge
        if changed_entry is not None:
            while changed_entry is not None:
                # New symbol added
                changed_entry_i = changed_entry.data
                changed_entry_i.create_node()
                non_merged += 1
                changed_entry = next(changes_iter, None)

        tree_copy = IntervalTree(tree)
        tree_copy.merge_overlaps(
            data_reducer=self.merge_interval, data_initializer=root)

        self.editor_tree_cache[editor_id] = tree
        self.sig_tree_updated.emit()
        self.sig_hide_spinner.emit()
        return True

    def remove_editor(self, editor):
        if editor in self.editor_ids:
            if self.current_editor is editor:
                self.current_editor = None
            editor_id = self.editor_ids.pop(editor)
            if editor_id in self.ordered_editor_ids:
                self.ordered_editor_ids.remove(editor_id)
            if editor_id not in list(self.editor_ids.values()):
                root_item = self.editor_items.pop(editor_id)
                self.editor_tree_cache.pop(editor_id)
                try:
                    self.takeTopLevelItem(
                        self.indexOfTopLevelItem(root_item.node))
                except RuntimeError:
                    # item has already been removed
                    pass

    def set_editor_ids_order(self, ordered_editor_ids):
        """
        Order the root file items in the Outline Explorer following the
        provided list of editor ids.
        """
        if self.ordered_editor_ids != ordered_editor_ids:
            self.ordered_editor_ids = ordered_editor_ids
            if self.sort_files_alphabetically is False:
                self.__sort_toplevel_items()

    def __sort_toplevel_items(self):
        """
        Sort the root file items in alphabetical order if
        'sort_files_alphabetically' is True, else order the items as
        specified in the 'self.ordered_editor_ids' list.
        """
        if self.show_all_files is False:
            return

        current_ordered_items = [self.topLevelItem(index) for index in
                                 range(self.topLevelItemCount())]
        if self.sort_files_alphabetically:
            new_ordered_items = sorted(
                current_ordered_items,
                key=lambda item: osp.basename(item.path.lower()))
        else:
            new_ordered_items = [
                self.editor_items.get(e_id).node for e_id in
                self.ordered_editor_ids if
                self.editor_items.get(e_id) is not None]

        if current_ordered_items != new_ordered_items:
            selected_items = self.selectedItems()
            self.save_expanded_state()
            for index in range(self.topLevelItemCount()):
                self.takeTopLevelItem(0)
            for index, item in enumerate(new_ordered_items):
                self.insertTopLevelItem(index, item)
            self.restore_expanded_state()
            self.clearSelection()
            if selected_items:
                selected_items[-1].setSelected(True)

    def root_item_selected(self, item):
        """Root item has been selected: expanding it and collapsing others"""
        if self.show_all_files:
            return
        for root_item in self.get_top_level_items():
            if root_item is item:
                self.expandItem(root_item)
            else:
                self.collapseItem(root_item)

    def restore(self):
        """Reimplemented OneColumnTree method"""
        if self.current_editor is not None:
            self.collapseAll()
            editor_id = self.editor_ids[self.current_editor]
            self.root_item_selected(self.editor_items[editor_id].node)

    def get_root_item(self, item):
        """Return the root item of the specified item."""
        root_item = item
        while isinstance(root_item.parent(), QTreeWidgetItem):
            root_item = root_item.parent()
        return root_item

    def get_visible_items(self):
        """Return a list of all visible items in the treewidget."""
        items = []
        iterator = QTreeWidgetItemIterator(self)
        while iterator.value():
            item = iterator.value()
            if not item.isHidden():
                if item.parent():
                    if item.parent().isExpanded():
                        items.append(item)
                else:
                    items.append(item)
            iterator += 1
        return items

    def activated(self, item):
        """Double-click event"""
        editor_root = self.editor_items.get(
            self.editor_ids.get(self.current_editor))
        root_item = editor_root.node
        text = ''
        if isinstance(item, FileRootItem):
            line = 1
            if id(root_item) != id(item):
                root_item = item
        else:
            line = item.ref.position[0] + 1
            text = item.ref.name

        path = item.ref.path
        self.freeze = True
        if line:
            self.parent().edit_goto.emit(path, line, text)
        else:
            self.parent().edit.emit(path)
        self.freeze = False

        for editor_id, i_item in list(self.editor_items.items()):
            if i_item.path == path:
                for editor, _id in list(self.editor_ids.items()):
                    self.current_editor = editor
                    break
            break

    def clicked(self, item):
        """Click event"""
        if isinstance(item, FileRootItem):
            self.root_item_selected(item)
        self.activated(item)

    def selection_switched(self, current_item, previous_item):
        if current_item is not None:
            current_ref = current_item.ref
            current_ref.selected = True
        if previous_item is not None:
            previous_ref = previous_item.ref
            previous_ref.selected = False

    def tree_item_collapsed(self, item):
        ref = item.ref
        ref.status = False

    def tree_item_expanded(self, item):
        ref = item.ref
        ref.status = True

    def set_editors_to_update(self, language, reset_info=False):
        """Set editors to update per language."""
        to_update = []
        for editor in self.editor_ids.keys():
            if editor.get_language().lower() == language:
                to_update.append(editor)
                if reset_info:
                    editor.info = None
        self.editors_to_update[language] = to_update

    def start_symbol_services(self, language):
        """Show symbols for all `language` files."""
        # Save all languages that can send info to this pane.
        self._languages.append(language)

        # Update all files associated to `language` through a timer
        # that allows to wait a bit between updates. That doesn't block
        # the interface at startup.
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(700)
        timer.timeout.connect(lambda: self.update_editors(language))
        self.update_timers[language] = timer

        # Set editors that need to be updated per language
        self.set_editors_to_update(language)

        # Start timer
        timer.start()

    def stop_symbol_services(self, language):
        """Disable LSP symbols functionality."""
        try:
            self._languages.remove(language)
        except ValueError:
            pass

        for editor in self.editor_ids.keys():
            if editor.get_language().lower() == language:
                editor.info = None


class OutlineExplorerWidget(PluginMainWidget):
    """Class browser"""
    edit_goto = Signal(str, int, str)
    edit = Signal(str)
    is_visible = Signal()
    sig_update_configuration = Signal()

    ENABLE_SPINNER = True
    CONF_SECTION = 'outline_explorer'

    def __init__(self, name, plugin, parent=None):
        super().__init__(name, plugin, parent)

        self.treewidget = OutlineExplorerTreeWidget(self)
        self.treewidget.sig_display_spinner.connect(self.start_spinner)
        self.treewidget.sig_hide_spinner.connect(self.stop_spinner)
        self.treewidget.sig_update_configuration.connect(
            self.sig_update_configuration)

        self.treewidget.header().hide()

        layout = QHBoxLayout()
        layout.addWidget(self.treewidget)
        self.setLayout(layout)

    # ---- PluginMainWidget API
    # ------------------------------------------------------------------------
    def get_focus_widget(self):
        """Define the widget to focus."""
        return self.treewidget

    def get_title(self):
        """Return the title of the plugin tab."""
        return _("Outline")

    def setup(self):
        """Performs the setup of plugin's menu and actions."""
        # Toolbar buttons
        toolbar = self.get_main_toolbar()
        fromcursor_btn = self.create_toolbutton(
            OutlineExplorerToolbuttons.GoToCursor,
            icon=self.create_icon('fromcursor'),
            tip=_('Go to cursor position'),
            triggered=self.treewidget.go_to_cursor_position)

        for item in [fromcursor_btn,
                     self.treewidget.collapse_all_action,
                     self.treewidget.expand_all_action,
                     self.treewidget.restore_action,
                     self.treewidget.collapse_selection_action,
                     self.treewidget.expand_selection_action]:
            self.add_item_to_toolbar(item, toolbar=toolbar,
                                     section=OutlineExplorerSections.Main)

        # Actions
        fromcursor_act = self.create_action(
            OutlineExplorerActions.GoToCursor,
            text=_('Go to cursor position'),
            icon=self.create_icon('fromcursor'),
            triggered=self.treewidget.go_to_cursor_position)

        fullpath_act = self.create_action(
            OutlineExplorerActions.ShowFullPath,
            text=_('Show absolute path'),
            toggled=True,
            option='show_fullpath')

        allfiles_act = self.create_action(
            OutlineExplorerActions.ShowAllFiles,
            text=_('Show all files'),
            toggled=True,
            option='show_all_files')

        comment_act = self.create_action(
            OutlineExplorerActions.ShowSpecialComments,
            text=_('Show special comments'),
            toggled=True,
            option='show_comments')

        group_cells_act = self.create_action(
            OutlineExplorerActions.GroupCodeCells,
            text=_('Group code cells'),
            toggled=True,
            option='group_cells')

        display_variables_act = self.create_action(
            OutlineExplorerActions.DisplayVariables,
            text=_('Display variables and attributes'),
            toggled=True,
            option='display_variables'
        )

        follow_cursor_act = self.create_action(
            OutlineExplorerActions.FollowCursor,
            text=_('Follow cursor position'),
            toggled=True,
            option='follow_cursor'
        )

        sort_files_alphabetically_act = self.create_action(
            OutlineExplorerActions.SortFiles,
            text=_('Sort files alphabetically'),
            toggled=True,
            option='sort_files_alphabetically'
        )

        actions = [fullpath_act, allfiles_act, group_cells_act,
                   display_variables_act, follow_cursor_act, comment_act,
                   sort_files_alphabetically_act, fromcursor_act]

        option_menu = self.get_options_menu()
        for action in actions:
            self.add_item_to_menu(
                action,
                option_menu,
                section=OutlineExplorerSections.DisplayOptions,
            )

    def update_actions(self):
        pass

    def set_current_editor(self, editor, update, clear):
        if clear:
            self.remove_editor(editor)
        if editor is not None:
            self.treewidget.set_current_editor(editor, update)

    def remove_editor(self, editor):
        self.treewidget.remove_editor(editor)

    def register_editor(self, editor):
        self.treewidget.register_editor(editor)

    def file_renamed(self, editor, new_filename):
        self.treewidget.file_renamed(editor, new_filename)

    def start_symbol_services(self, language):
        """Enable LSP symbols functionality."""
        self.treewidget.start_symbol_services(language)

    def stop_symbol_services(self, language):
        """Disable LSP symbols functionality."""
        self.treewidget.stop_symbol_services(language)

    def update_all_editors(self):
        """Update all editors with an associated LSP server."""
        self.treewidget.update_all_editors()
