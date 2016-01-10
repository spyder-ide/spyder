# -*- coding: utf-8 -*-
#
# Copyright © 2013 The Spyder Development Team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Introspection utilities used by Spyder
"""

import functools
import imp
import os
import os.path as osp
import re


class CodeInfo(object):

    id_regex = re.compile(r'[^\d\W][\w\.]*', re.UNICODE)
    func_call_regex = re.compile(r'([^\d\W][\w\.]*)\([^\)\()]*\Z',
                                 re.UNICODE)

    def __init__(self, name, source_code, position, filename=None,
            is_python_like=True, in_comment_or_string=False, **kwargs):
        self.__dict__.update(kwargs)
        self.name = name
        self.filename = filename
        self.source_code = source_code
        self.is_python_like = is_python_like
        self.in_comment_or_string = in_comment_or_string
        self.position = position

        # if in a comment, look for the previous definition
        if in_comment_or_string:
            # if this is a docstring, find it, set as our
            self.docstring = self._get_docstring()
            # backtrack and look for a line that starts with def or class
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

        if (self.name in ['info', 'definition'] and (not self.obj)
                and self.is_python_like):
            func_call = re.findall(self.func_call_regex, self.line)
            if func_call:
                self.obj = func_call[-1]
                self.column = self.line.index(self.obj) + len(self.obj)
                self.position = self.position - len(self.line) + self.column

    def split_words(self, position=None):
        """
        Split our source code into valid identifiers.

        """
        if position is None:
            position = self.offset
        text = self.source_code[:position]
        return re.findall(self.id_regex, text)

    def _get_docstring(self):
        """Find the docstring we are currently in"""
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
            return self.__dict__ == other.__dict__
        except Exception:
            return False


def memoize(obj):
    """
    Memoize objects to trade memory for execution speed

    Use a limited size cache to store the value, which takes into account
    The calling args and kwargs

    See https://wiki.python.org/moin/PythonDecoratorLibrary#Memoize
    """
    cache = obj.cache = {}

    @functools.wraps(obj)
    def memoizer(*args, **kwargs):
        key = str(args) + str(kwargs)
        if key not in cache:
            cache[key] = obj(*args, **kwargs)
        # only keep the most recent 100 entries
        if len(cache) > 100:
            cache.popitem(last=False)
        return cache[key]
    return memoizer


@memoize
def get_parent_until(path):
    """
    Given a file path, determine the full module path

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


if __name__ == '__main__':
    code = 'import numpy'
    test = CodeInfo('test', code, len(code) - 2)
    print(test.serialize())
    assert test.obj == 'num'
    assert test.full_obj == 'numpy'
    test2 = CodeInfo('test', code, len(code) - 2)
    assert test == test2
