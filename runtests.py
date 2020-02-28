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
import argparse

# To activate/deactivate certain things for pytest's only
# NOTE: Please leave this before any other import here!!
os.environ['SPYDER_PYTEST'] = 'True'

# Third party imports
# NOTE: This needs to be imported before any QApplication.
# Don't remove it or change it to a different location!
from qtpy import QtWebEngineWidgets
import pytest


# To run our slow tests only in our CIs
CI = os.environ.get('CI', None) is not None
RUN_SLOW = os.environ.get('RUN_SLOW', None) == 'true'


def main(run_slow=False, extra_args=None):
    """
    Run pytest tests for Spyder.
    """
    pytest_args = ['spyder',
                   '-vv',
                   '-rw',
                   '--durations=10']

    if CI:
        # Exit on first failure and show coverage
        pytest_args += ['-x', '--cov=spyder', '--no-cov-on-fail']

        # Run slow tests only
        if RUN_SLOW:
            pytest_args += ['--run-slow']

        # To display nice tests resume in Azure's web page
        if os.environ.get('AZURE', None) is not None:
            pytest_args += ['--cache-clear', '--junitxml=result.xml']
    elif run_slow:
        pytest_args += ['--run-slow']
    elif extra_args:
        pytest_args += extra_args

    print("Pytest Arguments: " + str(pytest_args))
    errno = pytest.main(pytest_args)

    # sys.exit doesn't work here because some things could be running in the
    # background (e.g. closing the main window) when this point is reached.
    # If that's the case, sys.exit doesn't stop the script as you would expect.
    if errno != 0:
        raise SystemExit(errno)


if __name__ == '__main__':
    test_parser = argparse.ArgumentParser(
        usage='python runtests.py [--run-slow] [-- pytest_args]')
    test_parser.add_argument('--run-slow', action='store_true',
                             default=False,
                             help='Run the slow tests')
    test_parser.add_argument('pytest_args', nargs='*',
                             help="Args to pass to pytest")
    test_args = test_parser.parse_args()
    main(run_slow=test_args.run_slow, extra_args=test_args.pytest_args)
