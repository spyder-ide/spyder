# -----------------------------------------------------------------------------
# Copyright (c) 2019- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""Tests for docstring generation."""

# Standard library imports
import dataclasses

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


# =============================================================================
# ---- Test Cases
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
    def _normalize_part(part):
        """Strip an empty first line and add a missing trailing line break."""
        lines = part.split('\n')
        part = '\n'.join(lines[1:] if len(lines) and not lines[0] else lines)
        part = part + '\n' if part.split('\n')[-1].strip() else part
        return part

    @classmethod
    def _join_parts(cls, parts):
        """Join the various parts of a test case input/output together."""
        return ''.join(cls._normalize_part(part) for part in parts)

    @property
    def input_text(self):
        """Generate the input text for the test case."""
        return self._join_parts(
            [self.pre, self.sig, self.doc, self.body, self.post]
        )

    @property
    def function_body(self):
        """Get the processed function body."""
        return self._normalize_part(self.body).removesuffix('\n')

    def get_expected(self, doc_type):
        """Generate the expected output for a given docstring format."""
        doc = getattr(self, doc_type)
        return self._join_parts(
            [self.pre, self.sig, doc, self.body, self.post]
        )


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
    'popup_enter': (
        '''def foo():\n''',
        '''def foo():
    """
    SUMMARY.

    Returns
    -------
    None.
    """''',
        Qt.Key_Enter,
    ),
    'popup_not_enter': (
        '''def foo():\n''',
        '''def foo():
    """a''',
        Qt.Key_A,
    ),
}

TEST_CASES_DOCSTRING = {
    'empty': Case(),
    'notafunc_if_block': Case(
        pre='if 1:',
        body='    ',
    ),
    'no_params_no_body': Case(
        sig='  def foo():',
        numpy='''
      """
      SUMMARY.

      Returns
      -------
      None.
      """''',
        google='''
      """SUMMARY.

      Returns:
          None.
      """''',
        sphinx='''
      """SUMMARY.

      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'no_params_bare_return': Case(
        sig='def foo():',
        body='    return',
        numpy='''
    """
    SUMMARY.

    Returns
    -------
    None.
    """''',
        google='''
    """SUMMARY.

    Returns:
        None.
    """''',
        sphinx='''
    """SUMMARY.

    :return: DESCRIPTION
    :rtype: TYPE
    """''',
    ),
    'if_else_block': Case(
        sig='    def foo():',
        body='''
        if 1:
            raise ValueError
        else:
            return''',
        post='class F:',
        numpy='''
        """
        SUMMARY.

        Returns
        -------
        None.

        Raises
        ------
        ValueError
            DESCRIPTION.
        """''',
        google='''
        """SUMMARY.

        Returns:
            None.

        Raises:
            ValueError: DESCRIPTION.
        """''',
        sphinx='''
        """SUMMARY.

        :raises ValueError: DESCRIPTION
        :return: DESCRIPTION
        :rtype: TYPE
        """''',
    ),
    'async_raise_yield': Case(
        sig='async def foo():',
        body='''
    raise
    raise ValueError
    raise ValueError("test")
    raise TypeError("test")
    yield value
    ''',
        numpy='''
    """
    SUMMARY.

    Yields
    ------
    TYPE
        DESCRIPTION.

    Raises
    ------
    ValueError
        DESCRIPTION.
    TypeError
        DESCRIPTION.
    """''',
        google='''
    """SUMMARY.

    Yields:
        value (TYPE): DESCRIPTION.

    Raises:
        ValueError: DESCRIPTION.
        TypeError: DESCRIPTION.
    """''',
        sphinx='''
    """SUMMARY.

    :raises ValueError: DESCRIPTION
    :raises TypeError: DESCRIPTION
    :yield: DESCRIPTION
    :rtype: TYPE
    """''',
    ),
    'raise_yield_in_varnames': Case(
        sig='  def foo():',
        body='''
      print('{}' % foo_raise Value)
      foo_yield''',
        numpy='''
      """
      SUMMARY.

      Returns
      -------
      None.
      """''',
        google='''
      """SUMMARY.

      Returns:
          None.
      """''',
        sphinx='''
      """SUMMARY.

      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'long_complex_def_brackets_in_strings': Case(
        sig='''def foo(arg, arg0, arg1: int, arg2: List[Tuple[str, float]],
    arg3='-> (float, int):', arg4=':float, int[', arg5: str='""') -> \
    (List[Tuple[str, float]], str, float):''',
        numpy='''
    """
    SUMMARY.

    Parameters
    ----------
    arg : TYPE
        DESCRIPTION.
    arg0 : TYPE
        DESCRIPTION.
    arg1 : int
        DESCRIPTION.
    arg2 : List[Tuple[str, float]]
        DESCRIPTION.
    arg3 : TYPE, optional
        DESCRIPTION. The default is '-> (float, int):'.
    arg4 : TYPE, optional
        DESCRIPTION. The default is ':float, int['.
    arg5 : str, optional
        DESCRIPTION. The default is '""'.

    Returns
    -------
    (List[Tuple[str, float]], str, float)
        DESCRIPTION.
    """''',
        google='''
    """SUMMARY.

    Args:
        arg (TYPE): DESCRIPTION.
        arg0 (TYPE): DESCRIPTION.
        arg1 (int): DESCRIPTION.
        arg2 (List[Tuple[str, float]]): DESCRIPTION.
        arg3 (TYPE, optional): DESCRIPTION. Defaults to '-> (float, int):'.
        arg4 (TYPE, optional): DESCRIPTION. Defaults to ':float, int['.
        arg5 (str, optional): DESCRIPTION. Defaults to '""'.

    Returns:
        (List[Tuple[str, float]], str, float): DESCRIPTION.
    """''',
        sphinx='''
    """SUMMARY.

    :param arg: DESCRIPTION
    :type arg: TYPE
    :param arg0: DESCRIPTION
    :type arg0: TYPE
    :param arg1: DESCRIPTION
    :type arg1: int
    :param arg2: DESCRIPTION
    :type arg2: List[Tuple[str, float]]
    :param arg3: DESCRIPTION, defaults to '-> (float, int):'
    :type arg3: TYPE, optional
    :param arg4: DESCRIPTION, defaults to ':float, int['
    :type arg4: TYPE, optional
    :param arg5: DESCRIPTION, defaults to '""'
    :type arg5: str, optional
    :return: DESCRIPTION
    :rtype: (List[Tuple[str, float]], str, float)
    """''',
    ),
    'raise_yield_true_and_false_positives': Case(
        sig='  def foo():',
        body='''
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      \traise TypeError('tt')
      _yield''',
        numpy='''
      """
      SUMMARY.

      Returns
      -------
      None.

      Raises
      ------
      ValueError
          DESCRIPTION.
      TypeError
          DESCRIPTION.
      """''',
        google='''
      """SUMMARY.

      Returns:
          None.

      Raises:
          ValueError: DESCRIPTION.
          TypeError: DESCRIPTION.
      """''',
        sphinx='''
      """SUMMARY.

      :raises ValueError: DESCRIPTION
      :raises TypeError: DESCRIPTION
      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'return_single_named_variable': Case(
        sig='  def foo():',
        body='''
      spam = 42
      return spam''',
        numpy='''
      """
      SUMMARY.

      Returns
      -------
      TYPE
          DESCRIPTION.
      """''',
        google='''
      """SUMMARY.

      Returns:
          spam (TYPE): DESCRIPTION.
      """''',
        sphinx='''
      """SUMMARY.

      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'long_return_tuple_with_return_none': Case(
        sig='def foo():',
        body='''
    return None
    return "f, b", v1, v2, 3.0, .7, (,), {}, [ab], f(a), None, a.b, a+b, True
    return "f, b", v1, v3, 420, 5., (,), {}, [ab], f(a), None, a.b, a+b, False
    ''',
        numpy='''
    """
    SUMMARY.

    Returns
    -------
    str
        DESCRIPTION.
    v1 : TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    numeric
        DESCRIPTION.
    float
        DESCRIPTION.
    tuple
        DESCRIPTION.
    dict
        DESCRIPTION.
    list
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    TYPE
        DESCRIPTION.
    bool
        DESCRIPTION.
    """''',
        google='''
    """SUMMARY.

    Returns:
        str: DESCRIPTION.
        v1 (TYPE): DESCRIPTION.
        TYPE: DESCRIPTION.
        numeric: DESCRIPTION.
        float: DESCRIPTION.
        tuple: DESCRIPTION.
        dict: DESCRIPTION.
        list: DESCRIPTION.
        TYPE: DESCRIPTION.
        TYPE: DESCRIPTION.
        TYPE: DESCRIPTION.
        TYPE: DESCRIPTION.
        bool: DESCRIPTION.
    """''',
        sphinx='''
    """SUMMARY.

    :return: DESCRIPTION
    :rtype: TYPE
    """''',
    ),
    'return_tuple_of_tuple_named_vars': Case(
        sig='def foo():',
        body='''
    return no, (ano, eo, dken)
    ''',
        numpy='''
    """
    SUMMARY.

    Returns
    -------
    TYPE
        DESCRIPTION.
    """''',
        google='''
    """SUMMARY.

    Returns:
        TYPE: DESCRIPTION.
    """''',
        sphinx='''
    """SUMMARY.

    :return: DESCRIPTION
    :rtype: TYPE
    """''',
    ),
    # Test auto docstring with annotated function call
    # Regression test for issue spyder-ide/spyder#14520
    'return_type_annotated_obj': Case(
        sig='''  def test(self) -> Annotated[str, int("2")]:''',
        numpy='''
      """
      SUMMARY.

      Returns
      -------
      Annotated[str, int("2")]
          DESCRIPTION.
      """''',
        google='''
      """SUMMARY.

      Returns:
          Annotated[str, int("2")]: DESCRIPTION.
      """''',
        sphinx='''
      """SUMMARY.

      :return: DESCRIPTION
      :rtype: Annotated[str, int("2")]
      """''',
    ),
    # Test auto docstring with function call with line breaks.
    # Regression test for issue spyder-ide/spyder#14521
    'def_linebreak_between_var_and_type': Case(
        sig='''
  def test(v:
           int):''',
        numpy='''
      """
      SUMMARY.

      Parameters
      ----------
      v : int
          DESCRIPTION.

      Returns
      -------
      None.
      """''',
        google='''
      """SUMMARY.

      Args:
          v (int): DESCRIPTION.

      Returns:
          None.
      """''',
        sphinx='''
      """SUMMARY.

      :param v: DESCRIPTION
      :type v: int
      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'comment_after_def': Case(
        sig='''  def test(v: str = "#"):  # comment, with '#' and "#"''',
        numpy='''
      """
      SUMMARY.

      Parameters
      ----------
      v : str, optional
          DESCRIPTION. The default is "#".

      Returns
      -------
      None.
      """''',
        google='''
      """SUMMARY.

      Args:
          v (str, optional): DESCRIPTION. Defaults to "#".

      Returns:
          None.
      """''',
        sphinx='''
      """SUMMARY.

      :param v: DESCRIPTION, defaults to "#"
      :type v: str, optional
      :return: DESCRIPTION
      :rtype: TYPE
      """''',
    ),
    'comment_middle_of_def': Case(
        sig='''
  def test(v1: str = "#", # comment, with '#' and "#"
           v2: str = '#') -> str:''',
        numpy='''
      """
      SUMMARY.

      Parameters
      ----------
      v1 : str, optional
          DESCRIPTION. The default is "#".
      v2 : str, optional
          DESCRIPTION. The default is '#'.

      Returns
      -------
      str
          DESCRIPTION.
      """''',
        google='''
      """SUMMARY.

      Args:
          v1 (str, optional): DESCRIPTION. Defaults to "#".
          v2 (str, optional): DESCRIPTION. Defaults to '#'.

      Returns:
          str: DESCRIPTION.
      """''',
        sphinx='''
      """SUMMARY.

      :param v1: DESCRIPTION, defaults to "#"
      :type v1: str, optional
      :param v2: DESCRIPTION, defaults to '#'
      :type v2: str, optional
      :return: DESCRIPTION
      :rtype: str
      """''',
    ),
}


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

    def __editor_docstring(text, doc_type=DOC_TYPE_DEFAULT):
        CONF.set('editor', 'docstring_type', DOC_TYPES[doc_type])

        editor = base_editor_docstring
        writer = editor.writer_docstring
        cursor = editor.textCursor()

        editor.set_text(text)
        cursor.setPosition(0, QTextCursor.MoveAnchor)
        editor.setTextCursor(cursor)

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_after_def(editor_docstring_start):
    """Editor with cursor on the line after function signature's end."""

    def __editor_docstring(text, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring_start(text, doc_type)

        prev_colon = cursor.block().text().strip().endswith(':')
        prev_paren = ')' in cursor.block().text()
        cursor.movePosition(QTextCursor.NextBlock)
        current_colon = cursor.block().text().strip().endswith(':')

        # Hack to get the cursor below the def for two-line func signatures
        if current_colon and not (prev_colon and prev_paren):
            cursor.movePosition(QTextCursor.NextBlock)
        cursor.movePosition(QTextCursor.EndOfBlock, QTextCursor.MoveAnchor)
        editor.setTextCursor(cursor)

        return editor, writer, cursor

    return __editor_docstring


@pytest.fixture
def editor_docstring_inside_def(editor_docstring_start):
    """Editor with cursor at the end of the second line of text."""

    def __editor_docstring(text, doc_type=DOC_TYPE_DEFAULT):
        editor, writer, cursor = editor_docstring_start(text, doc_type)

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
    __, writer, __ = editor_docstring_after_def(test_case.input_text)

    func_info = FunctionInfo()
    func_info.parse_def(test_case.input_text)

    result = writer.get_function_body(func_info.func_indent).removesuffix('\n')

    assert result == test_case.function_body


@pytest.mark.parametrize(
    'use_shortcut', [True, False], ids=['shortcut', 'action']
)
@pytest.mark.parametrize('doc_type', DOC_TYPES.keys())
@pytest.mark.parametrize(
    'test_case',
    TEST_CASES_DOCSTRING.values(),
    ids=TEST_CASES_DOCSTRING.keys(),
)
def test_docstring_by_shortcut(
    editor_docstring_start, test_case, doc_type, use_shortcut
):
    """Test auto docstring by shortcut."""
    editor, writer, __ = editor_docstring_start(test_case.input_text, doc_type)

    if use_shortcut:
        writer.write_docstring_for_shortcut()
    else:
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
def test_docstring_below_def(editor_docstring_after_def, test_case, doc_type):
    """Test auto docstring below function definition by shortcut."""
    editor, writer, __ = editor_docstring_after_def(
        test_case.input_text, doc_type
    )

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == test_case.get_expected(doc_type)


@pytest.mark.parametrize(
    ['input_text', 'expected', 'key'],
    TEST_CASES_DELAYED_POPUP.values(),
    ids=TEST_CASES_DELAYED_POPUP.keys(),
)
def test_docstring_delayed_popup(
    qtbot, editor_docstring_after_def, input_text, expected, key
):
    """Test auto docstring using delayed popup."""
    editor, __, __ = editor_docstring_after_def(input_text, 'numpy')

    qtbot.keyPress(editor, Qt.Key_Tab)
    for __ in range(3):
        qtbot.keyPress(editor, Qt.Key_QuoteDbl)
    qtbot.wait(1000)
    qtbot.keyPress(editor.menu_docstring, key)

    assert editor.toPlainText() == expected


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
    editor, writer, __ = editor_docstring_inside_def(
        test_case.input_text, doc_type
    )

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == test_case.get_expected(doc_type)
