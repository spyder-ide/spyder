# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""LL(1) parse routine for our snippets grammar."""

# Standard lib imports
import logging
import codecs

# Local imports
from spyder.utils.snippets.lexer import tokenize, token_regex, Token
from spyder.utils.snippets.parser import create_LL1_parsing_table
import spyder.utils.snippets.nodes as nodes


logger = logging.getLogger(__name__)

STARTING_RULE = 'START'
INVERSE_TOKEN_TABLE = dict(zip(token_regex.values(), token_regex.keys()))

GRAMMAR, _, _, PARSE_TABLE = create_LL1_parsing_table(
    starting_rule=STARTING_RULE)


CONTEXT_SWITCHER = {
    'TEXT': {
        'default': nodes.TextNode,
        'args': True
    },
    'TEXT_SNIPPETS': {
        'default': nodes.TextNode,
        'args': True
    },
    'TEXT_NO_COL': {
        'default': nodes.TextNode,
        'args': True
    },
    'TEXT_COL': {
        'default': nodes.TextNode,
        'args': True
    },
    'TEXT_REGEX': {
        'default': nodes.TextNode,
        'args': True
    },
    'TEXT_FORMAT': {
        'default': nodes.TextNode,
        'args': True
    },
    'EXPRLIST': {
        'default': nodes.TextNode,
        'args': True
    },
    'SNIPPET': {
        'default': None,
        'args': True
    },
    'INTSNIPPET': {
        'SNIPPET': nodes.TabstopSnippetNode,
        'args': False
    },
    'VARSNIPPET': {
        'SNIPPET': nodes.VariableSnippetNode,
        'args': False
    },
    'COLONBODY': {
        'INTSNIPPET': nodes.PlaceholderNode,
        'VARSNIPPET': nodes.VariablePlaceholderNode,
        'args': False
    },
    'PIPEBODY': {
        'INTSNIPPET': nodes.ChoiceNode,
        'args': False
    },

}

IGNORE_TERMINALS = {
    'SNIPPET': {'dollar'},
    'INTSNIPPET': {'left_curly', 'right_curly'},
    'VARSNIPPET': {'right_curly'},
    'COLONBODY': {'colon', 'right_curly'},
    'PIPEBODY': {'pipe', 'right_curly', 'comma'},
    'REGEXBODY': {'slash', 'right_curly'},
    'FORMATEXPR': {'dollar'},
    'FORMATBODY': {'left_curly', 'right_curly'},
    'TEXTSEQ': {'comma'}
}


def switch_context(current_rule, current_ctx, current_args, current_prefix,
                   context_stack, args_stack, prefix_stack):
    """Decide if a new AST node must be created."""
    new_ctx = current_ctx
    new_args = current_args
    new_prefix = current_prefix
    if current_rule in CONTEXT_SWITCHER:
        rule_switch = CONTEXT_SWITCHER[current_rule]
        Node = None
        current_ctx_name, _ = current_ctx
        if current_ctx_name in rule_switch:
            Node = rule_switch[current_ctx_name]
        elif 'default' in rule_switch:
            Node = rule_switch['default']
        else:
            raise ValueError('Cannot transition to '
                             'context {0} from {1}'.format(
                                 current_rule, current_ctx_name))
        new_ctx = (current_rule, Node)

        if rule_switch['args']:
            args_stack.insert(0, current_args)
            context_stack.insert(0, current_ctx)
            prefix_stack.insert(0, current_prefix)
            new_args = []
            new_prefix = []
    return (new_ctx, new_args, new_prefix,
            context_stack, args_stack, prefix_stack)


def build_snippet_ast(snippet_text):
    """Given a snippet string, return its abstract syntax tree (AST)."""
    tokens = tokenize(snippet_text)
    tokens += [Token('eof', '<eof>')]

    stack = [STARTING_RULE]

    current_ctx = (STARTING_RULE, None)
    current_args = []
    current_prefix = [STARTING_RULE]

    context_stack = []
    args_stack = []
    prefix_stack = []

    while len(stack) > 0:
        peek_token = tokens[0]
        current_rule = stack.pop(0)
        if current_rule in GRAMMAR:
            # A grammar production rule
            follow_predictions = PARSE_TABLE[current_rule]
            next_productions = []
            if peek_token.token in follow_predictions:
                next_productions = follow_predictions[peek_token.token]
            elif peek_token.value in follow_predictions:
                next_productions = follow_predictions[peek_token.value]
            else:
                raise SyntaxError('Syntax Error: Expected any of the following'
                                  ' characters: {0}, got {1}'.format(
                                      list(follow_predictions.keys()),
                                      peek_token
                                    ))
            current_prefix.pop(0)
            stack = next_productions + stack
            new_ctx = switch_context(current_rule, current_ctx, current_args,
                                     current_prefix, context_stack, args_stack,
                                     prefix_stack)
            (current_ctx, current_args, current_prefix,
             context_stack, args_stack, prefix_stack) = new_ctx
            current_prefix = next_productions + current_prefix
        else:
            # A terminal symbol
            if peek_token.token == current_rule:
                tokens.pop(0)
            elif peek_token.value == current_rule:
                tokens.pop(0)
            else:
                raise SyntaxError('Syntax Error: Expected {0}, got {1}'.format(
                    repr(peek_token.value), repr(current_rule)))

            current_name, _ = current_ctx
            add_to_args = True
            if current_name in IGNORE_TERMINALS:
                add_to_args = (peek_token.token not in
                               IGNORE_TERMINALS[current_name])

            if add_to_args:
                leaf = nodes.LeafNode(peek_token.token, peek_token.value)
                current_args.append(leaf)
            current_prefix.pop(0)

        if len(current_prefix) == 0:
            _, Node = current_ctx
            node = Node(*current_args)
            current_ctx = context_stack.pop(0)
            current_args = args_stack.pop(0)
            current_prefix = prefix_stack.pop(0)
            current_args.append(node)

    assert len(current_args) == 1
    return current_args[0]
