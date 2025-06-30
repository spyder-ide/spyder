# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Actions defined in the Spyder editor plugin.
"""

class EditorWidgetActions:
    # File operations
    PrintPreview = "print_preview_action"
    Print = "print_action"

    # Navigation
    GoToNextFile = "Go to next file"
    GoToPreviousFile = "Go to previous file"

    # Find/Search operations
    FindText = "Find text"
    FindNext = "Find next"
    FindPrevious = "Find previous"
    ReplaceText = "Replace text"

    # Source code operations
    ShowTodoList = "show_todo_list_action"
    ShowCodeAnalysisList = "show_code_analaysis_action"
    GoToPreviousWarning = "Previous warning"
    GoToNextWarning = "Next warning"
    GoToLastEditLocation = "Last edit location"
    GoToPreviousCursorPosition = "Previous cursor position"
    GoToNextCursorPosition = "Next cursor position"
    WinEOL = "win_eol_action"
    LinuxEOL = "linux_eol_action"
    MacEOL = "mac_eol_action"
    RemoveTrailingSpaces = "remove_trailing_spaces_action"
    FormatCode = "autoformating"
    FixIndentation = "fix_indentation_action"

    # Checkable operations
    ShowBlanks = "blank_spaces_action"
    WrapLines = "wrap_lines_action"
    ShowIndentGuides = "show_indent_guides_action"
    ShowCodeFolding = "show_code_folding_action"
    ShowClassFuncDropdown = "show_class_func_dropdown_action"
    ShowCodeStyleWarnings = "pycodestyle_action"
    ShowDoctringWarnings = "pydocstyle_action"
    UnderlineErrors = "underline_errors_action"

    # Stack menu
    GoToLine = "Go to line"
    SetWorkingDirectory = "set_working_directory_action"

    # Edit operations
    NewCell = "create_new_cell"
    ToggleComment = "Toggle comment"
    Blockcomment = "Blockcomment"
    Unblockcomment = "Unblockcomment"

    Indent = "indent_action"
    Unindent = "unindent_action"
    TransformToUppercase = "transform to uppercase"
    TransformToLowercase = "transform to lowercase"

    Undo = "Undo"
    Redo = "Redo"
    Copy = "Copy"
    Cut = "Cut"
    Paste = "Paste"
    SelectAll = "Select All"
