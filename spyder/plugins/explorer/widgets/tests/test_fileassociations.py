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

# Third party imports
import pytest

# Local imports
from spyder.plugins.explorer.utils import (get_application_icon,
                                           get_installed_applications,
                                           get_username)
