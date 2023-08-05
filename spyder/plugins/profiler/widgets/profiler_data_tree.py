# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# based on pylintgui.py by Pierre Raybaut
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Profiler widget.

See the official documentation on python profiling:
https://docs.python.org/3/library/profile.html
"""

# Standard library imports
import os
import os.path as osp
import tempfile

# Third party imports
from qtpy import PYQT5
from qtpy.QtCore import Qt, Signal
from qtpy.QtGui import QColor
from qtpy.QtWidgets import (QWidget, QMessageBox, QTreeWidget,
                            QTreeWidgetItem, QVBoxLayout)

# Local imports
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.translations import _
from spyder.api.widgets.mixins import SpyderWidgetMixin
from spyder.py3compat import to_text_string
from spyder.utils.palette import SpyderPalette
from spyder.utils.qthelpers import set_item_user_text
from spyder.widgets.helperwidgets import FinderWidget


class ProfilerKey:
    """
    Class to save the indexes of the profiler keys

    The quantities calculated by the profiler are as follows
    (from profile.Profile):
    [0] = The number of times this function was called, not counting direct
          or indirect recursion,
    [1] = Number of times this function appears on the stack, minus one
    [2] = Total time spent internal to this function
    [3] = Cumulative time that this function was present on the stack.  In
          non-recursive functions, this is the total execution time from start
          to finish of each invocation of a function, including time spent in
          all subfunctions.
    [4] = A dictionary indicating for each function name, the number of times
          it was called by us.
    """
    Calls = 0
    TotalCalls = 1
    LocalTime = 2
    TotalTime = 3
    Callers = 4


class ProfilerSubWidget(QWidget, SpyderWidgetMixin):
    """Profiler widget for shellwidget"""

    # Signals
    sig_edit_goto_requested = Signal(str, int, str)
    sig_display_requested = Signal(object)
    sig_hide_finder_requested = Signal()
    sig_refresh = Signal()

    def __init__(self, parent=None):
        if PYQT5:
            super().__init__(parent, class_parent=parent)
        else:
            QWidget.__init__(self, parent)
            SpyderWidgetMixin.__init__(self, class_parent=parent)

        # Finder
        self.data_tree = None
        self.finder = None
        self.setup()

    def toggle_finder(self, show):
        """Show and hide the finder."""
        if self.finder is None:
            return
        self.finder.set_visible(show)
        if not show:
            self.data_tree.setFocus()
            self.data_tree._show_tree()

    def do_find(self, text):
        """Search for text."""
        if self.data_tree is not None:
            self.data_tree.do_find(text)

    def finder_is_visible(self):
        """Check if the finder is visible."""
        if self.finder is None:
            return False
        return self.finder.isVisible()

    def setup(self):
        """Setup widget."""
        self.data_tree = ProfilerDataTree(self)
        self.data_tree.sig_edit_goto_requested.connect(
            self.sig_edit_goto_requested)
        self.data_tree.sig_refresh.connect(self.sig_refresh)

        self.finder = FinderWidget(self)
        self.finder.sig_find_text.connect(self.do_find)
        self.finder.sig_hide_finder_requested.connect(
            self.sig_hide_finder_requested)

        # Setup layout.
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.data_tree)
        layout.addSpacing(1)
        layout.addWidget(self.finder)
        self.setLayout(layout)

    def show_profile_buffer(self, prof_buffer, lib_pathlist):
        """Show profile file."""
        if not prof_buffer:
            return

        with tempfile.TemporaryDirectory() as dir:
            filename = os.path.join(dir, "tem.prof")
            with open(filename, "bw") as f:
                f.write(prof_buffer)
            self.data_tree.lib_pathlist = lib_pathlist
            self.data_tree.load_data(filename)

        # Show
        self.data_tree._show_tree()
        self.sig_display_requested.emit(self)

    def set_context_menu(self, menu):
        self.data_tree.menu = menu


class TreeWidgetItem(QTreeWidgetItem):
    """Item to show in the tree. It represent a function call."""
    def __init__(self, parent, item_key, profile_data, compare_data, icon_list,
                 index_dict):
        QTreeWidgetItem.__init__(self, parent)

        self.item_key = item_key
        self.index_dict = index_dict

        # Order is from profile data
        self.total_calls, self.local_time, self.total_time = profile_data[1:4]
        (filename, line_number, function_name, file_and_line, node_type
         ) = self.function_info(item_key)

        self.function_name = function_name
        self.filename = filename
        self.line_number = line_number

        self.set_item_data(filename, line_number)
        self.setIcon(self.index_dict["function_name"], icon_list[node_type])
        self.set_tooltips()

        data = {
            "function_name": function_name,
            "total_time": self.format_measure(self.total_time),
            "local_time": self.format_measure(self.local_time),
            "number_calls": self.format_measure(self.total_calls),
            "file:line": file_and_line
            }
        self.set_data(data)
        alignment = {
            "total_time": Qt.AlignRight,
            "local_time": Qt.AlignRight,
            "number_calls": Qt.AlignRight,
        }
        self.set_alignment(alignment)

        if self.is_recursive():
            self.setData(self.index_dict["file:line"],
                         Qt.DisplayRole, '(%s)' % _('recursion'))
            self.setDisabled(True)

        if compare_data is None:
            return

        diff_data = {}
        diff_colors = {}
        # Keep same order as profile data
        compare_keys = [
            "unused",
            "number_calls_diff",
            "local_time_diff",
            "total_time_diff"
        ]
        for i in range(1, 4):
            diff_str, color = self.color_diff(
                profile_data[i] - compare_data[i])
            diff_data[compare_keys[i]] = diff_str
            diff_colors[compare_keys[i]] = color

        self.set_data(diff_data)
        self.set_color(diff_colors)
        diff_alignment = {
            "total_time_diff": Qt.AlignLeft,
            "local_time_diff": Qt.AlignLeft,
            "number_calls_diff": Qt.AlignLeft
        }
        self.set_alignment(diff_alignment)

    def set_tooltips(self):
        """Set tooltips."""
        tooltips = {
            "function_name": _('Function or module name'),
            "total_time": _('Time in function (including sub-functions)'),
            "local_time": _('Local time in function (not in sub-functions)'),
            "number_calls": _('Total number of calls (including recursion)'),
            "file:line": _('File:line where function is defined')
        }
        for k, v in tooltips.items():
            self.setToolTip(self.index_dict[k], v)

    def set_data(self, data):
        """Set data in columns."""
        for k, v in data.items():
            self.setData(self.index_dict[k], Qt.DisplayRole, v)

    def set_color(self, colors):
        """Set colors"""
        for k, v in colors.items():
            self.setForeground(self.index_dict[k], QColor(v))

    def set_alignment(self, alignment):
        """Set alignment."""
        for k, v in alignment.items():
            self.setTextAlignment(self.index_dict[k], v)

    @staticmethod
    def color_diff(difference):
        """Color difference."""
        diff_str = ""
        color = "black"
        if difference:
            color, sign = (
                (SpyderPalette.COLOR_SUCCESS_1, '-')
                if difference < 0
                else (SpyderPalette.COLOR_ERROR_1, '+')
            )
            diff_str = '{}{}'.format(
                sign, TreeWidgetItem.format_measure(difference))
        return diff_str, color

    @staticmethod
    def format_measure(measure):
        """Get format and units for data coming from profiler task."""
        # Convert to a positive value.
        measure = abs(measure)

        # For number of calls
        if isinstance(measure, int):
            return to_text_string(measure)

        # For time measurements
        if 1.e-9 < measure <= 1.e-6:
            measure = u"{0:.2f} ns".format(measure / 1.e-9)
        elif 1.e-6 < measure <= 1.e-3:
            measure = u"{0:.2f} \u03BCs".format(measure / 1.e-6)
        elif 1.e-3 < measure <= 1:
            measure = u"{0:.2f} ms".format(measure / 1.e-3)
        elif 1 < measure <= 60:
            measure = u"{0:.2f} s".format(measure)
        elif 60 < measure <= 3600:
            m, s = divmod(measure, 3600)
            if s > 60:
                m, s = divmod(measure, 60)
                s = to_text_string(s).split(".")[-1]
            measure = u"{0:.0f}.{1:.2s} min".format(m, s)
        else:
            h, m = divmod(measure, 3600)
            if m > 60:
                m /= 60
            measure = u"{0:.0f}h:{1:.0f}min".format(h, m)
        return measure

    def __lt__(self, otherItem):
        column = self.treeWidget().sortColumn()
        try:
            if column == self.index_dict["total_time"]:
                return self.total_time > otherItem.total_time
            if column == self.index_dict["local_time"]:
                return self.local_time > otherItem.local_time

            return float(self.text(column)) > float(otherItem.text(column))
        except ValueError:
            return self.text(column) > otherItem.text(column)

    def set_item_data(self, filename, line_number):
        """Set tree item user data: filename (string) and line_number (int)"""
        # separator between filename and linenumber
        SEP = r"<[=]>"
        # (must be improbable as a filename)
        set_item_user_text(self, '%s%s%d' % (filename, SEP, line_number))

    def function_info(self, functionKey):
        """Returns processed information about the function's name and file."""
        node_type = 'function'
        filename, line_number, function_name = functionKey

        if function_name == '<module>':
            modulePath, moduleName = osp.split(filename)
            node_type = 'module'
            if moduleName == '__init__.py':
                modulePath, moduleName = osp.split(modulePath)
            function_name = '<' + moduleName + '>'

        if not filename or filename == '~':
            file_and_line = '(built-in)'
            node_type = 'builtin'
        else:
            if function_name == '__init__':
                node_type = 'constructor'
            file_and_line = '%s : %d' % (filename, line_number)

        return filename, line_number, function_name, file_and_line, node_type

    def is_recursive(self):
        """Returns True is a function is a descendant of itself."""
        ancestor = self.parent()
        while ancestor:
            if (self.function_name == ancestor.function_name
                    and self.filename == ancestor.filename
                    and self.line_number == ancestor.line_number):
                return True
            else:
                ancestor = ancestor.parent()
        return False


class ProfilerDataTree(QTreeWidget, SpyderConfigurationAccessor):
    """
    Convenience tree widget (with built-in model)
    to store and view profiler data.

    The quantities calculated by the profiler are as follows
    (from profile.Profile):
    [0] = The number of times this function was called, not counting direct
          or indirect recursion,
    [1] = Number of times this function appears on the stack, minus one
    [2] = Total time spent internal to this function
    [3] = Cumulative time that this function was present on the stack.  In
          non-recursive functions, this is the total execution time from start
          to finish of each invocation of a function, including time spent in
          all subfunctions.
    [4] = A dictionary indicating for each function name, the number of times
          it was called by us.
    """

    CONF_SECTION = 'profiler'

    # Signals
    sig_edit_goto_requested = Signal(str, int, str)
    sig_refresh = Signal()

    def __init__(self, parent=None):
        if PYQT5:
            super().__init__(parent)
        else:
            QTreeWidget.__init__(self, parent)

        self.header_list = [_('Function/Module'), _('Total Time'), _('Diff'),
                            _('Local Time'), _('Diff'), _('Calls'), _('Diff'),
                            _('File:line')]
        self.icon_list = {
            'module': parent.create_icon('python'),
            'function': parent.create_icon('function'),
            'builtin': parent.create_icon('python'),
            'constructor': parent.create_icon('class')
        }
        self.index_dict = {
            "function_name": 0,
            "total_time": 1,
            "total_time_diff": 2,
            "local_time": 3,
            "local_time_diff": 4,
            "number_calls": 5,
            "number_calls_diff": 6,
            "file:line": 7
        }
        self.profdata = None   # To be filled by self.load_data()
        self.items_to_be_shown = None
        self.current_view_depth = None
        self.compare_data = None
        self.inverted_tree = False
        self.ignore_builtins = False
        self.root_key = None
        self.menu = None
        self._last_children = None
        self.setColumnCount(len(self.header_list))
        self.setHeaderLabels(self.header_list)
        self.initialize_view()
        self.itemActivated.connect(self.item_activated)
        self.itemExpanded.connect(self.item_expanded)
        self.lib_pathlist = None
        self.history = []
        self.redo_history = []

    def contextMenuEvent(self, event):
        """Reimplement Qt method"""
        if self.menu is None:
            return
        if self.profdata:
            self.menu.popup(event.globalPos())
            event.accept()

    def initialize_view(self):
        """Clean the tree and view parameters"""
        self.clear()
        self.items_to_be_shown = {}
        self.current_view_depth = 0
        if (
            self.compare_data is not None
            and self.compare_data is not self.profdata
        ):
            self.hide_diff_cols(False)
        else:
            self.hide_diff_cols(True)

    def load_data(self, profdatafile):
        """Load profiler data saved by profile/cProfile module"""
        self.history = []
        self.redo_history = []
        if not os.path.isfile(profdatafile):
            self.profdata = None
            return
        import pstats

        # Fixes spyder-ide/spyder#6220.
        try:
            self.profdata = pstats.Stats(profdatafile)
            self.profdata.calc_callees()
            self.root_key = self.find_root()
        except (OSError, IOError):
            self.profdata = None
            return

    def compare(self, filename):
        """Load compare file."""
        if filename is None:
            self.compare_data = None
            return
        import pstats

        # Fixes spyder-ide/spyder#5587.
        try:
            self.compare_data = pstats.Stats(filename)
            self.compare_data.calc_callees()
            if self.profdata is None:
                # Show the compare data as prof_data
                self.profdata = self.compare_data
                self.root_key = self.find_root()
        except (OSError, IOError) as e:
            QMessageBox.critical(
                self,
                _("Error"),
                _("Error when trying to load profiler results. "
                  "The error was<br><br>"
                  "<tt>{0}</tt>").format(e)
            )
            self.compare_data = None

    def hide_diff_cols(self, hide):
        """Hide difference columns."""
        for i in (self.index_dict["total_time_diff"],
                  self.index_dict["local_time_diff"],
                  self.index_dict["number_calls_diff"]):
            self.setColumnHidden(i, hide)

    def save_data(self, filename):
        """Save profiler data."""
        self.profdata.dump_stats(filename)

    def find_root(self):
        """Find a function without a caller."""
        # Fixes spyder-ide/spyder#8336.
        if self.profdata is not None:
            self.profdata.sort_stats("cumulative")
        else:
            return
        for func in self.profdata.fcn_list:
            if (
                ('~', 0) != func[0:2]
                and not func[2].startswith('<built-in method exec>')
            ):
                # This skips the profiler function at the top of the list
                # it does only occur in Python 3
                return func

    def is_builtin(self, key):
        """Check if key is buit-in."""
        path = key[0]
        if not path:
            return True
        if path == "~":
            return True
        if path.startswith("<"):
            return True

        path = os.path.normcase(os.path.normpath(path))
        if self.lib_pathlist is not None:
            for libpath in self.lib_pathlist:
                libpath = os.path.normcase(os.path.normpath(libpath))
                commonpath = os.path.commonpath([libpath, path])
                if libpath == commonpath:
                    return True

        return False

    def find_children(self, parent):
        """Find all functions called by (parent) function."""
        if self.inverted_tree:
            # Return callers
            return self.profdata.stats[parent][ProfilerKey.Callers]
        else:
            # Return callees
            callees = self.profdata.all_callees[parent]
            if self.ignore_builtins:
                callees = [c for c in callees if not self.is_builtin(c)]
            return callees

    def do_find(self, text):
        """Find all function that match text."""
        if self.profdata is None:
            # Nothing to show
            return

        children = self.profdata.fcn_list
        children = [c for c in children if text in c[-1]]
        self._show_tree(children)

    def show_slow(self):
        """Show slow items."""
        if self.profdata is None:
            # Nothing to show
            return

        # Show items with large local time
        children = self.profdata.fcn_list

        # Only keep top n_slow_children
        N_children = self.get_conf('n_slow_children')
        children = sorted(
            children,
            key=lambda item: self.profdata.stats[item][ProfilerKey.LocalTime],
            reverse=True
        )

        if self.ignore_builtins:
            children = [c for c in children if not self.is_builtin(c)]
        children = children[:N_children]
        self._show_tree(children, max_items=N_children)

    def refresh_tree(self):
        """Refresh tree."""
        self._show_tree(self._last_children)

    def home_tree(self):
        """Reset tree."""
        self._show_tree()

    def show_selected(self):
        """Show current item."""
        self._show_tree([self.currentItem().item_key])

    def undo(self):
        """Undo change."""
        if len(self.history) > 1:
            self.redo_history.append(self.history.pop(-1))
            self._show_tree(self.history.pop(-1), reset_redo=False)

    def redo(self):
        """Redo changes."""
        if len(self.redo_history) > 0:
            self._show_tree(self.redo_history.pop(-1), reset_redo=False)

    def _show_tree(self, children=None, max_items=None,
                   reset_redo=True):
        """Populate the tree with profiler data and display it."""
        if self.profdata is None:
            # Nothing to show
            return

        self._last_children = children

        # List of internal functions to exclude
        internal_list = [
            ('~', 0, "<method 'disable' of '_lsprof.Profiler' objects>")
        ]

        # List of frames to hide at the top
        head_list = [self.root_key, ]
        head_list += list(
            self.profdata.stats[self.root_key][ProfilerKey.Callers])

        if children is None:
            if self.inverted_tree:
                # Show all callees
                self.tree_state = None
                children = []
                for key, value in self.profdata.all_callees.items():
                    if key in internal_list or key in head_list:
                        continue
                    if self.ignore_builtins:
                        if not self.is_builtin(key):
                            non_builtin_callees = [
                                k for k in value if not self.is_builtin(k)]
                            if len(non_builtin_callees) == 0:
                                children.append(key)
                    else:
                        if len(value) == 0:
                            children.append(key)
            else:
                # Show all called
                self.tree_state = None
                rootkey = self.root_key  # This root contains profiler overhead
                if rootkey is not None:
                    children = self.find_children(rootkey)
        else:
            if self.ignore_builtins:
                children = [c for c in children if not self.is_builtin(c)]
            children = [c for c in children if c not in internal_list]
            if max_items is not None:
                children = children[:max_items]

        self.initialize_view()  # Clear before re-populating
        self.setItemsExpandable(True)
        self.setSortingEnabled(False)
        if children is not None:
            if len(self.history) == 0 or self.history[-1] != children:
                # Do not add twice the same element
                self.history.append(children)
                if reset_redo:
                    self.redo_history = []

            # Populate the tree
            self.populate_tree(self, children)
            self.setSortingEnabled(True)
            self.sortItems(self.index_dict["total_time"], Qt.AscendingOrder)
            if len(children) < 100:
                # Only expand if not too many children are shown
                self.change_view(1)
            self.resizeColumnToContents(0)
        
        self.sig_refresh.emit()

    def populate_tree(self, parentItem, children_list):
        """
        Recursive method to create each item (and associated data)
        in the tree.
        """
        for child_key in children_list:
            item_profdata, item_compdata = self.get_item_data(child_key)
            child_item = TreeWidgetItem(
                parentItem,
                child_key,
                item_profdata,
                item_compdata,
                self.icon_list,
                self.index_dict
            )
            if not child_item.is_recursive():
                grandchildren_list = self.find_children(child_key)
                if grandchildren_list:
                    child_item.setChildIndicatorPolicy(
                        child_item.ShowIndicator)
                    self.items_to_be_shown[id(child_item)] = grandchildren_list

    def get_item_data(self, item_key):
        """Return the profile and compare data for the item_key."""
        item_profdata = self.profdata.stats.get(
            item_key, [0, 0, 0, 0, {}])
        item_compdata = None
        if self.compare_data is not None:
            item_compdata = self.compare_data.stats.get(
                item_key, [0, 0, 0, 0, {}])
        return item_profdata, item_compdata

    def item_activated(self, item):
        """Request editor to find item."""
        self.sig_edit_goto_requested.emit(item.filename, item.line_number, '')

    def item_expanded(self, item):
        """Fill item children."""
        if item.childCount() == 0 and id(item) in self.items_to_be_shown:
            children_list = self.items_to_be_shown[id(item)]
            self.populate_tree(item, children_list)

    def get_top_level_items(self):
        """Iterate over top level items."""
        return [self.topLevelItem(_i)
                for _i in range(self.topLevelItemCount())]

    def get_items(self, maxlevel):
        """Return all items with a level <= `maxlevel`"""
        itemlist = []

        def add_to_itemlist(item, maxlevel, level=1):
            level += 1
            for index in range(item.childCount()):
                citem = item.child(index)
                itemlist.append(citem)
                if level <= maxlevel:
                    add_to_itemlist(citem, maxlevel, level)

        for tlitem in self.get_top_level_items():
            itemlist.append(tlitem)
            if maxlevel > 0:
                add_to_itemlist(tlitem, maxlevel=maxlevel)

        return itemlist

    def change_view(self, change_in_depth):
        """
        Change the view depth by expand or collapsing all same-level nodes.
        """
        self.current_view_depth += change_in_depth
        if self.current_view_depth < 0:
            self.current_view_depth = 0
        self.collapseAll()
        if self.current_view_depth > 0:
            for item in self.get_items(maxlevel=self.current_view_depth-1):
                item.setExpanded(True)
