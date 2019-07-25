# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Generate Docstring."""

# Standard library imports
import re
from collections import OrderedDict

# Third party imports
from qtpy.QtGui import QTextCursor
from qtpy.QtCore import Qt
from qtpy.QtWidgets import QMenu

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

    ret = re.match(r'(\s*)', text)
    if ret:
        indent = ret.group(1)

    return indent


class DocstringWriterExtension(object):
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
            func_def, __ = result
            func_info = FunctionInfo()
            func_info.parse_def(func_def)

            if func_info.has_info:
                func_body = self.get_function_body(func_info.func_indent)
                if func_body:
                    func_info.parse_body(func_body)

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
            numpy_doc += '\n{}Parameters'.format(indent1)
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
                arg_text += ' The default is {}.'.format(arg_value)

            arg_text += '\n'

        numpy_doc += arg_text

        if func_info.raise_list:
            numpy_doc += '\n{}Raises'.format(indent1)
            numpy_doc += '\n{}------'.format(indent1)
            for raise_type in func_info.raise_list:
                numpy_doc += '\n{}{}'.format(indent1, raise_type)
                numpy_doc += '\n{}DESCRIPTION.'.format(indent2)
            numpy_doc += '\n'

        numpy_doc += '\n'
        if func_info.has_yield:
            header = '{0}Yields\n{0}------\n'.format(indent1)
        else:
            header = '{0}Returns\n{0}-------\n'.format(indent1)

        return_type_annotated = func_info.return_type_annotated
        if return_type_annotated:
            return_section = '{}{}{}'.format(header, indent1,
                                             return_type_annotated)
            return_section += '\n{}DESCRIPTION.'.format(indent2)
        else:
            return_element_type = indent1 + '{return_type}\n' + indent2 + \
                'DESCRIPTION.'
            placeholder = return_element_type.format(return_type='TYPE')
            return_element_name = indent1 + '{return_name} : ' + \
                placeholder.lstrip()

            try:
                return_section = self._generate_docstring_return_section(
                    func_info.return_value_in_body, header,
                    return_element_name, return_element_type, placeholder,
                    indent1)
            except (ValueError, IndexError):
                return_section = '{}{}None.'.format(header, indent1)

        numpy_doc += return_section
        numpy_doc += '\n\n{}{}'.format(indent1, self.quote3)

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

        if func_info.raise_list:
            google_doc += '\n{0}Raises:'.format(indent1)
            for raise_type in func_info.raise_list:
                google_doc += '\n{}{}'.format(indent2, raise_type)
                google_doc += ': DESCRIPTION.'
            google_doc += '\n'

        google_doc += '\n'
        if func_info.has_yield:
            header = '{}Yields:\n'.format(indent1)
        else:
            header = '{}Returns:\n'.format(indent1)

        return_type_annotated = func_info.return_type_annotated
        if return_type_annotated:
            return_section = '{}{}{}: DESCRIPTION.'.format(
                header, indent2, return_type_annotated)
        else:
            return_element_type = indent2 + '{return_type}: DESCRIPTION.'
            placeholder = return_element_type.format(return_type='TYPE')
            return_element_name = indent2 + '{return_name} ' + \
                '(TYPE): DESCRIPTION.'

            try:
                return_section = self._generate_docstring_return_section(
                    func_info.return_value_in_body, header,
                    return_element_name, return_element_type, placeholder,
                    indent2)
            except (ValueError, IndexError):
                return_section = '{}{}None.'.format(header, indent2)

        google_doc += return_section
        google_doc += '\n\n{}{}'.format(indent1, self.quote3)

        return google_doc

    @staticmethod
    def find_top_level_bracket_locations(string_toparse):
        """Get the locations of top-level brackets in a string."""
        bracket_stack = []
        replace_args_list = []
        bracket_type = None
        literal_type = ''
        brackets = {'(': ')', '[': ']', '{': '}'}
        for idx, character in enumerate(string_toparse):
            if (not bracket_stack and character in brackets.keys()
                    or character == bracket_type):
                bracket_stack.append(idx)
                bracket_type = character
            elif bracket_type and character == brackets[bracket_type]:
                begin_idx = bracket_stack.pop()
                if not bracket_stack:
                    if not literal_type:
                        if bracket_type == '(':
                            literal_type = '(None)'
                        elif bracket_type == '[':
                            literal_type = '[list]'
                        elif bracket_type == '{':
                            if idx - begin_idx <= 1:
                                literal_type = '{dict}'
                            else:
                                literal_type = '{set}'
                    replace_args_list.append(
                        (string_toparse[begin_idx:idx + 1],
                         literal_type, 1))
                    bracket_type = None
                    literal_type = ''
            elif len(bracket_stack) == 1:
                if bracket_type == '(' and character == ',':
                    literal_type = '(tuple)'
                elif bracket_type == '{' and character == ':':
                    literal_type = '{dict}'
                elif bracket_type == '(' and character == ':':
                    literal_type = '[slice]'

        if bracket_stack:
            raise IndexError('Bracket mismatch')
        for replace_args in replace_args_list:
            string_toparse = string_toparse.replace(*replace_args)
        return string_toparse

    @staticmethod
    def parse_return_elements(return_vals_group, return_element_name,
                              return_element_type, placeholder):
        """Return the appropriate text for a group of return elements."""
        all_eq = (return_vals_group.count(return_vals_group[0])
                  == len(return_vals_group))
        if all([{'[list]', '(tuple)', '{dict}', '{set}'}.issuperset(
                return_vals_group)]) and all_eq:
            return return_element_type.format(
                return_type=return_vals_group[0][1:-1])
        # Output placeholder if special Python chars present in name
        py_chars = {' ', '+', '-', '*', '/', '%', '@', '<', '>', '&', '|', '^',
                    '~', '=', ',', ':', ';', '#', '(', '[', '{', '}', ']',
                    ')', }
        if any([any([py_char in return_val for py_char in py_chars])
                for return_val in return_vals_group]):
            return placeholder
        # Output str type and no name if only string literals
        if all(['"' in return_val or '\'' in return_val
                for return_val in return_vals_group]):
            return return_element_type.format(return_type='str')
        # Output bool type and no name if only bool literals
        if {'True', 'False'}.issuperset(return_vals_group):
            return return_element_type.format(return_type='bool')
        # Output numeric types and no name if only numeric literals
        try:
            [float(return_val) for return_val in return_vals_group]
            num_not_int = 0
            for return_val in return_vals_group:
                try:
                    int(return_val)
                except ValueError:  # If not an integer (EAFP)
                    num_not_int = num_not_int + 1
            if num_not_int == 0:
                return return_element_type.format(return_type='int')
            elif num_not_int == len(return_vals_group):
                return return_element_type.format(return_type='float')
            else:
                return return_element_type.format(return_type='numeric')
        except ValueError:  # Not a numeric if float conversion didn't work
            pass
        # If names are not equal, don't contain "." or are a builtin
        if ({'self', 'cls', 'None'}.isdisjoint(return_vals_group) and all_eq
                and all(['.' not in return_val
                         for return_val in return_vals_group])):
            return return_element_name.format(return_name=return_vals_group[0])
        return placeholder

    def _generate_docstring_return_section(self, return_vals, header,
                                           return_element_name,
                                           return_element_type,
                                           placeholder, indent):
        """Generate the Returns section of a function/method docstring."""
        # If all return values are None, return none
        non_none_vals = [return_val for return_val in return_vals
                         if return_val and return_val != 'None']
        if not non_none_vals:
            return header + indent + 'None.'

        # Get only values with matching brackets that can be cleaned up
        non_none_vals = [return_val.strip(' ()\t\n').rstrip(',')
                         for return_val in non_none_vals]
        non_none_vals = [re.sub('([\"\'])(?:(?=(\\\\?))\\2.)*?\\1',
                                '"string"', return_val)
                         for return_val in non_none_vals]
        unambiguous_vals = []
        for return_val in non_none_vals:
            try:
                cleaned_val = self.find_top_level_bracket_locations(return_val)
            except IndexError:
                continue
            unambiguous_vals.append(cleaned_val)
        if not unambiguous_vals:
            return header + placeholder

        # If remaining are a mix of tuples and not, return single placeholder
        single_vals, tuple_vals = [], []
        for return_val in unambiguous_vals:
            (tuple_vals.append(return_val) if ',' in return_val
             else single_vals.append(return_val))
        if single_vals and tuple_vals:
            return header + placeholder

        # If return values are tuples of different length, return a placeholder
        if tuple_vals:
            num_elements = [return_val.count(',') + 1
                            for return_val in tuple_vals]
            if num_elements.count(num_elements[0]) != len(num_elements):
                return header + placeholder
            num_elements = num_elements[0]
        else:
            num_elements = 1

        # If all have the same len but some ambiguous return that placeholders
        if len(unambiguous_vals) != len(non_none_vals):
            return header + '\n'.join(
                [placeholder for __ in range(num_elements)])

        # Handle tuple (or single) values position by position
        return_vals_grouped = zip(*[
            [return_element.strip() for return_element in
             return_val.split(',')]
            for return_val in unambiguous_vals])
        return_elements_out = []
        for return_vals_group in return_vals_grouped:
            return_elements_out.append(
                self.parse_return_elements(return_vals_group,
                                           return_element_name,
                                           return_element_type,
                                           placeholder))

        return header + '\n'.join(return_elements_out)


class FunctionInfo(object):
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
        self.return_type_annotated = None
        self.return_value_in_body = []
        self.raise_list = None
        self.has_yield = False

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

        for idx, character in enumerate(text):
            if is_found_left_quote is False:
                if character == "'" or character == '"':
                    is_found_left_quote = True
                    quote = character
                    left_pos = idx
            else:
                if character == quote and text[idx - 1] != '\\':
                    pos[left_pos] = idx
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
        pos = {}
        pstack = []

        for idx, character in enumerate(text):
            if character == bracket_left and \
                    not self.is_char_in_pairs(idx, pos_quote):
                pstack.append(idx)
            elif character == bracket_right and \
                    not self.is_char_in_pairs(idx, pos_quote):
                if len(pstack) == 0:
                    raise IndexError(
                        "No matching closing parens at: " + str(idx))
                pos[pstack.pop()] = idx

        if len(pstack) > 0:
            raise IndexError(
                "No matching opening parens at: " + str(pstack.pop()))

        return pos

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

        while True:
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
            self.return_type_annotated = return_type_re.group(1)
            text_end = text.rfind(return_type_re.group(0))
        else:
            self.return_type_annotated = None
            text_end = len(text)

        pos_args_start = text.find('(') + 1
        pos_args_end = text.rfind(')', pos_args_start, text_end)

        self.args_text = text[pos_args_start:pos_args_end]

        args_list = self.split_args_text_to_list(self.args_text)
        if args_list is not None:
            self.has_info = True
            self.split_arg_to_name_type_value(args_list)

    def parse_body(self, text):
        """Parse the function body text."""
        re_raise = re.findall(r'[ \t]raise ([a-zA-Z0-9_]*)', text)
        if len(re_raise) > 0:
            self.raise_list = [x.strip() for x in re_raise]
            # remove duplicates from list while keeping it in the order
            # in python 2.7
            # stackoverflow.com/questions/7961363/removing-duplicates-in-lists
            self.raise_list = list(OrderedDict.fromkeys(self.raise_list))

        re_yield = re.search(r'[ \t]yield ', text)
        if re_yield:
            self.has_yield = True

        # get return value
        pattern_return = r'return |yield '
        line_list = text.split('\n')
        is_found_return = False
        line_return_tmp = ''

        for line in line_list:
            line = line.strip()

            if is_found_return is False:
                if re.match(pattern_return, line):
                    is_found_return = True

            if is_found_return:
                line_return_tmp += line
                # check the integrity of line
                try:
                    pos_quote = self._find_quote_position(line_return_tmp)

                    if line_return_tmp[-1] == '\\':
                        line_return_tmp = line_return_tmp[:-1]
                        continue

                    self._find_bracket_position(line_return_tmp, '(', ')',
                                                pos_quote)
                    self._find_bracket_position(line_return_tmp, '{', '}',
                                                pos_quote)
                    self._find_bracket_position(line_return_tmp, '[', ']',
                                                pos_quote)
                except IndexError:
                    continue

                return_value = re.sub(pattern_return, '', line_return_tmp)
                self.return_value_in_body.append(return_value)

                is_found_return = False
                line_return_tmp = ''


class QMenuOnlyForEnter(QMenu):
    """The class executes the selected action when "enter key" is input.

    If a input of keyboard is not the "enter key", the menu is closed and
    the input is inserted to code editor.
    """

    def __init__(self, code_editor):
        """Init QMenu."""
        super(QMenuOnlyForEnter, self).__init__(code_editor)
        self.code_editor = code_editor

    def keyPressEvent(self, event):
        """Close the instance if key is not enter key."""
        key = event.key()
        if key not in (Qt.Key_Enter, Qt.Key_Return):
            self.code_editor.keyPressEvent(event)
            self.close()
        else:
            super(QMenuOnlyForEnter, self).keyPressEvent(event)
