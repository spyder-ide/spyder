# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for qcookiecutter widget.
"""

# Standard library imports
import os
from unittest.mock import Mock

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.qcookiecutter import CookiecutterWidget


@pytest.fixture
def coookie_widget(qtbot):
    """Set up CookieCutter Widget."""
    widget = CookiecutterWidget(None)
    qtbot.addWidget(widget)
    return widget


def test_cookiecutter_widget_empty(coookie_widget):
    assert len(coookie_widget._widgets) == 0
    assert len(coookie_widget.get_values()) == 3

    coookie_widget.setup({})
    assert len(coookie_widget._widgets) == 0
    assert len(coookie_widget.get_values()) == 3


@pytest.mark.parametrize("option,value", [
    ("opt", "y"),
    ("opt", "yes"),
    ("opt", "true"),
    ("opt", "YES"),
    ("opt", "True"),
])
def test_cookiecutter_widget_checkbox_yes(coookie_widget, option, value):
    coookie_widget.setup({option: value})
    label, widget = coookie_widget._widgets[option]
    assert len(coookie_widget._widgets) == 1
    assert label == option.capitalize()
    assert widget.isChecked()
    assert widget.get_value() == value


@pytest.mark.parametrize("option,value", [
    ("opt", "n"),
    ("opt", "no"),
    ("opt", "false"),
    ("opt", "NO"),
    ("opt", "False"),
])
def test_cookiecutter_widget_checkbox_no(coookie_widget, option, value):
    coookie_widget.setup({option: value})
    label, widget = coookie_widget._widgets[option]
    assert len(coookie_widget._widgets) == 1
    assert label == option.capitalize()
    assert not widget.isChecked()
    assert widget.get_value() == value


@pytest.mark.parametrize("option,value", [
    ("opt", ["1", "2", "3"]),
])
def test_cookiecutter_widget_list(coookie_widget, option, value):
    coookie_widget.setup({option: value})
    label, widget = coookie_widget._widgets[option]
    assert len(coookie_widget._widgets) == 1
    assert label == option.capitalize()
    assert widget.get_value() == value[0]


@pytest.mark.parametrize("option,value", [
    ("opt", {"1": [1, 2], "2": [3, 4]}),
])
def test_cookiecutter_widget_dict(coookie_widget, option, value):
    coookie_widget.setup({option: value})
    label, widget = coookie_widget._widgets[option]
    assert len(coookie_widget._widgets) == 1
    assert label == option.capitalize()
    assert widget.get_value() == {"1": value["1"]}


@pytest.mark.parametrize("option,value", [
    ("_nope", "nothing"),
    ("__nope_2", "nothing"),
])
def test_cookiecutter_widget_private_variables(coookie_widget, option, value):
    coookie_widget.setup({option: value})
    assert len(coookie_widget._widgets) == 0
    assert len(coookie_widget.get_values()) == 4


def test_cookiecutter_widget_render(coookie_widget):
    coookie_widget.setup({
        "opt_1": "test",
        "opt_2": "{{ cookiecutter.opt_1 }}",
    })
    ows = coookie_widget._widgets
    assert ows["opt_2"][1].get_value() == ows["opt_1"][1].get_value()


def test_cookiecutter_widget_no_render(coookie_widget):
    coookie_widget.setup({
        "opt_1": "test",
        "opt_2": "{{ cookiecutter.opt_1 }}",
        "_opt_3": "{{ cookiecutter.opt_1 }}",
        "__opt_4": "{{ cookiecutter.opt_1 }}",
    })
    ows = coookie_widget.get_values()
    assert ows["_opt_3"] == ows["_opt_3"]
    assert ows["__opt_4"] == ows["__opt_4"]


def test_cookiecutter_widget_validate_passes(qtbot, coookie_widget):
    coookie_widget.setup({
        "opt_1": "test",
    })
    coookie_widget.set_pre_gen_code('''
import sys
sys.exit(0)
''')
    with qtbot.waitSignal(coookie_widget.sig_validated) as blocker:
        coookie_widget.validate()

    assert blocker.args == [0, ""]


def test_cookiecutter_widget_validate_fails(qtbot, coookie_widget):
    coookie_widget.setup({
        "opt_1": "test",
    })
    coookie_widget.set_pre_gen_code('''
import sys
print('ERROR!')  # spyder: test-skip
sys.exit(1)
''')
    with qtbot.waitSignal(coookie_widget.sig_validated) as blocker:
        coookie_widget.validate()

    assert blocker.args == [1, "ERROR! "]


if __name__ == "__main__":
    pytest.main()
