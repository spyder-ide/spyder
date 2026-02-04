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
from spyder.config.manager import CONF
from spyder.plugins.editor.extensions.docstring import FunctionInfo
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
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

@dataclasses.dataclass
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
    def function_body(self):
        """Get the processed function body."""
        return self.normalize_part(self.body).removesuffix('\n')

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
            line.removesuffix('#') if line.strip() == '#' else line
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

TEST_CASES_FUNCTION_PARSE = {
    'no_params_no_body': ('def foo():', '', [], [], [], None),
    'long_complex_def_brackets_in_strings': (
        ''' def foo(arg0, arg1=':', arg2: str='-> (float, str):') -> \
         (float, int): ''',
        ' ',
        ['arg0', 'arg1', 'arg2'],
        [None, None, 'str'],
        [None, "':'", "'-> (float, str):'"],
        '(float, int)',
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
    None.
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

@pytest.fixture
def base_editor_docstring():
    """Set up Editor with auto docstring activated."""
    app = qapplication()  # noqa
    editor = CodeEditor(parent=None)
    editor.setup_editor(
        language='Python', close_quotes=True, close_parentheses=True
    )
    return editor


@pytest.fixture
def editor_docstring_start(base_editor_docstring):
    """Editor with cursor at the start of the text."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        CONF.set('editor', 'docstring_type', DOC_TYPES[doc_type])

        editor = base_editor_docstring
        writer = editor.writer_docstring
        cursor = editor.textCursor()
        editor.set_text(test_case.input_text)

        for __ in range(test_case.normalize_part(test_case.pre).count('\n')):
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.setPosition(0, QTextCursor.MoveAnchor)

        editor.setTextCursor(cursor)
        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_after_def(editor_docstring_start):
    """Editor with cursor on the line after function signature's end."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring_start(test_case, doc_type)

        for __ in range(test_case.normalize_part(test_case.sig).count('\n')):
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.MoveAnchor)

        editor.setTextCursor(cursor)
        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_inside_def(editor_docstring_start):
    """Editor with cursor at the end of the second line of text."""

    def __editor_docstring(test_case, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring_start(test_case, doc_type)

        # Position cursor somewhere inside the `def` statement
        cursor.setPosition(11, QTextCursor.MoveAnchor)

        editor.setTextCursor(cursor)
        return editor, writer, cursor

    return __editor_docstring


# =============================================================================
# ---- Tests
# =============================================================================

@pytest.mark.parametrize(
    ['input_text', 'indent', 'name_list', 'type_list', 'value_list', 'rtype'],
    TEST_CASES_FUNCTION_PARSE.values(),
    ids=TEST_CASES_FUNCTION_PARSE.keys(),
)
def test_parse_function_def(
    input_text, indent, name_list, type_list, value_list, rtype
):
    """Test the parse_def method of FunctionInfo class."""
    func_info = FunctionInfo()
    func_info.parse_def(input_text)

    assert func_info.func_indent == indent
    assert func_info.arg_name_list == name_list
    assert func_info.arg_type_list == type_list
    assert func_info.arg_value_list == value_list
    assert func_info.return_type_annotated == rtype


@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_get_function_body(editor_docstring_after_def, test_case):
    """Test get function body."""
    __, writer, __ = editor_docstring_after_def(test_case)

    func_info = FunctionInfo()
    func_info.parse_def(test_case.input_text)

    result = writer.get_function_body(func_info.func_indent).removesuffix('\n')

    assert result == test_case.function_body


@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_write_docstring(
    editor_docstring_start, test_case, doc_type
):
    """Test auto docstring by shortcut."""
    editor, writer, __ = editor_docstring_start(test_case, doc_type)

    pos = editor.cursorRect().bottomRight()
    pos = editor.mapToGlobal(pos)
    writer.line_number_cursor = editor.get_line_number_at(pos)
    writer.write_docstring_at_first_line_of_function()

    assert editor.toPlainText() == test_case.get_expected(doc_type)


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
    qtbot.wait(1000)
    qtbot.keyPress(editor.menu_docstring, key)

    assert editor.toPlainText() == test_case.get_expected(doc_type).rstrip()


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
