# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Tours API."""


# TODO: Known issues
# How to handle if an specific dockwidget does not exists/load, like ipython
# on python3.3, should that frame be removed? should it display a warning?


class SpyderWidgets:
    """List of supported widgets to highlight/decorate."""

    # Panes
    ipython_console = 'ipyconsole'
    editor = 'editor'
    file_explorer = 'explorer'
    help_plugin = 'help'
    variable_explorer = 'variableexplorer'
    history_log = "historylog"
    plots_plugin = "plots"
    find_plugin = "findinfiles"
    profiler = "profiler"
    code_analysis = "pylint"

    # Editor objects
    editor_line_number_area = (
        'editor.get_current_editor().panels._panels[PanelPosition.LEFT].'
        'values()'
    )
    editor_scroll_flag_area = 'editor.get_current_editor().scrollflagarea'

    # Toolbars
    toolbars = ''
    toolbars_active = ''
    toolbar_file = ''
    toolbar_edit = ''
    toolbar_run = ''
    toolbar_debug = ''
    toolbar_main = ''

    status_bar = ''
    menu_bar = ''
    menu_file = ''
    menu_edit = ''
