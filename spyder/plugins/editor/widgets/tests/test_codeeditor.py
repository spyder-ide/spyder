# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

# Standard library imports
import os.path as osp
import sys

# Third party imports
from qtpy import QT_VERSION
from qtpy.QtCore import Qt, QEvent
from qtpy.QtGui import QFont, QTextCursor, QMouseEvent
from qtpy.QtWidgets import QApplication, QTextEdit
import pytest


HERE = osp.dirname(osp.abspath(__file__))
ASSETS = osp.join(HERE, 'assets')


def test_editor_upper_to_lower(codeeditor):
    widget = codeeditor
    text = 'UPPERCASE'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_lowercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


def test_editor_lower_to_upper(codeeditor):
    widget = codeeditor
    text = 'uppercase'
    widget.set_text(text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.NextCharacter,
                        QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.transform_to_uppercase()
    new_text = widget.get_text('sof', 'eof')
    assert text != new_text


@pytest.mark.parametrize(
    "input_text, expected_text, keys, strip_all",
    [
        ("for i in range(2): ",
         "for i in range(2): \n    \n     \n    ",
         [Qt.Key_Enter, Qt.Key_Enter, ' ', Qt.Key_Enter],
         False),
        ('for i in range(2): ',
         'for i in range(2):\n\n    ',
         [Qt.Key_Enter, Qt.Key_Enter],
         True),
        ('myvar = 2 ',
         'myvar = 2\n',
         [Qt.Key_Enter],
         True),
        ('somecode = 1\nmyvar = 2 \nmyvar = 3',
         'somecode = 1\nmyvar = 2 \nmyvar = 3',
         [' ', Qt.Key_Up, Qt.Key_Up],
         True),
        ('somecode = 1\nmyvar = 2 ',
         'somecode = 1\nmyvar = 2 ',
         [Qt.Key_Left],
         True),
        ('"""This is a string with important spaces\n    ',
         '"""This is a string with important spaces\n    \n',
         [Qt.Key_Enter],
         True),
        ('"""string   ',
         '"""string   \n',
         [Qt.Key_Enter],
         True),
        ('somecode = 1\nmyvar = 2',
         'somecode = 1\nmyvar = 2',
         [' ', (Qt.LeftButton, 0)],
         True),
        ('somecode = 1\nmyvar = 2',
         'somecode = 1\nmyvar = 2 ',
         [' ', (Qt.LeftButton, 23)],
         True),
        ('a=1\na=2 \na=3',
         'a=1\na=2 \na=3',
         [(Qt.LeftButton, 6), Qt.Key_Up],
         True),
        ('def fun():\n    """fun',
         'def fun():\n    """fun\n\n    ',
         [Qt.Key_Enter, Qt.Key_Enter],
         True),
        ('def fun():\n    """fun',
         'def fun():\n    """fun\n    \n    ',
         [Qt.Key_Enter, Qt.Key_Enter],
         False),
        ("('🚫')",
         "('🚫')\n",
         [Qt.Key_Enter],
         True),
        ("def fun():",
         "def fun():\n\n    ",
         [Qt.Key_Enter, Qt.Key_Enter],
         True),
        ("def fun():",
         "def fun():\n\n\n",
         [Qt.Key_Enter, Qt.Key_Enter, Qt.Key_Enter],
         True),
        ("def fun():\n    i = 0\n# no indent",
         "def fun():\n    i = 0\n# no indent\n",
         [Qt.Key_Enter],
         True),
        ("if a:\n    def b():\n        i = 1",
         "if a:\n    def b():\n        i = 1\n\n    ",
         [Qt.Key_Enter, Qt.Key_Enter, Qt.Key_Backspace],
         True),
    ])
def test_editor_rstrip_keypress(codeeditor, qtbot, input_text, expected_text,
                                keys, strip_all):
    """
    Test that whitespace is removed when leaving a line.
    """
    widget = codeeditor
    widget.strip_trailing_spaces_on_modify = strip_all
    widget.set_text(input_text)
    cursor = widget.textCursor()
    cursor.movePosition(QTextCursor.End)
    widget.setTextCursor(cursor)
    for key in keys:
        if isinstance(key, tuple):
            # Mouse event
            button, position = key
            cursor = widget.textCursor()
            cursor.setPosition(position)
            xypos = widget.cursorRect(cursor).center()
            widget.mousePressEvent(QMouseEvent(
                    QEvent.MouseButtonPress, xypos,
                    button, button,
                    Qt.NoModifier))
        else:
            qtbot.keyPress(widget, key)
    assert widget.toPlainText() == expected_text


@pytest.mark.parametrize(
    "input_text, expected_state", [
        ("'string ", [True, False]),
        ('"string ', [True, False]),
        ("'string \\", [True, True]),
        ('"string \\', [True, True]),
        ("'string \\ ", [True, False]),
        ('"string \\ ', [True, False]),
        ("'string ' ", [False, False]),
        ('"string " ', [False, False]),
        ("'string \"", [True, False]),
        ('"string \'', [True, False]),
        ("'string \" ", [True, False]),
        ('"string \' ', [True, False]),
        ("'''string ", [True, True]),
        ('"""string ', [True, True]),
        ("'''string \\", [True, True]),
        ('"""string \\', [True, True]),
        ("'''string \\ ", [True, True]),
        ('"""string \\ ', [True, True]),
        ("'''string ''' ", [False, False]),
        ('"""string """ ', [False, False]),
        ("'''string \"\"\"", [True, True]),
        ('"""string \'\'\'', [True, True]),
        ("'''string \"\"\" ", [True, True]),
        ('"""string \'\'\' ', [True, True]),
    ])
def test_in_string(codeeditor, input_text, expected_state):
    """
    Test that in_string works correctly.
    """
    widget = codeeditor
    widget.set_text(input_text + '\n  ')
    cursor = widget.textCursor()

    for blanks_enabled in [True, False]:
        widget.set_blanks_enabled(blanks_enabled)

        cursor.setPosition(len(input_text))
        assert cursor.position() == len(input_text)
        assert widget.in_string(cursor) == expected_state[0]

        cursor.setPosition(len(input_text) + 3)
        assert widget.in_string(cursor) == expected_state[1]


def test_comment(codeeditor):
    """
    Test that in_string works correctly.
    """
    widget = codeeditor
    widget.set_text("import numpy")
    cursor = widget.textCursor()
    cursor.setPosition(8)
    cursor.setPosition(11, QTextCursor.KeepAnchor)
    widget.setTextCursor(cursor)
    widget.toggle_comment()
    assert widget.toPlainText() == "# import numpy"
    widget.toggle_comment()
    assert widget.toPlainText() == "import numpy"


def test_undo_return(codeeditor, qtbot):
    """Test that we can undo a return."""
    editor = codeeditor
    text = "if True:\n    0"
    returned_text = "if True:\n    0\n    "
    editor.set_text(text)
    cursor = editor.textCursor()
    cursor.setPosition(14)
    editor.setTextCursor(cursor)
    qtbot.keyPress(editor, Qt.Key_Return)
    assert editor.toPlainText() == returned_text
    qtbot.keyPress(editor, "z", modifier=Qt.ControlModifier)
    assert editor.toPlainText() == text


def test_brace_match(codeeditor):
    """Tests for the highlighting of matching parenthesis, braces and brackets.

    Specifically provides regression tests for issues
     * spyder-ide/spyder#2965
     * spyder-ide/spyder#9179
     * spyder-ide/spyder#14374

    If this test fails the best way to investigate is probably to open
    assets/braces.py in Spyder, step through the file and visually
    observe brace matching.

    Some caveats for brace matching can be found in pull request
    spyder-ide/spyder#14376

    The functions being tested are essentially:
     * TextEditBaseWidget.find_brace_match
     * CodeEditor.in_comment
     * CodeEditor.in_string
    """
    # Create editor with contents loaded from assets/brackets.py
    editor = codeeditor
    with open(osp.join(ASSETS, 'braces.py'), 'r') as file:
        editor.set_text(file.read())

    # Each element of *positions* is a two element list:
    #  [position, expected]
    # Here *position* is the position at which to place the cursor and
    # *expected* is what editor.bracepos should be at that location if
    # the brace matching works correctly. Specifically if at *position* ...
    # a) ... there is no brace, then *expected* should be None.
    # b) ... there is an unmatched brace, then *expected* should be a
    #        1-tuple containing position-1
    # c) ... there is a matched brace then *expected* should be a
    #        2-tuple with the first element being position-1 and the
    #        second element being the position of the mathing brace.
    # At the end of each row, a comment has been added that attempts to
    # illustrate in what part of 'braces.py' the cursor is placed in
    # that test case.
    positions = [
        [0, None],       # b
        [5,  (4, 55)],   # b = [
        [56, (55,  4)],  # ]
        [7,  (6, 12)],   # [x
        [13, (12,  6)],  # x*2]
        [29, (28, 54)],  # [1
        [55, (54, 28)],  # ]
        [32, (31, 35)],  # [2
        [36, (35, 31)],  # 3]
        [38, (37, 53)],  # [4
        [54, (53, 37)],  # ]
        [41, (40, 42)],  # [5
        [42, None],      # 5
        [43, (42, 40)],  # 5]
        [47, (46, 52)],  # [7
        [53, (52, 46)],  # 8]
        [63, (62, 143)],  # a = [
        [144, (143, 62)],  # ]
        [69, (68, )],    # """(
        [70, (69, 78)],  # (
        [71, (70, 77)],  # (
        [72, (71, 76)],  # (
        [73, (72, 75)],  # (
        [74, (73, 74)],  # (
        [75, (74, 73)],  # )
        [76, (75, 72)],  # )
        [77, (76, 71)],  # )
        [78, (77, 70)],  # )
        [79, (78, 69)],  # )
        [82, (81, 88)],  # [
        [83, (82, 87)],  # [
        [84, (83, 86)],  # [
        [85, (84, 85)],  # [
        [86, (85, 84)],  # ]
        [87, (86, 83)],  # ]
        [88, (87, 82)],  # ]
        [89, (88, 81)],  # ]
        [90, (89, )],    # ]"""
        [99, (98, )],    # 'x)'
        [105, (104, )],  # 'b('
        [111, (110, )],  # # )
        [112, (111, 128)],  # {[
        [129, (128, 111)],  # ]}
        [113, (112, 127)],  # [(
        [128, (127, 112)],  # )]
        [114, (113, 126)],  # (
        [127, (126, 113)],  # )
    ]
    cursor = editor.textCursor()
    for position, expected in positions:
        cursor.setPosition(position)
        editor.setTextCursor(cursor)
        assert editor.bracepos == expected


def test_editor_backspace_char(codeeditor, qtbot):
    """Regression test for issue spyder-ide/spyder#12663."""
    editor = codeeditor
    text = "0123456789\nabcdefghij\n9876543210\njihgfedcba\n"
    editor.set_text(text)
    expected_column = 7
    cursor = editor.textCursor()
    cursor.setPosition(expected_column)
    editor.setTextCursor(cursor)
    for line in range(3):
        qtbot.keyPress(editor, Qt.Key_Backspace)
        expected_column -= 1
        assert editor.textCursor().columnNumber() == expected_column
        qtbot.keyPress(editor, Qt.Key_Down)
        assert editor.textCursor().columnNumber() == expected_column

    for line in range(3):
        qtbot.keyPress(editor, Qt.Key_Backspace)
        expected_column -= 1
        assert editor.textCursor().columnNumber() == expected_column
        qtbot.keyPress(editor, Qt.Key_Up)
        assert editor.textCursor().columnNumber() == expected_column


def test_editor_backspace_selection(codeeditor, qtbot):
    """Regression test for issue spyder-ide/spyder#12663."""
    editor = codeeditor
    text = "0123456789\nabcdefghij\n9876543210\njihgfedcba\n"
    editor.set_text(text)
    expected_column = 5
    cursor = editor.textCursor()
    cursor.setPosition(expected_column)
    editor.setTextCursor(cursor)

    # This first subtest does not trigger the original bug
    for press in range(3):
        qtbot.keyPress(editor, Qt.Key_Left, Qt.ShiftModifier)
    expected_column -= 3
    qtbot.keyPress(editor, Qt.Key_Backspace)
    assert editor.textCursor().columnNumber() == expected_column
    qtbot.keyPress(editor, Qt.Key_Down)
    assert editor.textCursor().columnNumber() == expected_column

    # However, this second subtest does trigger the original bug
    for press in range(3):
        qtbot.keyPress(editor, Qt.Key_Right, Qt.ShiftModifier)
    qtbot.keyPress(editor, Qt.Key_Backspace)
    assert editor.textCursor().columnNumber() == expected_column
    qtbot.keyPress(editor, Qt.Key_Down)
    assert editor.textCursor().columnNumber() == expected_column


def test_editor_delete_char(codeeditor, qtbot):
    """Regression test for issue spyder-ide/spyder#12663."""
    editor = codeeditor
    text = "0123456789\nabcdefghij\n9876543210\njihgfedcba\n"
    editor.set_text(text)
    expected_column = 2
    cursor = editor.textCursor()
    cursor.setPosition(expected_column)
    editor.setTextCursor(cursor)
    for line in range(3):
        qtbot.keyPress(editor, Qt.Key_Delete)
        assert editor.textCursor().columnNumber() == expected_column
        qtbot.keyPress(editor, Qt.Key_Down)
        assert editor.textCursor().columnNumber() == expected_column

    for line in range(3):
        qtbot.keyPress(editor, Qt.Key_Delete)
        assert editor.textCursor().columnNumber() == expected_column
        qtbot.keyPress(editor, Qt.Key_Up)
        assert editor.textCursor().columnNumber() == expected_column


# Fails in CI Linux tests, but not necessarily on all Linux installations
@pytest.mark.skipif(sys.platform.startswith('linux'), reason='Fail on Linux')
def test_editor_delete_selection(codeeditor, qtbot):
    """Regression test for issue spyder-ide/spyder#12663."""
    editor = codeeditor
    text = "0123456789\nabcdefghij\n9876543210\njihgfedcba\n"
    editor.set_text(text)
    expected_column = 5
    cursor = editor.textCursor()
    cursor.setPosition(expected_column)
    editor.setTextCursor(cursor)

    # This first subtest does not trigger the original bug
    for press in range(3):
        qtbot.keyPress(editor, Qt.Key_Left, Qt.ShiftModifier)
    expected_column -= 3
    qtbot.keyPress(editor, Qt.Key_Delete)
    assert editor.textCursor().columnNumber() == expected_column
    qtbot.keyPress(editor, Qt.Key_Down)
    assert editor.textCursor().columnNumber() == expected_column

    # However, this second subtest does trigger the original bug
    for press in range(3):
        qtbot.keyPress(editor, Qt.Key_Right, Qt.ShiftModifier)
    qtbot.keyPress(editor, Qt.Key_Delete)
    assert editor.textCursor().columnNumber() == expected_column
    qtbot.keyPress(editor, Qt.Key_Up)
    assert editor.textCursor().columnNumber() == expected_column


@pytest.mark.skipif(QT_VERSION.startswith('5.15'),
                    reason='Fixed on Qt 5.15')
def test_qtbug35861(qtbot):
    """This test will detect if upstream QTBUG-35861 is fixed.
    If that happens, then the workarounds for spyder-ide/spyder#12663
    can be removed. Such a fix would probably only happen in the most
    recent Qt version however...
    See also https://bugreports.qt.io/browse/QTBUG-35861
    """
    widget = QTextEdit(None)
    qtbot.addWidget(widget)
    widget.show()

    cursor = widget.textCursor()
    cursor.setPosition(0)
    # Build the text from a single character since a non-fixed width
    # font is used by default.
    cursor.insertText("0000000000\n"*5)

    expected_column = 5
    cursor.setPosition(expected_column)
    widget.setTextCursor(cursor)

    assert widget.textCursor().columnNumber() == expected_column
    for line in range(4):
        qtbot.keyClick(widget, Qt.Key_Backspace)
        assert widget.textCursor().columnNumber() == (expected_column - 1)
        qtbot.keyClick(widget, Qt.Key_Down)
        assert widget.textCursor().columnNumber() == expected_column

    for line in range(4):
        qtbot.keyClick(widget, Qt.Key_Backspace)
        assert widget.textCursor().columnNumber() == (expected_column - 1)
        qtbot.keyClick(widget, Qt.Key_Up)
        assert widget.textCursor().columnNumber() == expected_column


@pytest.mark.parametrize(
    "text",
    [
        "def foo(x):\n    return x\n",      # LF
        "def foo(x):\r\n    return x\r\n",  # CRLF
        "def foo(x):\r    return x\r"       # CR
    ]
)
def test_get_text_with_eol(codeeditor, text):
    """
    Test that get_text_with_eol returns the right text with the most
    common line endings.
    """
    editor = codeeditor
    editor.set_text(text)
    assert editor.get_text_with_eol() == text


def test_format_signature(codeeditor):
    """Test signature format method."""
    signature = """
    concatenate((a1, a2, a...), [b1, b2, b...], axis={}, index=[],
                *args, **kargs)"""
    editor = codeeditor

    format_signature = editor._format_signature(signature, parameter="(a1")

    assert "color:#259AE9'><b>a1</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="a2")
    assert "color:#259AE9'><b>a2</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="a...")
    print(format_signature)
    assert "color:#259AE9'><b>a...</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="[b1")
    assert "color:#259AE9'><b>b1</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="b2")
    assert "color:#259AE9'><b>b2</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="b...")
    assert "color:#259AE9'><b>b...</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="axis")
    assert "color:#259AE9'><b>axis</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="index")
    assert "color:#259AE9'><b>index</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="*args")
    assert "color:#259AE9'><b>*args</b></span>" in format_signature

    format_signature = editor._format_signature(signature, parameter="**kargs")
    assert "color:#259AE9'><b>**kargs</b></span>" in format_signature


def test_delete(codeeditor):
    """Test CodeEditor.delete()."""
    editor = codeeditor
    text = ('def f1(a, b):\n')
    editor.set_text(text)

    # Move to start and delete next character without selection.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == 'ef f1(a, b):'

    # Delete selection.
    cursor = editor.textCursor()
    cursor.select(QTextCursor.WordUnderCursor)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == ' f1(a, b):'

    # Move to end of document - nothing to delete after cursor.
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.End)
    editor.setTextCursor(cursor)
    editor.delete()
    assert editor.get_text_line(0) == ' f1(a, b):'


def test_paste_files(codeeditor, copy_files_clipboard):
    """Test pasting files/folders into the editor."""
    editor = codeeditor
    file_paths = copy_files_clipboard
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    editor.selectAll()
    text = editor.toPlainText()
    path_list_in_editor = [path.strip(',"') for path in text.splitlines()]
    assert len(file_paths) == len(path_list_in_editor)
    for path, expected_path in zip(path_list_in_editor, file_paths):
        assert osp.normpath(path) == osp.normpath(expected_path)


@pytest.mark.parametrize('line_ending_char', ['\n', '\r\n', '\r'])
@pytest.mark.parametrize('text', ['def fun(a, b):\n\treturn a + b',
                                  'https://www.spyder-ide.org'])
def test_paste_text(codeeditor, text, line_ending_char):
    """Test pasting text into the editor."""
    editor = codeeditor
    text = text.replace(osp.os.linesep, line_ending_char)
    cb = QApplication.clipboard()
    cb.setText(text, mode=cb.Clipboard)
    cursor = editor.textCursor()
    cursor.movePosition(QTextCursor.Start)
    editor.setTextCursor(cursor)
    editor.paste()
    for line_no, txt in enumerate(text.splitlines()):
        assert editor.get_text_line(line_no) == txt


def test_cell_highlight(codeeditor, qtbot):
    """Test cells are properly highlighted."""
    editor = codeeditor
    text = ('\n\n\n#%%\n\n\n')
    editor.set_text(text)
    # Set cursor to start of file
    cursor = editor.textCursor()
    cursor.setPosition(0)
    editor.setTextCursor(cursor)
    assert editor.current_cell[0].selectionStart() == 0
    assert editor.current_cell[0].selectionEnd() == 3

    # Set cursor to start second cell
    cursor = editor.textCursor()
    cursor.setPosition(6)
    editor.setTextCursor(cursor)
    assert editor.current_cell[0].selectionStart() == 3
    assert editor.current_cell[0].selectionEnd() == 9

    # Delete cell
    qtbot.keyPress(editor, Qt.Key_Backspace)
    assert editor.current_cell[0].selectionStart() == 0
    assert editor.current_cell[0].selectionEnd() == 8

    # Create cell
    qtbot.keyPress(editor, "%")
    assert editor.current_cell[0].selectionStart() == 3
    assert editor.current_cell[0].selectionEnd() == 9

    # Test delete
    cursor = editor.textCursor()
    cursor.setPosition(5)
    editor.setTextCursor(cursor)
    qtbot.keyPress(editor, Qt.Key_Delete)
    assert editor.current_cell[0].selectionStart() == 0
    assert editor.current_cell[0].selectionEnd() == 8

    # Test undo
    editor.undo()
    assert editor.current_cell[0].selectionStart() == 3
    assert editor.current_cell[0].selectionEnd() == 9
    editor.redo()
    assert editor.current_cell[0].selectionStart() == 0
    assert editor.current_cell[0].selectionEnd() == 8


if __name__ == '__main__':
    pytest.main(['test_codeeditor.py'])
