# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Enum of Spyder internal plugins."""


class Plugins:
    """
    Convenience class for accessing Spyder internal plugins.
    """
    All = "all"   # Wildcard to populate REQUIRES with all available plugins
    Appearance = 'appearance'
    Application = 'application'
    Breakpoints = 'breakpoints'
    Completions = 'completions'
    Console = 'internal_console'
    Editor = 'editor'
    Explorer = 'explorer'
    Find = 'find_in_files'
    Help = 'help'
    History = 'historylog'
    IPythonConsole = 'ipython_console'
    Layout = 'layout'
    MainInterpreter = 'main_interpreter'
    MainMenu = 'mainmenu'
    OnlineHelp = 'onlinehelp'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Preferences = 'preferences'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    PythonpathManager = 'pythonpath_manager'
    Run = 'run'
    Shortcuts = 'shortcuts'
    StatusBar = 'statusbar'
    Toolbar = "toolbar"
    Tours = 'tours'
    VariableExplorer = 'variable_explorer'
    WorkingDirectory = 'workingdir'


class DockablePlugins:
    Breakpoints = 'breakpoints'
    Console = 'internal_console'
    Editor = 'editor'
    Explorer = 'explorer'
    Find = 'find_in_files'
    Help = 'help'
    History = 'historylog'
    IPythonConsole = 'ipython_console'
    OnlineHelp = 'onlinehelp'
    OutlineExplorer = 'outline_explorer'
    Plots = 'plots'
    Profiler = 'profiler'
    Projects = 'project_explorer'
    Pylint = 'pylint'
    VariableExplorer = 'variable_explorer'
