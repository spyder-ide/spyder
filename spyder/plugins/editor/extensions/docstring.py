# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Generate Docstring."""

# Standard library imports
import re

# Third party imports
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.main import CONF
from spyder.py3compat import to_text_string


def is_start_of_function(text):
    """Return True if text is the beginning of the function definition."""
    if isinstance(text, str) or isinstance(text, unicode):
        function_prefix = ['def', 'async def']
        text = text.lstrip()

        for prefix in function_prefix:
            if text.startswith(prefix):
                return True

    return False


def get_indent(text):
    """Get indent of text.

    https://stackoverflow.com/questions/2268532/grab-a-lines-whitespace-
    indention-with-python
    """
    indent = ''

    ret = re.match(r'^(\s*)', text)
    if ret:
        indent = ret.group(1)

    return indent


class DocstringWriterExtension:
    """Class for insert docstring template automatically."""

    def __init__(self, code_editor):
        """Initialize and Add code_editor to the variable."""
        self.code_editor = code_editor
        self.quote3 = '"""'
        self.quote3_other = "'''"
        self.line_number_cursor = None

    @staticmethod
    def is_beginning_triple_quotes(text):
        """Return True if there are only triple quotes in text."""
        docstring_triggers = ['"""', 'r"""', "'''", "r'''"]
        if text.lstrip() in docstring_triggers:
            return True

        return False

    def get_function_definition_from_first_line(self):
        """Get func def when the cursor is located on the first def line."""
        document = self.code_editor.document()
        cursor = QTextCursor(
            document.findBlockByLineNumber(self.line_number_cursor - 1))

        func_text = ''
        func_indent = ''

        is_first_line = True
        line_number = cursor.blockNumber() + 1

        number_of_lines = self.code_editor.blockCount()
        remain_lines = number_of_lines - line_number + 1
        number_of_lines_of_function = 0

        for __ in range(min(remain_lines, 20)):
            cur_text = to_text_string(cursor.block().text()).rstrip()

            if is_first_line:
                if not is_start_of_function(cur_text):
                    return None

                func_indent = get_indent(cur_text)
                is_first_line = False
            else:
                cur_indent = get_indent(cur_text)
                if cur_indent <= func_indent:
                    return None
                if is_start_of_function(cur_text):
                    return None
                if cur_text.strip == '':
                    return None

            if cur_text[-1] == '\\':
                cur_text = cur_text[:-1]

            func_text += cur_text
            number_of_lines_of_function += 1

            if cur_text.endswith(':'):
                return func_text, number_of_lines_of_function

            cursor.movePosition(QTextCursor.NextBlock)

        return None

    def get_function_definition_from_below_last_line(self):
        """Get func def when the cursor is located below the last def line."""
        cursor = self.code_editor.textCursor()
        func_text = ''
        is_first_line = True
        line_number = cursor.blockNumber() + 1
        number_of_lines_of_function = 0

        for idx in range(min(line_number, 20)):
            if cursor.block().blockNumber() == 0:
                return None

            cursor.movePosition(QTextCursor.PreviousBlock)
            prev_text = to_text_string(cursor.block().text()).rstrip()

            if is_first_line:
                if not prev_text.endswith(':'):
                    return None
                is_first_line = False
            elif prev_text.endswith(':') or prev_text == '':
                return None

            if prev_text[-1] == '\\':
                prev_text = prev_text[:-1]

            func_text = prev_text + func_text

            number_of_lines_of_function += 1
            if is_start_of_function(prev_text):
                return func_text, number_of_lines_of_function

        return None

    def get_function_body(self, func_indent):
        """Get the function body text."""
        cursor = self.code_editor.textCursor()
        line_number = cursor.blockNumber() + 1
        number_of_lines = self.code_editor.blockCount()
        body_list = []

        for idx in range(number_of_lines - line_number + 1):
            text = to_text_string(cursor.block().text())
            text_indent = get_indent(text)

            if text.strip() == '':
                pass
            elif len(text_indent) <= len(func_indent):
                break

            body_list.append(text)

            cursor.movePosition(QTextCursor.NextBlock)

        return '\n'.join(body_list)

    def write_docstring(self):
        """Write docstring to editor."""
        line_to_cursor = self.code_editor.get_text('sol', 'cursor')
        if self.is_beginning_triple_quotes(line_to_cursor):
            cursor = self.code_editor.textCursor()
            prev_pos = cursor.position()

            quote = line_to_cursor[-1]
            docstring_type = CONF.get('editor', 'docstring_type')
            docstring = self._generate_docstring(docstring_type, quote)

            if docstring:
                self.code_editor.insert_text(docstring)

                cursor = self.code_editor.textCursor()
                cursor.setPosition(prev_pos, QTextCursor.KeepAnchor)
                cursor.movePosition(QTextCursor.NextBlock)
                cursor.movePosition(QTextCursor.EndOfLine,
                                    QTextCursor.KeepAnchor)
                cursor.clearSelection()
                self.code_editor.setTextCursor(cursor)
                return True

        return False

    def write_docstring_at_first_line_of_function(self):
        """Write docstring to editor at mouse position."""
        result = self.get_function_definition_from_first_line()
        editor = self.code_editor
        if result:
            func_text, number_of_line_func = result
            line_number_function = (self.line_number_cursor +
                                    number_of_line_func - 1)

            cursor = editor.textCursor()
            line_number_cursor = cursor.blockNumber() + 1
            offset = line_number_function - line_number_cursor
            if offset > 0:
                for __ in range(offset):
                    cursor.movePosition(QTextCursor.NextBlock)
            else:
                for __ in range(abs(offset)):
                    cursor.movePosition(QTextCursor.PreviousBlock)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
            editor.setTextCursor(cursor)

            indent = get_indent(func_text)
            editor.insert_text('\n{}{}"""'.format(indent, editor.indent_chars))
            self.write_docstring()

    def write_docstring_for_shortcut(self):
        """Write docstring to editor by shortcut of code editor."""
        # cursor placed below function definition
        result = self.get_function_definition_from_below_last_line()
        if result is not None:
            __, number_of_lines_of_function = result
            cursor = self.code_editor.textCursor()
            for __ in range(number_of_lines_of_function):
                cursor.movePosition(QTextCursor.PreviousBlock)

            self.code_editor.setTextCursor(cursor)

        cursor = self.code_editor.textCursor()
        self.line_number_cursor = cursor.blockNumber() + 1

        self.write_docstring_at_first_line_of_function()

    def _generate_docstring(self, doc_type, quote):
        """Generate docstring."""
        docstring = None

        self.quote3 = quote * 3
        if quote == '"':
            self.quote3_other = "'''"
        else:
            self.quote3_other = '"""'

        result = self.get_function_definition_from_below_last_line()

        if result:
            func_text, __ = result
            func_info = FunctionInfo()
            func_info.parse_def(func_text)

            if func_info.has_info:
                if doc_type == 'Numpydoc':
                    docstring = self._generate_numpy_doc(func_info)
                elif doc_type == 'Googledoc':
                    docstring = self._generate_google_doc(func_info)

        return docstring

    def _generate_numpy_doc(self, func_info):
        """Generate a docstring of numpy type."""
        numpy_doc = ''

        arg_names = func_info.arg_name_list
        arg_types = func_info.arg_type_list
        arg_values = func_info.arg_value_list

        if len(arg_names) > 0 and arg_names[0] == 'self':
            del arg_names[0]
            del arg_types[0]
            del arg_values[0]

        indent1 = func_info.func_indent + self.code_editor.indent_chars
        indent2 = func_info.func_indent + self.code_editor.indent_chars * 2

        numpy_doc += '\n{}\n'.format(indent1)

        if len(arg_names) > 0:
            numpy_doc += '\n{0}Parameters'.format(indent1)
            numpy_doc += '\n{}----------\n'.format(indent1)

        arg_text = ''
        for arg_name, arg_type, arg_value in zip(arg_names, arg_types,
                                                 arg_values):
            arg_text += '{}{} : '.format(indent1, arg_name)
            if arg_type:
                arg_text += '{}'.format(arg_type)
            else:
                arg_text += 'TYPE'

            if arg_value:
                arg_text += ', optional'

            arg_text += '\n{}DESCRIPTION.'.format(indent2)

            if arg_value:
                arg_value = arg_value.replace(self.quote3, self.quote3_other)
                arg_text += ' (the default is {})'.format(arg_value)

            arg_text += '\n'
        numpy_doc += arg_text

        numpy_doc += '\n{}Returns'.format(indent1)
        numpy_doc += '\n{}-------'.format(indent1)
        if func_info.return_type:
            numpy_doc += '\n{}{}'.format(indent1, func_info.return_type)
            numpy_doc += '\n{}DESCRIPTION.\n'.format(indent2)
        else:
            numpy_doc += '\n{}RETURN_TYPE'.format(indent1)
            numpy_doc += '\n{}DESCRIPTION.\n'.format(indent2)

        numpy_doc += '\n{}{}'.format(indent1, self.quote3)

        return numpy_doc

    def _generate_google_doc(self, func_info):
        """Generate a docstring of google type."""
        google_doc = ''

        arg_names = func_info.arg_name_list
        arg_types = func_info.arg_type_list
        arg_values = func_info.arg_value_list

        if len(arg_names) > 0 and arg_names[0] == 'self':
            del arg_names[0]
            del arg_types[0]
            del arg_values[0]

        indent1 = func_info.func_indent + self.code_editor.indent_chars
        indent2 = func_info.func_indent + self.code_editor.indent_chars * 2

        google_doc += '\n{}\n'.format(indent1)

        if len(arg_names) > 0:
            google_doc += '\n{0}Args:\n'.format(indent1)

        arg_text = ''
        for arg_name, arg_type, arg_value in zip(arg_names, arg_types,
                                                 arg_values):
            arg_text += '{}{} '.format(indent2, arg_name)

            arg_text += '('
            if arg_type:
                arg_text += '{}'.format(arg_type)
            else:
                arg_text += 'TYPE'

            if arg_value:
                arg_text += ', optional'
            arg_text += '):'

            arg_text += ' DESCRIPTION.'

            if arg_value:
                arg_value = arg_value.replace(self.quote3, self.quote3_other)
                arg_text += ' Defaults to {}.\n'.format(arg_value)
            else:
                arg_text += '\n'

        google_doc += arg_text

        google_doc += '\n{}Returns:'.format(indent1)
        if func_info.return_type:
            google_doc += '\n{}{}: DESCRIPTION.\n'.format(
                indent2, func_info.return_type)
        else:
            google_doc += '\n{}RETURN_TYPE: DESCRIPTION.\n'.format(indent2)

        google_doc += '\n{}{}'.format(indent1, self.quote3)

        return google_doc


class FunctionInfo:
    """Parse function definition text."""

    def __init__(self):
        """."""
        self.has_info = False
        self.func_text = ''
        self.args_text = ''
        self.func_indent = ''
        self.arg_name_list = []
        self.arg_type_list = []
        self.arg_value_list = []
        self.return_type = None
        self.raise_list = None

    @staticmethod
    def is_char_in_pairs(pos_char, pairs):
        """Return True if the charactor is in pairs of brackets or quotes."""
        for pos_left, pos_right in pairs.items():
            if pos_left < pos_char < pos_right:
                return True

        return False

    @staticmethod
    def _find_quote_position(text):
        """Return the start and end position of pairs of quotes."""
        pos = {}
        is_found_left_quote = False

        for i, c in enumerate(text):
            if is_found_left_quote is False:
                if c == "'" or c == '"':
                    is_found_left_quote = True
                    quote = c
                    left_pos = i
            else:
                if c == quote and text[i - 1] != '\\':
                    pos[left_pos] = i
                    is_found_left_quote = False

        if is_found_left_quote:
            raise IndexError("No matching close quote at: " + str(left_pos))

        return pos

    def _find_bracket_position(self, text, bracket_left, bracket_right,
                               pos_quote):
        """Return the start and end position of pairs of brackets.

        https://stackoverflow.com/questions/29991917/
        indices-of-matching-parentheses-in-python
        """
        idx = {}
        character = []

        for i, c in enumerate(text):
            if c == bracket_left and not self.is_char_in_pairs(i, pos_quote):
                character.append(i)
            elif c == bracket_right and not self.is_char_in_pairs(i,
                                                                  pos_quote):
                if len(character) == 0:
                    raise IndexError(
                        "No matching closing parens at: " + str(i))
                idx[character.pop()] = i

        if len(character) > 0:
            raise IndexError(
                "No matching opening parens at: " + str(character.pop()))

        return idx

    def split_arg_to_name_type_value(self, args_list):
        """Split argument text to name, type, value."""
        for arg in args_list:
            arg_type = None
            arg_value = None

            has_type = False
            has_value = False

            pos_colon = arg.find(':')
            pos_equal = arg.find('=')

            if pos_equal > -1:
                has_value = True

            if pos_colon > -1:
                if not has_value:
                    has_type = True
                elif pos_equal > pos_colon:  # exception for def foo(arg1=":")
                    has_type = True

            if has_value and has_type:
                arg_name = arg[0:pos_colon].strip()
                arg_type = arg[pos_colon + 1:pos_equal].strip()
                arg_value = arg[pos_equal + 1:].strip()
            elif not has_value and has_type:
                arg_name = arg[0:pos_colon].strip()
                arg_type = arg[pos_colon + 1:].strip()
            elif has_value and not has_type:
                arg_name = arg[0:pos_equal].strip()
                arg_value = arg[pos_equal + 1:].strip()
            else:
                arg_name = arg.strip()

            self.arg_name_list.append(arg_name)
            self.arg_type_list.append(arg_type)
            self.arg_value_list.append(arg_value)

    def split_args_text_to_list(self, args_text):
        """Split the text including multiple arguments to list.

        This function uses a comma to separate arguments and ignores a comma in
        brackets ans quotes.
        """
        args_list = []
        idx_find_start = 0
        idx_arg_start = 0

        try:
            pos_quote = self._find_quote_position(args_text)
            pos_round = self._find_bracket_position(args_text, '(', ')',
                                                    pos_quote)
            pos_curly = self._find_bracket_position(args_text, '{', '}',
                                                    pos_quote)
            pos_square = self._find_bracket_position(args_text, '[', ']',
                                                     pos_quote)
        except IndexError:
            return None

        while 1:
            pos_comma = args_text.find(',', idx_find_start)

            if pos_comma == -1:
                break

            idx_find_start = pos_comma + 1

            if self.is_char_in_pairs(pos_comma, pos_round) or \
               self.is_char_in_pairs(pos_comma, pos_curly) or \
               self.is_char_in_pairs(pos_comma, pos_square) or \
               self.is_char_in_pairs(pos_comma, pos_quote):
                continue

            args_list.append(args_text[idx_arg_start:pos_comma])
            idx_arg_start = pos_comma + 1

        if idx_arg_start < len(args_text):
            args_list.append(args_text[idx_arg_start:])

        return args_list

    def parse_def(self, text):
        """Parse the function definition text."""
        self.__init__()

        if not is_start_of_function(text):
            return

        self.func_indent = get_indent(text)

        text = text.strip()
        text = text.replace('\r\n', '')
        text = text.replace('\n', '')

        return_type_re = re.search(r'->[ ]*([a-zA-Z0-9_,()\[\] ]*):$', text)
        if return_type_re:
            self.return_type = return_type_re.group(1)
            text_end = text.rfind(return_type_re.group(0))
        else:
            self.return_type = None
            text_end = len(text)

        pos_args_start = text.find('(') + 1
        pos_args_end = text.rfind(')', pos_args_start, text_end)

        self.args_text = text[pos_args_start:pos_args_end]

        args_list = self.split_args_text_to_list(self.args_text)
        if args_list is not None:
            self.has_info = True
            self.split_arg_to_name_type_value(args_list)
