# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from gettext_helpers import do_rescan, do_rescan_files

if __name__ == "__main__":
    do_rescan("spyderlib")
    do_rescan_files(["spyderuiplugins/p_pylint/p_pylint.py",
                     "spyderuiplugins/p_pylint/widgets/pylintgui.py"],
                     "p_pylint", "spyderuiplugins/p_pylint")
    do_rescan_files(["spyderuiplugins/p_profiler/p_profiler.py",
                     "spyderuiplugins/p_profiler/widgets/profilergui.py"],
                     "p_profiler", "spyderuiplugins/p_profiler")
    do_rescan_files(["spyderuiplugins/p_breakpoints/p_breakpoints.py",
                     "spyderuiplugins/p_breakpoints/widgets/breakpointsgui.py"],
                     "p_breakpoints", "spyderuiplugins/p_breakpoints")

