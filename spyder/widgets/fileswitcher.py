# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from __future__ import print_function
import os
import os.path as osp
import sys

# Third party imports
from qtpy.QtCore import (Signal, Slot, QEvent, QFileInfo, QObject, QRegExp,
                         QSize, Qt)
from qtpy.QtGui import (QIcon, QRegExpValidator, QTextCursor)
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QLabel, QLineEdit,
                            QListWidget, QListWidgetItem, QVBoxLayout,
                            QMainWindow)

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, to_text_string
from spyder.config.utils import is_ubuntu
from spyder.utils import icon_manager as ima
from spyder.utils.stringmatching import get_search_scores
from spyder.widgets.helperwidgets import HelperToolButton, HTMLDelegate
from spyder.config.main import CONF


# --- Python Outline explorer helpers


def get_python_symbol_icons(symbols):
    """Return a list of icons for symbols of a python file."""
    class_icon = ima.icon('class')
    method_icon = ima.icon('method')
    function_icon = ima.icon('function')
    private_icon = ima.icon('private1')
    super_private_icon = ima.icon('private2')

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
    sig_enter_key_pressed = Signal()

    def eventFilter(self, src, e):
        if e.type() == QEvent.KeyPress:
            if e.key() == Qt.Key_Up:
                self.sig_up_key_pressed.emit()
            elif e.key() == Qt.Key_Down:
                self.sig_down_key_pressed.emit()
            elif (e.key() == Qt.Key_Return):
                self.sig_enter_key_pressed.emit()
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
    path_text_font_size = CONF.get('appearance', 'rich_font/size')
    if sys.platform == 'darwin':
        text_diff = 2
    else:
        text_diff = 1
    filename_text_font_size = path_text_font_size + text_diff
    FILE_MODE, SYMBOL_MODE = [1, 2]
    MAX_WIDTH = 600
    PATH_FG_COLOR = 'rgb(153, 153, 153)'
    SECTION_COLOR = 'rgb(70, 179, 239)'
    _FONT_SIZE = CONF.get('appearance', 'rich_font/size')
    _HEIGHT = 20
    _PADDING = 0
    _MIN_WIDTH = 500
    _STYLES = {
        'title_color': ima.MAIN_FG_COLOR,
        'description_color': 'rgb(153, 153, 153)',
        'section_color': SECTION_COLOR,
        'shortcut_color': 'rgb(153, 153, 153)',
        'title_font_size': filename_text_font_size,
        'description_font_size': path_text_font_size,
        'section_font_size': path_text_font_size,
        'shortcut_font_size': path_text_font_size,
    }
    _TEMPLATE = '''<table width="{width}" height="{height}"
                          cellpadding="{padding}">
  <tr>
    <td valign="middle">
      <span style="color:{title_color};font-size:{title_font_size}pt">
        {title}
      </span>&nbsp;
      <span
       style="color:{description_color};font-size:{description_font_size}pt">
        {description}
      </span>
    </td>
    <td valign="middle" align="right" float="right">
      <span style="color:{shortcut_color};font-size:{shortcut_font_size}pt">
         <span><code><i>{shortcut}</i></code></span>
      </span>&nbsp;
      <span style="color:{section_color};font-size:{section_font_size}pt">
         {section}
      </span>
    </td>
  </tr>
</table>'''
    _SEPARATOR = '_'
    _HEIGHT_SEP = 0
    _STYLES_SEP = {
        'color': 'black',
        'font_size': CONF.get('appearance', 'rich_font/size', 10),
    }
    _TEMPLATE_SEP = \
        '''<table cellpadding="0" cellspacing="0" width="{width}"
                  height="{height}" border="0">
  <tr><td valign="top" align="center"></td></tr>
</table>'''

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
        self.edit.setPlaceholderText(_("Start typing the name of an open file "
                                       "or console to switch to it"))
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
        self.filter.sig_enter_key_pressed.connect(self.enter)
        self.list.itemClicked.connect(self.enter)
        self.edit.returnPressed.connect(self.accept)
        self.edit.textChanged.connect(self.setup)
        self.list.itemSelectionChanged.connect(self.item_selection_changed)
        self.list.clicked.connect(self.edit.setFocus)

    # --- Properties
    @property
    def widgets(self):
        widgets = []
        for plugin in self.plugins_instances:
            tabs = self.get_plugin_tabwidget(plugin)
            widgets += [(tabs.widget(index), plugin) for
                        index in range(tabs.count())]
        return widgets

    @property
    def line_count(self):
        line_count = []
        for widget in self.widgets:
            try:
                current_line_count = widget[0].get_line_count()
            except AttributeError:
                current_line_count = 0
            line_count.append(current_line_count)
        return line_count

    @property
    def save_status(self):
        save_status = []
        for da, icon in self.plugins_data:
            save_status += [getattr(td, 'newly_created', False) for td in da]
        return save_status

    @property
    def paths(self):
        paths = []
        for plugin in self.plugins_instances:
            da = self.get_plugin_data(plugin)
            paths += [getattr(td, 'filename', None) for td in da]
        return paths

    @property
    def filenames(self):
        filenames = []
        for plugin in self.plugins_instances:
            da = self.get_plugin_data(plugin)
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
        return self.paths_by_widget.get(self.get_widget(), None)

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

    def get_item_size(self, content):
        """
        Get the max size (width and height) for the elements of a list of
        strings as a QLabel.
        """
        strings = []
        if content:
            for rich_text in content:
                label = QLabel(rich_text)
                label.setTextFormat(Qt.PlainText)
                strings.append(label.text())
                fm = label.fontMetrics()

            return (max([fm.width(s) * 1.3 for s in strings]), fm.height())

    def fix_size(self, content):
        """
        Adjusts the width and height of the file switcher
        based on the relative size of the parent and content.
        """
        # Update size of dialog based on relative size of the parent
        if content:
            width, height = self.get_item_size(content)

            # Width
            parent = self.parent()
            relative_width = parent.geometry().width() * 0.65
            if relative_width > self.MAX_WIDTH:
                relative_width = self.MAX_WIDTH
            self.list.setMinimumWidth(relative_width)

            # Height
            if len(content) < 15:
                max_entries = len(content)
            else:
                max_entries = 15
            max_height = height * max_entries * 1.7
            self.list.setMinimumHeight(max_height)

            # Resize
            self.list.resize(relative_width, self.list.height())

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
        if self.mode == self.SYMBOL_MODE:
            self.select_row(-1)
            return
        prev_row = self.current_row() - 1
        if prev_row >= 0:
            title = self.list.item(prev_row).text()
        else:
            title = ''
        if prev_row == 0 and '</b></big><br>' in title:
            self.list.scrollToTop()
        elif '</b></big><br>' in title:
            # Select the next previous row, the one following is a title
            self.select_row(-2)
        else:
            self.select_row(-1)

    def next_row(self):
        """Select next row in list widget."""
        if self.mode == self.SYMBOL_MODE:
            self.select_row(+1)
            return
        next_row = self.current_row() + 1
        if next_row < self.count():
            if '</b></big><br>' in self.list.item(next_row).text():
                # Select the next next row, the one following is a title
                self.select_row(+2)
            else:
                self.select_row(+1)

    def get_stack_index(self, stack_index, plugin_index):
        """Get the real index of the selected item."""
        other_plugins_count = sum([other_tabs[0].count() \
                                   for other_tabs in \
                                   self.plugins_tabs[:plugin_index]])
        real_index = stack_index - other_plugins_count

        return real_index

    # --- Helper methods: Widget
    def get_plugin_data(self, plugin):
        """Get the data object of the plugin's current tab manager."""
        # The data object is named "data" in the editor plugin while it is
        # named "clients" in the notebook plugin.
        try:
            data = plugin.get_current_tab_manager().data
        except AttributeError:
            data = plugin.get_current_tab_manager().clients

        return data

    def get_plugin_tabwidget(self, plugin):
        """Get the tabwidget of the plugin's current tab manager."""
        # The tab widget is named "tabs" in the editor plugin while it is
        # named "tabwidget" in the notebook plugin.
        try:
            tabwidget = plugin.get_current_tab_manager().tabs
        except AttributeError:
            tabwidget = plugin.get_current_tab_manager().tabwidget

        return tabwidget

    def get_widget(self, index=None, path=None, tabs=None):
        """Get widget by index.

        If no tabs and index specified the current active widget is returned.
        """
        if (index and tabs) or (path and tabs):
            return tabs.widget(index)
        elif self.plugin:
            return self.get_plugin_tabwidget(self.plugin).currentWidget()
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
            try:
                self.plugin.go_to_line(line_number)
            except AttributeError:
                pass

    # --- Helper methods: Outline explorer
    def get_symbol_list(self):
        """
        Get the list of symbols present in the file.

        Returns a list with line number, definition name, fold and token.
        """
        symbol_list = []
        for oedata in self.get_widget().outlineexplorer_data_list():
            if oedata.is_class_or_function():
                symbol_list.append((
                    oedata.block.firstLineNumber(),
                    oedata.def_name, oedata.fold_level,
                    oedata.get_token()))
        return sorted(symbol_list)

    # --- Handlers
    def item_selection_changed(self):
        """List widget item selection change handler."""
        row = self.current_row()
        if self.count() and row >= 0:
            if '</b></big><br>' in self.list.currentItem().text() and row == 0:
                self.next_row()
            if self.mode == self.FILE_MODE:
                try:
                    stack_index = self.paths.index(self.filtered_path[row])
                    self.plugin = self.widgets[stack_index][1]
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

    @Slot()
    @Slot(QListWidgetItem)
    def enter(self, itemClicked=None):
        if self.mode == self.FILE_MODE:
            row = self.current_row()
            stack_index = self.paths.index(self.filtered_path[row])
            self.plugin = self.widgets[stack_index][1]
            plugin_index = self.plugins_instances.index(self.plugin)
            # Count the real index in the tabWidget of the
            # current plugin
            real_index = self.get_stack_index(stack_index,
                                              plugin_index)
            self.sig_goto_file.emit(real_index,
                                    self.plugin.get_current_tab_manager())
            self.accept()

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
            if line_number == '':
                line_number = None
            # Get all the available filenames
            scores = get_search_scores('', self.filenames,
                                       template="<b>{0}</b>")
        else:
            line_number = None
            # Get all available filenames and get the scores for
            # "fuzzy" matching
            scores = get_search_scores(filter_text, self.filenames,
                                       template="<b>{0}</b>")

        # Get max width to determine if shortpaths should be used
        max_width = self.get_item_size(paths)[0]
        self.fix_size(paths)

        # Build the text that will appear on the list widget
        rich_font = CONF.get('appearance', 'rich_font/size', 10)
        if sys.platform == 'darwin':
            path_text_font_size = rich_font
            filename_text_font_size = path_text_font_size + 2
        elif os.name == 'nt':
            path_text_font_size = rich_font
            filename_text_font_size = path_text_font_size + 1
        elif is_ubuntu():
            path_text_font_size = rich_font - 2
            filename_text_font_size = path_text_font_size + 1
        else:
            path_text_font_size = rich_font
            filename_text_font_size = path_text_font_size + 1

        for index, score in enumerate(scores):
            text, rich_text, score_value = score
            linecount = ""
            if score_value != -1:
                fileName = rich_text.replace('&', '')
                if trying_for_line_number:
                    linecount = "[{0:} {1:}]".format(self.line_count[index],
                                                     _("lines"))
                if max_width > self.list.width():
                    path = short_paths[index]
                else:
                    path = paths[index]

                title = self.widgets[index][1].get_plugin_title().split(
                    ' - ')[0]

                text_item = self._TEMPLATE.format(
                    width=self._MIN_WIDTH, height=self._HEIGHT, title=fileName,
                    section=title, description=path, padding=self._PADDING,
                    shortcut=linecount, **self._STYLES)

                if ((trying_for_line_number and self.line_count[index] != 0)
                        or not trying_for_line_number):
                    results.append((score_value, index, text_item))

        # Sort the obtained scores and populate the list widget
        self.filtered_path = []
        plugin = None
        separator = self._TEMPLATE_SEP.format(
            width=self.list.width()-20, height=self._HEIGHT_SEP,
            **self._STYLES_SEP)
        for result in sorted(results):
            index = result[1]
            path = paths[index]
            if sys.platform == 'darwin':
                scale_factor = 0.9
            elif os.name == 'nt':
                scale_factor = 0.8
            elif is_ubuntu():
                scale_factor = 0.7
            else:
                scale_factor = 0.9
            icon = ima.get_icon_by_extension_or_type(path, scale_factor)
            text = ''
            try:
                title = self.widgets[index][1].get_plugin_title().split(' - ')
                if plugin != title[0]:
                    plugin = title[0]
                    text = separator
                    item = QListWidgetItem(text)
                    item.setToolTip(path)
                    item.setSizeHint(QSize(0, 25))
                    item.setFlags(Qt.ItemIsEditable)
                    self.list.addItem(item)
                    self.filtered_path.append(path)
            except:
                # The widget using the fileswitcher is not a plugin
                pass
            text = ''
            text += result[-1]
            item = QListWidgetItem(icon, text)
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

        # If a line number is searched look for it
        self.line_number = line_number
        self.goto_line(line_number)

    def setup_symbol_list(self, filter_text, current_path):
        """Setup list widget content for symbol list display."""
        # Get optional symbol name
        filter_text, symbol_text = filter_text.split('@')

        # Fetch the Outline explorer data, get the icons and values
        symbol_list = self.get_symbol_list()
        icons = get_python_symbol_icons(symbol_list)

        # The list of paths here is needed in order to have the same
        # point of measurement for the list widget size as in the file list
        # See issue 4648
        paths = self.paths
        # Update list size
        self.fix_size(paths)

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

        template = '{{0}}<span style="color:{0}">{{1}}</span>'.format(
                ima.MAIN_FG_COLOR)

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

        # Select edit line when using symbol search initially.
        # See issue 5661
        self.edit.setFocus()

        # Move selected item in list accordingly
        # NOTE: Doing this is causing two problems:
        # 1. It makes the cursor to auto-jump to the last selected
        #    symbol after opening or closing a different file
        # 2. It moves the cursor to the first symbol by default,
        #    which is very distracting.
        # That's why this line is commented!
        # self.set_current_row(0)

    def setup(self):
        """Setup list widget content."""
        if len(self.plugins_tabs) == 0:
            self.close()
            return

        self.list.clear()
        current_path = self.current_path
        filter_text = self.filter_text

        # Get optional line or symbol to define mode and method handler
        trying_for_symbol = ('@' in self.filter_text)

        if trying_for_symbol:
            self.mode = self.SYMBOL_MODE
            self.setup_symbol_list(filter_text, current_path)
        else:
            self.mode = self.FILE_MODE
            self.setup_file_list(filter_text, current_path)

        # Set position according to size
        self.set_dialog_position()

    def show(self):
        """
        Override Qt method to force an update of the fileswitcher before
        showing it. See Issue #5317 and PR #5389.
        """
        self.setup()
        super(FileSwitcher, self).show()

    def add_plugin(self, plugin, tabs, data, icon):
        """Add a plugin to display its files."""
        self.plugins_tabs.append((tabs, plugin))
        self.plugins_data.append((data, icon))
        self.plugins_instances.append(plugin)
