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

from spyder.config.base import is_stable_version


# Use this variable, which corresponds to the html dash symbol, for any command
# that requires a dash below. That way users will be able to copy/paste
# commands from the kernel error message directly to their terminals.
_d = '&#45;'

# Required version of Spyder-kernels
SPYDER_KERNELS_MIN_VERSION = '3.0.0'
SPYDER_KERNELS_MAX_VERSION = '3.1.0'
SPYDER_KERNELS_VERSION = (
    f'>={SPYDER_KERNELS_MIN_VERSION},<{SPYDER_KERNELS_MAX_VERSION}'
)

if is_stable_version(SPYDER_KERNELS_MIN_VERSION):
    SPYDER_KERNELS_CONDA = (
        f'conda install spyder{_d}kernels={SPYDER_KERNELS_MIN_VERSION[:-2]}'
    )
    SPYDER_KERNELS_PIP = (
        f'pip install spyder{_d}kernels=={SPYDER_KERNELS_MIN_VERSION[:-1]}*'
    )
else:
    SPYDER_KERNELS_CONDA = (
        f'conda install {_d}c conda{_d}forge/label/spyder_kernels_rc {_d}c '
        f'conda{_d}forge spyder{_d}kernels={SPYDER_KERNELS_MIN_VERSION}'
    )
    SPYDER_KERNELS_PIP = (
        f'pip install spyder{_d}kernels=={SPYDER_KERNELS_MIN_VERSION}'
    )


class SpyderKernelError(RuntimeError):
    """Error to be shown in client."""
    pass
