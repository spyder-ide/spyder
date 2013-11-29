# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Source code text utilities
"""


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
    
    
def is_binary(path):
    """
    Test if the given path is a binary file.
    
    Adapted from: http://stackoverflow.com/a/3002505
    
    Original Authors: Trent Mick <TrentM@ActiveState.com>
                      Jorge Orpinel <jorge@orpinel.com>
    """
    with open(path, 'rb') as fid:
        try:
            CHUNKSIZE = 1024
            while 1:
                chunk = fid.read(CHUNKSIZE).decode('utf-8')
                if '\0' in chunk: # found null byte
                    return True
                if len(chunk) < CHUNKSIZE:
                    break # done
        except UnicodeDecodeError:
            return True
        except Exception:
            pass
    return False
