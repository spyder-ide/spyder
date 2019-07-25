# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Snippet Abstract Syntax Tree (AST) nodes and definitions."""

import re

BACKSLASH_REPLACE_REGEX = re.compile(r'(\\)([^\\\s])')


class ParserContext:
    TABSTOP_SNIPPET = 1
    PLACEHOLDER_SNIPPET = 2
    CHOICE_SNIPPET = 3
    VARIABLE_SNIPPET = 4
    NO_SNIPPET = 5
    FORMAT_CONTEXT = 6


class SnippetKind:
    TABSTOP = 'tabstop'
    PLACEHOLDER = 'placeholder'
    CHOICE = 'choice'
    VARIABLE = 'variable'
    VARIABLE_PLACEHOLDER = 'variable_placeholder'
    REGEX = 'regex'


class NodeKind:
    TEXT = 'text'
    LEAF = 'leaf'


class ASTNode:
    """
    Base class that represents a node on a snippet AST.

    All other nodes should extend this class directly or indirectly.
    """

    def __init__(self, position, kind):
        self.kind = kind
        self.position = position

    def update_position(self, position):
        """Updates node text position."""
        self.position = position

    def update(self, value):
        """
        Update a node value or representation.

        Downstream classes can override this method if necessary.
        """
        pass

    def text(self):
        """
        This function should return a string that represents the current node.

        Downstream classes can override this method if necessary.
        """
        pass


class TextNode(ASTNode):
    """
    AST node representing a text sequence.

    The sequence is composed of one or more LeafNodes or any ASTNode.
    """

    def __init__(self, position, tokens=[]):
        ASTNode.__init__(self, position, kind=NodeKind.TEXT)
        self.tokens = tokens

    def add_token(self, token):
        """Adds a token to the text sequence."""
        self.tokens.append(token)

    def text(self):
        return ''.join([token.text() for token in self.tokens])


class LeafNode(ASTNode):
    """Node that represents a terminal symbol."""

    def __init__(self, position, name, value):
        ASTNode.__init__(self, position, kind=NodeKind.LEAF)
        self.name = name
        self.value = value

    def text(self):
        text = BACKSLASH_REPLACE_REGEX.sub(r'\2', self.value)
        return text


class SnippetASTNode(ASTNode):
    """
    Stub node that represents an actual snippet.

    Used to unify type hierarchies between int and variable snippets.
    """
    pass


class TabstopSnippetNode(SnippetASTNode):
    """
    Node that represents a tabstop int snippet.

    This node represents the expressions ${int} or $int.
    """

    DEFAULT_PLACEHOLDER = ''

    def __init__(self, position, number, placeholder=None,
                 kind=SnippetKind.TABSTOP):
        SnippetASTNode.__init__(self, position, kind)
        self.number = number
        self.placeholder = (placeholder if placeholder is not None else
                            self.DEFAULT_PLACEHOLDER)

    def update(self, new_placeholder):
        self.placeholder = new_placeholder

    def text(self):
        return self.placeholder


class PlaceholderNode(TabstopSnippetNode):
    """
    Node that represents a tabstop placeholder int snippet.

    This node represents the expression ${int: placeholder}, where placeholder
    can be a snippet or text.
    """

    def __init__(self, position, number, placeholder):
        TabstopSnippetNode.__init__(self, position, number, placeholder,
                                    kind=SnippetKind.PLACEHOLDER)

    def text(self):
        if isinstance(self._placeholder, str):
            return self._placeholder
        elif isinstance(self._placeholder, ASTNode):
            return self._placeholder.text()
        else:
            raise ValueError('Placeholder should be of type '
                             'SnippetASTNode or str, got {0}'.format(
                                 type(self._placeholder)))


class ChoiceNode(TabstopSnippetNode):
    """
    Node that represents a tabstop choice int snippet.

    This node represents the expression ${int:|options|}, where options are
    text sequences separated by comma.
    """

    def __init__(self, position, number, choices):
        TabstopSnippetNode.__init__(self, position, number, choices[0],
                                    kind=SnippetKind.CHOICE)
        self.current_choice = choices[0]
        self.choices = []

    def update(self, choice):
        if choice not in self.choices:
            raise LookupError('Choice {0} is not a valid value for this '
                              'snippet, expected any of {1}'.format(
                                  choice, self.choices))
        self.current_choice = choice
        self._placeholder = choice


class VariableSnippetNode(SnippetASTNode):
    def __init__(self, position, variable, kind=SnippetKind.VARIABLE):
        SnippetASTNode.__init__(self, position, kind=kind)
        self.variable = variable
        self.value = variable

    def update(self, value):
        self.value = value

    def text(self):
        return self.value


class VariablePlaceholderNode(VariableSnippetNode):
    def __init__(self, position, variable, placeholder):
        VariableSnippetNode.__init__(self, position, variable,
                                     kind=SnippetKind.VARIABLE_PLACEHOLDER)
        self.placeholder = placeholder

    def update(self, placeholder):
        self.placeholder = placeholder

    def text(self):
        if isinstance(self._placeholder, str):
            return self._placeholder
        elif isinstance(self._placeholder, ASTNode):
            # FIXME: Implement placeholder composition once
            # microsoft/language-server-protocol#801 is clarified
            return self._placeholder.text()
        else:
            raise ValueError('Placeholder should be of type '
                             'SnippetASTNode or str, got {0}'.format(
                                 type(self._placeholder)))


class RegexNode(VariableSnippetNode):
    def __init__(self, position, variable, regex, fmt, options):
        VariableSnippetNode.__init__(self, position, variable,
                                     kind=SnippetKind.REGEX)
        self.regex = re.compile(regex.text())
        self.format = fmt
        self.options = options

    def text(self):
        # FIXME: Implement regex variable placeholder composition once
        # microsoft/language-server-protocol#801 is clarified
        raise NotImplementedError('Regex variable snippets are '
                                  'not currently implemented')
