# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Introspection utilities used by Spyder
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
from pygments.lexers import (
    get_lexer_for_filename, get_lexer_by_name, TextLexer
)
from pygments.util import ClassNotFound
from pygments.token import Token


class CodeInfo(object):

    id_regex = re.compile(r'[^\d\W][\w\.]*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W][\w\.]*)\([^\)\()]*\Z',
                                 re.UNICODE)

    def __init__(self, name, source_code, position, filename=None,
                 is_python_like=False, in_comment_or_string=False,
                 sys_path=None, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.filename = filename
        self.source_code = source_code
        self.is_python_like = is_python_like
        self.in_comment_or_string = in_comment_or_string
        self.sys_path = sys_path

        self.position = position

        # if in a comment, look for the previous definition
        if in_comment_or_string:
            # if this is a docstring, find it, set as our
            self.docstring = self._get_docstring()
            # backtrack and look for a line that starts with def or class
            if name != 'completions':
                while position:
                    base = self.source_code[position: position + 6]
                    if base.startswith('def ') or base.startswith('class '):
                        position += base.index(' ') + 1
                        break
                    position -= 1
        else:
            self.docstring = ''

        self.position = position

        if position == 0:
            self.lines = []
            self.column = 0
            self.line_num = 0
            self.line = ''
            self.obj = ''
            self.full_obj = ''
        else:
            self._get_info()

    def _get_info(self):

        self.lines = self.source_code[:self.position].splitlines()
        self.line_num = len(self.lines)

        self.line = self.lines[-1]
        self.column = len(self.lines[-1])

        full_line = self.source_code.splitlines()[self.line_num - 1]

        lexer = find_lexer_for_filename(self.filename)

        # check for a text-based lexer that doesn't split tokens
        if len(list(lexer.get_tokens('a b'))) == 1:
            # Use regex to get the information
            tokens = re.findall(self.id_regex, self.line)
            if tokens and self.line.endswith(tokens[-1]):
                self.obj = tokens[-1]
            else:
                self.obj = None

            self.full_obj = self.obj

            if self.obj:
                full_line = self.source_code.splitlines()[self.line_num - 1]
                rest = full_line[self.column:]
                match = re.match(self.id_regex, rest)
                if match:
                    self.full_obj = self.obj + match.group()

            self.context = None
        else:
            # Use lexer to get the information
            pos = 0
            line_tokens = lexer.get_tokens(full_line)
            for (context, token) in line_tokens:
                pos += len(token)
                if pos >= self.column:
                    self.obj = token[:len(token) - (pos - self.column)]
                    self.full_obj = token
                    if context in Token.Literal.String:
                        context = Token.Literal.String
                    self.context = context
                    break

        if (self.name in ['info', 'definition'] and (not self.context in Token.Name)
                and self.is_python_like):
            func_call = re.findall(self.func_call_regex, self.line)
            if func_call:
                self.obj = func_call[-1]
                self.column = self.line.index(self.obj) + len(self.obj)
                self.position = self.position - len(self.line) + self.column

    def _get_docstring(self):
        """Find the docstring we are currently in."""
        left = self.position
        while left:
            if self.source_code[left: left + 3] in ['"""', "'''"]:
                left += 3
                break
            left -= 1
        right = self.position
        while right < len(self.source_code):
            if self.source_code[right - 3: right] in ['"""', "'''"]:
                right -= 3
                break
            right += 1
        if left and right < len(self.source_code):
            return self.source_code[left: right]
        return ''

    def __eq__(self, other):
        try:
            return self.serialize() == other.serialize()
        except Exception:
            return False

    def __getitem__(self, item):
        """Allow dictionary-like access."""
        return getattr(self, item)

    def serialize(self):
        state = {}
        for (key, value) in self.__dict__.items():
            try:
                pickle.dumps(value)
                state[key] = value
            except Exception:
                pass
        state['id_regex'] = self.id_regex
        state['func_call_regex'] = self.func_call_regex
        return state


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
        except ClassNotFound:
            return TextLexer()
    return lexer


def get_keywords(lexer):
    """Get the keywords for a given lexer.
    """
    if not hasattr(lexer, 'tokens'):
        return []
    if 'keywords' in lexer.tokens:
        try:
            return lexer.tokens['keywords'][0][0].words
        except:
            pass
    keywords = []
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

def get_words(file_path=None, content=None, extension=None):
    """
    Extract all words from a source code file to be used in code completion.

    Extract the list of words that contains the file in the editor,
    to carry out the inline completion similar to VSCode.
    """
    if (file_path is None and (content is None or extension is None) or
                    file_path and content and extension):
        error_msg = ('Must provide `file_path` or `content` and `extension`')
        raise Exception(error_msg)

    if file_path and content is None and extension is None:
        extension = os.path.splitext(file_path)[1]
        with open(file_path) as infile:
            content = infile.read()

    if extension in ['.css']:
        regex = re.compile(r'([^a-zA-Z-])')
    elif extension in ['.R', '.c', '.md', '.cpp', '.java', '.py']:
        regex = re.compile(r'([^a-zA-Z_])')
    else:
        regex = re.compile(r'([^a-zA-Z])')

    words = sorted(set(regex.sub(r' ', content).split()))
    return words

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
