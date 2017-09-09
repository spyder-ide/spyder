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
import re

from spyder.config.base import debug_print, get_conf_path
from spyder.utils.external import toml

regex_variables = re.compile(r'\$\{(\d+)\:(\w*)\}')


class Snippet():
    def __init__(self, name, **kwargs):
        """Create a Snippet object."""
        self.name = name
        self.content = kwargs['content']
        self.prefix = kwargs['prefix']
        self.language = kwargs['language']

    def text(self):
        """Return content with variables defaults replaced."""
        return re.sub(regex_variables, r'\2', self.content)

    def variables_position(self):
        """
        Return the position and lenght of the next variable.

        Return:
            start (line, column)
            lenght: lenght of the default value for the variable.
        """
        position = 0
        lenght_diff = 0
        for match in re.finditer(regex_variables, self.content):
            position = match.start() - (lenght_diff)
            lenght_diff = len(match.group()) - len(match.group(2))
            yield (position, len(match.group(2)))

    def to_toml(self):
        """Dump the contents to a toml formated str."""
        snippet = {self.name: {'prefix': self.prefix,
                               'language': self.language,
                               'content': self.content}}
        return toml.dumps(snippet)

    def __str__(self):
        return "[{}]\n{}".format(self.name, self.content)

    def __eq__(self, other):
        return self.__dict__ == other.__dict__


class SnippetManager():
    def __init__(self):
        """Create an snippets manager, and load snippets from config."""
        self.snippets = {}
        self.path = get_conf_path("snippets")
        self.load_snippets()

    def load_snippets(self):
        """
        Load snippets from the path specified in the configurations.

        Return the amount of loaded snippets.

        TODO: Validate that snnipets have unique prefix.
        """
        if not os.path.isdir(self.path):
            return
        amount_snippets = 0
        for fname in os.listdir(self.path):
            fname = os.path.join(self.path, fname)
            snippets = self.load_snippet_file(fname)

            self.snippets.update(snippets)
            amount_snippets += len(snippets)
        return amount_snippets

    @staticmethod
    def load_snippet_file(fname):
        """Load an snipped file."""
        snippets = {}

        with codecs.open(fname) as f:
            try:
                dict_snippets = toml.load(f)
            except toml.TomlDecodeError:
                debug_print('Malformed snippet: {}'.format(fname))
            else:
                for name, snippet in dict_snippets.items():
                    try:
                        snippets[snippet['prefix']] = Snippet(name, **snippet)
                        debug_print('Load snippet: {}'.format(snippet))
                    except KeyError as e:
                        debug_print(
                            'Error while loading snippet: {}, {}'.format(
                                snippet, e))
        return snippets

    def search_snippet(self, prefix):
        """
        Search and return an snippet by its prefix.

        Return None if the snippet does not exist.
        """
        return self.snippets.get(prefix)

    def save_snippet(self, snippet, file_name=None):
        """Save an snippet in the configuration path."""
        if file_name is None:
            file_name = '{}.toml'.format(snippet.prefix)

        try:
            os.makedirs(self.path)
        except OSError as e:
            if e.errno == errno.EEXIST and os.path.isdir(self.path):
                pass
            else:
                debug_print('Unable to create snippets directory: {}'.format(
                    self.path))
                return
        try:
            file = os.path.join(self.path, file_name)

            with codecs.open(file, "w", "utf-8") as f:
                f.write(snippet.to_toml())
        except OSError as e:
            debug_print('Failed to save snippet:\n{}'.format(snippet))
