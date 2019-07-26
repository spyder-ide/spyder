# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard lib imports
import logging
import codecs

# Local imports
from spyder.plugins.editor.extensions.snippets.utils.lexer import (
    tokenize, token_regex, Token)
from spyder.plugins.editor.extensions.snippets.utils.parser import (
    create_LL1_parsing_table)
import spyder.plugins.editor.extensions.snippets.utils.nodes as nodes


logger = logging.getLogger(__name__)

STARTING_RULE = 'START'
INVERSE_TOKEN_TABLE = dict(zip(token_regex.values(), token_regex.keys()))

GRAMMAR, _, _, PARSE_TABLE = create_LL1_parsing_table(
    starting_rule=STARTING_RULE)


class ParserContext:
    TABSTOP_SNIPPET = 1
    PLACEHOLDER_SNIPPET = 2
    CHOICE_SNIPPET = 3
    VARIABLE_SNIPPET = 4
    NO_SNIPPET = 5
    FORMAT_CONTEXT = 6


def build_snippet_ast(snippet_text):
    """Given a snippet string, return its abstract syntax tree (AST)."""
    snippet_text = codecs.decode(snippet_text, 'unicode_escape')
    logger.debug(snippet_text)
    tokens = tokenize(snippet_text)
    tokens += [Token('eof', '<eof>')]

    stack = [STARTING_RULE]
    while len(stack) > 0:
        tokens_repr = [t.value for t in tokens]
        logger.debug('Tokens: {0} - Stack: {1}'.format(tokens_repr, stack))
        peek_token = tokens[0]
        current_rule = stack.pop(0)
        if current_rule in GRAMMAR:
            # A grammar production rule
            follow_predictions = PARSE_TABLE[current_rule]
            if peek_token.token in follow_predictions:
                stack = follow_predictions[peek_token.token] + stack
            elif peek_token.value in follow_predictions:
                stack = follow_predictions[peek_token.value] + stack
            else:
                raise SyntaxError('Syntax Error: Expected any of the following'
                                  ' characters: {0}, got {1}'.format(
                                      list(follow_predictions.keys()),
                                      peek_token
                                    ))
        else:
            # A terminal symbol
            if peek_token.token == current_rule:
                tokens.pop(0)
            elif peek_token.value == current_rule:
                tokens.pop(0)
            else:
                raise SyntaxError('Syntax Error: Expected {0}, got {1}'.format(
                    repr(peek_token.value), repr(current_rule)))
