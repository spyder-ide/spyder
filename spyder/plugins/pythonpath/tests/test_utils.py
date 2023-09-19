# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

import os

from spyder.plugins.pythonpath.utils import check_path


def test_check_path(tmp_path):
    """
    Test for the check_path utility function.

    Test cases taken from
    https://discuss.python.org/t/understanding-site-packages-directories/12959
    """

    # A regular path must pass the check
    assert check_path(str(tmp_path / 'foo'))

    if os.name == 'nt':
        assert not check_path(
            'C:\\Users\\User\\Anaconda3\\envs\\foo\\Lib\\site-packages'
        )
        assert not check_path('lib\\site-packages')
        assert not check_path('lib\\dist-packages')
        assert not check_path('Lib/site-packages')
    else:
        # One digit Python versions
        assert not check_path('lib/python3.9/site-packages')

        # Two digit Python versions
        assert not check_path('lib/python3.11/site-packages')

        # Global Python in Redhat and derivatives
        assert not check_path('lib64/python3.10/site-packages')

        # Global Python in Debian and derivatives
        assert not check_path('lib/python3/dist-packages')

        # Framework installations on Mac
        assert not check_path('Library/Python/3.9/lib/python/site-packages')

        # Paths that don't have digits must pass
        assert check_path('lib/pythonX.Y/site-packages')
