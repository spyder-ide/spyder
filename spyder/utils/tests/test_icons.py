# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""Tests for conda.py"""

# Third party imports
import pytest
from qtpy.QtGui import QIcon

# Local imports
from spyder.utils.icon_manager import ima
from spyder.utils.qthelpers import qapplication


def test_icon_mapping():
    """Test that all the entries on the icon dict for QtAwesome are valid."""
    # Needed instance of QApplication to run QtAwesome
    qapp = qapplication()
    # Check each entry of the dict and try to get the respective icon
    icons_dict = ima._qtaargs
    for key in icons_dict:
        try:
            assert isinstance(ima.icon(key), QIcon)
        except Exception as e:
            print('Invalid icon name:', key)
            raise e


if __name__ == "__main__":
    pytest.main()
