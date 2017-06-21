# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import print_function
import os
import os.path as osp

# Third party imports
from qtpy.QtCore import Signal, QEvent, QObject, QRegExp, QSize, Qt
from qtpy.QtGui import (QIcon, QRegExpValidator, QTextCursor)
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QVBoxLayout,
                            QMainWindow)

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, to_text_string
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HelperToolButton, HTMLDelegate


# --- Python Outline explorer helpers
def process_python_symbol_data(oedata):
    """Returns a list with line number, definition name, fold and token."""
    symbol_list = []
    for key in oedata:
        val = oedata[key]
        if val and key != 'found_cell_separators':
            if val.is_class_or_function():
                symbol_list.append((key, val.def_name, val.fold_level,
                                    val.get_token()))
    return sorted(symbol_list)


def get_python_symbol_icons(oedata):
    """Return a list of icons for oedata of a python file."""
    class_icon = ima.icon('class')
    method_icon = ima.icon('method')
    function_icon = ima.icon('function')
    private_icon = ima.icon('private1')
    super_private_icon = ima.icon('private2')

    symbols = process_python_symbol_data(oedata)

    # line - 1, name, fold level
    fold_levels = sorted(list(set([s[2] for s in symbols])))
    parents = [None]*len(symbols)
    icons = [None]*len(symbols)
    indexes = []

    parent = None
    for level in fold_levels:
        for index, item in enumerate(symbols):
            line, name, fold_level, token = item
            if index in indexes:
                continue

            if fold_level == level:
                indexes.append(index)
                parent = item
            else:
                parents[index] = parent

    for index, item in enumerate(symbols):
        parent = parents[index]

        if item[-1] == 'def':
            icons[index] = function_icon
        elif item[-1] == 'class':
            icons[index] = class_icon
        else:
            icons[index] = QIcon()

        if parent is not None:
            if parent[-1] == 'class':
                if item[-1] == 'def' and item[1].startswith('__'):
                    icons[index] = super_private_icon
                elif item[-1] == 'def' and item[1].startswith('_'):
                    icons[index] = private_icon
                else:
                    icons[index] = method_icon

    return icons


def shorten_paths(path_list, is_unsaved):
    """
    Takes a list of paths and tries to "intelligently" shorten them all. The
    aim is to make it clear to the user where the paths differ, as that is
    likely what they care about. Note that this operates on a list of paths
    not on individual paths.

    If the path ends in an actual file name, it will be trimmed off.
    """
    # TODO: at the end, if the path is too long, should do a more dumb kind of
    # shortening, but not completely dumb.

    # Convert the path strings to a list of tokens and start building the
    # new_path using the drive
    path_list = path_list[:]  # Make a local copy
    new_path_list = []

    for ii, (path, is_unsav) in enumerate(zip(path_list, is_unsaved)):
        if is_unsav:
            new_path_list.append(_('unsaved file'))
            path_list[ii] = None
        else:
            drive, path = osp.splitdrive(osp.dirname(path))
            new_path_list.append(drive + osp.sep)
            path_list[ii] = [part for part in path.split(osp.sep) if part]

    def recurse_level(level_idx):
        sep = os.sep

        # If toks are all empty we need not have recursed here
        if not any(level_idx.values()):
            return

        # Firstly, find the longest common prefix for all in the level
        # s = len of longest common prefix
        sample_toks = list(level_idx.values())[0]
        if not sample_toks:
            s = 0
        else:
            for s, sample_val in enumerate(sample_toks):
                if not all(len(toks) > s and toks[s] == sample_val
                           for toks in level_idx.values()):
                    break

        # Shorten longest common prefix
        if s == 0:
            short_form = ''
        else:
            if s == 1:
                short_form = sample_toks[0]
            elif s == 2:
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:
                short_form = "..." + sep + sample_toks[s-1]
            for idx in level_idx:
                new_path_list[idx] += short_form + sep
                level_idx[idx] = level_idx[idx][s:]

        # Group the remaining bit after the common prefix, shorten, and recurse
        while level_idx:
            k, group = 0, level_idx  # k is length of the group's common prefix
            while True:
                # Abort if we've gone beyond end of one or more in the group
                prospective_group = {idx: toks for idx, toks
                                     in group.items() if len(toks) == k}
                if prospective_group:
                    if k == 0:  # we spit out the group with no suffix
                        group = prospective_group
                    break
                # Only keep going if all n still match on the kth token
                _, sample_toks = next(iteritems(group))
                prospective_group = {idx: toks for idx, toks
                                     in group.items()
                                     if toks[k] == sample_toks[k]}
                if len(prospective_group) == len(group) or k == 0:
                    group = prospective_group
                    k += 1
                else:
                    break
            _, sample_toks = next(iteritems(group))
            if k == 0:
                short_form = ''
            elif k == 1:
                short_form = sample_toks[0]
            elif k == 2:
                short_form = sample_toks[0] + sep + sample_toks[1]
            else:  # k > 2
                short_form = sample_toks[0] + "..." + sep + sample_toks[k-1]
            for idx in group.keys():
                new_path_list[idx] += short_form + (sep if k > 0 else '')
                del level_idx[idx]
            recurse_level({idx: toks[k:] for idx, toks in group.items()})

    recurse_level({i: pl for i, pl in enumerate(path_list) if pl})

    return [path.rstrip(os.sep) for path in new_path_list]


class KeyPressFilter(QObject):
    """Use with `installEventFilter` to get up/down arrow key press signal."""
    UP, DOWN = [-1, 1]  # Step constants

    sig_up_key_pressed = Signal()
    sig_down_key_pressed = Signal()

    def eventFilter(self, src, e):
        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Up:
                self.sig_up_key_pressed.emit()
            elif e.key() == Qt.Key_Down:
                self.sig_down_key_pressed.emit()

        return super(KeyPressFilter, self).eventFilter(src, e)


class FilesFilterLine(QLineEdit):
    """QLineEdit used to filter files by name."""

    # User has not clicked outside this widget
    clicked_outside = False

    def focusOutEvent(self, event):
        """
        Detect when the focus goes out of this widget.

        This is used to make the file switcher leave focus on the
        last selected file by the user.
        """
        self.clicked_outside = True
        return super(QLineEdit, self).focusOutEvent(event)


class FileSwitcher(QDialog):
    """A Sublime-like file switcher."""
    sig_goto_file = Signal(int, object)

    # Constants that define the mode in which the list widget is working
    # FILE_MODE is for a list of files, SYMBOL_MODE if for a list of symbols
    # in a given file when using the '@' symbol.
    FILE_MODE, SYMBOL_MODE = [1, 2]

    def __init__(self, parent, plugin, tabs, data, icon):
        QDialog.__init__(self, parent)

        # Variables
        self.plugins_tabs = []
        self.plugins_data = []
        self.plugins_instances = []
        self.add_plugin(plugin, tabs, data, icon)
        self.plugin = None                # Last plugin with focus
        self.mode = self.FILE_MODE        # By default start in this mode
        self.initial_cursors = None       # {fullpath: QCursor}
        self.initial_path = None          # Fullpath of initial active editor
        self.initial_widget = None        # Initial active editor
        self.line_number = None           # Selected line number in filer
        self.is_visible = False           # Is the switcher visible?

        help_text = _("Press <b>Enter</b> to switch files or <b>Esc</b> to "
                      "cancel.<br><br>Type to filter filenames.<br><br>"
                      "Use <b>:number</b> to go to a line, e.g. "
                      "<b><code>main:42</code></b><br>"
                      "Use <b>@symbol_text</b> to go to a symbol, e.g. "
                      "<b><code>@init</code></b>"
                      "<br><br> Press <b>Ctrl+W</b> to close current tab.<br>")

        # Either allow searching for a line number or a symbol but not both
        regex = QRegExp("([A-Za-z0-9_]{0,100}@[A-Za-z0-9_]{0,100})|" +
                        "([A-Za-z0-9_]{0,100}:{0,1}[0-9]{0,100})")

        # Widgets
        self.edit = FilesFilterLine(self)
        self.help = HelperToolButton()
        self.list = QListWidget(self)
        self.filter = KeyPressFilter()
        regex_validator = QRegExpValidator(regex, self.edit)

        # Widgets setup
        self.setWindowFlags(Qt.Popup | Qt.FramelessWindowHint)
        self.setWindowOpacity(0.95)
        self.edit.installEventFilter(self.filter)
        self.edit.setValidator(regex_validator)
        self.help.setToolTip(help_text)
        self.list.setItemDelegate(HTMLDelegate(self))

        # Layout
        edit_layout = QHBoxLayout()
        edit_layout.addWidget(self.edit)
        edit_layout.addWidget(self.help)
        layout = QVBoxLayout()
        layout.addLayout(edit_layout)
        layout.addWidget(self.list)
        self.setLayout(layout)

        # Signals
        self.rejected.connect(self.restore_initial_state)
        self.filter.sig_up_key_pressed.connect(self.previous_row)
        self.filter.sig_down_key_pressed.connect(self.next_row)
        self.edit.returnPressed.connect(self.accept)
        self.edit.textChanged.connect(self.setup)
        self.list.itemSelectionChanged.connect(self.item_selection_changed)
        self.list.clicked.connect(self.edit.setFocus)

    # --- Properties
    @property
    def widgets(self):
        widgets = []
        for tabs, plugin in self.plugins_tabs:
            widgets += [(tabs.widget(index), plugin) for
                        index in range(tabs.count())]
        return widgets

    @property
    def line_count(self):
        return [widget.get_line_count() for widget in self.widgets]

    @property
    def save_status(self):
        save_status = []
        for da, icon in self.plugins_data:
            save_status += [getattr(td, 'newly_created', False) for td in da]
        return save_status

    @property
    def paths(self):
        paths = []
        for da, icon in self.plugins_data:
            paths += [getattr(td, 'filename', None) for td in da]
        return paths

    @property
    def filenames(self):
        filenames = []
        for da, icon in self.plugins_data:
            filenames += [os.path.basename(getattr(td,
                                                   'filename',
                                                   None)) for td in da]
        return filenames

    @property
    def icons(self):
        icons = []
        for da, icon in self.plugins_data:
            icons += [icon for td in da]
        return icons

    @property
    def current_path(self):
        return self.paths_by_widget[self.get_widget()]

    @property
    def paths_by_widget(self):
        widgets = [w[0] for w in self.widgets]
        return dict(zip(widgets, self.paths))

    @property
    def widgets_by_path(self):
        widgets = [w[0] for w in self.widgets]
        return dict(zip(self.paths, widgets))

    @property
    def filter_text(self):
        """Get the normalized (lowecase) content of the filter text."""
        return to_text_string(self.edit.text()).lower()

    def set_search_text(self, _str):
        self.edit.setText(_str)

    def save_initial_state(self):
        """Save initial cursors and initial active widget."""
        paths = self.paths
        self.initial_widget = self.get_widget()
        self.initial_cursors = {}

        for i, editor in enumerate(self.widgets):
            if editor is self.initial_widget:
                self.initial_path = paths[i]
            # This try is needed to make the fileswitcher work with 
            # plugins that does not have a textCursor.
            try:
                self.initial_cursors[paths[i]] = editor.textCursor()
            except AttributeError:
                pass

    def accept(self):
        self.is_visible = False
        QDialog.accept(self)
        self.list.clear()

    def restore_initial_state(self):
        """Restores initial cursors and initial active editor."""
        self.list.clear()
        self.is_visible = False
        widgets = self.widgets_by_path

        if not self.edit.clicked_outside:
            for path in self.initial_cursors:
                cursor = self.initial_cursors[path]
                if path in widgets:
                    self.set_editor_cursor(widgets[path], cursor)

            if self.initial_widget in self.paths_by_widget:
                index = self.paths.index(self.initial_path)
                self.sig_goto_file.emit(index)

    def set_dialog_position(self):
        """Positions the file switcher dialog."""
        parent = self.parent()
        geo = parent.geometry()
        width = self.list.width()  # This has been set in setup
        left = parent.geometry().width()/2 - width/2
        # Note: the +1 pixel on the top makes it look better
        if isinstance(parent, QMainWindow):
            top = (parent.toolbars_menu.geometry().height() +
                   parent.menuBar().geometry().height() + 1)
        else:
            top = self.plugins_tabs[0][0].tabBar().geometry().height() + 1
        while parent:
            geo = parent.geometry()
            top += geo.top()
            left += geo.left()
            parent = parent.parent()

        self.move(left, top)

    def fix_size(self, content, extra=50):
        """
        Adjusts the width and height of the file switcher,
        based on its content.
        """
        # Update size of dialog based on longest shortened path
        strings = []
        if content:
            for rich_text in content:
                label = QLabel(rich_text)
                label.setTextFormat(Qt.PlainText)
                strings.append(label.text())
                fm = label.fontMetrics()

            # Max width
            max_width = max([fm.width(s) * 1.3 for s in strings])
            self.list.setMinimumWidth(max_width + extra)

            # Max height
            if len(strings) < 8:
                max_entries = len(strings)
            else:
                max_entries = 8
            max_height = fm.height() * max_entries * 2.5
            self.list.setMinimumHeight(max_height)

            # Set position according to size
            self.set_dialog_position()

    # --- Helper methods: List widget
    def count(self):
        """Gets the item count in the list widget."""
        return self.list.count()

    def current_row(self):
        """Returns the current selected row in the list widget."""
        return self.list.currentRow()

    def set_current_row(self, row):
        """Sets the current selected row in the list widget."""
        return self.list.setCurrentRow(row)

    def select_row(self, steps):
        """Select row in list widget based on a number of steps with direction.

        Steps can be positive (next rows) or negative (previous rows).
        """
        row = self.current_row() + steps
        if 0 <= row < self.count():
            self.set_current_row(row)

    def previous_row(self):
        """Select previous row in list widget."""
        self.select_row(-1)

    def next_row(self):
        """Select next row in list widget."""
        self.select_row(+1)

    def get_stack_index(self, stack_index, plugin_index):
        """Get the real index of the selected item."""
        other_plugins_count = sum([other_tabs[0].count() \
                                   for other_tabs in \
                                   self.plugins_tabs[:plugin_index]])
        real_index = stack_index - other_plugins_count

        return real_index

    # --- Helper methods: Widget
    def get_widget(self, index=None, path=None, tabs=None):
        """Get widget by index.
        
        If no tabs and index specified the current active widget is returned.
        """
        if index and tabs:
            return tabs.widget(index)
        elif path and tabs:
            return tabs.widget(index)
        elif self.plugin:
            index = self.plugins_instances.index(self.plugin)
            return self.plugins_tabs[index][0].currentWidget()
        else:
            return self.plugins_tabs[0][0].currentWidget()

    def set_editor_cursor(self, editor, cursor):
        """Set the cursor of an editor."""
        pos = cursor.position()
        anchor = cursor.anchor()

        new_cursor = QTextCursor()
        if pos == anchor:
            new_cursor.movePosition(pos)
        else:
            new_cursor.movePosition(anchor)
            new_cursor.movePosition(pos, QTextCursor.KeepAnchor)
        editor.setTextCursor(cursor)

    def goto_line(self, line_number):
        """Go to specified line number in current active editor."""
        if line_number:
            line_number = int(line_number)
            editor = self.get_widget()
            try:
                editor.go_to_line(min(line_number, editor.get_line_count()))
            except AttributeError:
                pass

    # --- Helper methods: Outline explorer
    def get_symbol_list(self):
        """Get the list of symbols present in the file."""
        try:
            oedata = self.get_widget().get_outlineexplorer_data()
        except AttributeError:
            oedata = {}
        return oedata

    # --- Handlers
    def item_selection_changed(self):
        """List widget item selection change handler."""
        row = self.current_row()
        if self.count() and row >= 0:
            if self.mode == self.FILE_MODE:
                try:
                    stack_index = self.paths.index(self.filtered_path[row])
                    self.plugin = self.widgets[stack_index][1]
                    plugin_index = self.plugins_instances.index(self.plugin)
                    # Count the real index in the tabWidget of the
                    # current plugin
                    real_index = self.get_stack_index(stack_index,
                                                      plugin_index)
                    self.sig_goto_file.emit(real_index,
                                            self.plugin.get_current_tab_manager())
                    self.goto_line(self.line_number)
                    try:
                        self.plugin.switch_to_plugin()
                        self.raise_()
                    except AttributeError:
                        # The widget using the fileswitcher is not a plugin
                        pass
                    self.edit.setFocus()
                except ValueError:
                    pass
            else:
                line_number = self.filtered_symbol_lines[row]
                self.goto_line(line_number)

    def setup_file_list(self, filter_text, current_path):
        """Setup list widget content for file list display."""
        short_paths = shorten_paths(self.paths, self.save_status)
        paths = self.paths
        icons = self.icons
        results = []
        trying_for_line_number = ':' in filter_text

        # Get optional line number
        if trying_for_line_number:
            filter_text, line_number = filter_text.split(':')
        else:
            line_number = None

        # Get all available filenames and get the scores for "fuzzy" matching
        scores = get_search_scores(filter_text, self.filenames,
                                   template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            if score_value != -1:
                text_item = '<big>' + rich_text.replace('&', '') + '</big>'
                if trying_for_line_number:
                    text_item += " [{0:} {1:}]".format(self.line_count[index],
                                                       _("lines"))
                text_item += u"<br><i>{0:}</i>".format(short_paths[index])
                results.append((score_value, index, text_item))

        # Sort the obtained scores and populate the list widget
        self.filtered_path = []
        plugin = None
        for result in sorted(results):
            index = result[1]
            path = paths[index]
            icon = icons[index]
            text = ''
            try:
                title = self.widgets[index][1].get_plugin_title().split(' - ')
                if plugin != title[0]:
                    plugin = title[0]
                    text += '<big><b>' + plugin + '</b></big><br>'
            except:
                # The widget using the fileswitcher is not a plugin
                pass
            text += result[-1]
            item = QListWidgetItem(ima.icon(icon), text)
            item.setToolTip(path)
            item.setSizeHint(QSize(0, 25))
            self.list.addItem(item)
            self.filtered_path.append(path)

        # To adjust the delegate layout for KDE themes
        self.list.files_list = True

        # Move selected item in list accordingly and update list size
        if current_path in self.filtered_path:
            self.set_current_row(self.filtered_path.index(current_path))
        elif self.filtered_path:
            self.set_current_row(0)
        self.fix_size(short_paths, extra=200)

        # If a line number is searched look for it
        self.line_number = line_number
        self.goto_line(line_number)

    def setup_symbol_list(self, filter_text, current_path):
        """Setup list widget content for symbol list display."""
        # Get optional symbol name
        filter_text, symbol_text = filter_text.split('@')

        # Fetch the Outline explorer data, get the icons and values
        oedata = self.get_symbol_list()
        icons = get_python_symbol_icons(oedata)

        symbol_list = process_python_symbol_data(oedata)
        line_fold_token = [(item[0], item[2], item[3]) for item in symbol_list]
        choices = [item[1] for item in symbol_list]
        scores = get_search_scores(symbol_text, choices, template="<b>{0}</b>")

        # Build the text that will appear on the list widget
        results = []
        lines = []
        self.filtered_symbol_lines = []
        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            line, fold_level, token = line_fold_token[index]
            lines.append(text)
            if score_value != -1:
                results.append((score_value, line, text, rich_text,
                                fold_level, icons[index], token))

        template = '{0}{1}'

        for (score, line, text, rich_text, fold_level, icon,
             token) in sorted(results):
            fold_space = '&nbsp;'*(fold_level)
            line_number = line + 1
            self.filtered_symbol_lines.append(line_number)
            textline = template.format(fold_space, rich_text)
            item = QListWidgetItem(icon, textline)
            item.setSizeHint(QSize(0, 16))
            self.list.addItem(item)

        # To adjust the delegate layout for KDE themes
        self.list.files_list = False

        # Move selected item in list accordingly
        # NOTE: Doing this is causing two problems:
        # 1. It makes the cursor to auto-jump to the last selected
        #    symbol after opening or closing a different file
        # 2. It moves the cursor to the first symbol by default,
        #    which is very distracting.
        # That's why this line is commented!
        # self.set_current_row(0)

        # Update list size
        self.fix_size(lines, extra=125)

    def setup(self):
        """Setup list widget content."""
        if len(self.plugins_tabs) == 0:
            self.close()
            return

        self.list.clear()
        current_path = self.current_path
        filter_text = self.filter_text
        self.set_dialog_position()

        # Get optional line or symbol to define mode and method handler
        trying_for_symbol = ('@' in self.filter_text)

        if trying_for_symbol:
            self.mode = self.SYMBOL_MODE
            self.setup_symbol_list(filter_text, current_path)
        else:
            self.mode = self.FILE_MODE
            self.setup_file_list(filter_text, current_path)

    def add_plugin(self, plugin, tabs, data, icon):
        """Add a plugin to display its files."""
        self.plugins_tabs.append((tabs, plugin))
        self.plugins_data.append((data, icon))
        self.plugins_instances.append(plugin)
