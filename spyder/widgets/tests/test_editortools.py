# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for editortool.py
"""

# Third party imports
import pytest

# Local imports
from spyder.widgets.editortools import OutlineExplorerWidget
from spyder.widgets.sourcecode.codeeditor import CodeEditor


text = ("# -*- coding: utf-8 -*-\n"
        "\n"
        "# %% functions\n"
        "\n"
        "\n"
        "# ---- func 1 and 2\n"
        "\n"
        "def func1():\n"
        "    for i in range(3):\n"
        "        print(i)\n"
        "\n"
        "\n"
        "def func3():\n"
        "    if True:\n"
        "        pass\n"
        "\n"
        "\n"
        "# ---- func 3\n"
        "\n"
        "def func3():\n"
        "    pass\n"
        "\n"
        "\n"
        "# %% classes\n"
        "\n"
        "class class1(object):\n"
        "\n"
        "    def __ini__(self):\n"
        "        super(class1, self).__init__()\n"
        "\n"
        "    def method1(self):\n"
        "        if False:\n"
        "            pass\n"
        "\n"
        "    def method2(self):\n"
        "        try:\n"
        "            assert 2 == 3\n"
        "        except AssertionError:\n"
        "            pass")


# Qt Test Fixtures
# --------------------------------

@pytest.fixture
def outline_explorer_bot(qtbot):
    editor = CodeEditor()
    editor = CodeEditor(None)
    editor.set_language('py', 'test_outline_explorer.py')
    editor.set_text(text)

    outline_explorer = OutlineExplorerWidget()
    outline_explorer.set_current_editor(
            editor, 'test_outline_explorer.py', False, False)

    qtbot.addWidget(outline_explorer)

    return outline_explorer, qtbot


# Test OutlineExplorerWidget
# -------------------------------

def test_outline_explorer(outline_explorer_bot):
    """Basic test to asser the outline explorer is initializing correctly."""
    outline_explorer, qtbot = outline_explorer_bot
    outline_explorer.show()
    outline_explorer.setFixedSize(400, 350)
    assert outline_explorer


if __name__ == "__main__":
    import os
    pytest.main(['-x', os.path.basename(__file__), '-v', '-rw'])
