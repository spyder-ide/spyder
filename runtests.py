# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Script for running Spyder tests programmatically.
"""

# Standard library imports
import os
import sys

# Third party imports
import pytest


# To run our slow tests only in our CIs
RUN_CI = os.environ.get('CI', None) is not None
run_slow = RUN_CI or '--run-slow' in sys.argv


def main():
    """
    Run pytest tests for Spyder.
    """
    pytest_args = ['spyder',
                   'spyder_profiler',
                   '-vv',
                   '-rw',
                   '--durations=10']

    if RUN_CI:
        pytest_args.append('-x')
    if run_slow:
        pytest_args.append('--run-slow')

    errno = pytest.main(pytest_args)

    # sys.exit doesn't work here because some things could be running in the
    # background (e.g. closing the main window) when this point is reached.
    # If that's the case, sys.exit doesn't stop the script as you would expect.
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    main()
