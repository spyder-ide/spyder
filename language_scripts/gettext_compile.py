# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os

# Local imports
from gettext_helpers import do_compile

HERE = os.path.dirname(os.path.realpath(__file__))
REPO_BASE = os.path.dirname(HERE)
PLUGIN_MODULES = {
    'spyder': 'spyder',
    'pylint': 'spyder_pylint',
    'profiler': 'spyder_profiler',
    'breakpoints': 'spyder_breakpoints',
}

if __name__ == "__main__":
    for module, folder in PLUGIN_MODULES.items():
        do_compile(module, os.path.join(REPO_BASE, folder))
