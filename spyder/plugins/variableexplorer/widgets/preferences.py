# -----------------------------------------------------------------------------
# Copyright (c) Spyder Project Contributors
#
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)
# -----------------------------------------------------------------------------

"""
Dialog window for setting the viewing preferences of the data frame editor.
"""

# Standard library import
from typing import Optional

# Third party imports
from qtpy.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QRadioButton,
    QVBoxLayout,
    QWidget
)

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.utils.icon_manager import ima
from spyder.widgets.helperwidgets import TipWidget


FORMAT_SPEC_URL = (
    'https://docs.python.org/3/library/string.html'
    '#format-specification-mini-language'
)


class PreferencesDialog(QDialog):
    """
    Dialog window for setting viewing preferences of dataframe or array editor.

    Set the attributes `float_format`, `varying_background` and `global_algo`
    to set the options, if necessary. Call `exec_()` to show the dialog to the
    user and allow them to interact. Finally, read the attributes to retrieve
    the options selected by the user.

    Parameters
    ----------
    type_string: str
        Type of variable being edited; should be 'dataframe' or 'array'.
        The main difference is that arrays do not support the "by column"
        coloring algorithm. Some text also uses the type.
    parent: QWidget, optional
        Parent widget.
    """

    def __init__(self, type_string: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.type_string = type_string

        self.setWindowTitle(
            _('{} editor preferences').format(type_string.capitalize())
        )

        main_layout = QVBoxLayout(self)

        formatting_group = QGroupBox(_('Formatting'))
        formatting_layout = QVBoxLayout(formatting_group)
        format_label = QLabel(
            _('<a href="{url}">Format specification</a> for floats:')
            .format(url=FORMAT_SPEC_URL)
        )

        format_label_layout = QHBoxLayout()
        format_label_layout.setSpacing(0)
        format_label_layout.addWidget(format_label)
        format_tip_text = _(
            'Use same syntax as for built-in <tt>format()</tt> function. '
            'Default is <tt>.6g</tt>.'
        )
        self.add_help_info_label(format_label_layout, format_tip_text)

        # Stylesheet aligns `format_label` and `format_input` to the left
        self.format_input = QLineEdit(self)
        self.format_input.setStyleSheet('margin-left: 5px')

        formatting_layout.addLayout(format_label_layout)
        formatting_layout.addWidget(self.format_input)
        main_layout.addWidget(formatting_group)

        background_group = QGroupBox(_('Background color'))
        background_layout = QVBoxLayout(background_group)

        self.default_background_button = self.create_radio_button(
            _('Use default background color'),
            _('Use same background color for all cells'),
            background_group,
            background_layout
        )

        self.varying_background_button = self.create_radio_button(
            _('Vary background color according to value'),
            _(
                'Use red for largest number, blue for smallest number, '
                'and intermediate colors for the other numbers.'
            ),
            background_group,
            background_layout
        )

        main_layout.addWidget(background_group)

        if type_string == 'dataframe':
            comparator_group = QGroupBox(_('Coloring algorithm'))
            comparator_layout = QVBoxLayout(comparator_group)

            self.global_button = self.create_radio_button(
                _('Global'),
                _(
                    'Compare each cell against the largest and smallest '
                    'numbers in the entire dataframe'
                ),
                comparator_group,
                comparator_layout
            )

            self.by_column_button = self.create_radio_button(
                _('Column by column'),
                _(
                    'Compare each cell against the largest and smallest '
                    'numbers in the same column'
                ),
                comparator_group,
                comparator_layout
            )

            main_layout.addWidget(comparator_group)

        self.buttons = SpyderDialogButtonBox(
            QDialogButtonBox.Ok | QDialogButtonBox.Cancel
        )
        main_layout.addWidget(self.buttons)
        self.buttons.accepted.connect(self.accept)
        self.buttons.rejected.connect(self.reject)

        self.default_background_button.setChecked(True)

        if type_string == 'dataframe':
            self.global_button.setChecked(True)
            comparator_group.setEnabled(False)
            self.varying_background_button.toggled.connect(
                lambda value: comparator_group.setEnabled(value)
            )

    @property
    def float_format(self) -> str:
        """
        Format specification for floats.
        """
        return self.format_input.text()

    @float_format.setter
    def float_format(self, new_format: str) -> None:
        self.format_input.setText(new_format)

    @property
    def varying_background(self) -> bool:
        """
        Whether to use a colored background.

        If True, then vary the background of the cells in the editor according
        to the value. If False, then use the default background in all cells.
        """
        return self.varying_background_button.isChecked()

    @varying_background.setter
    def varying_background(self, value: bool):
        if value:
            self.varying_background_button.setChecked(True)
        else:
            self.default_background_button.setChecked(True)

    @property
    def global_algo(self) -> bool:
        """
        Whether to use the global minimum and maximum to pick colors.

        If True, then select the background color by comparing the cell value
        against the minimum and maximum over the whole dataframe. If False,
        then use the minimum and maximum over the column.

        This attribute has no effect if `varying_background` is False.
        """
        if self.type_string == 'dataframe':
            return self.global_button.isChecked()
        else:
            return True

    @global_algo.setter
    def global_algo(self, value: bool):
        if self.type_string == 'dataframe':
            if value:
                self.global_button.setChecked(True)
            else:
                self.by_column_button.setChecked(True)

    def add_help_info_label(self, layout, tip_text):
        help_label = TipWidget(
            tip_text=tip_text,
            icon=ima.icon('question_tip'),
            hover_icon=ima.icon('question_tip_hover'),
            wrap_text=True,
        )
        layout.addWidget(help_label)
        layout.addStretch(100)

    def create_radio_button(self, text, tip_text, button_group, layout):
        hor_layout = QHBoxLayout()
        hor_layout.setContentsMargins(0, 0, 0, 0)
        radio_button = QRadioButton(text, button_group)
        hor_layout.addWidget(radio_button)
        self.add_help_info_label(hor_layout, tip_text)
        layout.addLayout(hor_layout)
        return radio_button
