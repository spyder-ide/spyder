# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""Tests for close quotes."""

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
def test_information_of_function(text, indent, name_list, type_list,
                                 value_list, rtype):
    """Test FunctionInfo."""
    func_info = FunctionInfo()
    func_info.parse(text)

    assert func_info.func_indent == indent
    assert func_info.arg_name_list == name_list
    assert func_info.arg_type_list == type_list
    assert func_info.arg_value_list == value_list
    assert func_info.return_type == rtype


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
    ''',
         '''async def foo():
    """\n    \n
    Returns
    -------
    RETURN_TYPE

    """
    '''
         ),
        ('Numpydoc',
         '''  def foo():
      ''',
         '''  def foo():
      """\n      \n
      Returns
      -------
      RETURN_TYPE

      """
      ''',
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
        DESCRIPTION
    arg0 : TYPE
        DESCRIPTION
    arg1 : int
        DESCRIPTION
    arg2 : List[Tuple[str, float]]
        DESCRIPTION
    arg3 : TYPE, optional
        DESCRIPTION (the default is '-> (float, int):')
    arg4 : TYPE, optional
        DESCRIPTION (the default is ':float, int[')
    arg5 : str, optional
        DESCRIPTION (the default is '""')

    Returns
    -------
    (List[Tuple[str, float]], str, float)
        DESCRIPTION

    """
    '''),
        ('Googledoc',
         '''async def foo():
    ''',
         '''async def foo():
    """\n    \n
    Returns:
        RETURN_TYPE: DESCRIPTION

    """
    '''
         ),
        ('Googledoc',
         '''  def foo():
      ''',
         '''  def foo():
      """\n      \n
      Returns:
          RETURN_TYPE: DESCRIPTION

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
        arg (TYPE): DESCRIPTION
        arg0 (TYPE): DESCRIPTION
        arg1 (int): DESCRIPTION
        arg2 (List[Tuple[str, float]]): DESCRIPTION
        arg3 (TYPE, optional): Defaults to '-> (float, int):'. DESCRIPTION
        arg4 (TYPE, optional): Defaults to ':float, int['. DESCRIPTION
        arg5 (str, optional): Defaults to '""'. DESCRIPTION

    Returns:
        (List[Tuple[str, float]], str, float): DESCRIPTION

    """
    '''),
    ])
def test_editor_docstring_by_shortcut(qtbot, editor_auto_docstring, doc_type,
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
