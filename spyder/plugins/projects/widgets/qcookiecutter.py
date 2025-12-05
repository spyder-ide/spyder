# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# Copyright © Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Cookiecutter widget.
"""

import sys
import tempfile
from collections import OrderedDict

from jinja2 import Template
from qtpy import QtCore
from qtpy import QtWidgets

from spyder.api.translations import _
from spyder.plugins.projects.utils.cookie import (
    generate_cookiecutter_project, load_cookiecutter_project)
from spyder.utils.icon_manager import ima
from spyder.widgets.config import SpyderConfigPage


class Namespace:
    """
    Namespace to provide a holder for attributes when rendering a template.
    """

    def __init__(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)


class CookiecutterDialog(QtWidgets.QDialog):
    """
    QDialog to display cookiecutter.json options.

    cookiecutter_settings: dict
        A cookiecutter.json settings content.
    pre_gen_code: str
        The code of the pregeneration script.
    """

    sig_validated = QtCore.Signal(str)
    """
    This signal is emitted after validation has been executed.

    It provides the process exit code and the output captured.
    """

    def __init__(self, parent, cookiecutter_settings=None, pre_gen_code=None):
        super().__init__(parent)

        self._widget = CookiecutterWidget(
            self, cookiecutter_settings,
            pre_gen_code
        )
        self._info_label = QtWidgets.QLabel()
        self._validate_button = QtWidgets.QPushButton("Validate")

        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self._widget)
        layout.addWidget(self._info_label)
        layout.addWidget(self._validate_button)
        self.setLayout(layout)

        # Signals
        self._validate_button.clicked.connect(self.validate)
        self._widget.sig_validated.connect(self._set_message)
        self._widget.sig_validated.connect(self.sig_validated)

    def _set_message(self, exit_code, message):
        if exit_code != 0:
            self._info_label.setText(message)

    def setup(self, cookiecutter_settings):
        """
        Setup the widget using options.
        """
        self._widget.setup(cookiecutter_settings)

    def set_pre_gen_code(self, pre_gen_code):
        """
        Set the cookiecutter pregeneration code.
        """
        self._widget.set_pre_gen_code(pre_gen_code)

    def validate(self):
        """
        Run, pre generation script and provide information on finished.
        """
        self._widget.validate()

    def get_values(self):
        """
        Return all entered and generated values.
        """
        return self._widget.get_values()


class CookiecutterWidget(SpyderConfigPage):
    """
    QWidget to display cookiecutter.json options.

    cookiecutter_settings: dict
        A cookiecutter.json settings content.
    pre_gen_code: str
        The code of the pregeneration script.
    """

    CONF_SECTION = "project_explorer"

    sig_validated = QtCore.Signal(int, str)
    """
    This signal is emitted after validation has been executed.

    It provides the process exit code and the output captured.
    """

    def __init__(self, parent, project_path=None):
        super().__init__(parent)

        # Attributes
        self._parent = parent
        self.project_path = project_path
        cookiecutter_settings, pre_gen_code = load_cookiecutter_project(
            self.project_path)
        self._cookiecutter_settings = cookiecutter_settings
        self._pre_gen_code = pre_gen_code
        self._widgets = OrderedDict()
        self._defined_settings = OrderedDict()
        self._rendered_settings = OrderedDict()
        self._rendered_values = OrderedDict()
        self._process = None
        self._tempfile = tempfile.mkstemp(suffix=".py")[-1]

        # Cookiecutter special variables
        self._extensions = None
        self._copy_without_render = None
        self._new_lines = None
        self._private_vars = None
        self._rendered_private_var = None

        # Layout
        self._form_layout = QtWidgets.QFormLayout()
        self._form_layout.setFieldGrowthPolicy(
            self._form_layout.AllNonFixedFieldsGrow)
        self._form_layout.setContentsMargins(0, 0, 0, 0)
        self.setLayout(self._form_layout)

    # --- Helpers
    # ------------------------------------------------------------------------
    def _check_jinja_options(self):
        """
        Check which values are Jinja2 expressions.
        """
        if self._cookiecutter_settings:
            # https://cookiecutter.readthedocs.io/en/latest/advanced/template_extensions.html
            self._extensions = self._cookiecutter_settings.pop("_extensions",
                                                               [])

            # https://cookiecutter.readthedocs.io/en/latest/advanced/copy_without_render.html
            self._copy_without_render = self._cookiecutter_settings.pop(
                "_copy_without_render", [])

            # https://cookiecutter.readthedocs.io/en/latest/advanced/new_line_characters.html
            self._new_lines = self._cookiecutter_settings.pop("_new_lines", "")

            for setting, value in self._cookiecutter_settings.items():
                # Treat everything like a list for convenience
                if isinstance(value, dict):
                    # https://cookiecutter.readthedocs.io/en/latest/advanced/dict_variables.html
                    list_values = list(value.keys())
                elif not isinstance(value, list):
                    list_values = [value]
                else:
                    list_values = value

                are_rendered_values = []
                if list_values and value:
                    for list_value in list_values:
                        template = Template(list_value)
                        rendered_value = template.render(
                            cookiecutter=Namespace(
                                **self._cookiecutter_settings))

                        are_rendered_values.append(
                            list_value != rendered_value)

                if any(are_rendered_values):
                    self._rendered_settings[setting] = value
                else:
                    self._defined_settings[setting] = value

    def _is_jinja(self, setting):
        """
        Check if option contains jinja2 code.
        """
        return setting in self._rendered_settings

    def _parse_bool_text(self, text):
        """
        Convert a text value into a boolean.
        """
        value = None
        if text.lower() in ["n", "no", "false"]:
            value = False
        elif text.lower() in ["y", "yes", "true"]:
            value = True

        return value

    def _create_field(self, setting, value):
        """
        Create a form field.
        """
        label = " ".join(setting.split("_")).capitalize()
        if isinstance(value, (list, dict)):
            field_type = "combobox"
            choices = []
            if isinstance(value, dict):
                for label, val in value.items():
                    choices.append((label, val))
            else:
                for choice in value:
                    choices.append((str(choice).capitalize(), choice))
            # https://cookiecutter.readthedocs.io/en/latest/advanced/choice_variables.html
            widget = self.create_combobox(text=label, option=setting,
                                          choices=choices)
            widget_in = widget.combobox
        elif isinstance(value, str):
            if value.lower() in ["y", "yes", "true", "n", "no", "false"]:
                field_type = "checkbox"
                val = self._parse_bool_text(value)
                widget = self.create_checkbox(text=label, option=setting,
                                              default=val)
                widget_in = widget.checkbox
                widget_in.setChecked(val)
            else:
                field_type = "textbox"
                widget = self.create_lineedit(text=label, option=setting,
                                              default='', status_icon=ima.icon("error"))
                widget_in = widget.textbox
        else:
            raise Exception(
                "Cookiecutter option '{}'cannot be processed".format(setting))

        self._widgets[setting] = (field_type, widget_in, widget)

        return widget, widget_in

    def _on_process_finished(self):
        """
        Process output of valiation script.
        """
        if self._process is not None:
            out = bytes(self._process.readAllStandardOutput()).decode()
            error = bytes(self._process.readAllStandardError()).decode()
            message = ""
            if out:
                message += out

            if error:
                message += error

            message = message.replace("\r\n", " ")
            message = message.replace("\n", " ")
            return message
            #self.sig_validated.emit(self._process.exitCode(), message)

    # --- API
    # ------------------------------------------------------------------------
    def setup(self):
        """
        Setup the widget using options.
        """
        # self._cookiecutter_settings = cookiecutter_settings
        self._check_jinja_options()

        for setting, value in self._cookiecutter_settings.items():
            if (not setting.startswith(("__", "_")) and
                    not self._is_jinja(setting)):
                widget, widget_in = self._create_field(setting, value)
                self._form_layout.addRow(widget)
        self.render()

    def render(self):
        """
        Render text that contains Jinja2 expressions and set their values.
        """
        cookiecutter_settings = self.get_values()
        for setting, value in self._rendered_settings.items():
            if not setting.startswith(("__", "_")):
                template = Template(value)
                val = template.render(
                    cookiecutter=Namespace(**cookiecutter_settings))
                self._rendered_values[setting] = val

    def get_values(self):
        """
        Return all entered and generated values.
        """
        cookiecutter_settings = cs = OrderedDict()
        if self._cookiecutter_settings:
            for setting, value in self._cookiecutter_settings.items():
                if setting.startswith(("__", "_")):
                    cookiecutter_settings[setting] = value
                elif self._is_jinja(setting):
                    for setting, value in self._rendered_values.items():
                        cookiecutter_settings[setting] = value
                else:
                    type, widget_in, widget = self._widgets[setting]
                    if type == "combobox":
                        cookiecutter_settings[setting] = widget_in.currentData()
                    elif type == "checkbox":
                        cookiecutter_settings[setting] = widget_in.isChecked()
                    elif type == "textbox":
                        cookiecutter_settings[setting] = widget_in.text()
        # Cookiecutter special variables
        cookiecutter_settings["_extensions"] = self._extensions
        cookiecutter_settings["_copy_without_render"] = (
            self._copy_without_render)
        cookiecutter_settings["_new_lines"] = self._new_lines

        return cookiecutter_settings

    def validate(self):
        """
        Run, pre generation script and provide information on finished.
        """
        reasons = {}
        self.render()
        cookiecutter_settings = self.get_values()
        for setting, value in cookiecutter_settings.items():
            if not (setting.startswith(("__", "_")) or
                    self._is_jinja(setting)):                
                type, widget_in, widget = self._widgets[setting]
                if type == "textbox":
                    widget.status_action.setVisible(False)
                    if value.strip() == '':
                        widget.status_action.setVisible(True)
                        widget.status_action.setToolTip(_("This is empty"))
                        reasons["missing_info"] = True
        if reasons:
            return reasons
        if self._pre_gen_code is not None:
            cookiecutter_settings = self.get_values()
            template = Template(self._pre_gen_code)
            val = template.render(
                cookiecutter=Namespace(**cookiecutter_settings))

            with open(self._tempfile, "w") as fh:
                fh.write(val)

            if self._process is not None:
                self._process.close()

            self._process = QtCore.QProcess(self)
            self._process.setProgram(sys.executable)
            self._process.setArguments([self._tempfile])

            loop = QtCore.QEventLoop()
            self._process.finished.connect(loop.quit)
            self._process.start()
            loop.exec_()

            message = self._on_process_finished()
            if self._process.exitCode() != 0:
                reasons["cookiecutter_error"] = True
                reasons["cookiecutter_error_detail"] = message
                return reasons

        return None

    def create_project(self, location):
        status, result = generate_cookiecutter_project(self.project_path,
                                                       location,
                                                       self.get_values())
        return status


if __name__ == "__main__":
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    dlg = CookiecutterDialog(parent=None)
    spyder_url = "https://github.com/spyder-ide/spyder5-plugin-cookiecutter"
    cookiecutter_settings, pre_gen_code = load_cookiecutter_project(project_path=spyder_url, token="algo")
    dlg.setup(cookiecutter_settings)
    dlg.set_pre_gen_code(pre_gen_code)
    dlg.show()
    sys.exit(app.exec_())
