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

from spyder.py3compat import PY2
if PY2:
    from itertools import izip as zip

# Order is important:
EOL_CHARS = (("\r\n", 'nt'), ("\n", 'posix'), ("\r", 'mac'))

ALL_LANGUAGES = {
                 'Python': ('py', 'pyw', 'python', 'ipy'),
                 'Cython': ('pyx', 'pxi', 'pxd'),
                 'Enaml': ('enaml',),
                 'Fortran77': ('f', 'for', 'f77'),
                 'Fortran': ('f90', 'f95', 'f2k'),
                 'Idl': ('pro',),
                 'Diff': ('diff', 'patch', 'rej'),
                 'GetText': ('po', 'pot'),
                 'Nsis': ('nsi', 'nsh'),
                 'Html': ('htm', 'html'),
                 'Cpp': ('c', 'cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx'),
                 'OpenCL': ('cl',),
                 'Yaml':('yaml','yml'),
                 }

PYTHON_LIKE_LANGUAGES = ('Python', 'Cython', 'Enaml')

CELL_LANGUAGES = {'Python': ('#%%', '# %%', '# <codecell>', '# In[')}


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


def fix_indentation(text):
    """Replace tabs by spaces"""
    return text.replace('\t', ' '*4)

    
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
        
    Taken from http://stackoverflow.com/q/21498939/438386
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
     
    Taken from http://stackoverflow.com/q/21498939/438386
    """
    longest_prefix = []
    for (elmt0, elmt1) in zip(path_components0, path_components1):
        if elmt0 != elmt1:
            break
        longest_prefix.append(elmt0)
    file_name_length = len(path_components0[len(path_components0) - 1])
    path_0 = os.path.join(*path_components0)[:-file_name_length - 1]
    if(len(longest_prefix) > 2):
        longest_path_prefix = os.path.join(*longest_prefix)
        length_to_delete = len(longest_path_prefix) + 1 
        return path_0[length_to_delete:]
    else:
        return path_0
