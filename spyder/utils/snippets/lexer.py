# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Lexer to tokenize snippet text."""

import re
from collections import OrderedDict

whitespace = re.compile(r'\s')

token_regex = OrderedDict({
    'text_colon': r'^\\:$',
    'colon': r'^:$',
    'colon_plus': r'^:\+$',
    'colon_dash': r'^:-$',
    'colon_question': r'^:\?$',
    'text_comma': r'^\\\,$',
    'text_dollar': r'^\\\$$',
    'text_pipe': r'^\\\|$',
    'text_right_curly': r'^\\}$',
    'text_backslash': r'^\\$',
    'text_slash': r'^\\\/$',
    'dollar': r'^\$$',
    'int': r'^\d+$',
    'left_curly': r'^\{$',
    'right_curly': r'^\}$',
    'pipe': r'^\|$',
    'case': r'^/upcase|/downcase|/capitalize$',
    'slash': r'^/$',
    'comma': r'^,$',
    'left_curly_name': r'^\{[a-zA-Z_]\w*$',
    'name': r'^(?=[\w])(?=[^\d])\w*$',
    'symbol': r'^(?=[^_\w]$)(?=[^\s]$)'
})

token_regex = {name: re.compile(r) for name, r in token_regex.items()}


class Token(object):
    def __init__(self, token, value, line=0, col=0):
        self.token = token
        self.value = value
        self.line = line
        self.col = col

    def __str__(self):
        return u'<{0}, {1}>'.format(self.token, self.value)

    def __repr__(self):
        return self.__str__()

    def __eq__(self, y):
        if not isinstance(y, Token):
            return False
        return self.token == y.token

    def __neq__(self, y):
        if not isinstance(y, Token):
            return True
        return self.token != y.token

    def __hash__(self):
        return hash(self.token)


def tokenize(snippet):
    """Split snippet into well-defined tokens."""
    tokens = []
    word = ''
    i = 0
    last_name = None
    while i < len(snippet):
        c = snippet[i]
        if whitespace.match(c) is not None:
            if last_name is not None:
                token = Token(last_name, word, 1, i + 1)
                tokens.append(token)
            token = Token('whitespace', c, line=1, col=i + 1)
            tokens.append(token)
            word = ''
            last_name = None
            i += 1
        else:
            temp_word = word + c
            match_found = False
            for token_name in token_regex:
                regex = token_regex[token_name]
                if regex.match(temp_word) is not None:
                    last_name = token_name
                    match_found = True
                    word = temp_word
                    break
            if not match_found:
                if last_name is not None:
                    token = Token(last_name, word, 1, i + 1)
                    tokens.append(token)
                    word = ''
                    last_name = None
            else:
                word = temp_word
                i += 1
    if last_name is not None:
        token = Token(last_name, word, 1, i + 1)
        tokens.append(token)
    return tokens
