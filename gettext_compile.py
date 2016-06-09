# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

from gettext_helpers import do_compile

if __name__ == "__main__":
    do_compile("spyderlib")
    do_compile("pylint", "spyder_pylint")
    do_compile("profiler", "spyder_profiler")
    do_compile("breakpoints", "spyder_breakpoints")
