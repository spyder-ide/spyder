# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Utilities needed by the fallback completion engine.
"""

import imp
import os
import pickle
import os.path as osp
import re

from spyder.utils.misc import memoize

from spyder.utils.syntaxhighlighters import (
    custom_extension_lexer_mapping
)

from pygments.lexer import words
from pygments.lexers import (get_lexer_for_filename, get_lexer_by_name,
                             TextLexer)
from pygments.token import Token


# CamelCase and snake_case regex:
# Get all valid tokens that start by a letter (Unicode) and are
# followed by a sequence of letters, numbers or underscores of length > 0
all_regex = re.compile(r'[^\W\d_]\w+')

# CamelCase, snake_case and kebab-case regex:
# Same as above, but it also considers words separated by "-"
kebab_regex = re.compile(r'[^\W\d_]\w+[-\w]*')

LANGUAGE_REGEX = {
    'css': kebab_regex,
    'scss': kebab_regex,
    'html': kebab_regex,
    'xml': kebab_regex
}


def find_lexer_for_filename(filename):
    """Get a Pygments Lexer given a filename.
    """
    filename = filename or ''
    root, ext = os.path.splitext(filename)
    if ext in custom_extension_lexer_mapping:
        lexer = get_lexer_by_name(custom_extension_lexer_mapping[ext])
    else:
        try:
            lexer = get_lexer_for_filename(filename)
        except Exception:
            return TextLexer()
    return lexer


def get_keywords(lexer):
    """Get the keywords for a given lexer.
    """
    search_attrs = ('builtin', 'keyword', 'word')
    keywords = []
    for attr in dir(lexer):
        for search_attr in search_attrs:
            if attr.lower().startswith(search_attr):
                keywords += getattr(lexer, attr)

    if not hasattr(lexer, 'tokens'):
        return keywords
    if 'keywords' in lexer.tokens:
        try:
            return keywords + lexer.tokens['keywords'][0][0].words
        except Exception:
            pass
    for vals in lexer.tokens.values():
        for val in vals:
            try:
                if isinstance(val[0], words):
                    keywords.extend(val[0].words)
                else:
                    ini_val = val[0]
                    if ')\\b' in val[0] or ')(\\s+)' in val[0]:
                        val = re.sub(r'\\.', '', val[0])
                        val = re.sub(r'[^0-9a-zA-Z|]+', '', val)
                        if '|' in ini_val:
                            keywords.extend(val.split('|'))
                        else:
                            keywords.append(val)
            except Exception:
                continue
    return keywords


def get_words(text, language=None):
    """
    Extract all words from a source code file to be used in code completion.

    Extract the list of words that contains the file in the editor,
    to carry out the inline completion similar to VSCode.
    """
    regex = LANGUAGE_REGEX.get(language.lower(), all_regex)
    tokens = list({x for x in regex.findall(text) if x != ''})
    return tokens


@memoize
def get_parent_until(path):
    """
    Given a file path, determine the full module path.

    e.g. '/usr/lib/python2.7/dist-packages/numpy/core/__init__.pyc' yields
    'numpy.core'
    """
    dirname = osp.dirname(path)
    try:
        mod = osp.basename(path)
        mod = osp.splitext(mod)[0]
        imp.find_module(mod, [dirname])
    except ImportError:
        return
    items = [mod]
    while 1:
        items.append(osp.basename(dirname))
        try:
            dirname = osp.dirname(dirname)
            imp.find_module('__init__', [dirname + os.sep])
        except ImportError:
            break
    return '.'.join(reversed(items))


def default_info_response():
    """Default response when asking for info."""
    return dict(name='', argspec='', note='', docstring='', calltip='')
