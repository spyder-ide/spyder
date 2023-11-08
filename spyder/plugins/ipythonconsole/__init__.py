# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.plugins.ipythonconsole
=============================

IPython Console plugin based on QtConsole
"""

# Required version of Spyder-kernels
SPYDER_KERNELS_MIN_VERSION = '2.5.0'
SPYDER_KERNELS_MAX_VERSION = '2.6.0'
SPYDER_KERNELS_VERSION = (
    f'>={SPYDER_KERNELS_MIN_VERSION},<{SPYDER_KERNELS_MAX_VERSION}')
SPYDER_KERNELS_CONDA = (
    f'conda install spyder&#45;kernels={SPYDER_KERNELS_MIN_VERSION[:-2]}')
SPYDER_KERNELS_PIP = (
    f'pip install spyder&#45;kernels=={SPYDER_KERNELS_MIN_VERSION[:-1]}*')
