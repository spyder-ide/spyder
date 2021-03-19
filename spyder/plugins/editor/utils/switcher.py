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

# Local imports
from spyder.config.base import _
from spyder.config.manager import CONF
from spyder.utils.icon_manager import ima
from spyder.utils.switcher import shorten_paths, get_file_icon
from spyder.plugins.completion.api import SymbolKind, SYMBOL_KIND_ICON


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
        line_template_title = u"{title} [{lines} {text}]"
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
        language = editor.language
        editor.update_whitespace_count(0, 0)
        self._current_line = editor.get_cursor_line_number()
        self._switcher.clear()
        self._switcher.set_placeholder_text(_('Select symbol'))
        oe_symbols = editor.oe_proxy.info or []
        display_variables = CONF.get('outline_explorer', 'display_variables')

        idx = 0
        total_symbols = len(oe_symbols)
        oe_symbols = sorted(
            oe_symbols, key=lambda x: x['location']['range']['start']['line'])
        for symbol in oe_symbols:
            symbol_name = symbol['name']
            symbol_kind = symbol['kind']
            if language.lower() == 'python':
                if symbol_kind == SymbolKind.MODULE:
                    total_symbols -= 1
                    continue
                if (symbol_kind == SymbolKind.VARIABLE and
                        not display_variables):
                    total_symbols -= 1
                    continue
                if symbol_kind == SymbolKind.FIELD and not display_variables:
                    total_symbols -= 1
                    continue

            symbol_range = symbol['location']['range']
            symbol_start = symbol_range['start']['line']

            fold_level = editor.leading_whitespaces[symbol_start]

            space = ' ' * fold_level
            formated_title = '{space}{title}'.format(title=symbol_name,
                                                     space=space)
            icon = ima.icon(SYMBOL_KIND_ICON.get(symbol_kind, 'no_match'))
            data = {'title': symbol_name,
                    'line_number': symbol_start + 1}
            last_item = idx + 1 == total_symbols
            self._switcher.add_item(title=formated_title,
                                    icon=icon,
                                    section=self._section,
                                    data=data,
                                    last_item=last_item)
            idx += 1
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
