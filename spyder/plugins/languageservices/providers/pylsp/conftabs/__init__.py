# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Preference tabs of the pylsp provider."""

from .advanced import AdvancedConfigTab
from .formatting import FormattingConfigTab
from .introspection import IntrospectionConfigTab
from .linting import LintingConfigTab

TABS = [
    LintingConfigTab,
    IntrospectionConfigTab,
    FormattingConfigTab,
    AdvancedConfigTab,
]
