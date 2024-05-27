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
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, SpyderStyleSheet


# ---- Stylesheet
# -----------------------------------------------------------------------------
class _MenuBarStylesheet(SpyderStyleSheet):
    """Stylesheet for menubars used in Spyder."""

    def set_stylesheet(self):
        css = self.get_stylesheet()

        # Set the same color as the one used for the app toolbar
        css.QMenuBar.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_4
        )

        # Give more padding and margin to items
        css['QMenuBar::item'].setValues(
            padding=f'{2 * AppStyle.MarginSize}px',
            margin='0px 2px'
        )

        # Remove padding when pressing main menus
        css['QMenuBar::item:pressed'].setValues(
            padding='0px'
        )

        # Set hover and pressed state of items in the menu bar
        for state in ['selected', 'pressed']:
            # Don't use a different color for the QMenuBar pressed state
            # because a lighter color has too little contrast with the text.
            bg_color = SpyderPalette.COLOR_BACKGROUND_5

            css[f"QMenuBar::item:{state}"].setValues(
                backgroundColor=bg_color,
                borderRadius=SpyderPalette.SIZE_BORDER_RADIUS
            )


MENUBAR_STYLESHEET = _MenuBarStylesheet()


# ---- Menu constants
# -----------------------------------------------------------------------------
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
    FindInText = 'find_text_section'
    FindInFiles = 'find_files_section'


class SourceMenuSections:
    Options = 'options_section'
    Linting = 'linting_section'
    Cursor = 'cursor_section'
    Formatting = 'formatting_section'
    CodeAnalysis = 'code_analysis_section'


class RunMenuSections:
    Run = 'run_section'
    RunExtras = 'run_extras_section'
    RunInExecutors = 'executors_section'

class DebugMenuSections:
    StartDebug = 'start_debug_section'
    ControlDebug = 'control_debug_section'
    EditBreakpoints = 'edit_breakpoints_section'


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


# ---- App menu class
# -----------------------------------------------------------------------------
class ApplicationMenu(SpyderMenu):
    """
    Spyder main window application menu.

    This class provides application menus with some predefined functionality.
    """

    APP_MENU = True
