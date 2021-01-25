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

    sig_validated = QtCore.Signal(int, str)
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


class CookiecutterWidget(QtWidgets.QWidget):
    """
    QWidget to display cookiecutter.json options.

    cookiecutter_settings: dict
        A cookiecutter.json settings content.
    pre_gen_code: str
        The code of the pregeneration script.
    """

    sig_validated = QtCore.Signal(int, str)
    """
    This signal is emitted after validation has been executed.

    It provides the process exit code and the output captured.
    """

    def __init__(self, parent, cookiecutter_settings=None, pre_gen_code=None):
        super().__init__(parent)

        # Attributes
        self._parent = parent
        self._cookiecutter_settings = cookiecutter_settings
        self._pre_gen_code = pre_gen_code
        self._widgets = OrderedDict()
        self._defined_settings = OrderedDict()
        self._rendered_settings = OrderedDict()
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

    def _create_textbox(self, setting, label, default=None):
        """
        Create a textbox field.
        """
        if default is not None and len(default) > 30:
            box = QtWidgets.QTextEdit(parent=self)
            box.setText = box.setPlainText
            box.text = box.toPlainText
        else:
            box = QtWidgets.QLineEdit(parent=self)

        box.setting = setting
        if default is not None:
            box.setText(default)
            box.textChanged.connect(lambda x=None: self.render())

        box.get_value = lambda: box.text()
        box.set_value = lambda text: box.setText(text)

        return box

    def _create_checkbox(self, setting, label, default=None):
        """
        Create a checkbox field.
        """
        box = QtWidgets.QCheckBox(parent=self)
        box.setting = setting
        if default is not None:
            new_default = self._parse_bool_text(default)
            box.setChecked(new_default)

        def _get_value():
            bool_to_values = {
                self._parse_bool_text(default): default,
                not self._parse_bool_text(default): "other-value-" + default
            }
            return bool_to_values[box.isChecked()]

        box.get_value = _get_value

        return box

    def _create_combobox(self, setting, label, choices, default=None):
        """
        Create a combobox field.
        """
        box = QtWidgets.QComboBox(parent=self)
        if isinstance(choices, dict):
            temp = OrderedDict()
            for choice, choice_value in choices.items():
                box.addItem(choice, {choice: choice_value})
        else:
            for choice in choices:
                box.addItem(choice, choice)

        box.setting = setting
        box.get_value = lambda: box.currentData()

        return box

    def _create_field(self, setting, value):
        """
        Create a form field.
        """
        label = " ".join(setting.split("_")).capitalize()
        if isinstance(value, (list, dict)):
            # https://cookiecutter.readthedocs.io/en/latest/advanced/choice_variables.html
            widget = self._create_combobox(setting, label, value)
        elif isinstance(value, str):
            if value.lower() in ["y", "yes", "true", "n", "no", "false"]:
                widget = self._create_checkbox(setting, label, default=value)
            else:
                default = None if self._is_jinja(setting) else value
                widget = self._create_textbox(setting, label, default=default)
        else:
            raise Exception(
                "Cookiecutter option '{}'cannot be processed".format(setting))

        self._widgets[setting] = (label, widget)

        return label, widget

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
            self.sig_validated.emit(self._process.exitCode(), message)

    # --- API
    # ------------------------------------------------------------------------
    def setup(self, cookiecutter_settings):
        """
        Setup the widget using options.
        """
        self._cookiecutter_settings = cookiecutter_settings
        self._check_jinja_options()

        for setting, value in self._cookiecutter_settings.items():
            if not setting.startswith(("__", "_")):
                label, widget = self._create_field(setting, value)
                self._form_layout.addRow(label, widget)

        self.render()

    def set_pre_gen_code(self, pre_gen_code):
        """
        Set the cookiecutter pregeneration code.
        """
        self._pre_gen_code = pre_gen_code

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
                __, widget = self._widgets[setting]
                widget.set_value(val)

    def get_values(self):
        """
        Return all entered and generated values.
        """
        cookiecutter_settings = cs = OrderedDict()
        if self._cookiecutter_settings:
            for setting, value in self._cookiecutter_settings.items():
                if setting.startswith(("__", "_")):
                    cookiecutter_settings[setting] = value
                else:
                    __, widget = self._widgets[setting]
                    cookiecutter_settings[setting] = widget.get_value()

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
        if self._pre_gen_code is not None:
            cookiecutter_settings = self.get_values()
            template = Template(self._pre_gen_code)
            val = template.render(
                cookiecutter=Namespace(**cookiecutter_settings))

            with open(self._tempfile, "w") as fh:
                fh.write(val)

            if self._process is not None:
                self._process.terminate()

            self._process = QtCore.QProcess()
            self._process.setProgram(sys.executable)
            self._process.setArguments([self._tempfile])
            self._process.finished.connect(self._on_process_finished)
            self._process.start()


if __name__ == "__main__":
    from spyder.utils.qthelpers import qapplication

    app = qapplication()
    dlg = CookiecutterDialog(parent=None)
    dlg.setup(
        {
            "list_option": ["1", "2", "3"],
            "checkbox_option": "y",
            "checkbox_option_2": "false",
            "fixed_option": "goanpeca",
            "rendered_option": "{{ cookiecutter.fixed_option|upper }}",
            "dict_option": {
                "png": {
                    "name": "Portable Network Graphic",
                    "library": "libpng",
                    "apps": [
                        "GIMP"
                    ]
                },
                "bmp": {
                    "name": "Bitmap",
                    "library": "libbmp",
                    "apps": [
                        "Paint",
                        "GIMP"
                    ]
                }
            },
            "_private": "{{ cookiecutter.fixed_option }}",
            "__private_rendered": "{{ cookiecutter.fixed_option }}",
        }
    )
    dlg.set_pre_gen_code('''
import sys
print("HELP!")  # spyder: test-skip
sys.exit(10)''')
    dlg.show()
    sys.exit(app.exec_())
