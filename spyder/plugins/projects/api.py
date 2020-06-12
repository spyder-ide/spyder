# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Projects Plugin API.
"""

from spyder.plugins.projects.project_types import BaseProjectType


class ProjectsMenuSections:
    New = 'new_section'
    Open = 'open_section'
    Recent = 'recent_section'
    