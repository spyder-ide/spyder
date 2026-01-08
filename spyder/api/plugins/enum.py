# -----------------------------------------------------------------------------
# Copyright (c) 2021- Spyder Project Contributors
#
# Released under the terms of the MIT License
# (see LICENSE.txt in the project root directory for details)
# -----------------------------------------------------------------------------

"""
Enums listing Spyder internal plugins.

.. deprecated:: 6.2

    This module will be renamed to the private :mod:`!_enum` in Spyder 6.2,
    while the current public name will become an alias raising a
    :exc:`DeprecationWarning` on import and be removed in 7.0.

    Use the canonical location, the top-level :mod:`spyder.api.plugins` instead
    which already exports all the public objects of this module.

    For example, ``import spyder.api.plugins`` instead of
    ``import spyder.api.plugins.enums``, or
    ``from spyder.api.plugins import Plugins`` instead of
    ``from spyder.api.plugins.enums import Plugins``.
"""


class DockablePlugins:
    """Pseudo-enum class listing the names of Spyder internal dockable plugins.

    Values correspond to the plugin's
    :attr:`~spyder.api.plugins.SpyderPluginV2.NAME`.
    """

    Console = "internal_console"
    """The Spyder Internal Console plugin."""

    Debugger = "debugger"
    """The Spyder Debugger plugin."""

    Editor = "editor"
    """The Spyder Editor plugin."""

    Explorer = "explorer"
    """The Spyder Files plugin."""

    Find = "find_in_files"
    """The Spyder Find plugin."""

    Help = "help"
    """The Spyder Help plugin."""

    History = "historylog"
    """The Spyder History plugin."""

    IPythonConsole = "ipython_console"
    """The Spyder IPython Console plugin."""

    OnlineHelp = "onlinehelp"
    """The Spyder Online Help plugin."""

    OutlineExplorer = "outline_explorer"
    """The Spyder Outline plugin."""

    Plots = "plots"
    """The Spyder Plots plugin."""

    Profiler = "profiler"
    """The Spyder Profiler plugin."""

    Projects = "project_explorer"
    """The Spyder Projects plugin."""

    Pylint = "pylint"
    """The Spyder Code Analysis plugin."""

    VariableExplorer = "variable_explorer"
    """The Spyder Variable Explorer plugin."""


class Plugins(DockablePlugins):
    """Pseudo-enum class listing the names of all Spyder internal plugins.

    Values correspond to the plugin's
    :attr:`~spyder.api.plugins.SpyderPluginV2.NAME`.

    .. note::

        This "enum" also includes all the members from :class:`DockablePlugins`
        via inheritance from that class.
    """

    All = "all"
    """Wildcard to populate :attr:`~spyder.api.plugins.SpyderPluginV2.REQUIRES`
    with all available plugins.
    """

    Appearance = "appearance"
    """The Spyder Appearance plugin."""

    Application = "application"
    """The Spyder Application plugin."""

    Completions = "completions"
    """The Spyder Completions plugin."""

    ExternalTerminal = "external_terminal"
    """The Spyder External Terminal plugin."""

    Layout = "layout"
    """The Spyder Layout plugin."""

    MainInterpreter = "main_interpreter"
    """The Spyder Main Interpreter plugin."""

    MainMenu = "mainmenu"
    """The Spyder Main Menu plugin."""

    Preferences = "preferences"
    """The Spyder Preferences plugin."""

    PythonpathManager = "pythonpath_manager"
    """The Spyder PYTHONPATH Manager plugin."""

    RemoteClient = "remoteclient"
    """The Spyder Remote Client plugin."""

    Run = "run"
    """The Spyder Run plugin."""

    Shortcuts = "shortcuts"
    """The Spyder Shortcuts plugin."""

    StatusBar = "statusbar"
    """The Spyder Status Bar plugin."""

    Switcher = "switcher"
    """The Spyder Switcher plugin."""

    Toolbar = "toolbar"
    """The Spyder Toolbar plugin."""

    Tours = "tours"
    """The Spyder Tours plugin."""

    UpdateManager = "update_manager"
    """The Spyder Update Manager plugin."""

    WorkingDirectory = "workingdir"
    """The Spyder Working Directory plugin."""


class OptionalPlugins:
    """Pseudo-enum class listing the names of Spyder optional plugins.

    Values correspond to the plugin's
    :attr:`~spyder.api.plugins.SpyderPluginV2.NAME`.
    """

    EnvManager = "spyder_env_manager"
    """The Spyder Environment Manager plugin."""
