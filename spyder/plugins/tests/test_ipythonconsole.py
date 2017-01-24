# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import os

import pytest
from qtpy.QtCore import Qt
from pytestqt import qtbot
from spyder.py3compat import to_text_string
from spyder.plugins.ipythonconsole import IPythonConsole


# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def ipyconsole_bot(qtbot):
    widget = IPythonConsole(None, testing=True)
    widget.create_new_client()
    qtbot.addWidget(widget)
    return qtbot, widget


# Tests
#-------------------------------
@pytest.mark.skipif(os.name == 'nt', reason="It's timing out on Windows")
def test_sys_argv_clear(ipyconsole_bot):
    qtbot, ipyconsole = ipyconsole_bot
    shell = ipyconsole.get_current_shellwidget()
    client = ipyconsole.get_current_client()

    qtbot.waitUntil(lambda: shell._prompt_html is not None, timeout=6000)
    shell.execute('import sys; A = sys.argv')
    argv = shell.get_value("A")
    assert argv == ['']

def test_console_coloring(ipyconsole_bot):

    def get_console_font_color(syntax_style):
        import pygments
        syntax_path = pygments.__file__.rpartition('/')[0] + '/styles/'
        syntax_style_filename = syntax_path + syntax_style + '.py'
        with open(syntax_style_filename, "r") as syntax_file:
            content = syntax_file.read()
        font_color = content.split('Name:')[1].spit(',')[0]

        return font_color

    def get_console_background_color(style_sheet):
        background_color = style_sheet.split('background-color:')[1]
        background_color = background_color.split(';')[0]
        return background_color

    qtbot, ipyconsole = ipyconsole_bot
    config_options = ipyconsole.config_options()
    
    syntax_style = config_options.JupyterWidget.syntax_style
    style_sheet = config_options.JupyterWidget.style_sheet
    console_font_color = get_console_font_color(syntax_style)
    console_background_color = get_console_background_color(style_sheet)

    from spyder.config.gui import get_color_scheme
    from spyder.config.main import CONF
    selected_color_scheme = CONF.get('color_schemes', 'selected')
    color_scheme = get_color_scheme(selected_color_scheme)
    editor_background_color = color_scheme['background']
    editor_font_color = color_scheme['normal'][0]    

    assert console_background_color == editor_background_color
    assert console_font_color == editor_font_color