# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.app
==========

Modules related to starting and restarting the Spyder application
"""
import os
import sys

# On macOS conda installations, sys.executable may be a symlink in the
# application bundle, and therefore should be resolved to the executable in the
# environment. Also store the orignal sys.executable.
SHORTCUT_EXE = None
if sys.platform == "darwin" and sys.executable.endswith("MacOS/python"):
    SHORTCUT_EXE = sys.executable
    sys.executable = os.readlink(sys.executable)
