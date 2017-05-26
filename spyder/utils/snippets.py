# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Snippet support to codeEditor"""

# Standard library imports
import os
import errno
import codecs
import toml
import re

from spyder.config.base import debug_print, get_conf_path


regex_variables = re.compile(r'\$\{(\d+)\:(\w*)\}')


class Snippet():
    def __init__(self, content):
        self.content = content

    def text(self):
        return re.sub(regex_variables, r'\2', self.content)

    def variables(self):
        """
        Return the position and lenght of the next variable.

        Return:
            position: position of the variable relative to the
                end of last match.
            lenght: lenght of current variable.
        """
        position = 0
        lenght = 0
        for match in re.finditer(regex_variables, self.content):
            position = match.start() - (position + lenght)
            lenght = len(match.group())
            yield position, len(match.group(2))


class SnippetManager():
    def __init__(self):
        self.snippets = {}
        self.path = get_conf_path("snippets")
        self.load_snippets()

    def load_snippets(self):
        if not os.path.isdir(self.path):
            return
        loaded_snippets = 0
        for file in os.listdir(self.path):
            file = os.path.join(self.path, file)
            with codecs.open(file, encoding='utf-8') as f:
                try:
                    snippets = toml.load(f)
                except toml.TomlDecodeError:
                    debug_print('Malformed snippet: {}'.format(file))
                else:
                    for name, snippet in snippets.items():
                        debug_print(snippet)
                        self.snippets[snippet['prefix']] = snippet['content']
                        debug_print('Load snippet: {}'.format(snippet))
                        loaded_snippets += 1
        return loaded_snippets

    def search_snippet(self, prefix):
        return self.snippets.get(prefix)

    def save_snippet(self, prefix, content, file_name=None):
        self.snippets[prefix] = content

        if file_name is None:
            file_name = '{}.toml'.format(prefix)

        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                debug_print('Unable to create snipets directory: {}'.format(
                        self.path))
                return

        try:
            file = os.path.join(self.path, file_name)

            with codecs.open(file, "w", "utf-8") as f:
                f.write(toml.dumps({'prefix': prefix, 'content': content}))
        except OSError as e:
            debug_print('Failed to save snippet:\n{}\n{}'.format(prefix,
                                                                 content))
