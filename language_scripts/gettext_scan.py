# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os

# Local imports
from gettext_helpers import do_rescan, do_rescan_files

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_BASE = os.path.dirname(HERE)
PLUGIN_MODULES = {
    'pylint': (
        'spyder_pylint',
        ["spyder_pylint/pylint.py",
         "spyder_pylint/widgets/pylintgui.py"],
        ),
    'profiler': (
        'spyder_profiler',
        ["spyder_profiler/profiler.py",
         "spyder_profiler/widgets/profilergui.py"],
        ),
    'breakpoints': (
        'spyder_breakpoints',
        ["spyder_breakpoints/breakpoints.py",
         "spyder_breakpoints/widgets/breakpointsgui.py"],
         ),
    }


if __name__ == "__main__":
    do_rescan(os.path.join(REPO_BASE, "spyder"))
    for module, (folder, files) in PLUGIN_MODULES.items():
        files = [os.path.join(REPO_BASE, f) for f in files]
        do_rescan_files(files, module, os.path.join(REPO_BASE, folder)),
