# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog window notifying user of autosave-related errors."""

# Standard library imports
import logging

# Third party imports
from qtpy.QtWidgets import (QCheckBox, QDialog, QDialogButtonBox, QLabel,
                            QVBoxLayout)

# Local imports
from spyder.config.base import _


logger = logging.getLogger(__name__)


class AutosaveErrorDialog(QDialog):
    """
    Dialog window notifying user of autosave-related errors.

    The window also includes a check box which allows the user to hide any
    future autosave-related errors.

    Class attribute:
        show_errors (bool): whether to show errors or not
    """

    show_errors = True

    def __init__(self, action, error):
        """
        Constructor.

        Args:
            action (str): what Spyder was trying to do when error occured
            error (Exception): the error that occured
        """
        logger.error(action, exc_info=error)

        QDialog.__init__(self)
        self.setWindowTitle(_('Autosave error'))
        self.setModal(True)

        layout = QVBoxLayout()

        header = _('Error message:')
        txt = '<br>{}<br><br>{}<br>{!s}'.format(action, header, error)
        layout.addWidget(QLabel(txt))
        layout.addSpacing(15)

        txt = _("Hide all future autosave-related errors during this session")
        self.dismiss_box = QCheckBox(txt)
        layout.addWidget(self.dismiss_box)
        layout.addSpacing(15)

        button_box = QDialogButtonBox(QDialogButtonBox.Ok)
        button_box.accepted.connect(self.accept)
        layout.addWidget(button_box)

        self.setLayout(layout)

    def exec_if_enabled(self):
        """
        Execute dialog box unless disabled by the user.

        The dialog box is disabled once the user clicks the 'Hide all future
        errors' check box on one dialog box.
        """
        if AutosaveErrorDialog.show_errors:
            return self.exec_()

    def accept(self):
        """
        Update `show_errors` and hide dialog box.

        Overrides method of `QDialogBox`.
        """
        AutosaveErrorDialog.show_errors = not self.dismiss_box.isChecked()
        return QDialog.accept(self)
