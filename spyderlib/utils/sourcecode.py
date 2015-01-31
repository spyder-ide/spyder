# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Source code text utilities
"""
import re

# Order is important:
EOL_CHARS = (("\r\n", 'nt'), ("\n", 'posix'), ("\r", 'mac'))

ALL_LANGUAGES = {
                 'Python': ('py', 'pyw', 'python', 'ipy'),
                 'Cython': ('pyx', 'pxi', 'pxd'),
                 'Enaml': ('enaml',),
                 'Fortran77': ('f', 'for', 'f77'),
                 'Fortran': ('f90', 'f95', 'f2k'),
                 'Idl': ('pro',),
                 'Matlab': ('m',),
                 'Julia': ('jl',),
                 'Diff': ('diff', 'patch', 'rej'),
                 'GetText': ('po', 'pot'),
                 'Nsis': ('nsi', 'nsh'),
                 'Html': ('htm', 'html'),
                 'Css': ('css',),
                 'Xml': ('xml',),
                 'Js': ('js',),
                 'Json': ('json', 'ipynb'),
                 'Cpp': ('c', 'cc', 'cpp', 'cxx', 'h', 'hh', 'hpp', 'hxx'),
                 'OpenCL': ('cl',),
                 'Batch': ('bat', 'cmd', 'nt'),
                 'Ini': ('properties', 'session', 'ini', 'inf', 'reg', 'url',
                         'cfg', 'cnf', 'aut', 'iss'),
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
    from spyderlib.py3compat import builtins
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


if __name__ == '__main__':
    code = 'import functools\nfunctools.partial'
    assert get_primary_at(code, len(code)) == 'functools.partial'
    assert get_identifiers(code) == ['import', 'functools', 
                                     'functools.partial']
    assert split_source(code) == ['import functools', 'functools.partial']
    code = code.replace('\n', '\r\n')
    assert split_source(code) == ['import functools', 'functools.partial']
