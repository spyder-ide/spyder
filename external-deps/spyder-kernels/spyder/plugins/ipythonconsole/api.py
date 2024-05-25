# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Spyder IPythonConsole API."""

# Standard library imports
from __future__ import annotations
from typing import TypedDict

# Third-party imports
from typing_extensions import NotRequired  # Available from Python 3.11


class IPythonConsolePyConfiguration(TypedDict):
    """IPythonConsole python execution parameters."""

    # True if the execution is using the current console. False otherwise
    current: bool

    # If True, then the console will start a debugging session if an error
    # occurs. False otherwise.
    post_mortem: bool

    # True if the console is using custom Python arguments. False otherwise.
    python_args_enabled: bool

    # Custom arguments to pass to the console.
    python_args: str

    # If True, then the console will clear all variables before execution.
    # False otherwise.
    clear_namespace: bool

    # If True, then the console will reuse the current namespace. If False,
    # then it will use an empty one.
    console_namespace: bool

    # If not None, then the console will use an alternative run method
    # (e.g. `runfile`, `debugfile` or `debugcell`).
    run_method: NotRequired[str]


class IPythonConsoleWidgetActions:
    # Clients creation
    CreateNewClient = 'new tab'
    CreateCythonClient = 'create cython client'
    CreateSymPyClient = 'create cympy client'
    CreatePyLabClient = 'create pylab client'
    CreateNewClientEnvironment = 'create environment client'

    # Current console actions
    ConnectToKernel = 'connect to kernel'
    Interrupt = 'interrupt kernel'
    Restart = 'Restart kernel'
    ResetNamespace = 'reset namespace'
    ShowEnvironmentVariables = 'Show environment variables'
    ShowSystemPath = 'show system path'
    ToggleElapsedTime = 'toggle elapsed time'

    # Tabs
    RenameTab = 'rename tab'

    # Documentation and help
    IPythonDocumentation = 'ipython documentation'
    ConsoleHelp = 'console help'
    QuickReference = 'quick reference'


class IPythonConsoleWidgetMenus:
    SpecialConsoles = 'special_consoles_submenu'
    Documentation = 'documentation_submenu'
    EnvironmentConsoles = 'environment_consoles_submenu'
    ClientContextMenu = 'client_context_menu'
    TabsContextMenu = 'tabs_context_menu'


class IPythonConsoleWidgetOptionsMenuSections:
    Edit = 'edit_section'
    View = 'view_section'


class IPythonConsoleWidgetTabsContextMenuSections:
    Consoles = 'tabs_consoles_section'
    Edit = 'tabs_edit_section'


class ClientContextMenuSections:
    Edit = 'edit'
    Inspect = 'inspect'
    Array = 'array'
    Export = 'export'
    Clear = 'clear'
    Image = 'image'
    SVG = 'svg'


class ClientContextMenuActions:
    # Edit section
    Cut = 'cut'
    Copy = 'copy'
    CopyRaw = 'copy_raw'
    Paste = 'paste'
    SelectAll = 'select_all'

    # Inspect section
    InspectObject = 'Inspect current object'

    # Array section
    ArrayInline = 'enter array inline'
    ArrayTable = 'enter array table'

    # Export section
    Export = 'export'
    Print = 'print'

    # Clear section
    ClearConsole = 'Clear shell'
    ClearLine = 'clear line'

    # Image section
    CopyImage = 'copy_image'
    SaveImage = 'save_image'

    # Svg section
    CopySvg = 'copy_svg'
    SaveSvg = 'save_svg'


class IPythonConsoleWidgetCornerWidgets:
    ResetButton = "reset_button"
    InterruptButton = "interrupt_button"
    TimeElapsedLabel = "time_elapsed_label"
