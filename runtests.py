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
import sys

# Third party imports
import qtpy  # to ensure that Qt4 uses API v2
import pytest


# To run our slow tests only in our CIs
run_slow = False
if os.environ.get('CI', None) is not None or '--run-slow' in sys.argv:
    run_slow = True


# Skip slow tests for macOS and Python 3 in our CIs because they
# don't run correctly
if (sys.platform == 'darwin' and sys.version_info[0] == 3 and
        os.environ.get('CI', None) is not None):
    run_slow = False


def main():
    """
    Run pytest tests.
    """
    pytest_args = ['spyder',
                   '-x',
                   '-vv',
                   '-rw',
                   '--durations=10',
                   '--cov=spyder']

    if run_slow:
        pytest_args.append('--run-slow')

    errno = pytest.main(pytest_args)

    # sys.exit doesn't work here because some things could be running
    # in the background (e.g. closing the main window) when this point
    # is reached. And if that's the case, sys.exit does't stop the
    # script (as you would expected).
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    main()
