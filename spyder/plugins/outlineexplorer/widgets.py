# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Outline explorer widgets."""

# Standard library imports
from __future__ import print_function
import os.path as osp

# Third party imports
from qtpy.compat import from_qvariant
from qtpy.QtCore import QSize, Qt, Signal, Slot
from qtpy.QtWidgets import (QHBoxLayout, QTreeWidgetItem, QWidget,
                            QTreeWidgetItemIterator)

# Local imports
from spyder.config.base import _, STDOUT
from spyder.py3compat import to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (create_action, create_toolbutton,
                                    set_item_user_text, create_plugin_layout)
from spyder.widgets.onecolumntree import OneColumnTree


class FileRootItem(QTreeWidgetItem):
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
            line = self.current_editor.get_cursor_line_number()
            editor_id = self.editor_ids[self.current_editor]
            root_item = self.editor_items[editor_id]
            item = item_at_line(root_item, line)
            if not expand:
                # Look for a non expanded item
                tree_iter = item
                while tree_iter:
                    if not tree_iter.isExpanded():
                        item = tree_iter
                    tree_iter = tree_iter.parent()
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
            sig_update.connect(self.update_all)
            sig_move.connect(self.do_follow_cursor)
            self.do_follow_cursor()
        else:
            try:
                sig_update.disconnect(self.update_all)
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
            item = self.editor_items[editor_id]
            if not self.freeze:
                self.scrollToItem(item)
                self.root_item_selected(item)
                self.__hide_or_show_root_items(item)
            if update:
                self.save_expanded_state()
                tree_cache = self.editor_tree_cache[editor_id]
                self.populate_branch(editor, item, tree_cache)
                self.restore_expanded_state()
        else:
            root_item = FileRootItem(editor.fname, self, editor.is_python())
            root_item.set_text(fullpath=self.show_fullpath)
            tree_cache = self.populate_branch(editor, root_item)
            self.__hide_or_show_root_items(root_item)
            self.root_item_selected(root_item)
            self.editor_items[editor_id] = root_item
            self.editor_tree_cache[editor_id] = tree_cache
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
            root_item = self.editor_items[editor_id]
            root_item.set_path(new_filename, fullpath=self.show_fullpath)
            self.__sort_toplevel_items()

    @Slot()
    def update_all(self):
        self.save_expanded_state()
        for editor, editor_id in list(self.editor_ids.items()):
            item = self.editor_items[editor_id]
            tree_cache = self.editor_tree_cache[editor_id]
            self.populate_branch(editor, item, tree_cache)
        self.restore_expanded_state()
        self.do_follow_cursor()

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
                    self.takeTopLevelItem(self.indexOfTopLevelItem(root_item))
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
                self.editor_items.get(e_id) for e_id in
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

    def populate_branch(self, editor, root_item, tree_cache=None):
        """
        Generates an outline of the editor's content and stores the result
        in a cache.
        """
        if tree_cache is None:
            tree_cache = {}

        for _l in list(tree_cache.keys()):
            # Checking if key is still in tree cache in case one of its
            # ancestors was deleted in the meantime (deleting all children):
            if _l not in tree_cache:
                continue

            # Removing deleted items
            if not tree_cache[_l][0].oedata.is_valid():
                remove_from_tree_cache(tree_cache, line=_l)
                continue

            # Moving cached items whose line changed
            block_line = tree_cache[_l][0].line
            if _l != block_line:
                if block_line in tree_cache:
                    remove_from_tree_cache(tree_cache, line=block_line)
                if _l in tree_cache:
                    if block_line is not None:
                        tree_cache[block_line] = tree_cache[_l]
                    tree_cache.pop(_l)

        ancestors = [(root_item, 0)]
        cell_ancestors = [(root_item, 0)]
        previous_item = None
        previous_level = None
        prev_cell_level = None
        prev_cell_item = None

        for data in editor.outlineexplorer_data_list():
            try:
                line_nb = data.get_block_number()
                if line_nb is None:
                    continue
                line_nb += 1
            except AttributeError:
                continue
            level = None if data is None else data.fold_level
            citem, _d = tree_cache.get(line_nb, (None, ""))
            if citem is not None:
                # Check if underlying C++ object has been deleted
                try:
                    citem.text(0)
                except RuntimeError:
                    tree_cache.pop(line_nb)
                    citem, _d = (None, "")

            # Skip iteration if line is not the first line of a foldable block
            if level is None:
                if citem is not None:
                    remove_from_tree_cache(tree_cache, line=line_nb)
                continue

            # Searching for class/function statements
            not_class_nor_function = data.is_not_class_nor_function()
            if not not_class_nor_function:
                class_name = data.get_class_name()
                if class_name is None:
                    func_name = data.get_function_name()
                    if func_name is None:
                        if citem is not None:
                            remove_from_tree_cache(tree_cache, line=line_nb)
                        continue

            # Skip iteration for if/else/try/for/etc foldable blocks.
            if not_class_nor_function and not data.is_comment():
                if citem is not None:
                    remove_from_tree_cache(tree_cache, line=line_nb)
                continue

            if citem is not None:
                cname = to_text_string(citem.text(0))
                cparent = citem.parent()
                clevel = citem.level()

            # Blocks for Cell Groups.
            if (data is not None and data.def_type == data.CELL and
                    self.group_cells):
                preceding = (root_item if previous_item is None
                             else previous_item)
                cell_level = data.cell_level
                if prev_cell_level is not None:
                    if cell_level == prev_cell_level:
                        pass
                    elif cell_level > prev_cell_level:
                        cell_ancestors.append((prev_cell_item,
                                               prev_cell_level))
                    else:
                        while (len(cell_ancestors) > 1 and
                               cell_level <= prev_cell_level):
                            cell_ancestors.pop(-1)
                            _item, prev_cell_level = cell_ancestors[-1]
                parent, _level = cell_ancestors[-1]
                if citem is not None:
                    if data.text == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                item = CellItem(data, parent, preceding)
                debug = "%s -- %s/%s" % (str(item.line).rjust(6),
                                         to_text_string(item.parent().text(0)),
                                         to_text_string(item.text(0)))
                tree_cache[line_nb] = (item, debug)
                ancestors = [(item, 0)]
                prev_cell_level = cell_level
                prev_cell_item = item
                previous_item = item
                continue

            # Blocks for Code Groups.
            if previous_level is not None:
                if level == previous_level:
                    pass
                elif level > previous_level:
                    ancestors.append((previous_item, previous_level))
                else:
                    while len(ancestors) > 1 and level <= previous_level:
                        ancestors.pop(-1)
                        _item, previous_level = ancestors[-1]
            parent, _level = ancestors[-1]

            preceding = root_item if previous_item is None else previous_item
            if not_class_nor_function and data.is_comment():
                if not self.show_comments:
                    if citem is not None:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                    continue
                if citem is not None:
                    if data.text == cname and level == clevel:
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                if data.def_type == data.CELL:
                    item = CellItem(data, parent, preceding)
                else:
                    item = CommentItem(data, parent, preceding)
            elif class_name is not None:
                if citem is not None:
                    if (class_name == cname and level == clevel and
                            parent is cparent):
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                item = ClassItem(data, parent, preceding)
            else:
                if citem is not None:
                    if (func_name == cname and level == clevel and
                            parent is cparent):
                        previous_level = clevel
                        previous_item = citem
                        continue
                    else:
                        remove_from_tree_cache(tree_cache, line=line_nb)
                item = FunctionItem(data, parent, preceding)

            debug = "%s -- %s/%s" % (str(item.line).rjust(6),
                                     to_text_string(item.parent().text(0)),
                                     to_text_string(item.text(0)))
            tree_cache[line_nb] = (item, debug)
            previous_level = level
            previous_item = item

        return tree_cache

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
            self.root_item_selected(self.editor_items[editor_id])

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
        editor_item = self.editor_items.get(
            self.editor_ids.get(self.current_editor))
        line = 0
        if item == editor_item:
            line = 1
        elif isinstance(item, TreeItem):
            line = item.line

        self.freeze = True
        root_item = self.get_root_item(item)
        if line:
            self.parent().edit_goto.emit(root_item.path, line, item.text(0))
        else:
            self.parent().edit.emit(root_item.path)
        self.freeze = False

        parent = self.current_editor.parent()
        for editor_id, i_item in list(self.editor_items.items()):
            if i_item is root_item:
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
