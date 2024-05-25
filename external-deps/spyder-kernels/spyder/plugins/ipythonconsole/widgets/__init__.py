# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright (c) 2009- Spyder Project Contributors
#
# Distributed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------


"""
Widgets for the IPython Console.
"""

from .control import ControlWidget, PageControlWidget
from .debugging import DebuggingWidget
from .help import HelpWidget
from .namespacebrowser import NamepaceBrowserWidget
from .figurebrowser import FigureBrowserWidget
from .kernelconnect import KernelConnectionDialog
from .restartdialog import ConsoleRestartDialog
from .status import MatplotlibStatus

# ShellWidget contains the other widgets and ClientWidget
# contains it
from .shell import ShellWidget
from .client import ClientWidget

# Constant for different types of completion available
COMPLETION_WIDGET_TYPE = {0: "droplist", 1: "ncurses", 2: "plain"}
