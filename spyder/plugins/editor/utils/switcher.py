# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor Switcher manager.
"""

# Standard library imports
import os.path as osp

# Third party imports
from qtpy.QtGui import QIcon

# Local imports
from spyder.config.base import _
from spyder.utils import icon_manager as ima
from spyder.utils.switcher import shorten_paths, get_file_icon


def get_symbol_list(outlineexplorer_data_list):
    """
    Get the list of symbols present in the outline explorer data list.

    Returns a list with line number, definition name, fold and token.
    """
    symbol_list = []
    for oedata in outlineexplorer_data_list:
        if oedata.is_class_or_function():
            line_number = oedata.get_block_number()
            if line_number is not None:
                symbol_list.append((
                    line_number + 1,
                    oedata.def_name,
                    oedata.fold_level,
                    oedata.get_token()))
    return sorted(symbol_list)


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


class EditorSwitcherManager(object):
    """
    Switcher instance manager to handle base modes for an Editor.

    Symbol mode -> '@'
    Line mode -> ':'
    Files mode -> ''
    """

    SYMBOL_MODE = '@'
    LINE_MODE = ':'
    FILES_MODE = ''

    def __init__(self, plugin, switcher_instance, get_codeeditor,
                 get_editorstack, section=_("Editor")):
        """
        'get_codeeditor' and 'get_editorstack' params should be callables
        to get the current CodeEditor or EditorStack instance as needed.
        As an example:
            current_codeeditor = get_codeditor()
            current_editorstack = get_editorstack()
        """
        self._plugin = plugin
        self._switcher = switcher_instance
        self._editor = get_codeeditor
        self._editorstack = get_editorstack
        self._section = section
        self._current_line = None

        self.setup_switcher()

    def setup_switcher(self):
        """Setup switcher modes and signals."""
        self._switcher.add_mode(self.LINE_MODE, _('Go to Line'))
        self._switcher.add_mode(self.SYMBOL_MODE, _('Go to Symbol in File'))
        self._switcher.sig_mode_selected.connect(self.handle_switcher_modes)
        self._switcher.sig_item_selected.connect(
            self.handle_switcher_selection)
        self._switcher.sig_text_changed.connect(self.handle_switcher_text)
        self._switcher.sig_rejected.connect(self.handle_switcher_rejection)
        self._switcher.sig_item_changed.connect(
            self.handle_switcher_item_change)

    def handle_switcher_modes(self, mode):
        """Handle switcher for registered modes."""
        if mode == self.SYMBOL_MODE:
            self.create_symbol_switcher()
        elif mode == self.LINE_MODE:
            self.create_line_switcher()
        elif mode == self.FILES_MODE:
            # Each plugin that wants to attach to the switcher should do this?
            self.create_editor_switcher()

    def create_editor_switcher(self):
        """Populate switcher with open files."""
        self._switcher.set_placeholder_text(
            _('Start typing the name of an open file'))

        editorstack = self._editorstack()
        paths = [data.filename.lower()
                 for data in editorstack.data]
        save_statuses = [data.newly_created
                         for data in editorstack.data]
        short_paths = shorten_paths(paths, save_statuses)

        for idx, data in enumerate(editorstack.data):
            path = data.filename
            title = osp.basename(path)
            icon = get_file_icon(path)
            # TODO: Handle of shorten paths based on font size
            # and available space per item
            if len(paths[idx]) > 75:
                path = short_paths[idx]
            else:
                path = osp.dirname(data.filename.lower())
            last_item = idx + 1 == len(editorstack.data)
            self._switcher.add_item(title=title,
                                    description=path,
                                    icon=icon,
                                    section=self._section,
                                    data=data,
                                    last_item=last_item)

    def create_line_switcher(self):
        """Populate switcher with line info."""
        editor = self._editor()
        editorstack = self._editorstack()
        self._current_line = editor.get_cursor_line_number()
        self._switcher.clear()
        self._switcher.set_placeholder_text(_('Select line'))
        data = editorstack.get_current_finfo()
        path = data.filename
        title = osp.basename(path)
        lines = data.editor.get_line_count()
        icon = get_file_icon(path)
        line_template_title = "{title} [{lines} {text}]"
        title = line_template_title.format(title=title, lines=lines,
                                           text=_("lines"))
        description = _('Go to line')
        self._switcher.add_item(title=title,
                                description=description,
                                icon=icon,
                                section=self._section,
                                data=data,
                                action_item=True)

    def create_symbol_switcher(self):
        """Populate switcher with symbol info."""
        editor = self._editor()
        self._current_line = editor.get_cursor_line_number()
        self._switcher.clear()
        self._switcher.set_placeholder_text(_('Select symbol'))
        oedata_list = editor.outlineexplorer_data_list()

        symbols_list = get_symbol_list(oedata_list)
        icons = get_python_symbol_icons(symbols_list)
        for idx, symbol in enumerate(symbols_list):
            title = symbol[1]
            fold_level = symbol[2]
            space = ' ' * fold_level
            formated_title = '{space}{title}'.format(title=title,
                                                     space=space)
            line_number = symbol[0]
            icon = icons[idx]
            data = {'title': title,
                    'line_number': line_number + 1}
            last_item = idx + 1 == len(symbols_list)
            self._switcher.add_item(title=formated_title,
                                    icon=icon,
                                    section=self._section,
                                    data=data,
                                    last_item=last_item)
        # Needed to update fold spaces for items titles
        self._switcher.setup()

    def handle_switcher_selection(self, item, mode, search_text):
        """Handle item selection of the switcher."""
        data = item.get_data()
        if mode == '@':
            self.symbol_switcher_handler(data)
        elif mode == ':':
            self.line_switcher_handler(data, search_text)
        elif mode == '':
            # Each plugin that wants to attach to the switcher should do this?
            if item.get_section() == self._section:
                self.editor_switcher_handler(data)
                self._plugin.switch_to_plugin()

    def handle_switcher_text(self, search_text):
        """Handle switcher search text for line mode."""
        editorstack = self._editorstack()
        mode = self._switcher.get_mode()
        if mode == ':':
            item = self._switcher.current_item()
            self.line_switcher_handler(item.get_data(), search_text,
                                       visible=True)
        elif self._current_line and mode == '':
            editorstack.go_to_line(self._current_line)
            self._current_line = None

    def handle_switcher_rejection(self):
        """Do actions when the Switcher is rejected."""
        # Reset current cursor line
        if self._current_line:
            editorstack = self._editorstack()
            editorstack.go_to_line(self._current_line)
            self._current_line = None

    def handle_switcher_item_change(self, current):
        """Handle item selection change."""
        editorstack = self._editorstack()
        mode = self._switcher.get_mode()
        if mode == '@' and current is not None:
            line_number = int(current.get_data()['line_number'])
            editorstack.go_to_line(line_number)

    def editor_switcher_handler(self, data):
        """Populate switcher with FileInfo data."""
        editorstack = self._editorstack()
        editorstack.set_current_filename(data.filename)
        self._switcher.hide()

    def line_switcher_handler(self, data, search_text, visible=False):
        """Handle line switcher selection."""
        editorstack = self._editorstack()
        editorstack.set_current_filename(data.filename)
        line_number = search_text.split(':')[-1]
        try:
            line_number = int(line_number)
            editorstack.go_to_line(line_number)
            self._switcher.setVisible(visible)
            # Closing the switcher
            if not visible:
                self._current_line = None
                self._switcher.set_search_text('')
        except Exception:
            # Invalid line number
            pass

    def symbol_switcher_handler(self, data):
        """Handle symbol switcher selection."""
        editorstack = self._editorstack()
        line_number = data['line_number']
        editorstack.go_to_line(int(line_number))
        self._current_line = None
        self._switcher.hide()
        self._switcher.set_search_text('')
