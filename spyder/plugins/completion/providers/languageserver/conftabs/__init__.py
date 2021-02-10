# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Language Server Protocol configuration tabs."""

from .advanced import AdvancedConfigTab
from .docstring import DocstringConfigTab
from .formatting import FormattingStyleConfigTab
from .introspection import IntrospectionConfigTab
from .linting import LintingConfigPage
from .otherlanguages import OtherLanguagesConfigTab


# LSP provider tabs
TABS = [
    LintingConfigPage,
    IntrospectionConfigTab,
    FormattingStyleConfigTab,
    DocstringConfigTab,
    AdvancedConfigTab,
    OtherLanguagesConfigTab
]
