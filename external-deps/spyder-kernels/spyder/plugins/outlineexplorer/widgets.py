# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer widgets."""

# Standard library imports
import bisect
import logging
import os.path as osp
import uuid

# Third party imports
from intervaltree import IntervalTree
from packaging.version import parse
from qtpy import PYSIDE2, PYSIDE_VERSION
from qtpy.QtCore import Qt, QTimer, Signal, Slot
from qtpy.QtWidgets import QTreeWidgetItem, QTreeWidgetItemIterator

# Local imports
from spyder.api.config.decorators import on_conf_change
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.plugins.completion.api import SymbolKind, SYMBOL_KIND_ICON
from spyder.utils.qthelpers import set_item_user_text
from spyder.widgets.onecolumntree import OneColumnTree


# For logging
logger = logging.getLogger(__name__)


# ---- Constants
# -----------------------------------------------------------------------------
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


# ---- Symbol status
# -----------------------------------------------------------------------------
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

        if (
            self.node.parent is not None
            and hasattr(self.node.parent, 'remove_children')
        ):
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

    def set_path(self, new_path):
        self.name = new_path
        self.path = new_path

    def __repr__(self):
        return str(self)

    def __str__(self):
        return '({0}, {1}, {2}, {3})'.format(
            self.position, self.name, self.id, self.status)

    def __eq__(self, other):
        return (
            self.name == other.name
            and self.kind == other.kind
            and self.position == other.position
        )


# ---- Items
# -----------------------------------------------------------------------------
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


# ---- Treewidget
# -----------------------------------------------------------------------------
class OutlineExplorerTreeWidget(OneColumnTree):
    # Used only for debug purposes
    sig_tree_updated = Signal()
    sig_display_spinner = Signal()
    sig_hide_spinner = Signal()
    sig_update_configuration = Signal()

    CONF_SECTION = 'outline_explorer'

    def __init__(self, parent):
        if hasattr(parent, 'CONTEXT_NAME'):
            self.CONTEXT_NAME = parent.CONTEXT_NAME

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
        self.starting = {}
        self.editors_to_update = {}
        self.ordered_editor_ids = []
        self._current_editor = None
        self._languages = []
        self.is_visible = False

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
        current_editor = self.current_editor
        if current_editor is not None:
            editor_id = self.editor_ids[current_editor]
            item = self.editor_items[editor_id].node
            self.__hide_or_show_root_items(item)
            self.__sort_toplevel_items()
            if self.show_all_files is False:
                self.root_item_selected(
                    self.editor_items[self.editor_ids[current_editor]])
            self.do_follow_cursor()

    @on_conf_change(option='show_comments')
    def toggle_show_comments(self, state):
        self.show_comments = state
        self.sig_update_configuration.emit()
        self.update_editors(language='python')

    @on_conf_change(option='group_cells')
    def toggle_group_cells(self, state):
        self.group_cells = state
        self.sig_update_configuration.emit()
        self.update_editors(language='python')

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

        logger.debug(f"Set current editor to file {editor.fname}")
        self.current_editor = editor

        if (
            self.is_visible
            and (editor.get_language().lower() in self._languages)
            and not editor.is_tree_updated
        ):
            if editor.info is not None:
                self.update_editor(editor.info)

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
            # Fixes spyder-ide/spyder#8813.
            return

        editor_id = editor.get_id()
        if editor_id in list(self.editor_ids.values()):
            items = self.editor_items[editor_id]

            # Set path for items
            items.set_path(new_filename)

            # Change path of root item (i.e. the file name)
            root_item = items.node
            root_item.set_path(new_filename, fullpath=self.show_fullpath)

            # Clear and re-populate the tree again.
            # Fixes spyder-ide/spyder#15517
            items.delete()
            editor.request_symbols()

            # Resort root items
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
        else:
            if self.starting.get(language):
                logger.debug("Finish updating files at startup")
                self.starting[language] = False

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

        if editor is None:
            editor = self.current_editor

        # Only perform an update if the widget is visible.
        if not self.is_visible:
            logger.debug(
                f"Don't update tree of file {editor.fname} because plugin is "
                f"not visible"
            )
            self.sig_hide_spinner.emit()
            return

        update = self.update_tree(items, editor)

        if update:
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

    def update_tree(self, items, editor):
        """Update tree with new items that come from the LSP."""
        editor_id = editor.get_id()
        language = editor.get_language()
        current_tree = self.editor_tree_cache[editor_id]
        root = self.editor_items[editor_id]
        tree_info = []

        # Create tree with items that come from the LSP
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

        # We must update the tree if the editor's root doesn't have children
        # yet but we have symbols for it saved in the cache
        must_update = root.node.childCount() == 0 and len(current_tree) > 0

        if not must_update:
            # Compare with current tree to check if it's necessary to update
            # it.
            if tree == current_tree:
                logger.debug(
                    f"Current and new trees for file {editor.fname} are the "
                    f"same, so no update is necessary"
                )
                editor.is_tree_updated = True
                self.sig_hide_spinner.emit()
                return False

        logger.debug(f"Updating tree for file {editor.fname}")

        # Create nodes with new tree
        for entry in sorted(tree):
            entry.data.create_node()

        # Remove previous tree to create the new one.
        # NOTE: This is twice as fast as detecting the symbols that changed
        # and updating only those in current_tree.
        self.editor_items[editor_id].delete()

        # Recreate tree structure
        tree_copy = IntervalTree(tree)
        tree_copy.merge_overlaps(
            data_reducer=self.merge_interval,
            data_initializer=root
        )

        # Save new tree and finish
        self.editor_tree_cache[editor_id] = tree
        editor.is_tree_updated = True
        self.sig_tree_updated.emit()
        self.sig_hide_spinner.emit()
        return True

    def remove_editor(self, editor):
        if editor in self.editor_ids:
            if self.current_editor is editor:
                self.current_editor = None

            logger.debug(f"Removing tree of file {editor.fname}")

            editor_id = self.editor_ids.pop(editor)
            language = editor.get_language().lower()

            if editor_id in self.ordered_editor_ids:
                self.ordered_editor_ids.remove(editor_id)

            # Remove editor from the list that it's waiting to be updated
            # because it's not necessary anymore.
            if (
                language in self._languages
                and editor in self.editors_to_update[language]
            ):
                self.editors_to_update[language].remove(editor)

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

        # Convert list to a dictionary in order to remove duplicated entries
        # when having multiple editors (splitted or in new windows).
        # See spyder-ide/spyder#14646
        current_ordered_items_dict = {
            item.path.lower(): item for item in current_ordered_items}

        if self.sort_files_alphabetically:
            new_ordered_items = sorted(
                current_ordered_items_dict.values(),
                key=lambda item: osp.basename(item.path.lower()))
        else:
            new_ordered_items = [
                self.editor_items.get(e_id).node for e_id in
                self.ordered_editor_ids if
                self.editor_items.get(e_id) is not None]

        # PySide <= 5.15.0 doesn’t support == and != comparison for the data
        # types inside the compared lists (see [1], [2])
        #
        # [1] https://bugreports.qt.io/browse/PYSIDE-74
        # [2] https://codereview.qt-project.org/c/pyside/pyside-setup/+/312945
        update = (
            (PYSIDE2 and parse(PYSIDE_VERSION) <= parse("5.15.0"))
            or (current_ordered_items != new_ordered_items)
        )
        if update:
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
            line = None
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
        logger.debug(f"Start symbol services for language {language}")

        # Save all languages that can send info to this pane.
        self._languages.append(language)

        # Update all files associated to `language` through a timer
        # that allows to wait a bit between updates. That doesn't block
        # the interface at startup.
        timer = QTimer(self)
        timer.setSingleShot(True)
        timer.setInterval(150)
        timer.timeout.connect(lambda: self.update_editors(language))
        self.update_timers[language] = timer
        self.starting[language] = True

        # Set editors that need to be updated per language
        self.set_editors_to_update(language)

        # Start timer
        timer.start()

    def stop_symbol_services(self, language):
        """Disable LSP symbols functionality."""
        logger.debug(f"Stop symbol services for language {language}")
        try:
            self._languages.remove(language)
        except ValueError:
            pass

        for editor in self.editor_ids.keys():
            if editor.get_language().lower() == language:
                editor.info = None

    def change_visibility(self, is_visible):
        """Actions to take when the widget visibility has changed."""
        self.is_visible = is_visible

        if is_visible:
            # Udpdate outdated trees for all LSP languages
            for language in self._languages:
                # Don't run this while trees are being updated after their LSP
                # started.
                if not self.starting[language]:
                    # Check which editors need to be updated
                    for editor in self.editor_ids.keys():
                        if (
                            editor.get_language().lower() == language
                            and not editor.is_tree_updated
                            and editor not in self.editors_to_update[language]
                        ):
                            self.editors_to_update[language].append(editor)

                    # Update editors
                    if self.editors_to_update[language]:
                        logger.debug(
                            f"Updating outdated trees for {language} files "
                            f"because the plugin has become visible"
                        )
                        self.update_editors(language)

            # Udpdate current tree if it has info available
            ce = self.current_editor
            if ce and ce.info and not ce.is_tree_updated:
                self.update_editor(ce.info, ce)
