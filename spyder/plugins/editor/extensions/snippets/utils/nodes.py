# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Snippet Abstract Syntax Tree (AST) nodes and definitions."""

import re

BACKSLASH_REPLACE_REGEX = re.compile(r'(\\)([^\\\s])')

# ------------------------ ASTNode identifiers --------------------------------


class SnippetKind:
    TABSTOP = 'tabstop'
    PLACEHOLDER = 'placeholder'
    CHOICE = 'choice'
    VARIABLE = 'variable'
    VARIABLE_PLACEHOLDER = 'variable_placeholder'
    REGEX = 'regex'


class FormatKind:
    SIMPLE = 'simple'
    IF = 'if'
    IF_ELSE = 'if_else'
    ELSE = 'else'


class NodeKind:
    TEXT = 'text'
    LEAF = 'leaf'
    FORMAT = 'format'


# ------------------------- Base AST Node classes -----------------------------


class ASTNode:
    """
    Base class that represents a node on a snippet AST.

    All other nodes should extend this class directly or indirectly.
    """

    # Node string identifier
    # Status: Required
    KIND = None

    def __init__(self, position=(0, 0)):
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

    def accept(self, visitor):
        """Accept visitor to iterate through the AST."""
        visitor.visit(self)


class TextNode(ASTNode):
    """
    AST node representing a text sequence.

    The sequence is composed of one or more LeafNodes or any ASTNode.
    """

    KIND = NodeKind.TEXT

    def __init__(self, *tokens):
        ASTNode.__init__(self)
        self.tokens = tokens

    def add_token(self, token):
        """Adds a token to the text sequence."""
        self.tokens.append(token)

    def text(self):
        return ''.join([token.text() for token in self.tokens])

    def accept(self, visitor):
        visitor.visit(self)
        for token in self.tokens:
            visitor.visit(token)


class LeafNode(ASTNode):
    """Node that represents a terminal symbol."""

    KIND = NodeKind.LEAF

    def __init__(self, name='EPSILON', value=''):
        ASTNode.__init__(self)
        self.name = name
        self.value = value

    def text(self):
        text = BACKSLASH_REPLACE_REGEX.sub(r'\2', self.value)
        if self.name == 'left_curly_name':
            text = text[1:]
        return text

    def __str__(self):
        return 'LeafNode({0}: {1})'.format(self.name, self.value)

    def __repr__(self):
        return r'{0}'.format(self.__str__())


class SnippetASTNode(ASTNode):
    """
    Stub node that represents an actual snippet.

    Used to unify type hierarchies between int and variable snippets.
    """
    pass


class FormatNode(ASTNode):
    """
    Base regex formatting node.

    All regex formatting nodes shoudld extend this class.
    """

    def transform_regex(self, regex_result):
        """
        Transform a regex match.

        This method takes a regex result and applies some transformation to
        return a new string.
        """
        return ''


# -------------------------- Int snippet node classes -------------------------


class TabstopSnippetNode(SnippetASTNode):
    """
    Node that represents an int tabstop snippet.

    This node represents the expressions ${int} or $int.
    """

    KIND = SnippetKind.TABSTOP
    DEFAULT_PLACEHOLDER = ''

    def __init__(self, number, placeholder=None):
        SnippetASTNode.__init__(self)
        self.number = int(number.value)
        self.placeholder = (placeholder if placeholder is not None else
                            self.DEFAULT_PLACEHOLDER)

    def update(self, new_placeholder):
        self.placeholder = new_placeholder

    def text(self):
        return self.placeholder


class PlaceholderNode(TabstopSnippetNode):
    """
    Node that represents an int tabstop placeholder snippet.

    This node represents the expression ${int: placeholder}, where placeholder
    can be a snippet or text.
    """

    KIND = SnippetKind.PLACEHOLDER

    def __init__(self, number, placeholder=''):
        TabstopSnippetNode.__init__(self, number, placeholder)

    def text(self):
        if isinstance(self.placeholder, str):
            return self.placeholder
        elif isinstance(self.placeholder, ASTNode):
            return self.placeholder.text()
        else:
            raise ValueError('Placeholder should be of type '
                             'SnippetASTNode or str, got {0}'.format(
                                 type(self.placeholder)))


class ChoiceNode(TabstopSnippetNode):
    """
    Node that represents an int tabstop choice snippet.

    This node represents the expression ${int:|options|}, where options are
    text sequences separated by comma.
    """

    KIND = SnippetKind.CHOICE

    def __init__(self, number, choices):
        TabstopSnippetNode.__init__(self, number, choices[0])
        self.current_choice = choices[0]
        self.choices = []

    def update(self, choice):
        if choice not in self.choices:
            # TODO: Maybe we should display this as a warning
            # instead of raising an exception.
            raise LookupError('Choice {0} is not a valid value for this '
                              'snippet, expected any of {1}'.format(
                                  choice, self.choices))
        self.current_choice = choice
        self.placeholder = choice


# --------------------- Variable snippet node classes -------------------------


class VariableSnippetNode(SnippetASTNode):
    """
    Node that represents a variable snippet.

    This node represents the expression ${var} or $var, where var is some
    variable qualified name.
    """

    KIND = SnippetKind.VARIABLE

    def __init__(self, variable):
        SnippetASTNode.__init__(self)
        self.variable = variable
        self.value = variable

    def update(self, value):
        self.value = value

    def text(self):
        return self.value


class VariablePlaceholderNode(VariableSnippetNode):
    """
    Node that represents a variable placeholder snippet.

    This node represents the expression ${var: placeholder}, where placeholder
    can be a snippet or text.
    """

    KIND = SnippetKind.VARIABLE_PLACEHOLDER

    def __init__(self, variable, placeholder):
        VariableSnippetNode.__init__(self, variable)
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


class RegexNode(VariableSnippetNode):
    """
    Node that represents a variable regex transformation snippet.

    This node represents the expression ${var/regex/format/options}, where
    regex is a PCRE-valid regex expression, format corresponds to a FormatNode
    and options is a TextNode containing valid regex options.
    """

    KIND = SnippetKind.REGEX

    def __init__(self, variable, regex, fmt, options):
        VariableSnippetNode.__init__(self, variable)
        self.regex = re.compile(regex.text())
        self.format = fmt
        self.options = options

    def text(self):
        # FIXME: Implement regex variable placeholder composition once
        # microsoft/language-server-protocol#801 is clarified
        raise NotImplementedError('Regex variable snippets are '
                                  'not currently implemented')


# -------------------- Regex formatting node classes --------------------------


class FormatSequenceNode(FormatNode):
    """Node that represents a sequence of formatting or text nodes."""

    KIND = FormatKind.SIMPLE

    def __init__(self, *formatting_nodes):
        FormatNode.__init__(self)
        self.formatting_nodes = formatting_nodes

    def add_format(self, fmt):
        self.formatting_nodes.append(fmt)

    def transform_regex(self, regex_result):
        result = ''
        for fmt in self.formatting_nodes:
            if isinstance(fmt, TextNode):
                result += fmt.text()
            elif isinstance(fmt, FormatNode):
                result += fmt.transform_regex(regex_result)
        return result

    def accept(self, visitor):
        visitor.visit(self)
        for fmt in self.formatting_nodes:
            visitor.visit(fmt)


class SimpleFormatNode(FormatNode):
    """
    Extract a single group from a regex match.

    This node represents the expression $int or ${int} where int corresponds
    to a group on a regex match.
    """

    KIND = NodeKind.FORMAT

    def __init__(self, group_number):
        FormatNode.__init__(self)
        self.group_number = group_number

    def transform_regex(self, regex_result):
        return regex_result.group(self.group_number)


class IfFormatNode(SimpleFormatNode):
    """
    Choose a string if a regex group was found.

    This node represents the expression ${group :+ value_if_exists}, where
    value_if_exists is evaluated if $group is present on the regex match.
    """

    KIND = FormatKind.IF

    def __init__(self, group_number, positive_match):
        SimpleFormatNode.__init__(self, group_number)
        self.positive_match = positive_match

    def transform_regex(self, regex_result):
        result = ''
        if regex_result.group(self.group_number) is not None:
            result = self.positive_match.transform_regex(regex_result)
        return result


class IfElseNode(SimpleFormatNode):
    """
    Choose a string if a regex group was found, otherwise choose other.

    This node represents the expression
    ${group ?: value_if_exists : value_otherwise}, where
    value_if_exists is evaluated if $group is present on the regex match,
    otherwise, the node value_otherwise is evaluated.
    """

    KIND = FormatKind.IF_ELSE

    def __init__(self, group_number, positive_match, negative_match):
        SimpleFormatNode.__init__(self, group_number)
        self.positive_match = positive_match
        self.negative_match = negative_match

    def transform_regex(self, regex_result):
        result = ''
        if regex_result.group(self.group_number) is not None:
            result = self.positive_match.transform_regex(regex_result)
        else:
            result = self.negative_match.transform_regex(regex_result)
        return result


class ElseNode(SimpleFormatNode):
    """
    Choose a string if a regex group was not found.

    This node represents the expression ${group :- value_if_not_exists}, where
    value_if_not_exists is evaluated if $group is not present on the
    regex match, otherwise the group value is returned.
    """

    KIND = FormatKind.ELSE

    def __init__(self, group_number, negative_match):
        SimpleFormatNode.__init__(self, group_number)
        self.negative_match = negative_match

    def transform_regex(self, regex_result):
        result = ''
        if regex_result.group(self.group_number) is None:
            result = self.negative_match.transform_regex(regex_result)
        else:
            result = regex_result.group(self.group_number)
        return result
