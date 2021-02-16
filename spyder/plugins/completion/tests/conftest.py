# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)


# This is needed to avoid an error because QtAwesome
# needs a QApplication to work correctly.
from spyder.utils.qthelpers import qapplication
app = qapplication()

# PyTest imports
import pytest
from pytestqt.plugin import QtBot


@pytest.fixture(scope="module")
def qtbot_module(qapp, request):
    """Module fixture for qtbot."""
    result = QtBot(request)
    return result
