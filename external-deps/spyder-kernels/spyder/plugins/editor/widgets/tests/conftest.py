# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Testing utilities for Editor/EditorStack widgets to be used with pytest.
"""

# Local imports
from spyder.plugins.editor.tests.conftest import (
    editor_plugin,
    editor_plugin_open_files,
    python_files,
)
from spyder.plugins.completion.tests.conftest import (
    completion_plugin_all_started,
    completion_plugin_all,
    qtbot_module,
)
from spyder.plugins.editor.widgets.editorstack.tests.conftest import (
    setup_editor,
    completions_editor,
)
