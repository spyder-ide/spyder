# -*- coding: utf-8 -*-
# ----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# ----------------------------------------------------------------------------
"""
Tests for explorer plugin utilities.
"""

# Standard imports
import os
import os.path as osp
import sys

# Third party imports
import pytest

# Local imports
from spyder.plugins.explorer.utils import (get_application_icon,
                                           get_installed_applications,
                                           parse_linux_desktop_entry)


def test_get_installed_apps_and_icons(qtbot):
    apps = get_installed_applications()
    assert apps
    for app in apps:
        fpath = apps[app]
        icon = get_application_icon(fpath)
        assert icon
        assert osp.isdir(fpath) or osp.isfile(fpath)


@pytest.mark.skipif(not sys.platform.startswith('linux'),
                    reason="Test for linux only")
def test_parse_linux_desktop_entry():
    apps = get_installed_applications()
    for app in apps:
        fpath = apps[app]
        data = parse_linux_desktop_entry(fpath)
        assert data

        for key in ['name', 'icon_path', 'hidden', 'exec', 'type', 'fpath']:
            assert key in data

        assert fpath == data['fpath']
