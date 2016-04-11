# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from gettext_helpers import do_rescan, do_rescan_files

if __name__ == "__main__":
    do_rescan("spyderlib")
    do_rescan_files(["spyplugins/ui/pylint/pylint.py",
                     "spyplugins/ui/pylint/widgets/pylintgui.py"],
                     "pylint", "spyplugins/ui/pylint")
    do_rescan_files(["spyplugins/ui/profiler/profiler.py",
                     "spyplugins/ui/profiler/widgets/profilergui.py"],
                     "profiler", "spyplugins/ui/profiler")
    do_rescan_files(["spyplugins/ui/breakpoints/breakpoints.py",
                     "spyplugins/ui/breakpoints/widgets/breakpointsgui.py"],
                     "breakpoints", "spyplugins/ui/breakpoints")

