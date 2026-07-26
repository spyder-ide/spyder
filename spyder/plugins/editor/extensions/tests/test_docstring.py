# -----------------------------------------------------------------------------
# Copyright (c) 2019- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Tests for docstring generation."""

# Standard library imports
import dataclasses
from pathlib import Path

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.plugins.editor.extensions.docstring import (
    DocstringInfo,
    FunctionInfo,
    get_indent,
    remove_comments,
)
from spyder.plugins.editor.widgets.codeeditor import (
    CodeEditor,
    CodeEditorActions,
    DocstringContext,
)
from spyder.utils.qthelpers import qapplication


# =============================================================================
# ---- Constants
# =============================================================================

DOC_TYPE_DEFAULT = 'numpy'
DOC_TYPES = {
    'numpy': 'Numpydoc',
    'google': 'Googledoc',
    'sphinx': 'Sphinxdoc',
}

TEST_CASE_DOCSTRING_DIR = Path(__file__).parent / 'docstring_test_cases'
TEST_CASE_FILE_NAME_PATTERN = '*.py'


# =============================================================================
# ---- Helpers
# =============================================================================

@dataclasses.dataclass(frozen=True)
class Case:
    """Associated data for one docstring test case."""
    pre: str = ''
    sig: str = ''
    doc: str = ''
    body: str = ''
    post: str = ''

    numpy: str = ''
    google: str = ''
    sphinx: str = ''


    @staticmethod
    def normalize_part(part):
        """Strip an empty first line and add a missing trailing line break."""
        lines = part.split('\n')
        part = '\n'.join(lines[1:] if len(lines) and not lines[0] else lines)
        part = part + '\n' if lines[-1].strip() else part
        return part

    @classmethod
    def _join_parts(cls, parts):
        """Join the various parts of a test case input/output together."""
        return ''.join(cls.normalize_part(part) for part in parts)

    @property
    def input_text(self):
        """Generate the input text for the test case."""
        return self._join_parts(
            [self.pre, self.sig, self.doc, self.body, self.post]
        )

    @property
    def function_def(self):
        """Get the processed function signature information."""
        if not self.sig.strip():
            return None

        def_text = self.normalize_part(self.sig).removesuffix('\n')
        def_text = remove_comments(def_text)
        return def_text.replace('\n', ''), def_text.count('\n') + 1

    @property
    def function_docstring(self):
        """Get the processed existing function docstring."""
        docstring = self.normalize_part(self.doc).rstrip()
        return docstring or None

    @property
    def function_body(self):
        """Get the processed function body."""
        parts = [self.normalize_part(part) for part in [self.doc, self.body]]
        return ''.join(parts).removesuffix('\n')

    def get_expected(self, doc_type):
        """Generate the expected output for a given docstring format."""
        doc = getattr(self, doc_type)
        return self._join_parts(
            [self.pre, self.sig, doc, self.body, self.post]
        )


def load_docstring_test_case(test_case_path):
    """Read and process an individual docstring test case from a file."""
    file_content = Path(test_case_path).read_text(encoding='UTF-8')
    sections = {}

    file_content = '\n' + file_content.lstrip()
    file_content = file_content.replace("\n#%% ", "\n# %%")
    blocks = file_content.split('\n# %% ')[1:]
    for block in blocks:
        lines = block.split('\n')
        block_title = lines[0].strip()
        block_content = '\n'.join(
            line[:-1] if len(line) > 1 and line[-2:] in {' #', '\t#'} else line
            for line in lines[1:]
        )
        sections[block_title] = block_content

    test_case = Case(**sections)
    return test_case


def load_docstring_test_cases(test_cases_dir=TEST_CASE_DOCSTRING_DIR):
    """Load docstring test cases from the filesystem."""
    test_case_paths = test_cases_dir.glob(TEST_CASE_FILE_NAME_PATTERN)

    test_cases = {
        path.stem: load_docstring_test_case(path) for path in test_case_paths
    }

    return test_cases


# =============================================================================
# ---- Test Cases
# =============================================================================

TEST_CASES_DEF_PARSE = {
    'empty': ('', False, '', [], [], [], None),
    'no_params_no_body': ('def foo():', True, '', [], [], [], None),
    'long_complex_def_brackets_in_strings': (
        ''' def foo(arg0, arg1=':', arg2: str='-> (float, str):') -> \
         (float, int): ''',
        True,
        ' ',
        ['arg0', 'arg1', 'arg2'],
        [None, None, 'str'],
        [None, "':'", "'-> (float, str):'"],
        ['float, int'],
    ),
}

TEST_CASES_DOCSTRING_PARSE = {
    'empty': ('', False, None, None, None, None, None, None, None),
    'oneline': (
        '''
            """This is a test docstring."""
        ''',
        '''This is a test docstring.''',
        None,
        None,
        '''This is a test docstring.''',
        None,
        None,
        None,
        None,
    ),
    'oneline_fenced': (
        '''
            """
            This is a test docstring.   #
            """  #
        ''',
        '''This is a test docstring.''',
        None,
        None,
        '''This is a test docstring.''',
        None,
        None,
        None,
        None,
    ),
    'multiline_compressed': (
        '''
            """This is a multi line docstring.

            It is very long.
                Sub indent."""
        ''',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        '            ',
        None,
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        None,
        None,
        None,
        None,
    ),
    'multiline_fenced': (
        '''"""
            This is a multi line docstring.

            It is very long.
                Sub indent.
            """''',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        '            ',
        None,
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        None,
        None,
        None,
        None,
    ),
    'numpy': (
        '''"""
            This is a multi line docstring.

            It is very long.
                Sub indent.

            Parameters
            ----------
            arg1 : str
                The first arg.
            arg2 : bool, optional
                The second arg. The default is True.

            Returns
            -------
            str
                The string value passed.
            bool
                The boolean value passed.

            Examples
            --------
            Examples.

            Raises
            ------
            ValueError
                If the wrong arg is passed.

            See also
            --------
            See also stuff.
            """''',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.

            Parameters
            ----------
            arg1 : str
                The first arg.
            arg2 : bool, optional
                The second arg. The default is True.

            Returns
            -------
            str
                The string value passed.
            bool
                The boolean value passed.

            Examples
            --------
            Examples.

            Raises
            ------
            ValueError
                If the wrong arg is passed.

            See also
            --------
            See also stuff.''',
        '            ',
        'Numpydoc',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        '''Parameters
            ----------
            arg1 : str
                The first arg.
            arg2 : bool, optional
                The second arg. The default is True.''',
        '''Returns
            -------
            str
                The string value passed.
            bool
                The boolean value passed.''',
        '''Raises
            ------
            ValueError
                If the wrong arg is passed.''',
        '''Examples
            --------
            Examples.

            See also
            --------
            See also stuff.''',
    ),
    'google': (
        '''"""This is a multi line docstring.

            It is very long.
                Sub indent.

            Args:
                arg1 (str): The first arg.
                arg2 (bool, optional): The second arg. Defaults to True.

            Returns:
                tuple[str, bool]: The string and boolean value passed.

            Examples:
                An example.

            Raises:
                ValueError: If the wrong value is passed.

            See Also:
                See also stuff.
            """''',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.

            Args:
                arg1 (str): The first arg.
                arg2 (bool, optional): The second arg. Defaults to True.

            Returns:
                tuple[str, bool]: The string and boolean value passed.

            Examples:
                An example.

            Raises:
                ValueError: If the wrong value is passed.

            See Also:
                See also stuff.''',
        '            ',
        'Googledoc',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        '''Args:
                arg1 (str): The first arg.
                arg2 (bool, optional): The second arg. Defaults to True.''',
        '''Returns:
                tuple[str, bool]: The string and boolean value passed.''',
        '''Raises:
                ValueError: If the wrong value is passed.''',
        '''Examples:
                An example.

            See Also:
                See also stuff.''',
    ),
    'sphinx': (
        '''"""This is a multi line docstring.

            It is very long.
                Sub indent.

            :param arg1: The first arg
            :type arg1: str
            :param arg2: The second arg, defaults to True
            :type arg2: bool

            Other content here.

            :rtype: tuple[str, bool]
            :returns: The string and boolean value passed.

            More content here.

            :raises ValueError: If the wrong value is passed.

            Some other content.
            """''',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.

            :param arg1: The first arg
            :type arg1: str
            :param arg2: The second arg, defaults to True
            :type arg2: bool

            Other content here.

            :rtype: tuple[str, bool]
            :returns: The string and boolean value passed.

            More content here.

            :raises ValueError: If the wrong value is passed.

            Some other content.''',
        '            ',
        'Sphinxdoc',
        '''This is a multi line docstring.

            It is very long.
                Sub indent.''',
        ''':param arg1: The first arg
            :type arg1: str
            :param arg2: The second arg, defaults to True
            :type arg2: bool''',
        ''':rtype: tuple[str, bool]
            :returns: The string and boolean value passed.''',
        ''':raises ValueError: If the wrong value is passed.''',
        '''Other content here.

            More content here.

            Some other content.''',
    ),
}

TEST_CASES_BODY_PARSE = {
    'empty': ('', [], None, False),
    'simple_body': ('return True', ['True'], None, False),
    'long_complex_body': (
        '''
            raise
            raise ValueError
            raise ValueError('tt')
            \traise TypeError('tt')

            yield None
            yield "f, b", v1, v2, 3.0, .7, (,)
            yield {}, [ab], f(a), None, a.b, a+b, False
            return foo, bar
        ''',
        [
            'None',
            '"f, b", v1, v2, 3.0, .7, (,)',
            '{}, [ab], f(a), None, a.b, a+b, False',
        ],
        ['ValueError', 'TypeError'],
        True,
    ),
}

TEST_CASES_DELAYED_POPUP = {
    'popup_press_enter': (
        Case(
            sig='def foo():',
            numpy='''
    """
    SUMMARY.

    Returns
    -------
    None
    """''',
        ),
        Qt.Key_Enter,
    ),
    'popup_press_letter': (
        Case(
        sig='def foo():',
        numpy='    """a''',
        ),
    Qt.Key_A,
    ),
}

TEST_CASES_DOCSTRING = load_docstring_test_cases(TEST_CASE_DOCSTRING_DIR)


# =============================================================================
# ---- Fixtures
# =============================================================================

@pytest.fixture(scope="module")
def base_editor_docstring():
    """Set up Editor with auto docstring activated."""
    app = qapplication()  # noqa
    editor = CodeEditor(parent=None)

    def write_docstring():
        action = editor.get_action(CodeEditorActions.Docstring)
        if action.data()["at_cursor_position"]:
            editor.writer_docstring.write_docstring_at_first_line_of_function()
        else:
            editor.for_each_cursor(editor.writer_docstring.write_docstring)()

    # This action is available at the main widget level, so we need to recreate
    # it here
    editor.create_action(
        CodeEditorActions.Docstring,
        text="Generate docstring",
        register_shortcut=True,
        data=DocstringContext(at_cursor_position=False),
        triggered=write_docstring,
    )

    editor.setup_editor(
        language='Python', close_quotes=True, close_parentheses=True
    )

    return editor, editor.writer_docstring, editor.textCursor()


@pytest.fixture
def editor_docstring(base_editor_docstring):
    """Editor with per-test setup."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = base_editor_docstring
        editor.set_conf('docstring_type', DOC_TYPES[doc_type])
        editor.set_text(test_case.input_text)

        cursor.setPosition(0)

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_start(editor_docstring):
    """Editor with cursor at the start of the function."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring(test_case, doc_type)

        move_count = test_case.normalize_part(test_case.pre).count('\n')
        cursor.movePosition(QTextCursor.NextBlock, n=move_count)

        editor.setTextCursor(cursor)
        writer.line_number_cursor = cursor.blockNumber() + 1

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_end_def(editor_docstring):
    """Editor with cursor at the end of the function signature."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring(test_case, doc_type)

        move_count = (
            test_case.normalize_part(test_case.pre).count("\n")
            + test_case.normalize_part(test_case.sig).count("\n")
            - 1
        )
        cursor.movePosition(QTextCursor.NextBlock, n=move_count)
        cursor.movePosition(QTextCursor.EndOfBlock)

        editor.setTextCursor(cursor)
        writer.line_number_cursor = cursor.blockNumber() + 1

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_after_def(editor_docstring):
    """Editor with cursor on the line after the function signature's end."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring(test_case, doc_type)

        move_count = (
            test_case.normalize_part(test_case.pre).count("\n")
            + test_case.normalize_part(test_case.sig).count("\n")
        )
        cursor.movePosition(QTextCursor.NextBlock, n=move_count)
        cursor.movePosition(QTextCursor.EndOfBlock)

        editor.setTextCursor(cursor)
        writer.line_number_cursor = cursor.blockNumber() + 1

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_inside_def(editor_docstring):
    """Editor with cursor at the end of the second line of text."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring(test_case, doc_type)

        # Position cursor somewhere inside the `def` statement
        move_count = test_case.normalize_part(test_case.pre).count('\n')
        cursor.movePosition(QTextCursor.NextBlock, n=move_count)
        cursor.movePosition(QTextCursor.NextCharacter, n=9)

        editor.setTextCursor(cursor)
        writer.line_number_cursor = cursor.blockNumber() + 1

        return editor, writer, cursor

    return __editor_docstring


# =============================================================================
# ---- Tests
# =============================================================================

@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_get_function_def_start(editor_docstring_start, test_case):
    """Test get function definition at the start of the signature."""
    __, writer, __ = editor_docstring_start(test_case)

    result = writer.get_function_definition_from_first_line()

    assert result == test_case.function_def


@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_get_function_def_below(editor_docstring_after_def, test_case):
    """Test get function definition below the signature."""
    __, writer, __ = editor_docstring_after_def(test_case)

    result = writer.get_function_definition_from_below_last_line()

    assert result == test_case.function_def


@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_get_function_docstring(editor_docstring_end_def, test_case):
    """Test get function docstring."""
    __, writer, __ = editor_docstring_end_def(test_case)
    indent = get_indent(test_case.sig)

    result = writer.get_function_docstring(indent)

    assert result == test_case.function_docstring


@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_get_function_body(editor_docstring_after_def, test_case):
    """Test get function body."""
    __, writer, __ = editor_docstring_after_def(test_case)
    indent = get_indent(test_case.sig)

    result = writer.get_function_body(indent)

    assert result.removesuffix('\n') == test_case.function_body


@pytest.mark.parametrize(
    [
         'input_text',
         'has_info',
         'indent',
         'name_list',
         'type_list',
         'value_list',
         'return_type',
     ],
    TEST_CASES_DEF_PARSE.values(),
    ids=TEST_CASES_DEF_PARSE.keys(),
)
def test_parse_function_def(
    input_text, has_info, indent, name_list, type_list, value_list, return_type
):
    """Test the parse_def method of the FunctionInfo class."""
    func_info = FunctionInfo()

    func_info.parse_def(input_text)

    assert func_info.has_info == has_info
    assert func_info.func_indent == indent
    assert func_info.arg_name_list == name_list
    assert func_info.arg_type_list == type_list
    assert func_info.arg_value_list == value_list
    assert func_info.return_type_annotated == return_type


@pytest.mark.parametrize(
    [
        "input_text",
        "expected_text",
        "doc_indent",
        "format_name",
        "description",
        "parameters",
        "returns",
        "raises",
        "other",
    ],
    TEST_CASES_DOCSTRING_PARSE.values(),
    ids=TEST_CASES_DOCSTRING_PARSE.keys(),
)
def test_parse_function_docstring(
    input_text,
    expected_text,
    doc_indent,
    format_name,
    description,
    parameters,
    returns,
    raises,
    other,
):
    """Test the parse_docstring method of the DocstringInfo class."""
    doc_info = DocstringInfo()

    doc_info.parse_docstring(input_text.replace('#\n', '\n'))
    doc_format = doc_info.doc_format

    assert doc_info.text == expected_text
    assert doc_info.doc_indent == doc_indent
    assert doc_info.format_name == format_name
    assert (doc_format.name if doc_format else doc_format) == format_name
    assert doc_info.description == description
    assert doc_info.parameters == parameters
    assert doc_info.returns == returns
    assert doc_info.raises == raises
    assert doc_info.other == other


@pytest.mark.parametrize(
    ['input_text', 'return_value', 'raise_list', 'has_yield'],
    TEST_CASES_BODY_PARSE.values(),
    ids=TEST_CASES_BODY_PARSE.keys(),
)
def test_parse_function_body(
    input_text, return_value, raise_list, has_yield
):
    """Test the parse_body method of the FunctionInfo class."""
    func_info = FunctionInfo()
    func_info.parse_body(input_text)

    assert func_info.return_value_in_body == return_value
    assert func_info.raise_list == raise_list
    assert func_info.has_yield == has_yield


@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_write_docstring(
    editor_docstring_start, test_case, doc_type
):
    """Test auto docstring by calling the function directly."""
    editor, writer, __ = editor_docstring_start(test_case, doc_type)

    pos = editor.cursorRect().bottomRight()
    pos = editor.mapToGlobal(pos)
    writer.line_number_cursor = editor.get_line_number_at(pos)
    writer.write_docstring_at_first_line_of_function()

    assert editor.toPlainText() == test_case.get_expected(doc_type)

    editor.undo()
    assert editor.toPlainText() == test_case.input_text


@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_docstring_by_shortcut(
    editor_docstring_start, test_case, doc_type
):
    """Test auto docstring by shortcut."""
    editor, writer, __ = editor_docstring_start(test_case, doc_type)

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == test_case.get_expected(doc_type)

    editor.undo()
    assert editor.toPlainText() == test_case.input_text


@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_docstring_below_def(editor_docstring_after_def, test_case, doc_type):
    """Test auto docstring below function definition by shortcut."""
    editor, writer, __ = editor_docstring_after_def(test_case, doc_type)

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == test_case.get_expected(doc_type)

    editor.undo()
    assert editor.toPlainText() == test_case.input_text



@pytest.mark.parametrize('doc_type', ['numpy'])
@pytest.mark.parametrize(
    ['test_case', 'key'],
    TEST_CASES_DELAYED_POPUP.values(),
    ids=TEST_CASES_DELAYED_POPUP.keys(),
)
def test_docstring_delayed_popup(
    qtbot, editor_docstring_after_def, test_case, key, doc_type
):
    """Test auto docstring using delayed popup."""
    editor, __, __ = editor_docstring_after_def(test_case, doc_type)

    qtbot.keyPress(editor, Qt.Key_Tab)
    for __ in range(3):
        qtbot.keyPress(editor, Qt.Key_QuoteDbl)
    initial_text = editor.toPlainText()
    qtbot.wait(600)
    qtbot.keyPress(editor.menu_docstring, key)

    assert editor.toPlainText() == test_case.get_expected(doc_type).rstrip()

    if key == Qt.Key_Enter:
        editor.undo()
        assert editor.toPlainText() == initial_text


@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_docstring_inside_def(
    editor_docstring_inside_def, test_case, doc_type
):
    """Test auto docstring inside the function definition block."""
    editor, writer, __ = editor_docstring_inside_def(test_case, doc_type)

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == test_case.get_expected(doc_type)

    editor.undo()
    assert editor.toPlainText() == test_case.input_text
