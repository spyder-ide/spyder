# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Editor Switcher manager.
"""

# Standard library imports
import os
import os.path as osp
import sys


from qtpy.QtGui import QIcon

# Local imports
from spyder.config.base import _
from spyder.py3compat import iteritems, PY2
from spyder.utils import icon_manager as ima

if PY2:
    from itertools import izip as zip


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
    common_prefix = osp.dirname(osp.commonprefix(path_list))

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

    if common_prefix:
        result_paths = ["...{}".format(
                        path.rstrip(os.sep).split(common_prefix)[-1])
                        for path in new_path_list]
    else:
        result_paths = [path.rstrip(os.sep) for path in new_path_list]

    return result_paths


def get_file_icon(path):
    """Get icon for file by extension."""

    if sys.platform == 'darwin':
        scale_factor = 0.9
    elif os.name == 'nt':
        scale_factor = 0.8
    else:
        scale_factor = 0.7

    return ima.get_icon_by_extension_or_type(path, scale_factor)


def get_symbol_list(outlineexplorer_data_list):
    """
    Get the list of symbols present in the outline explorer data list.

    Returns a list with line number, definition name, fold and token.
    """
    symbol_list = []
    for oedata in outlineexplorer_data_list:
        if oedata.is_class_or_function():
            symbol_list.append((
                oedata.block.firstLineNumber(),
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

    def __init__(self, switcher_instance, get_codeeditor, get_editorstack,
                 section=_("Editor")):
        """
        'get_codeeditor' and 'get_editorstack' params should be callables
        to get the current CodeEditor or EditorStack instance as needed.
        As an example:
            current_codeeditor = get_codeditor()
            current_editorstack = get_editorstack()
        """
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
