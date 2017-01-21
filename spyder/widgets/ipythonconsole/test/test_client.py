# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

import sys
import pytest
from pytestqt import qtbot
from spyder.config.main import CONF
from spyder.config.user import NoDefault
from traitlets.config.loader import Config
from spyder.widgets.ipythonconsole import ClientWidget

CONF_SECTION = 'ipython_console'

# Other functions
#--------------------------------
def get_option(option, default=NoDefault):
    return CONF.get(CONF_SECTION, option, default)

def interpreter_versions():
    if CONF.get('main_interpreter', 'default'):
        from IPython.core import release
        versions = dict(
            python_version=sys.version.split("\n")[0].strip(),
            ipython_version=release.version
        )
    else:
        import subprocess
        versions = {}
        pyexec = CONF.get('main_interpreter', 'executable')
        py_cmd = "%s -c 'import sys; print(sys.version.split(\"\\n\")[0])'" % \
                 pyexec
        ipy_cmd = "%s -c 'import IPython.core.release as r; print(r.version)'" \
                  % pyexec
        for cmd in [py_cmd, ipy_cmd]:
            try:
                proc = programs.run_shell_command(cmd)
                output, _err = proc.communicate()
            except subprocess.CalledProcessError:
                output = ''
            output = output.decode().split('\n')[0].strip()
            if 'IPython' in cmd:
                versions['ipython_version'] = output
            else:
                versions['python_version'] = output
    return versions

def additional_options():
    options = dict(
        pylab = get_option('pylab'),
        autoload_pylab = get_option('pylab/autoload'),
        sympy = get_option('symbolic_math'),
        light_color = get_option('light_color'),
        show_banner = get_option('show_banner')
    )
    return options

# Qt Test Fixtures
#--------------------------------
@pytest.fixture
def botclient(qtbot):
    widget = ClientWidget(None, name='Test',
                          history_filename='history.py',
                          config_options=Config(),
                          additional_options=additional_options(),
                          interpreter_versions=interpreter_versions())
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget

# Tests
#-------------------------------
def test_sys_argv_clear(botclient):
    qtbot, client = botclient
    with qtbot.waitSignal(client.shellwidget.executing) as blocker:
        client.shellwidget.silent_exec_method('import sys')
        client.shellwidget.silent_exec_method('print(len(sys.argv))')
    assert client != None

