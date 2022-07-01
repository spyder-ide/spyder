# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Spyder application menu constants.
"""
# Local imports
from spyder.api.widgets.menus import SpyderMenu


class ApplicationContextMenu:
    Documentation = 'context_documentation_section'
    About = 'context_about_section'


class ApplicationMenus:
    File = 'file_menu'
    Edit = 'edit_menu'
    Search = 'search_menu'
    Source = 'source_menu'
    Run = 'run_menu'
    Debug = 'debug_menu'
    Consoles = 'consoles_menu'
    Projects = 'projects_menu'
    Tools = 'tools_menu'
    View = 'view_menu'
    Help = 'help_menu'


class FileMenuSections:
    New = 'new_section'
    Open = 'open_section'
    Save = 'save_section'
    Print = 'print_section'
    Close = 'close_section'
    Switcher = 'switcher_section'
    Navigation = 'navigation_section'
    Restart = 'restart_section'


class EditMenuSections:
    UndoRedo = 'undo_redo_section'
    Copy = 'copy_section'
    Editor = 'editor_section'


class SearchMenuSections:
    Search = 'undo_redo_section'


class SourceMenuSections:
    Options = 'options_section'
    Linting = 'linting_section'
    Cursor = 'cursor_section'
    Actions = 'actions_section'
    CodeAnalysis = 'code_analysis_section'


class RunMenuSections:
    Run = 'run_section'
    RunExtras = 'run_extras_section'
    Profile = 'profile_section'


class DebugMenuSections:
    Run = 'debug_section'
    Options = 'options_section'


class ConsolesMenuSections:
    New = 'new_section'
    Restart = 'restart_section'


class ProjectsMenuSections:
    New = 'new_section'
    Open = 'open_section'
    Extras = 'extras_section'


class ToolsMenuSections:
    Tools = 'tools_section'
    External = 'external_section'
    Extras = 'extras_section'


class ViewMenuSections:
    Top = 'top_section'
    Pane = 'pane_section'
    Toolbar = 'toolbar_section'
    Layout = 'layout_section'
    Bottom = 'bottom_section'


class HelpMenuSections:
    Documentation = 'documentation_section'
    Support = 'support_section'
    ExternalDocumentation = 'external_documentation_section'
    About = 'about_section'


class ApplicationMenu(SpyderMenu):
    """
    Spyder Main Window application Menu.

    This class provides application menus with some predefined functionality
    and section definition.
    """
