# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

from gettext_helpers import do_rescan, do_rescan_files

if __name__ == "__main__":
    do_rescan("spyder")
    do_rescan_files(["spyder_pylint/pylint.py",
                     "spyder_pylint/widgets/pylintgui.py"],
                     "pylint", "spyder_pylint")
    do_rescan_files(["spyder_profiler/profiler.py",
                     "spyder_profiler/widgets/profilergui.py"],
                     "profiler", "spyder_profiler")
    do_rescan_files(["spyder_breakpoints/breakpoints.py",
                     "spyder_breakpoints/widgets/breakpointsgui.py"],
                     "breakpoints", "spyder_breakpoints")
