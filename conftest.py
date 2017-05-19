# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
File for customising pytest.
"""

def pytest_configure(config):
    import qtpy
    import os
    os.environ['SPYDER_PYTEST'] = 'True'
