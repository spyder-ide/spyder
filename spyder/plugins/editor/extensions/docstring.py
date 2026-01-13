# -----------------------------------------------------------------------------
# Copyright (c) 2019- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Automatically generate function docstrings."""

# Standard library imports
import re

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.api.widgets.menus import SpyderMenu
from spyder.config.manager import CONF


# Constants

_MAX_CHARACTERS_PER_LINE = 120

MAX_SIG_LINES = 1000
"""Maximum number of lines scanned for function signatures."""

MAX_SIG_CHARS = MAX_SIG_LINES * _MAX_CHARACTERS_PER_LINE
"""Maximum number of characters in a function signature."""

MAX_RETURN_TYPE_LINES = 100
"""Maximum number of lines for the return type annotation."""

MAX_RETURN_TYPE_CHARS = MAX_RETURN_TYPE_LINES * _MAX_CHARACTERS_PER_LINE
"""Maximum number of characters in the return type annotation."""


def is_start_of_function(text):
    """Return True if text is the beginning of the function definition."""
    if isinstance(text, str):
        function_prefix = ['def ', 'async def ']
        text = text.lstrip()

        for prefix in function_prefix:
            if text.startswith(prefix):
                return True

    return False


def get_indent(text):
    """Get indent of text.

    Originally adapted from https://stackoverflow.com/q/2268532
    """
    indent = ''

    ret = re.match(r'(\s*)', text)
    if ret:
        indent = ret.group(1)

    return indent


def is_in_scope_forward(text):
    """Check if the next empty line could be part of the definition."""
    text = text.replace(r"\"", "").replace(r"\'", "")
    scopes = ["'''", '"""', "'", '"']
    indices = [MAX_SIG_CHARS] * 4
    for i in range(len(scopes)):
        if scopes[i] in text:
            indices[i] = text.index(scopes[i])
    if min(indices) == MAX_SIG_CHARS:
        return (text.count(")") != text.count("(") or
                text.count("]") != text.count("[") or
                text.count("}") != text.count("{"))

    s = scopes[indices.index(min(indices))]
    p = indices[indices.index(min(indices))]
    ls = len(s)
    if s in text[p + ls:]:
        text = text[:p] + text[p + ls:][text[p + ls:].index(s) + ls:]
        return is_in_scope_forward(text)
    if ls == 3:
        text = text[:p]
        return (text.count(")") != text.count("(") or
                text.count("]") != text.count("[") or
                text.count("}") != text.count("{"))

    return False


def is_tuple_brackets(text):
    """Check if the return type is a tuple."""
    scopes = ["(", "[", "{"]
    complements = [")", "]", "}"]
    indices = [MAX_RETURN_TYPE_CHARS] * 4
    for i in range(len(scopes)):
        if scopes[i] in text:
            indices[i] = text.index(scopes[i])
    if min(indices) == MAX_RETURN_TYPE_CHARS:
        return "," in text
    s = complements[indices.index(min(indices))]
    p = indices[indices.index(min(indices))]
    if s in text[p + 1:]:
        text = text[:p] + text[p + 1:][text[p + 1:].index(s) + 1:]
        return is_tuple_brackets(text)
    return False


def is_tuple_strings(text):
    """Check if the return type is a string."""
    text = text.replace(r"\"", "").replace(r"\'", "")
    scopes = ["'''", '"""', "'", '"']
    indices = [MAX_RETURN_TYPE_CHARS] * 4
    for i in range(len(scopes)):
        if scopes[i] in text:
            indices[i] = text.index(scopes[i])
    if min(indices) == MAX_RETURN_TYPE_CHARS:
        return is_tuple_brackets(text)
    s = scopes[indices.index(min(indices))]
    p = indices[indices.index(min(indices))]
    ls = len(s)
    if s in text[p + ls:]:
        text = text[:p] + text[p + ls:][text[p + ls:].index(s) + ls:]
        return is_tuple_strings(text)
    return False


def is_in_scope_backward(text):
    """Check if the next empty line could be part of the definition."""
    return is_in_scope_forward(
        text.replace(r"\"", "").replace(r"\'", "")[::-1])


def remove_comments(text):
    """
    Remove code comments from text.

    Ignores hash symbols (``#``) inside quotes, which can be part of
    function arguments.
    """
    return re.sub(pattern=r"""(?<!['"])(#.*)""", repl="", string=text)


def collapse_line_breaks_annotation(text):
    """Collapse a type annotation into a single line."""
    lines = re.sub("\s{2,}", "\n", text.strip()).split("\n")
    collapsed_lines = []
    for line in lines:
        line = line.strip()
        if not line:
            continue

        if not collapsed_lines:
            collapsed_lines.append(line)
            continue

        prev = collapsed_lines[-1][-1]
        this = line[0]
        if this in {")", "]", "}"}:
            collapsed_lines[-1] = collapsed_lines[-1].rstrip(",")
            collapsed_lines.append(line)
        elif prev in {"(", "[", "{"}:
            collapsed_lines.append(line)
        else:
            collapsed_lines.append(f" {line}")

    return "".join(collapsed_lines)


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

    def is_end_of_function_definition(self, text, line_number):
        """Return True if text is the end of the function definition."""
        text_without_whitespace = "".join(text.split())
        if (
            text_without_whitespace.endswith("):") or
            text_without_whitespace.endswith("]:") or
            (text_without_whitespace.endswith(":") and
             "->" in text_without_whitespace)
        ):
            return True

        if text_without_whitespace.endswith(":") and line_number > 1:
            complete_text = text_without_whitespace
            document = self.code_editor.document()
            cursor = QTextCursor(
                document.findBlockByNumber(line_number - 2))  # previous line

            for i in range(line_number - 2, -1, -1):
                txt = "".join(str(cursor.block().text()).split())
                if txt.endswith("\\") or is_in_scope_backward(complete_text):
                    if txt.endswith("\\"):
                        txt = txt[:-1]
                    complete_text = txt + complete_text
                else:
                    break
                if i:
                    cursor.movePosition(QTextCursor.PreviousBlock)

            if is_start_of_function(complete_text):
                return (
                    complete_text.endswith("):") or
                    complete_text.endswith("]:") or
                    (complete_text.endswith(":") and
                     "->" in complete_text)
                )
            return False

        return False

    def get_function_definition_from_first_line(self):
        """Get func def when the cursor is located on the first def line."""
        document = self.code_editor.document()
        cursor = QTextCursor(
            document.findBlockByNumber(self.line_number_cursor - 1))

        func_text = ''
        func_indent = ''

        is_first_line = True
        line_number = cursor.blockNumber() + 1

        number_of_lines = self.code_editor.blockCount()
        remain_lines = number_of_lines - line_number + 1
        number_of_lines_of_function = 0

        for __ in range(min(remain_lines, MAX_SIG_LINES)):
            cur_text = str(cursor.block().text()).rstrip()
            cur_text = remove_comments(cur_text)
            strip_text = cur_text.strip()

            if is_first_line:
                if not is_start_of_function(cur_text):
                    return None

                func_indent = get_indent(cur_text)
                is_first_line = False
            elif not strip_text:  # Skip empty lines
                pass
            else:
                cur_indent = get_indent(cur_text)
                if cur_indent < func_indent:  # Outside the function scope
                    return None
                if cur_indent == func_indent and not re.search(
                    r'^([\])]\s*:|\)\s*->.*[\[(:])$', strip_text
                ):  # Black-style function last line
                    return None
                if is_start_of_function(cur_text):
                    return None
                if not is_in_scope_forward(func_text):
                    return None

            if len(cur_text) > 0 and cur_text[-1] == '\\':
                cur_text = cur_text[:-1]

            func_text += cur_text
            number_of_lines_of_function += 1

            if self.is_end_of_function_definition(
                    cur_text, line_number + number_of_lines_of_function - 1):
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

        for __ in range(min(line_number, MAX_SIG_LINES)):
            if cursor.block().blockNumber() == 0:
                return None

            cursor.movePosition(QTextCursor.PreviousBlock)
            prev_text = str(cursor.block().text()).rstrip()
            prev_text = remove_comments(prev_text)

            if is_first_line:
                if not self.is_end_of_function_definition(
                        prev_text, line_number - 1):
                    return None
                is_first_line = False
            elif self.is_end_of_function_definition(
                    prev_text, line_number - number_of_lines_of_function - 1):
                return None

            if len(prev_text) > 0 and prev_text[-1] == '\\':
                prev_text = prev_text[:-1]

            func_text = prev_text + func_text

            number_of_lines_of_function += 1
            if is_start_of_function(prev_text):
                return func_text, number_of_lines_of_function

        return None

    def get_function_docstring(self, func_indent, delete_existing=True):
        """Get the function's existing docstring content."""
        cursor = self.code_editor.textCursor()
        line_number = cursor.blockNumber()
        number_of_lines = self.code_editor.blockCount()
        docstring_list = []
        docstring_quotes = None
        last_line = False

        cursor.clearSelection()
        for __ in range(number_of_lines - line_number):
            cursor.movePosition(QTextCursor.NextBlock, QTextCursor.KeepAnchor)
            if last_line:
                break

            text = str(cursor.block().text())
            text_indent = get_indent(text)

            # Stop if outside the function scope
            if text.strip() and len(text_indent) <= len(func_indent):
                break

            # Look for the start of the docstring
            if not docstring_quotes:
                if not remove_comments(text).strip():
                    continue
                elif '"""' in text:
                    docstring_quotes = '"""'
                elif "'''" in text:
                    docstring_quotes = "'''"
                else:  # Found function body, no docstring
                    return None

                # One line docstring
                if text.count(docstring_quotes) > 1:
                    last_line = True
                cursor.clearSelection()
            # Look for the end
            elif docstring_quotes in text:
                last_line = True

            docstring_list.append(text)
            # So the final line is selected if docstring ends at the EOF
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)

        # If docstring was found and terminated
        if last_line:
            if delete_existing:
                cursor.removeSelectedText()
            cursor.clearSelection()
            return '\n'.join(docstring_list)
        else:
            cursor.clearSelection()
            return None

    def get_function_body(self, func_indent):
        """Get the function body text."""
        cursor = self.code_editor.textCursor()
        line_number = cursor.blockNumber()
        number_of_lines = self.code_editor.blockCount()
        body_list = []

        for __ in range(number_of_lines - line_number):
            text = str(cursor.block().text())
            text_indent = get_indent(text)

            # Stop if outside the function scope
            if text.strip() and len(text_indent) <= len(func_indent):
                break

            body_list.append(text)

            cursor.movePosition(QTextCursor.NextBlock)

        return '\n'.join(body_list)

    def write_docstring(self):
        """Write docstring to editor."""
        line_to_cursor = self.code_editor.get_text('sol', 'cursor')
        if not self.is_beginning_triple_quotes(line_to_cursor):
            return False

        cursor = self.code_editor.textCursor()
        prev_pos = cursor.position()

        quote = line_to_cursor[-1]
        docstring_type = CONF.get('editor', 'docstring_type')
        docstring = self._generate_docstring(docstring_type, quote)

        if not docstring:
            return False

        self.code_editor.insert_text(docstring)

        # Set cursor to first line of summary
        cursor = self.code_editor.textCursor()
        cursor.setPosition(prev_pos, QTextCursor.KeepAnchor)
        cursor.movePosition(QTextCursor.NextBlock)
        cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.KeepAnchor)
        cursor.clearSelection()
        self.code_editor.setTextCursor(cursor)

        return True

    def write_docstring_at_first_line_of_function(self):
        """Write docstring to editor at mouse position."""
        func_def_info = self.get_function_definition_from_first_line()
        editor = self.code_editor

        if func_def_info:
            func_text, number_of_line_func = func_def_info
            func_last_line_number = (
                self.line_number_cursor + number_of_line_func - 1
            )

            cursor = editor.textCursor()
            cursor_line_number = cursor.blockNumber() + 1
            offset = func_last_line_number - cursor_line_number
            if offset > 0:
                for __ in range(offset):
                    cursor.movePosition(QTextCursor.NextBlock)
            else:
                for __ in range(abs(offset)):
                    cursor.movePosition(QTextCursor.PreviousBlock)
            cursor.movePosition(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
            editor.setTextCursor(cursor)

            body_indent = get_indent(func_text) + editor.indent_chars
            editor.insert_text(f'\n{body_indent}"""')
            self.write_docstring()

    def write_docstring_for_shortcut(self):
        """Write docstring to editor by shortcut of code editor."""
        # cursor placed below function definition
        func_def_info = self.get_function_definition_from_below_last_line()
        if func_def_info is not None:
            __, number_of_lines_of_function = func_def_info
            cursor = self.code_editor.textCursor()
            for __ in range(number_of_lines_of_function):
                cursor.movePosition(QTextCursor.PreviousBlock)

            self.code_editor.setTextCursor(cursor)

        cursor = self.code_editor.textCursor()
        self.line_number_cursor = cursor.blockNumber() + 1

        self.write_docstring_at_first_line_of_function()

    def _generate_docstring(self, doc_type, quote):
        """Generate a function/method docstring of the specified format."""
        docstring = None

        self.quote3 = quote * 3
        if quote == '"':
            self.quote3_other = "'''"
        else:
            self.quote3_other = '"""'

        func_def_info = self.get_function_definition_from_below_last_line()

        if not func_def_info:
            return None

        func_def, __ = func_def_info
        func_info = FunctionInfo()
        func_info.parse_def(func_def)

        if not func_info.has_info:
            return None

        func_docstring = self.get_function_docstring(
            func_info.func_indent
        )
        if func_docstring:
            func_info.parse_docstring(func_docstring)

        func_body = self.get_function_body(func_info.func_indent)
        if func_body:
            func_info.parse_body(func_body)

        if doc_type == "Numpydoc":
            docstring = self._generate_numpy_doc(func_info)
        elif doc_type == "Googledoc":
            docstring = self._generate_google_doc(func_info)
        elif doc_type == "Sphinxdoc":
            docstring = self._generate_sphinx_doc(func_info)
        else:
            raise ValueError(f"Unknown docstring format {doc_type!r}")

        return docstring

    def _generate_numpy_doc(self, func_info):
        """Generate a NumPy format docstring."""
        numpy_doc = ''

        indent1 = func_info.func_indent + self.code_editor.indent_chars
        indent2 = self.code_editor.indent_chars

        summary = func_info.docstring_text or 'SUMMARY.'
        numpy_doc += '\n{}{}\n'.format(indent1, summary)

        for section_fn in [
            self._generate_numpy_param_section,
            self._generate_numpy_return_section,
            self._generate_numpy_raise_section,
        ]:
            doc_section = section_fn(func_info, indent1, indent2)
            if doc_section:
                numpy_doc += f"\n{indent1}{doc_section}\n"

        numpy_doc = numpy_doc.rstrip()
        numpy_doc += '\n{}{}'.format(indent1, self.quote3)

        return numpy_doc

    def _generate_numpy_param_section(self, func_info, indent1, indent2):
        """Generate the Parameters section for a NumPy format docstring."""
        arg_names = func_info.arg_name_list.copy()
        arg_types = func_info.arg_type_list.copy()
        arg_values = func_info.arg_value_list.copy()

        if arg_names and arg_names[0] in ('self', 'cls'):
            del arg_names[0]
            del arg_types[0]
            del arg_values[0]

        if not arg_names:
            return None

        heading = 'Parameters'
        header_lines = [heading, '-' * len(heading)]

        body_lines = []
        for arg_name, arg_type, arg_value in zip(
            arg_names, arg_types, arg_values
        ):
            param_type = arg_type or 'TYPE'
            optional = ', optional' if arg_value else ''
            type_line = f'{arg_name} : {param_type}{optional}'

            default = ''
            if arg_value:
                arg_value = arg_value.replace(self.quote3, self.quote3_other)
                default = f' The default is {arg_value}.'
            desc_line = f'{indent2}DESCRIPTION.{default}'

            body_lines += [type_line, desc_line]

        return f'\n{indent1}'.join(header_lines + body_lines)

    def _generate_numpy_return_section(self, func_info, indent1, indent2):
        """Generate the Returns section for a NumPy format docstring."""
        heading = 'Yields' if func_info.has_yield else 'Returns'
        header = f'{heading}\n{indent1}{"-" * len(heading)}\n'
        indent3 = indent1 + indent2

        return_types = func_info.return_type_annotated
        if return_types:
            if len(return_types) > 1:
                return_type_annotated = (
                    f'\n{indent3}DESCRIPTION.\n{indent1}'.join(return_types)
                )
            else:
                return_type_annotated = return_types[0]
            return_section = '{}{}{}'.format(
                header, indent1, return_type_annotated
            )
            if return_type_annotated != 'None':
                return_section += '\n{}DESCRIPTION.'.format(indent3)
            return return_section

        return_element_type = (
            indent1 + '{return_type}\n' + indent3 + 'DESCRIPTION.'
        )
        placeholder = return_element_type.format(return_type='TYPE')
        return_values = [
            rv for rvs in func_info.return_value_in_body
            for rv in rvs.split(",")
        ]
        if len(return_values) == 1:
            # numpydoc RT02, only include type and not name if it's a single return value
            return_element_name = indent1 + placeholder.lstrip()
        else:
            return_element_name = (
                indent1 + '{return_name} : ' + placeholder.lstrip()
            )

        try:
            return_section = self._generate_docstring_return_section(
                return_vals=func_info.return_value_in_body,
                header=header,
                return_element_name=return_element_name,
                return_element_type=return_element_type,
                placeholder=placeholder,
                indent=indent1,
                expand_tuple=True,
            )
        except (ValueError, IndexError):
            return_section = '{}{}None'.format(header, indent1)

        return return_section

    @staticmethod
    def _generate_numpy_raise_section(func_info, indent1, indent2):
        """Generate the Raises section for a NumPy format docstring."""
        if not func_info.raise_list:
            return None

        heading = 'Raises'
        header_lines = [heading, '-' * len(heading)]
        body_lines = [
            [f'{raise_type}', f'{indent2}DESCRIPTION.']
            for raise_type in func_info.raise_list
        ]

        return f'\n{indent1}'.join(sum(body_lines, header_lines))

    def _generate_google_doc(self, func_info):
        """Generate a Google format docstring."""
        google_doc = ''

        indent1 = func_info.func_indent + self.code_editor.indent_chars
        indent2 = self.code_editor.indent_chars

        summary = func_info.docstring_text or 'SUMMARY.'
        google_doc += '{}\n'.format(summary)

        for section_fn in [
            self._generate_google_param_section,
            self._generate_google_return_section,
            self._generate_google_raise_section,
        ]:
            doc_section = section_fn(func_info, indent1, indent2)
            if doc_section:
                google_doc += f"\n{indent1}{doc_section}\n"

        google_doc = google_doc.rstrip()
        google_doc += '\n{}{}'.format(indent1, self.quote3)

        return google_doc

    def _generate_google_param_section(self, func_info, indent1, indent2):
        """Generate the Args section for a Google format docstring."""
        arg_names = func_info.arg_name_list.copy()
        arg_types = func_info.arg_type_list.copy()
        arg_values = func_info.arg_value_list.copy()

        if arg_names and arg_names[0] in ('self', 'cls'):
            del arg_names[0]
            del arg_types[0]
            del arg_values[0]

        if not arg_names:
            return None

        header_lines = ['Args:']

        body_lines = []
        for arg_name, arg_type, arg_value in zip(
            arg_names, arg_types, arg_values
        ):
            param_type = arg_type or 'TYPE'
            optional = ', optional' if arg_value else ''
            type_chunk = f'{indent2}{arg_name} ({param_type}{optional})'

            default = ''
            if arg_value:
                arg_value = arg_value.replace(self.quote3, self.quote3_other)
                default = f' Defaults to {arg_value}.'
            desc_chunk = f'DESCRIPTION.{default}'

            param_line = f'{type_chunk}: {desc_chunk}'
            body_lines.append(param_line)

        return f'\n{indent1}'.join(header_lines + body_lines)

    def _generate_google_return_section(self, func_info, indent1, indent2):
        """Generate the Returns section for a Google format docstring."""
        heading = 'Yields' if func_info.has_yield else 'Returns'
        header = f'{heading}:\n'
        indent3 = indent1 + indent2

        return_types = func_info.return_type_annotated
        if return_types:
            if len(return_types) > 1:
                tuple_values = ', '.join(return_types)
                return_type_annotated = f'tuple[{tuple_values}]'
            else:
                return_type_annotated = return_types[0]
            return_section = '{}{}{}'.format(
                header, indent3, return_type_annotated
            )
            if return_type_annotated != 'None':
                return_section += ': DESCRIPTION.'
            return return_section

        return_element_type = indent3 + '{return_type}: DESCRIPTION.'
        placeholder = return_element_type.format(return_type='TYPE')

        try:
            return_section = self._generate_docstring_return_section(
                return_vals=func_info.return_value_in_body,
                header=header,
                return_element_name=placeholder,
                return_element_type=return_element_type,
                placeholder=placeholder,
                indent=indent3,
                expand_tuple=False,
            )
        except (ValueError, IndexError):
            return_section = '{}{}None'.format(header, indent3)

        return return_section

    @staticmethod
    def _generate_google_raise_section(func_info, indent1, indent2):
        """Generate the Raises section for a Google format docstring."""
        if not func_info.raise_list:
            return None

        header_lines = ['Raises:']
        body_lines = [
            f'{indent2}{raise_type}: DESCRIPTION.'
            for raise_type in func_info.raise_list
        ]

        return f'\n{indent1}'.join(header_lines + body_lines)

    def _generate_sphinx_doc(self, func_info):
        """Generate a Sphinx format docstring."""
        sphinx_doc = ''
        indent1 = func_info.func_indent + self.code_editor.indent_chars

        summary = func_info.docstring_text or 'SUMMARY.'
        sphinx_doc += '{}\n'.format(summary)

        for section_fn in [
            self._generate_sphinx_param_section,
            self._generate_sphinx_return_section,
            self._generate_sphinx_raise_section,
        ]:
            doc_section = section_fn(func_info, indent1)
            if doc_section:
                sphinx_doc += f"\n{indent1}{doc_section}\n"

        sphinx_doc = sphinx_doc.rstrip()
        sphinx_doc += '\n{}{}'.format(indent1, self.quote3)

        return sphinx_doc

    def _generate_sphinx_param_section(self, func_info, indent1):
        """Generate the :param: sections for a Sphinx format docstring."""
        arg_names = func_info.arg_name_list.copy()
        arg_types = func_info.arg_type_list.copy()
        arg_values = func_info.arg_value_list.copy()

        if arg_names and arg_names[0] in ('self', 'cls'):
            del arg_names[0]
            del arg_types[0]
            del arg_values[0]

        if not arg_names:
            return None

        param_lines = []
        for arg_name, arg_type, arg_value in zip(
            arg_names, arg_types, arg_values
        ):
            param_desc = f':param {arg_name}: DESCRIPTION'

            if arg_value:
                arg_value = arg_value.replace(self.quote3, self.quote3_other)
                param_desc += f', defaults to {arg_value}'

            param_type = f':type {arg_name}: '

            if arg_type:
                param_type += f'{arg_type}'
            else:
                param_type += 'TYPE'

            param_lines += [param_desc, param_type]

        return f'\n{indent1}'.join(param_lines)

    def _generate_sphinx_return_section(self, func_info, indent1):
        """Generate the :return: section for a Sphinx format docstring."""
        header = ':rtype: '
        return_desc = f'{indent1}:returns: DESCRIPTION'

        return_types = func_info.return_type_annotated
        if return_types:
            if len(return_types) > 1:
                tuple_values = ', '.join(return_types)
                return_type_annotated = f'tuple[{tuple_values}]'
            else:
                return_type_annotated = return_types[0]
            return_section = f'{header}{return_type_annotated}'
            if return_type_annotated != 'None':
                return_section += f'\n{return_desc}'
            return return_section

        return_element_type = f'{{return_type}}\n{return_desc}'
        placeholder = return_element_type.format(return_type='TYPE')

        try:
            return_section = self._generate_docstring_return_section(
                return_vals=func_info.return_value_in_body,
                header=header,
                return_element_name=placeholder,
                return_element_type=return_element_type,
                placeholder=placeholder,
                indent="",
                expand_tuple=False,
            )
        except (ValueError, IndexError):
            return_section = f'{header}None'

        return return_section

    @staticmethod
    def _generate_sphinx_raise_section(func_info, indent1):
        """Generate the :raises: sections for a Sphinx format docstring."""
        if not func_info.raise_list:
            return None

        raise_lines = [
            f':raises {raise_type}: DESCRIPTION'
            for raise_type in func_info.raise_list
        ]

        return f'\n{indent1}'.join(raise_lines)

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
    def parse_return_elements(return_vals_group):
        """Return the appropriate text for a group of return elements."""
        all_eq = return_vals_group.count(return_vals_group[0]) == len(
            return_vals_group
        )
        builtin_collections = {"[list]", "(tuple)", "{dict}", "{set}"}
        if builtin_collections.issuperset(return_vals_group) and all_eq:
            return return_vals_group[0][1:-1], None

        # Output placeholder if special Python chars present in name
        py_chars = {' ', '+', '-', '*', '/', '%', '@', '<', '>', '&', '|', '^',
                    '~', '=', ',', ':', ';', '#', '(', '[', '{', '}', ']',
                    ')', }
        if any(
            any(py_char in return_val for py_char in py_chars)
            for return_val in return_vals_group
        ):
            return None, None

        # Output str type and no name if only string literals
        if all(
            '"' in return_val or "'" in return_val
            for return_val in return_vals_group
        ):
            return 'str', None

        # Output bool type and no name if only bool literals
        if {'True', 'False'}.issuperset(return_vals_group):
            return 'bool', None

        # Output numeric types and no name if only numeric literals
        try:
            [float(return_val) for return_val in return_vals_group]
            num_not_int = 0
            for return_val in return_vals_group:
                try:
                    int(return_val)
                except ValueError:  # If not an integer (EAFP)
                    num_not_int += 1
            if num_not_int == 0:
                return 'int', None
            if num_not_int == len(return_vals_group):
                return 'float', None
            return 'numeric', None

        except ValueError:  # Not a numeric if float conversion didn't work
            pass

        # If names are not equal, don't contain "." or are a builtin
        if (
            {"self", "cls", "None"}.isdisjoint(return_vals_group)
            and all_eq
            and all("." not in return_val for return_val in return_vals_group)
        ):

            return None, return_vals_group[0]
        return None, None

    def _generate_docstring_return_section(
        self,
        return_vals,
        header,
        return_element_name,
        return_element_type,
        placeholder,
        indent,
        *,
        expand_tuple=True,
    ):
        """Generate the Returns section of a function/method docstring."""
        # If all return values are None, return None
        non_none_vals = [return_val for return_val in return_vals
                         if return_val and return_val != 'None']
        if not non_none_vals:
            return header + indent + 'None'

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
            if ',' in return_val:
                tuple_vals.append(return_val)
            else:
                single_vals.append(return_val)
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

        # If all have the same len but some ambiguous return placeholders
        if len(unambiguous_vals) != len(non_none_vals):
            if expand_tuple:
                return header + '\n'.join([placeholder] * len(num_elements))

            return_elements_out = ', '.join(['TYPE'] * len(num_elements))
            return header + return_element_type.format(
                return_type=f'tuple[{return_elements_out}]'
            )

        # Handle tuple (or single) values position by position
        return_vals_grouped = zip(*[
            [return_element.strip() for return_element in
             return_val.split(',')]
            for return_val in unambiguous_vals])
        return_vals_parsed = []
        for return_vals_group in return_vals_grouped:
            return_vals_parsed.append(
                self.parse_return_elements(return_vals_group)
            )

        # Represent a tuple as a single tuple return value
        if not expand_tuple:
            return_elements = [
                rtype if rtype is not None else 'TYPE'
                for rtype, __ in return_vals_parsed
            ]
            if len(return_elements) == 1:
                return_type = return_elements[0]
            else:
                return_type = 'tuple[{}]'.format(', '.join(return_elements))
            return header + return_element_type.format(return_type=return_type)

        # Represent a tuple as multiple return values
        return_elements = []
        for rtype, rname in return_vals_parsed:
            if rtype is not None:
                element = return_element_type.format(return_type=rtype)
            elif rname is not None:
                element = return_element_name.format(return_name=rname)
            else:
                element = placeholder
            return_elements.append(element)
        return header + '\n'.join(return_elements)


class FunctionInfo:
    """Parse function definition text."""

    RETURN_TYPE_REGEX = (
        r'->\s*((?:\s|[\"\'a-zA-Z0-9_,.()\[\]|])+)\s*\: *$'
    )
    RETURN_TUPLE_REGEX = r'^(?:typing\.)?[Tt]uple\[\s*((?:\s|.)+)\s*\]$'

    def __init__(self):
        self.has_info = False
        self.args_text = ''
        self.docstring_text = None
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
        """Return True if the character is in pairs of brackets or quotes."""
        for pos_left, pos_right in pairs.items():
            if pos_left < pos_char < pos_right:
                return True

        return False

    @staticmethod
    def _find_quote_position(text):
        """Return the start and end position of pairs of quotes."""
        pos = {}
        is_found_left_quote = False
        quote = None
        left_pos = None

        for idx, character in enumerate(text):
            if not is_found_left_quote:
                if character in {"'", '"'}:
                    is_found_left_quote = True
                    quote = character
                    left_pos = idx
            else:
                if character == quote and text[idx - 1] != '\\':
                    pos[left_pos] = idx
                    is_found_left_quote = False

        if is_found_left_quote:
            raise IndexError(f"No matching close quote at: {left_pos}")

        return pos

    def _find_bracket_position(
        self, text, bracket_left, bracket_right, pos_quote
    ):
        """Return the start and end position of pairs of brackets.

        Originally adapted from https://stackoverflow.com/q/29991917
        """
        pos = {}
        pstack = []

        for idx, character in enumerate(text):
            if character == bracket_left and \
                    not self.is_char_in_pairs(idx, pos_quote):
                pstack.append(idx)
            elif character == bracket_right and \
                    not self.is_char_in_pairs(idx, pos_quote):
                if not len(pstack):
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
        brackets and quotes.
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
            arg_text = args_text[idx_arg_start:]
            # Skip arg if its empty (e.g. trailing comma)
            if arg_text.strip():
                args_list.append(arg_text)

        return args_list

    def split_return_tuple(self, text):
        """Split the type variables to a return tuple."""
        return_items = self.split_args_text_to_list(text)
        return_items_stripped = []

        for item in return_items:
            item = item.strip().strip(""" "'""")
            if item and item != '...':
                return_items_stripped.append(item)

        return return_items_stripped

    def parse_return_type_annotation(self, text):
        """Extract, parse and format the function's return type annotation."""
        return_type_match = re.search(self.RETURN_TYPE_REGEX, text)

        if not return_type_match:
            return None, len(text)

        return_type = return_type_match.group(1).strip().strip(
            """ "'()\\"""
        )
        return_type = collapse_line_breaks_annotation(return_type)
        text_end = text.rfind(return_type_match.group(0))

        # If not a tuple, return the whole type
        return_tuple_match = re.search(self.RETURN_TUPLE_REGEX, return_type)
        if not return_tuple_match:
            return [return_type], text_end

        # If a 1-tuple, return the whole type
        tuple_values = return_tuple_match.group(1).strip()
        if not is_tuple_brackets(tuple_values):
            return [return_type], text_end

        # If only one item or an arbitrary-length tuple, return the whole type
        return_types = self.split_return_tuple(tuple_values)
        if len(return_types) < 2:
            return [return_type], text_end

        # Else, return the list of return tuple items
        return return_types, text_end

    def parse_def(self, text):
        """Parse the function definition text."""
        self.__init__()

        if not is_start_of_function(text):
            return

        self.func_indent = get_indent(text)

        text = text.strip()
        self.return_type_annotated, text_end = (
            self.parse_return_type_annotation(text)
        )

        pos_args_start = text.find('(') + 1
        pos_args_end = text.rfind(')', pos_args_start, text_end)

        self.args_text = text[pos_args_start:pos_args_end]

        args_list = self.split_args_text_to_list(self.args_text)
        if args_list is not None:
            self.has_info = True
            self.split_arg_to_name_type_value(args_list)

    def parse_docstring(self, text):
        """Process the function's docstring into a more usable form."""
        if not text:
            self.docstring_text = False

        # Stip leading/trailing whitespace and quotes
        text = text.strip()
        for quotes in ['"""', "'''"]:
            text = text.removeprefix(quotes).removesuffix(quotes)
        text = text.strip()
        text = "\n".join(line.rstrip() for line in text.split("\n"))

        self.docstring_text = text

    def parse_body(self, text):
        """Parse the function body text."""
        re_raise = re.findall(r'(?:^|\n)[ \t]+raise +(\w+)', text)
        if len(re_raise) > 0:
            raise_list = [x.strip() for x in re_raise]
            # Remove duplicates from list while keeping it in order
            self.raise_list = list(dict.fromkeys(raise_list))

        re_yield = re.search(r'(?:^|\n)[ \t]+yield +\S', text)
        if re_yield:
            self.has_yield = True

        # Extract return value
        pattern_return = r'yield +' if re_yield else r'return +'
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


class QMenuOnlyForEnter(SpyderMenu):
    """The class executes the selected action when "enter key" is input.

    If a input of keyboard is not the "enter key", the menu is closed and
    the input is inserted to code editor.
    """

    def __init__(self, code_editor):
        """Init SpyderMenu."""
        super().__init__(code_editor)
        self.code_editor = code_editor

    def keyPressEvent(self, event):
        """Close the instance if key is not enter key."""
        key = event.key()
        if key not in (Qt.Key_Enter, Qt.Key_Return):
            self.code_editor.keyPressEvent(event)
            self.close()
        else:
            super().keyPressEvent(event)
