# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""Tests for docstring generation."""

# Third party imports
import pytest
from qtpy.QtCore import Qt
from qtpy.QtGui import QTextCursor

# Local imports
from spyder.config.main import CONF
from spyder.utils.qthelpers import qapplication
from spyder.plugins.editor.widgets.codeeditor import CodeEditor
from spyder.plugins.editor.extensions.docstring import FunctionInfo


# =============================================================================
# ---- Fixtures
# =============================================================================
@pytest.fixture
def editor_auto_docstring():
    """Set up Editor with auto docstring activated."""
    app = qapplication()
    editor = CodeEditor(parent=None)
    kwargs = {}
    kwargs['language'] = 'Python'
    kwargs['close_quotes'] = True
    kwargs['close_parentheses'] = True
    editor.setup_editor(**kwargs)
    return editor


# =============================================================================
# ---- Tests
# =============================================================================
@pytest.mark.parametrize(
    "text, indent, name_list, type_list, value_list, rtype",
    [
        ('def foo():', '', [], [], [], None),
        (""" def foo(arg0, arg1=':', arg2: str='-> (float, str):') -> \
             (float, int): """,
         ' ', ['arg0', 'arg1', 'arg2'], [None, None, 'str'],
         [None, "':'", "'-> (float, str):'"],
         '(float, int)')
    ])
def test_parse_function_definition(text, indent, name_list, type_list,
                                   value_list, rtype):
    """Test the parse_def method of FunctionInfo class."""
    func_info = FunctionInfo()
    func_info.parse_def(text)

    assert func_info.func_indent == indent
    assert func_info.arg_name_list == name_list
    assert func_info.arg_type_list == type_list
    assert func_info.arg_value_list == value_list
    assert func_info.return_type_annotated == rtype


@pytest.mark.parametrize(
    "text, indent, expected",
    [
        ("""    def foo():\n
        if 1:
            raise ValueError
        else:
            return\n
    class F:""",
         "    ",
         """\n        if 1:
            raise ValueError
        else:
            return\n"""),
        ("""def foo():
    return""",
         "",
         """    return""")
    ])
def test_get_function_body(editor_auto_docstring, text, indent, expected):
    """Test get function body."""
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.setPosition(0, QTextCursor.MoveAnchor)
    cursor.movePosition(QTextCursor.NextBlock)
    editor.setTextCursor(cursor)

    writer = editor.writer_docstring
    result = writer.get_function_body(indent)

    assert expected == result


@pytest.mark.parametrize("use_shortcut", [True, False])
@pytest.mark.parametrize(
    "doc_type, text, expected",
    [
        ('Numpydoc',
         '',
         ''
         ),
        ('Numpydoc',
         'if 1:\n    ',
         'if 1:\n    '
         ),
        ('Numpydoc',
         '''async def foo():
    raise
    raise ValueError
    raise ValueError("test")
    raise TypeError("test")
    yield ''',
         '''async def foo():
    """\n    \n
    Raises
    ------
    ValueError
        DESCRIPTION.
    TypeError
        DESCRIPTION.\n
    Yields
    ------
    None.

    """
    raise
    raise ValueError
    raise ValueError("test")
    raise TypeError("test")
    yield '''
         ),
        ('Numpydoc',
         '''  def foo():
      print('{}' % foo_raise Value)
      foo_yield''',
         '''  def foo():
      """\n      \n
      Returns
      -------
      None.

      """
      print('{}' % foo_raise Value)
      foo_yield''',
         ),
        ('Numpydoc',
         '''def foo(arg, arg0, arg1: int, arg2: List[Tuple[str, float]],
    arg3='-> (float, int):', arg4=':float, int[', arg5: str='""') -> \
  (List[Tuple[str, float]], str, float):
    ''',
         '''def foo(arg, arg0, arg1: int, arg2: List[Tuple[str, float]],
    arg3='-> (float, int):', arg4=':float, int[', arg5: str='""') -> \
  (List[Tuple[str, float]], str, float):
    """\n    \n
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

    """
    '''),
        ('Googledoc',
         '''async def foo():
    raise
    raise ValueError
    raise TypeError("test")
    yield value
    ''',
         '''async def foo():
    """\n    \n
    Raises:
        ValueError: DESCRIPTION.
        TypeError: DESCRIPTION.\n
    Yields:
        value (TYPE): DESCRIPTION.

    """
    raise
    raise ValueError
    raise TypeError("test")
    yield value
    '''
         ),
        ('Googledoc',
         '''  def foo():
      ''',
         '''  def foo():
      """\n      \n
      Returns:
          None.

      """
      ''',
         ),
        ('Googledoc',
         '''def foo(arg, arg0, arg1: int, arg2: List[Tuple[str, float]],
    arg3='-> (float, int):', arg4=':float, int[', arg5: str='""') -> \
  (List[Tuple[str, float]], str, float):
    ''',
         '''def foo(arg, arg0, arg1: int, arg2: List[Tuple[str, float]],
    arg3='-> (float, int):', arg4=':float, int[', arg5: str='""') -> \
  (List[Tuple[str, float]], str, float):
    """\n    \n
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

    """
    '''),
    ])
def test_editor_docstring_by_shortcut(editor_auto_docstring, doc_type,
                                      text, expected, use_shortcut):
    """Test auto docstring by shortcut."""
    CONF.set('editor', 'docstring_type', doc_type)
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.setPosition(0, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)
    writer = editor.writer_docstring

    if use_shortcut:
        writer.write_docstring_for_shortcut()
    else:
        pos = editor.cursorRect().bottomRight()
        pos = editor.mapToGlobal(pos)
        writer.line_number_cursor = editor.get_line_number_at(pos)
        writer.write_docstring_at_first_line_of_function()

    assert editor.toPlainText() == expected


@pytest.mark.parametrize(
    'text, expected',
    [
        ('''  def foo():
      ''',
         '''  def foo():
      """\n      \n
      Returns
      -------
      None.

      """
      ''',)
    ])
def test_editor_docstring_below_def_by_shortcut(qtbot, editor_auto_docstring,
                                                text, expected):
    """Test auto docstring below function definition by shortcut."""
    CONF.set('editor', 'docstring_type', 'Numpydoc')
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.NextBlock)
    cursor.setPosition(QTextCursor.End, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)

    editor.writer_docstring.write_docstring_for_shortcut()

    assert editor.toPlainText() == expected


@pytest.mark.parametrize(
    'text, expected, key',
    [
        ('''def foo():
''',
         '''def foo():
    """\n    \n
    Returns
    -------
    None.

    """''',
         Qt.Key_Enter),
        ('''def foo():
''',
         '''def foo():
    """a''',
         Qt.Key_A)
    ])
def test_editor_docstring_delayed_popup(qtbot, editor_auto_docstring,
                                        text, expected, key):
    """Test auto docstring using delayed popup."""
    CONF.set('editor', 'docstring_type', 'Numpydoc')
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.NextBlock)
    cursor.setPosition(QTextCursor.EndOfLine, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)

    qtbot.keyPress(editor, Qt.Key_Space)
    qtbot.keyPress(editor, Qt.Key_Space)
    qtbot.keyPress(editor, Qt.Key_Space)
    qtbot.keyPress(editor, Qt.Key_Space)
    qtbot.keyPress(editor, Qt.Key_QuoteDbl)
    qtbot.keyPress(editor, Qt.Key_QuoteDbl)
    qtbot.keyPress(editor, Qt.Key_QuoteDbl)
    qtbot.wait(1000)
    qtbot.keyPress(editor.menu_docstring, key)
    qtbot.wait(1000)

    assert editor.toPlainText() == expected


@pytest.mark.parametrize(
    'text, expected',
    [
        ('''  def foo():
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      \traise TypeError('tt')
      _yield
      ''',
         '''  def foo():
      """\n      \n
      Raises
      ------
      ValueError
          DESCRIPTION.
      TypeError
          DESCRIPTION.\n
      Returns
      -------
      None.

      """
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      \traise TypeError('tt')
      _yield
      ''',),
        ('''def foo():
    return None
    return "f, b", v1, v2, 3.0, .7, (,), {}, [ab], f(a), None, a.b, a+b, True
    return "f, b", v1, v3, 420, 5., (,), {}, [ab], f(a), None, a.b, a+b, False
    ''',
         '''def foo():
    """\n    \n
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

    """
    return None
    return "f, b", v1, v2, 3.0, .7, (,), {}, [ab], f(a), None, a.b, a+b, True
    return "f, b", v1, v3, 420, 5., (,), {}, [ab], f(a), None, a.b, a+b, False
    '''),
        ('''def foo():
    return no, (ano, eo, dken)
    ''',
         '''def foo():
    """\n    \n
    Returns
    -------
    TYPE
        DESCRIPTION.

    """
    return no, (ano, eo, dken)
    ''')
    ])
def test_editor_docstring_with_body_numpydoc(qtbot, editor_auto_docstring,
                                             text, expected):
    """Test auto docstring of numpydoc when the function body is complex."""
    CONF.set('editor', 'docstring_type', 'Numpydoc')
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.setPosition(0, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)
    writer = editor.writer_docstring

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == expected


@pytest.mark.parametrize(
    'text, expected',
    [
        ('''  def foo():
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      \traise TypeError('tt')
      _yield
      ''',
         '''  def foo():
      """\n      \n
      Raises:
          ValueError: DESCRIPTION.
          TypeError: DESCRIPTION.\n
      Returns:
          None.

      """
      raise
      foo_raise()
      raisefoo()
      raise ValueError
      is_yield()
      raise ValueError('tt')
      yieldfoo()
      \traise TypeError('tt')
      _yield
      ''',),
        ('''def foo():
    return None
    return "f, b", v1, v2, 3.0, .7, (,), {}, [ab], f(a), None, a.b, a+b, True
    return "f, b", v1, v3, 420, 5., (,), {}, [ab], f(a), None, a.b, a+b, False
    ''',
         '''def foo():
    """\n    \n
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

    """
    return None
    return "f, b", v1, v2, 3.0, .7, (,), {}, [ab], f(a), None, a.b, a+b, True
    return "f, b", v1, v3, 420, 5., (,), {}, [ab], f(a), None, a.b, a+b, False
    '''),
        ('''def foo():
    return no, (ano, eo, dken)
    ''',
         '''def foo():
    """\n    \n
    Returns:
        TYPE: DESCRIPTION.

    """
    return no, (ano, eo, dken)
    ''')
    ])
def test_editor_docstring_with_body_googledoc(qtbot, editor_auto_docstring,
                                              text, expected):
    """Test auto docstring of googledoc when the function body is complex."""
    CONF.set('editor', 'docstring_type', 'Googledoc')
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.setPosition(0, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)
    writer = editor.writer_docstring

    writer.write_docstring_for_shortcut()

    assert editor.toPlainText() == expected
