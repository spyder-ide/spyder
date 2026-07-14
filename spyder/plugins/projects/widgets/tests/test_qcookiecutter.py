# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
#

"""
Tests for qcookiecutter widget.
"""

# Third party imports
import pytest

# Local imports
from spyder.plugins.projects.widgets.qcookiecutter import CookiecutterWidget


@pytest.fixture(autouse=True)
def mock_load_cookiecutter_project(monkeypatch):
    """
    Avoid real filesystem access in CookiecutterWidget constructor.
    """
    def fake_loader(path, token):
        return {}, None

    monkeypatch.setattr(
        "spyder.plugins.projects.widgets.qcookiecutter.load_cookiecutter_project",
        fake_loader
    )


@pytest.fixture
def coookie_widget(qtbot):
    widget = CookiecutterWidget(None)
    qtbot.addWidget(widget)
    return widget


def test_cookiecutter_widget_empty(coookie_widget):
    coookie_widget.setup()

    assert len(coookie_widget._widgets) == 0

    values = coookie_widget.get_values()
    assert "_extensions" in values
    assert "_copy_without_render" in values
    assert "_new_lines" in values


@pytest.mark.parametrize("value", ["y", "yes", "true", "YES", "True"])
def test_cookiecutter_widget_checkbox_yes(coookie_widget, value):

    coookie_widget._cookiecutter_settings = {"opt": value}
    coookie_widget.setup()

    field_type, widget_in, widget = coookie_widget._widgets["opt"]

    assert field_type == "checkbox"
    assert widget_in.isChecked()


@pytest.mark.parametrize("value", ["n", "no", "false", "NO", "False"])
def test_cookiecutter_widget_checkbox_no(coookie_widget, value):
    coookie_widget._cookiecutter_settings = {"opt": value}
    coookie_widget.setup()

    field_type, widget_in, widget = coookie_widget._widgets["opt"]

    assert field_type == "checkbox"
    assert not widget_in.isChecked()


def test_cookiecutter_widget_list(coookie_widget):
    coookie_widget._cookiecutter_settings = {"opt": ["1", "2", "3"]}
    coookie_widget.setup()

    widget = coookie_widget._widgets["opt"][1]
    assert widget.currentData() == "1"


def test_cookiecutter_widget_dict(coookie_widget):
    value = {"1": [1, 2], "2": [3, 4]}
    coookie_widget._cookiecutter_settings = {"opt": value}
    coookie_widget.setup()

    widget = coookie_widget._widgets["opt"][1]
    assert widget.currentData() == value["1"]


@pytest.mark.parametrize("opt", ["_nope", "__nope"])
def test_cookiecutter_widget_private_variables(coookie_widget, opt):

    coookie_widget._cookiecutter_settings = {opt: "hidden"}
    coookie_widget.setup()

    assert opt not in coookie_widget._widgets

    values = coookie_widget.get_values()
    assert opt in values


def test_cookiecutter_widget_jinja_not_in_form(coookie_widget):

    coookie_widget._cookiecutter_settings = {
        "opt_1": "hello",
        "opt_2": "{{ cookiecutter.opt_1 }}",
    }

    coookie_widget.setup()

    assert "opt_1" in coookie_widget._widgets
    assert "opt_2" not in coookie_widget._widgets
    assert "opt_2" in coookie_widget._rendered_settings


def test_cookiecutter_widget_render(coookie_widget):

    coookie_widget._cookiecutter_settings = {
        "opt_1": "test",
        "opt_2": "{{ cookiecutter.opt_1 }}",
    }

    coookie_widget.setup()

    assert coookie_widget._rendered_values["opt_2"] == ""


def test_cookiecutter_widget_no_render_on_private(coookie_widget):

    coookie_widget._cookiecutter_settings = {
        "_opt": "{{ cookiecutter.opt }}",
        "__opt2": "{{ cookiecutter.opt }}"
    }

    coookie_widget.setup()

    values = coookie_widget.get_values()

    assert values["_opt"] == "{{ cookiecutter.opt }}"
    assert values["__opt2"] == "{{ cookiecutter.opt }}"


def test_cookiecutter_widget_validate_empty_field(coookie_widget):

    coookie_widget._cookiecutter_settings = {
        "opt": "text"
    }

    coookie_widget.setup()

    reasons = coookie_widget.validate()
    assert reasons == {"missing_info": True}



def test_cookiecutter_widget_validate_no_pre_gen(coookie_widget):

    coookie_widget._cookiecutter_settings = {
        "opt": "filled"
    }

    coookie_widget.setup()

    reasons = coookie_widget.validate()
    assert reasons == {'missing_info': True}


def test_cookiecutter_widget_validate_pre_gen_error(coookie_widget):

    coookie_widget._cookiecutter_settings = {"opt": ["1", "2", "3"]}
    coookie_widget._pre_gen_code = """
import sys
print("boom")
sys.exit(1)
"""

    coookie_widget.setup()

    result = coookie_widget.validate()

    assert result["cookiecutter_error"]
    assert "boom" in result["cookiecutter_error_detail"]


def test_cookiecutter_widget_validate_pre_gen_ok(coookie_widget):

    coookie_widget._cookiecutter_settings = {"opt": ["1", "2", "3"]}
    coookie_widget._pre_gen_code = "import sys; sys.exit(0)"

    coookie_widget.setup()

    result = coookie_widget.validate()
    assert result is None


def test_cookiecutter_widget_create_project(monkeypatch, coookie_widget):

    def fake_generate(path, location, values):
        return True, "ok"

    monkeypatch.setattr(
        "spyder.plugins.projects.widgets.qcookiecutter.generate_cookiecutter_project",
        fake_generate
    )

    status = coookie_widget.create_project("/tmp")

    assert status is True


if __name__ == "__main__":
    pytest.main()
