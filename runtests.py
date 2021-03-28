# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Script for running Spyder tests programmatically.
"""

# Standard library imports
import argparse
import os

# To activate/deactivate certain things for pytests only
# NOTE: Please leave this before any other import here!!
os.environ['SPYDER_PYTEST'] = 'True'

# Third party imports
# NOTE: This needs to be imported before any QApplication.
# Don't remove it or change it to a different location!
# pylint: disable=wrong-import-position
from qtpy import QtWebEngineWidgets  # pylint: disable=unused-import
import pytest


# To run our slow tests only in our CIs
CI = os.environ.get('CI', None) is not None
RUN_SLOW = os.environ.get('RUN_SLOW', None) == 'true'


def run_pytest(run_slow=False, extra_args=None):
    """Run pytest tests for Spyder."""
    # Be sure to ignore subrepos
    pytest_args = ['-vv', '-rw', '--durations=10', '--ignore=./external-deps',
                   '-W ignore::UserWarning']

    if CI:
        # Exit on first failure and show coverage
        pytest_args += ['-x', '--cov=spyder', '--no-cov-on-fail']

        # To display nice tests resume in Azure's web page
        if os.environ.get('AZURE', None) is not None:
            pytest_args += ['--cache-clear', '--junitxml=result.xml']
    if run_slow or RUN_SLOW:
        pytest_args += ['--run-slow']
    # Allow user to pass a custom test path to pytest to e.g. run just one test
    if extra_args:
        pytest_args += extra_args

    print("Pytest Arguments: " + str(pytest_args))
    errno = pytest.main(pytest_args)

    # sys.exit doesn't work here because some things could be running in the
    # background (e.g. closing the main window) when this point is reached.
    # If that's the case, sys.exit doesn't stop the script as you would expect.
    if errno != 0:
        raise SystemExit(errno)


def main():
    """Parse args then run the pytest suite for Spyder."""
    test_parser = argparse.ArgumentParser(
        usage='python runtests.py [-h] [--run-slow] [pytest_args]',
        description="Helper script to run Spyder's test suite")
    test_parser.add_argument('--run-slow', action='store_true', default=False,
                             help='Run the slow tests')
    test_args, pytest_args = test_parser.parse_known_args()
    run_pytest(run_slow=test_args.run_slow, extra_args=pytest_args)


if __name__ == '__main__':
    main()
