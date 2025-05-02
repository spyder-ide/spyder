# -*- coding: utf-8 -*-
#
# Copyright © Spyder Kernels Contributors
# Licensed under the terms of the MIT License
#

"""
Main configuration file for Pytest
"""

import pytest


@pytest.fixture
def anyio_backend():
    return 'asyncio'
