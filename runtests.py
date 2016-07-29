# -*- coding: utf-8 -*-
#
# Copyright © 2009- The Spyder Development Team
# Licensed under the terms of the MIT License
#

"""
File for running tests programmatically.
"""

# Standard library imports
import sys

# Third party imports
import qtpy  # to ensure that Qt4 uses API v2
import pytest


def main():
    """
    Run pytest tests.
    """
    errno = pytest.main(['-x', 'spyderlib',  '-v', '-rw', '--durations=10',
                         '--cov=spyderlib', '--cov-report=term-missing'])
    sys.exit(errno)

if __name__ == '__main__':
    main()
