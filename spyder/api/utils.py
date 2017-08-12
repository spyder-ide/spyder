# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
spyder.api.utils
==================

This package exposes utility functions that can be used in
third-party plugins.
"""

from spyder.config.base import _, get_translation, get_conf_path, DEV
from spyder.config.gui import set_shortcut, config_shortcut

from spyder.utils import icon_manager as ima
from spyder.utils.qthelpers import (create_action, create_toolbutton,
                                    add_actions, get_icon)
from spyder.utils.programs import (is_module_installed, shell_split,
                                   find_program)
from spyder.utils.misc import (add_pathlist_to_PYTHONPATH,
                               get_python_executable, select_port)
