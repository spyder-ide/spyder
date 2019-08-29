# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Source code text utilities
"""

import re
import os
import os.path as osp
import sys

# Third party imports
from qtpy.QtGui import QIcon

# Local imports
from spyder.config.base import _
from spyder.config.utils import is_ubuntu
from spyder.py3compat import iteritems, PY2
from spyder.utils import icon_manager as ima

if PY2:
    from itertools import izip as zip

# Order is important:
EOL_CHARS = (("\r\n", 'nt'), ("\n", 'posix'), ("\r", 'mac'))


def get_eol_chars(text):
    """Get text EOL characters"""
    for eol_chars, _os_name in EOL_CHARS:
        if text.find(eol_chars) > -1:
            return eol_chars


def get_os_name_from_eol_chars(eol_chars):
    """Return OS name from EOL characters"""
    for chars, os_name in EOL_CHARS:
        if eol_chars == chars:
            return os_name


def get_eol_chars_from_os_name(os_name):
    """Return EOL characters from OS name"""
    for eol_chars, name in EOL_CHARS:
        if name == os_name:
            return eol_chars


def has_mixed_eol_chars(text):
    """Detect if text has mixed EOL characters"""
    eol_chars = get_eol_chars(text)
    if eol_chars is None:
        return False
    correct_text = eol_chars.join((text+eol_chars).splitlines())
    return repr(correct_text) != repr(text)


def normalize_eols(text, eol='\n'):
    """Use the same eol's in text"""
    for eol_char, _ in EOL_CHARS:
        if eol_char != eol:
            text = text.replace(eol_char, eol)
    return text


def fix_indentation(text, indent_chars):
    """Replace tabs by spaces"""
    return text.replace('\t', indent_chars)


def is_builtin(text):
    """Test if passed string is the name of a Python builtin object"""
    from spyder.py3compat import builtins
    return text in [str(name) for name in dir(builtins)
                    if not name.startswith('_')]


def is_keyword(text):
    """Test if passed string is the name of a Python keyword"""
    import keyword
    return text in keyword.kwlist


def get_primary_at(source_code, offset, retry=True):
    """Return Python object in *source_code* at *offset*
    Periods to the left of the cursor are carried forward
      e.g. 'functools.par^tial' would yield 'functools.partial'
    Retry prevents infinite recursion: retry only once
    """
    obj = ''
    left = re.split(r"[^0-9a-zA-Z_.]", source_code[:offset])
    if left and left[-1]:
        obj = left[-1]
    right = re.split(r"\W", source_code[offset:])
    if right and right[0]:
        obj += right[0]
    if obj and obj[0].isdigit():
        obj = ''
    # account for opening chars with no text to the right
    if not obj and retry and offset and source_code[offset - 1] in '([.':
        return get_primary_at(source_code, offset - 1, retry=False)
    return obj


def split_source(source_code):
    '''Split source code into lines
    '''
    eol_chars = get_eol_chars(source_code)
    if eol_chars:
        return source_code.split(eol_chars)
    else:
        return [source_code]


def get_identifiers(source_code):
    '''Split source code into python identifier-like tokens'''
    tokens = set(re.split(r"[^0-9a-zA-Z_.]", source_code))
    valid = re.compile(r'[a-zA-Z_]')
    return [token for token in tokens if re.match(valid, token)]

def path_components(path):
    """
    Return the individual components of a given file path
    string (for the local operating system).

    Taken from https://stackoverflow.com/q/21498939/438386
    """
    components = []
    # The loop guarantees that the returned components can be
    # os.path.joined with the path separator and point to the same
    # location:
    while True:
        (new_path, tail) = os.path.split(path)  # Works on any platform
        components.append(tail)
        if new_path == path:  # Root (including drive, on Windows) reached
            break
        path = new_path
    components.append(new_path)
    components.reverse()  # First component first
    return components

def differentiate_prefix(path_components0, path_components1):
    """
    Return the differentiated prefix of the given two iterables.

    Taken from https://stackoverflow.com/q/21498939/438386
    """
    longest_prefix = []
    root_comparison = False
    common_elmt = None
    for index, (elmt0, elmt1) in enumerate(zip(path_components0, path_components1)):
        if elmt0 != elmt1:
            if index == 2:
                root_comparison = True
            break
        else:
            common_elmt = elmt0
        longest_prefix.append(elmt0)
    file_name_length = len(path_components0[len(path_components0) - 1])
    path_0 = os.path.join(*path_components0)[:-file_name_length - 1]
    if len(longest_prefix) > 0:
        longest_path_prefix = os.path.join(*longest_prefix)
        longest_prefix_length = len(longest_path_prefix) + 1
        if path_0[longest_prefix_length:] != '' and not root_comparison:
            path_0_components = path_components(path_0[longest_prefix_length:])
            if path_0_components[0] == ''and path_0_components[1] == ''and len(
                                        path_0[longest_prefix_length:]) > 20:
                path_0_components.insert(2, common_elmt)
                path_0 = os.path.join(*path_0_components)
            else:
                path_0 = path_0[longest_prefix_length:]
        elif not root_comparison:
            path_0 = common_elmt
        elif sys.platform.startswith('linux') and path_0 == '':
            path_0 = '/'
    return path_0

def disambiguate_fname(files_path_list, filename):
    """Get tab title without ambiguation."""
    fname = os.path.basename(filename)
    same_name_files = get_same_name_files(files_path_list, fname)
    if len(same_name_files) > 1:
        compare_path = shortest_path(same_name_files)
        if compare_path == filename:
            same_name_files.remove(path_components(filename))
            compare_path = shortest_path(same_name_files)
        diff_path = differentiate_prefix(path_components(filename),
                                             path_components(compare_path))
        diff_path_length = len(diff_path)
        path_component = path_components(diff_path)
        if (diff_path_length > 20 and len(path_component) > 2):
            if path_component[0] != '/' and path_component[0] != '':
                path_component = [path_component[0], '...',
                                          path_component[-1]]
            else:
                path_component = [path_component[2], '...',
                                          path_component[-1]]
            diff_path = os.path.join(*path_component)
        fname = fname + " - " + diff_path
    return fname

def get_same_name_files(files_path_list, filename):
    """Get a list of the path components of the files with the same name."""
    same_name_files = []
    for fname in files_path_list:
        if filename == os.path.basename(fname):
            same_name_files.append(path_components(fname))
    return same_name_files

def shortest_path(files_path_list):
    """Shortest path between files in the list."""
    if len(files_path_list) > 0:
        shortest_path = files_path_list[0]
        shortest_path_length = len(files_path_list[0])
        for path_elmts in files_path_list:
            if len(path_elmts) < shortest_path_length:
                shortest_path_length = len(path_elmts)
                shortest_path = path_elmts
        return os.path.join(*shortest_path)


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
                oedata.def_name, oedata.fold_level,
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
