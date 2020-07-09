# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer widgets."""

# Standard library imports
from __future__ import print_function
import bisect
import os.path as osp
import uuid

# Third party imports
from intervaltree import IntervalTree
from qtpy.compat import from_qvariant
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import (QHBoxLayout, QTreeWidgetItem, QWidget,
                            QTreeWidgetItemIterator)

# Local imports
from spyder.config.base import _, STDOUT
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.plugins.completion.languageserver import SymbolKind
from spyder.utils.qthelpers import (create_action, create_toolbutton,
                                    set_item_user_text, create_plugin_layout)
from spyder.widgets.onecolumntree import OneColumnTree


SYMBOL_KIND_ICON = {
    SymbolKind.FILE: 'file',
    SymbolKind.MODULE: 'module',
    SymbolKind.NAMESPACE: 'namespace',
    SymbolKind.PACKAGE: 'package',
    SymbolKind.CLASS: 'class',
    SymbolKind.METHOD: 'method',
    SymbolKind.PROPERTY: 'property',
    SymbolKind.FIELD: 'field',
    SymbolKind.CONSTRUCTOR: 'constructor',
    SymbolKind.ENUM: 'enum',
    SymbolKind.INTERFACE: 'interface',
    SymbolKind.FUNCTION: 'function',
    SymbolKind.VARIABLE: 'variable',
    SymbolKind.CONSTANT: 'constant',
    SymbolKind.STRING: 'string',
    SymbolKind.NUMBER: 'number',
    SymbolKind.BOOLEAN: 'boolean',
    SymbolKind.ARRAY: 'array',
    SymbolKind.OBJECT: 'object',
    SymbolKind.KEY: 'key',
    SymbolKind.NULL: 'null',
    SymbolKind.ENUM_MEMBER: 'enum_member',
    SymbolKind.STRUCT: 'struct',
    SymbolKind.EVENT: 'event',
    SymbolKind.OPERATOR: 'operator',
    SymbolKind.TYPE_PARAMETER: 'type_parameter'
}

SYMBOL_NAME_MAP = {
    SymbolKind.FILE: _('File'),
    SymbolKind.MODULE: _('Module'),
    SymbolKind.NAMESPACE: _('Namespace'),
    SymbolKind.PACKAGE: _('Package'),
    SymbolKind.CLASS: _('Class'),
    SymbolKind.METHOD: _('Method'),
    SymbolKind.PROPERTY: _('Property'),
    SymbolKind.FIELD: _('Field'),
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
    SymbolKind.TYPE_PARAMETER: _('Type parameter')
}

ICON_CACHE = {}


class SymbolStatus:
    def __init__(self, name, kind, position, node=None):
        self.name = name
        self.position = position
        self.kind = kind
        self.node = node
        self.id = str(uuid.uuid4())
        self.index = None
        self.children = []
        self.status = False
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
        node.parent = self
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
        self.children = node.children
        self.status = node.status
        self.node = node.node
        self.parent = node.parent
        self.node.update_info(self.name, self.kind, self.position[0] + 1)
        self.node.ref = self

        for child in self.children:
            child.parent = self

        if self.parent is not None:
            self.parent.replace_node(self.index, self)

    def replace_node(self, index, node):
        self.children[index] = node

    def create_node(self):
        self.node = SymbolItem(None, self, self.name, self.kind,
                               self.position[0] + 1)

    def __repr__(self):
        return str(self)

    def __str__(self):
        return f'({self.position}, {self.name}, {self.id}, {self.status})'


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
    def __init__(self, path, treewidget, is_python=True):
        QTreeWidgetItem.__init__(self, treewidget, QTreeWidgetItem.Type)
        self.path = path
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
    def __init__(self, parent, ref, name, kind, position):
        QTreeWidgetItem.__init__(self, parent, QTreeWidgetItem.Type)
        self.parent = parent
        self.ref = ref
        self.num_children = 0

        self.setIcon(0, ima.icon(SYMBOL_KIND_ICON.get(kind, 'no_match')))
        identifier = SYMBOL_NAME_MAP.get(kind, '')
        identifier = identifier.replace('_', ' ').capitalize()
        self.setToolTip(0, '{3} {2}: {0} {1}'.format(
            identifier, name, position, _('Line')))
        set_item_user_text(self, name)
        self.setText(0, name)

    def update_info(self, name, kind, position):
        self.setIcon(0, ima.icon(SYMBOL_KIND_ICON.get(kind, 'no_match')))
        identifier = SYMBOL_NAME_MAP.get(kind, '')
        identifier = identifier.replace('_', ' ').capitalize()
        self.setToolTip(0, '{3} {2}: {0} {1}'.format(
            identifier, name, position, _('Line')))
        set_item_user_text(self, name)
        self.setText(0, name)


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

class ClassItem(TreeItem):
    def get_name(self):
        """Get name."""
        return self.oedata.get_class_name()

    def setup(self):
        self.set_icon(ima.icon('class'))
        self.setToolTip(0, _("Class defined at line %s") % str(self.line))

class FunctionItem(TreeItem):
    def get_name(self):
        """Get name."""
        return self.oedata.get_function_name()

    def is_method(self):
        return isinstance(self.parent(), ClassItem)

    def setup(self):
        if self.is_method():
            self.setToolTip(0, _("Method defined at line %s") % str(self.line))
            name = to_text_string(self.text(0))
            if name.startswith('__'):
                self.set_icon(ima.icon('private2'))
            elif name.startswith('_'):
                self.set_icon(ima.icon('private1'))
            else:
                self.set_icon(ima.icon('method'))
        else:
            self.set_icon(ima.icon('function'))
            self.setToolTip(0, _("Function defined at line %s"
                                 ) % str(self.line))

class CommentItem(TreeItem):
    def get_name(self):
        """Get name."""
        return self.oedata.def_name.lstrip("# ")

    def setup(self):
        self.set_icon(ima.icon('blockcomment'))
        font = self.font(0)
        font.setItalic(True)
        self.setFont(0, font)
        self.setToolTip(0, _("Line %s") % str(self.line))

class CellItem(TreeItem):
    def setup(self):
        self.set_icon(ima.icon('cell'))
        font = self.font(0)
        font.setItalic(True)
        self.setFont(0, font)
        self.setToolTip(0, _("Cell starts at line %s") % str(self.line))

def get_item_children(item):
    """Return a sorted list of all the children items of 'item'."""
    children = [item.child(index) for index in range(item.childCount())]
    for child in children[:]:
        others = get_item_children(child)
        if others is not None:
            children += others
    # Remove any child without line number
    children = [child for child in children if child.line is not None]
    return sorted(children, key=lambda child: child.line)


def item_at_line(root_item, line):
    """
    Find and return the item of the outline explorer under which is located
    the specified 'line' of the editor.
    """
    previous_item = root_item
    item = root_item
    for item in get_item_children(root_item):
        if item.line > line:
            return previous_item
        previous_item = item
    else:
        return item


def remove_from_tree_cache(tree_cache, line=None, item=None):
    if line is None:
        for line, (_it, _debug) in list(tree_cache.items()):
            if _it is item:
                break
    if line is None:
        # Could not find the item
        return
    item, debug = tree_cache.pop(line)
    try:
        for child in [item.child(_i) for _i in range(item.childCount())]:
            remove_from_tree_cache(tree_cache, item=child)
        item.parent().removeChild(item)
    except RuntimeError:
        # Item has already been deleted
        #XXX: remove this debug-related fragment of code
        print("unable to remove tree item: ", debug, file=STDOUT)


class OutlineExplorerTreeWidget(OneColumnTree):
    def __init__(self, parent, show_fullpath=False, show_all_files=True,
                 group_cells=True, show_comments=True,
                 sort_files_alphabetically=False, follow_cursor=True):
        self.show_fullpath = show_fullpath
        self.show_all_files = show_all_files
        self.group_cells = group_cells
        self.follow_cursor = follow_cursor
        self.show_comments = show_comments
        self.sort_files_alphabetically = sort_files_alphabetically
        OneColumnTree.__init__(self, parent)
        self.freeze = False  # Freezing widget to avoid any unwanted update
        self.editor_items = {}
        self.editor_tree_cache = {}
        self.editor_ids = {}
        self.ordered_editor_ids = []
        self._current_editor = None
        title = _("Outline")
        self.set_title(title)
        self.setWindowTitle(title)
        self.setUniformRowHeights(True)

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

    def get_actions_from_items(self, items):
        """Reimplemented OneColumnTree method"""
        fromcursor_act = create_action(self, text=_('Go to cursor position'),
                                       icon=ima.icon('fromcursor'),
                                       triggered=self.go_to_cursor_position)
        fullpath_act = create_action(self, text=_('Show absolute path'),
                                     toggled=self.toggle_fullpath_mode)
        fullpath_act.setChecked(self.show_fullpath)
        allfiles_act = create_action(self, text=_('Show all files'),
                                     toggled=self.toggle_show_all_files)
        allfiles_act.setChecked(self.show_all_files)
        comment_act = create_action(self, text=_('Show special comments'),
                                    toggled=self.toggle_show_comments)
        comment_act.setChecked(self.show_comments)
        group_cells_act = create_action(self, text=_('Group code cells'),
                                        toggled=self.toggle_group_cells)
        group_cells_act.setChecked(self.group_cells)
        sort_files_alphabetically_act = create_action(
            self, text=_('Sort files alphabetically'),
            toggled=self.toggle_sort_files_alphabetically)
        sort_files_alphabetically_act.setChecked(
            self.sort_files_alphabetically)
        actions = [fullpath_act, allfiles_act, group_cells_act, comment_act,
                   sort_files_alphabetically_act, fromcursor_act]
        return actions

    @Slot(bool)
    def toggle_fullpath_mode(self, state):
        self.show_fullpath = state
        self.setTextElideMode(Qt.ElideMiddle if state else Qt.ElideRight)
        for index in range(self.topLevelItemCount()):
            self.topLevelItem(index).set_text(fullpath=self.show_fullpath)

    def __hide_or_show_root_items(self, item):
        """
        show_all_files option is disabled: hide all root items except *item*
        show_all_files option is enabled: do nothing
        """
        for _it in self.get_top_level_items():
            _it.setHidden(_it is not item and not self.show_all_files)

    @Slot(bool)
    def toggle_show_all_files(self, state):
        self.show_all_files = state
        if self.current_editor is not None:
            editor_id = self.editor_ids[self.current_editor]
            item = self.editor_items[editor_id]
            self.__hide_or_show_root_items(item)
            self.__sort_toplevel_items()
            if self.show_all_files is False:
                self.root_item_selected(
                    self.editor_items[self.editor_ids[self.current_editor]])

    @Slot(bool)
    def toggle_show_comments(self, state):
        self.show_comments = state
        self.update_all()

    @Slot(bool)
    def toggle_group_cells(self, state):
        self.group_cells = state
        self.update_all()

    @Slot(bool)
    def toggle_sort_files_alphabetically(self, state):
        self.sort_files_alphabetically = state
        self.update_all()
        self.__sort_toplevel_items()

    @Slot()
    def go_to_cursor_position(self, expand=True):
        if self.current_editor is not None:
            editor_id = self.editor_ids[self.current_editor]
            line = self.current_editor.get_cursor_line_number()
            tree = self.editor_tree_cache[editor_id]
            overlap = tree[line - 1]
            if len(overlap) == 0:
                return

            sorted_nodes = sorted(overlap)
            # The last item of the sorted elements correspond to the current
            # node
            item_interval = sorted_nodes[-1]
            item_ref = item_interval.data
            item = item_ref.node
            self.setCurrentItem(item)
            self.scrollToItem(item)

    @Slot()
    def do_follow_cursor(self):
        """Go to cursor position without expending."""
        if self.follow_cursor:
            self.go_to_cursor_position(expand=False)

    @Slot(bool)
    def toggle_follow_cursor(self, state):
        """Follow the cursor."""
        self.follow_cursor = state

    def connect_current_editor(self, state):
        """Connect or disconnect the editor from signals."""
        editor = self.current_editor
        if editor is None:
            return

        # Connect syntax highlighter
        sig_update = editor.sig_outline_explorer_data_changed
        sig_move = editor.sig_cursor_position_changed
        if state:
            sig_update.connect(self.update_current)
            sig_move.connect(self.do_follow_cursor)
            self.do_follow_cursor()
        else:
            try:
                sig_update.disconnect(self.update_current)
                sig_move.disconnect(self.do_follow_cursor)
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
        if editor_id in list(self.editor_ids.values()):
            item = self.editor_items[editor_id].node
            if not self.freeze:
                self.scrollToItem(item)
                self.root_item_selected(item)
                self.__hide_or_show_root_items(item)
            if update:
                self.save_expanded_state()
                # tree_cache = self.editor_tree_cache[editor_id]
                # self.populate_branch(editor, item, tree_cache)
                self.restore_expanded_state()
        else:
            this_root = SymbolStatus(editor.fname, None, None)
            root_item = FileRootItem(editor.fname, self, editor.is_python())
            root_item.set_text(fullpath=self.show_fullpath)
            editor_tree = IntervalTree()
            this_root.node = root_item
            # tree_cache = self.populate_branch(editor, root_item)
            self.__hide_or_show_root_items(root_item)
            self.root_item_selected(root_item)
            self.editor_items[editor_id] = this_root
            self.editor_tree_cache[editor_id] = editor_tree
            self.resizeColumnToContents(0)
        if editor not in self.editor_ids:
            self.editor_ids[editor] = editor_id
            self.ordered_editor_ids.append(editor_id)
            self.__sort_toplevel_items()
        self.current_editor = editor

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

    @Slot()
    def update_all(self):
        """
        Update the outline explorer for all editors tree preserving the tree
        state
        """
        self.save_expanded_state()
        for editor, editor_id in list(self.editor_ids.items()):
            self.__do_update(editor, editor_id)
        self.restore_expanded_state()
        self.do_follow_cursor()

    @Slot(list)
    def update_current(self, items):
        """
        Update the outline explorer for the current editor tree preserving the
        tree state
        """
        plugin_base = self.parent().parent()
        editor = self.current_editor
        editor_id = editor.get_id()
        update = self.update_tree(items, editor_id)
        if getattr(plugin_base, "_isvisible", True) and update:
            self.save_expanded_state()
            self.__do_update(editor, editor_id)
            self.restore_expanded_state()
            self.do_follow_cursor()

    def merge_interval(self, parent, node):
        if node.parent is not None:
            return node

        match = False
        start, end = node.position
        while parent.parent is not None and not match:
            parent_start, parent_end = parent.position
            if parent_end <= start:
                parent = parent.parent
            else:
                match = True

        parent.add_node(node)
        return node

    def update_tree(self, items, editor_id):
        current_tree = self.editor_tree_cache[editor_id]
        tree_info = []
        for symbol in items:
            symbol_name = symbol['name']
            symbol_kind = symbol['kind']
            # NOTE: This could be also a DocumentSymbol
            symbol_range = symbol['location']['range']
            symbol_start = symbol_range['start']['line']
            symbol_end = symbol_range['end']['line']
            symbol_repr = SymbolStatus(symbol_name, symbol_kind,
                                       (symbol_start, symbol_end))
            tree_info.append((symbol_start, symbol_end + 1, symbol_repr))

        tree = IntervalTree.from_tuples(tree_info)
        changes = tree - current_tree
        deleted = current_tree - tree

        if len(changes) == 0 and len(deleted) == 0:
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

        if non_merged > 0:
            tree_copy = IntervalTree(tree)
            tree_copy.merge_overlaps(
                data_reducer=self.merge_interval, data_initializer=root)

        self.editor_tree_cache[editor_id] = tree
        return True

    def __do_update(self, editor, editor_id):
        """
        Recalculate the and update the tree items in the Outliner for a
        given editor
        """
        item = self.editor_items[editor_id].node
        tree_cache = self.editor_tree_cache[editor_id]
        # self.populate_branch(editor, item, tree_cache)

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

        self.freeze = True
        if line:
            self.parent().edit_goto.emit(root_item.path, line, text)
        else:
            self.parent().edit.emit(root_item.path)
        self.freeze = False

        parent = self.current_editor.parent()
        for editor_id, i_item in list(self.editor_items.items()):
            if i_item.node is root_item:
                for editor, _id in list(self.editor_ids.items()):
                    if _id == editor_id and editor.parent() is parent:
                        self.current_editor = editor
                        break
                break

    def clicked(self, item):
        """Click event"""
        if isinstance(item, FileRootItem):
            self.root_item_selected(item)
        self.activated(item)


class OutlineExplorerWidget(QWidget):
    """Class browser"""
    edit_goto = Signal(str, int, str)
    edit = Signal(str)
    is_visible = Signal()

    def __init__(self, parent=None, show_fullpath=True, show_all_files=True,
                 group_cells=True, show_comments=True,
                 sort_files_alphabetically=False,
                 follow_cursor=True,
                 options_button=None):
        QWidget.__init__(self, parent)

        self.treewidget = OutlineExplorerTreeWidget(
            self,
            show_fullpath=show_fullpath,
            show_all_files=show_all_files,
            group_cells=group_cells,
            show_comments=show_comments,
            sort_files_alphabetically=sort_files_alphabetically,
            follow_cursor=follow_cursor,
            )

        self.visibility_action = create_action(self,
                                           _("Show/hide outline explorer"),
                                           icon='outline_explorer_vis.png',
                                           toggled=self.toggle_visibility)
        self.visibility_action.setChecked(True)

        btn_layout = QHBoxLayout()
        for btn in self.setup_buttons():
            btn.setAutoRaise(True)
            btn.setIconSize(QSize(16, 16))
            btn_layout.addWidget(btn)
        if options_button:
            btn_layout.addStretch()
            btn_layout.addWidget(options_button, Qt.AlignRight)

        layout = create_plugin_layout(btn_layout, self.treewidget)
        self.setLayout(layout)

    @Slot(bool)
    def toggle_visibility(self, state):
        self.setVisible(state)
        current_editor = self.treewidget.current_editor
        if current_editor is not None:
            current_editor.give_focus()
            if state:
                self.is_visible.emit()

    def setup_buttons(self):
        """Setup the buttons of the outline explorer widget toolbar."""
        self.fromcursor_btn = create_toolbutton(
            self, icon=ima.icon('fromcursor'), tip=_('Go to cursor position'),
            triggered=self.treewidget.go_to_cursor_position)

        buttons = [self.fromcursor_btn]
        for action in [self.treewidget.collapse_all_action,
                       self.treewidget.expand_all_action,
                       self.treewidget.restore_action,
                       self.treewidget.collapse_selection_action,
                       self.treewidget.expand_selection_action]:
            buttons.append(create_toolbutton(self))
            buttons[-1].setDefaultAction(action)
        return buttons

    def set_current_editor(self, editor, update, clear):
        if clear:
            self.remove_editor(editor)
        if editor is not None:
            self.treewidget.set_current_editor(editor, update)

    def remove_editor(self, editor):
        self.treewidget.remove_editor(editor)

    def get_options(self):
        """
        Return outline explorer options
        """
        return dict(
            show_fullpath=self.treewidget.show_fullpath,
            show_all_files=self.treewidget.show_all_files,
            group_cells=self.treewidget.group_cells,
            show_comments=self.treewidget.show_comments,
            sort_files_alphabetically=(
                self.treewidget.sort_files_alphabetically),
            expanded_state=self.treewidget.get_expanded_state(),
            scrollbar_position=self.treewidget.get_scrollbar_position(),
            visibility=self.isVisible(),
            )

    def update(self):
        self.treewidget.update_all()

    def file_renamed(self, editor, new_filename):
        self.treewidget.file_renamed(editor, new_filename)
