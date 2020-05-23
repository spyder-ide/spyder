# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Kernels Contributors
#
# Licensed under the terms of the MIT License
# (see spyder_kernels/__init__.py for details)
# -----------------------------------------------------------------------------

import sys
import os


if __name__ == '__main__':
    # Remove the current working directory from sys.path for Python 3.7+
    # because since that version it's added by default to sys.path when
    # using 'python -m'.
    if sys.version_info[0] == 3 and sys.version_info[1] >= 7:
        cwd = os.getcwd()
        if cwd in sys.path:
            sys.path.remove(cwd)

    from spyder_kernels.console import start
    start.main()
