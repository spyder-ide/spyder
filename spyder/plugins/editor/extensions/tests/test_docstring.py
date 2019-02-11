# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see LICENSE.txt for details)

"""Tests for close quotes."""

# Third party imports
import pytest
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
    """\n    

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
      """\n      

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
    """\n    

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
    """\n    

    Returns:
        RETURN_TYPE: DESCRIPTION

    """
    '''
         ),
        ('Googledoc',
         '''  def foo():
      ''',
         '''  def foo():
      """\n      

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
    """\n    

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
                                      text, expected):
    """Test auto docstring by shortcut."""
    CONF.set('editor', 'docstring_type', doc_type)
    editor = editor_auto_docstring
    editor.set_text(text)

    cursor = editor.textCursor()
    cursor.setPosition(0, QTextCursor.MoveAnchor)
    editor.setTextCursor(cursor)

    pos = editor.cursorRect().bottomRight()
    pos = editor.mapToGlobal(pos)

    qtbot.mouseMove(editor, pos=pos, delay=-1)
    editor.writer_docstring.write_docstring_for_shortcut()

    assert editor.toPlainText() == expected


# =============================================================================
# ---- Example for manual Testing of numpy docstring
# =============================================================================
# def foo():
#     """
#
#
#     Returns
#     -------
#     RETURN_TYPE
#
#     """
#     pass
#
#
# def foo1(arg2):
#     """
#
#
#     Parameters
#     ----------
#     arg2 : TYPE
#         DESCRIPTION
#
#     Returns
#     -------
#     RETURN_TYPE
#
#     """
#     return arg1
#
#
# def foo2(arg1, arg2, arg3, arg4, arg5) -> (float, str):
#     """
#
#
#     Parameters
#     ----------
#     arg1 : TYPE
#         DESCRIPTION
#     arg2 : TYPE
#         DESCRIPTION
#     arg3 : TYPE
#         DESCRIPTION
#     arg4 : TYPE
#         DESCRIPTION
#     arg5 : TYPE
#         DESCRIPTION
#
#     Returns
#     -------
#     (float, str)
#         DESCRIPTION
#
#     """
#     pass
#
#
# def foo3(arg1: int, arg2: List[Tuple[str, float]], arg3='-> (float, int):',
#          arg4=':float, int[', arg5: str = '"\'"', arg7: str = """string1
#          string2""") -> \
#         (List[Tuple[str, float]], str, float):
#     """
#
#
#     Parameters
#     ----------
#     arg1 : int
#         DESCRIPTION
#     arg2 : List[Tuple[str, float]]
#         DESCRIPTION
#     arg3 : TYPE, optional
#         DESCRIPTION (the default is '-> (float, int):')
#     arg4 : TYPE, optional
#         DESCRIPTION (the default is ':float, int[')
#     arg5 : str, optional
#         DESCRIPTION (the default is '"\'"')
#     arg7 : str, optional
#         DESCRIPTION (the default is '''string1         string2''')
#
#     Returns
#     -------
#     (List[Tuple[str, float]], str, float)
#         DESCRIPTION
#
#     """
#     pass

# =============================================================================
# ---- Example for manual Testing of google docstring
# =============================================================================
# def foo():
#     """
#
#
#     Returns:
#         RETURN_TYPE: DESCRIPTION
#
#     """
#     return 0
#
#
# def foo1(arg2):
#     """
#
#
#     Args:
#         arg2 (TYPE): DESCRIPTION
#
#     Returns:
#         RETURN_TYPE: DESCRIPTION
#
#     """
#     return arg2
#
#
# def foo2(arg1, arg2, arg3, arg4=3, arg5: float=5.0) -> (float, str):
#     """
#
#
#     Args:
#         arg1 (TYPE): DESCRIPTION
#         arg2 (TYPE): DESCRIPTION
#         arg3 (TYPE): DESCRIPTION
#         arg4 (TYPE, optional): Defaults to 3. DESCRIPTION
#         arg5 (float, optional): Defaults to 5.0. DESCRIPTION
#
#     Returns:
#         (float, str): DESCRIPTION
#
#     """
#     pass
#
#
# def foo3(arg1: int, arg2: List[Tuple[str, float]], arg3='-> (float, int):',
#           arg4=':float, int[', arg5: str = '"\'"', arg7: str = """string1
#           string2""") -> \
#         (List[Tuple[str, float]], str, float):
#     """
#
#
#     Args:
#         arg1 (int): DESCRIPTION
#         arg2 (List[Tuple[str, float]]): DESCRIPTION
#         arg3 (TYPE, optional): Defaults to '-> (float, int):'. DESCRIPTION
#         arg4 (TYPE, optional): Defaults to ':float, int['. DESCRIPTION
#         arg5 (str, optional): Defaults to '"\'"'. DESCRIPTION
#         arg7 (str, optional): Defaults to '''string1          string2'''.
#                               DESCRIPTION
#
#     Returns:
#         (List[Tuple[str, float]], str, float): DESCRIPTION
#
#     """
#     pass
