# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities to be used with pytest.
"""

# Standard library imports
import shutil
import tempfile

# Third party imports
import pytest
from qtpy.QtGui import QFont

# Local imports
from spyder.widgets.editor import codeeditor
from spyder.config.user import UserConfig
from spyder.config.main import CONF_VERSION, DEFAULTS


@pytest.fixture
def tmpconfig(request):
    """
    Fixtures that returns a temporary CONF element.
    """
    SUBFOLDER = tempfile.mkdtemp()
    CONF = UserConfig('spyder-test',
                      defaults=DEFAULTS,
                      version=CONF_VERSION,
                      subfolder=SUBFOLDER,
                      raw_mode=True,
                      )

    def fin():
        """
        Fixture finalizer to delete the temporary CONF element.
        """
        shutil.rmtree(SUBFOLDER)

    request.addfinalizer(fin)
    return CONF

@pytest.fixture
def editorbot(qtbot):
    widget = codeeditor.CodeEditor(None)
    widget.setup_editor(linenumbers=True, markers=True, tab_mode=False,
                         font=QFont("Courier New", 10),
                         show_blanks=True, color_scheme='Zenburn')
    widget.setup_editor(language='Python')
    qtbot.addWidget(widget)
    widget.show()
    return qtbot, widget
