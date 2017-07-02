# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
File for running tests programmatically.
"""

# Standard library imports
import os

# Third party imports
import qtpy  # to ensure that Qt4 uses API v2
import pytest


# To activate/deactivate certain things for pytest's only
os.environ['SPYDER_PYTEST'] = 'True'


def main():
    """
    Run pytest tests.
    """
    errno = pytest.main(['-x', 'spyder',  '-v', '-rw', '--durations=10',
                         '--cov=spyder', '--cov-report=term-missing'])

    # sys.exit doesn't work here because some things could be running
    # in the background (e.g. closing the main window) when this point
    # is reached. And if that's the case, sys.exit does't stop the
    # script (as you would expected).
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    main()
