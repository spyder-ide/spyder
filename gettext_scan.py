# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from gettext_helpers import do_rescan, do_rescan_files

if __name__ == "__main__":
    do_rescan("spyderlib")
    do_rescan_files(["spyderplugins/p_pylint/p_pylint.py",
                     "spyderplugins/p_pylint/widgets/pylintgui.py"],
                     "p_pylint", "spyderplugins/p_pylint")
    do_rescan_files(["spyderplugins/p_profiler/p_profiler.py",
                     "spyderplugins/p_profiler/widgets/profilergui.py"],
                     "p_profiler", "spyderplugins/p_profiler")
    do_rescan_files(["spyderplugins/p_breakpoints/p_breakpoints.py",
                     "spyderplugins/p_breakpoints/widgets/breakpointsgui.py"],
                     "p_breakpoints", "spyderplugins/p_breakpoints")
