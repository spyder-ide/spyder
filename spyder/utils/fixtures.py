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

# Local imports
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
