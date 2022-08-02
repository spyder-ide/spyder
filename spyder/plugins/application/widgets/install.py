# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update installation widget."""

# Standard library imports
import sys

# Third-party imports
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtWidgets import (QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette


# Update Installation process statusesf
NO_STATUS = _("No status")
DOWNLOADING_INSTALLER = _("Downloading installer")
INSTALLING = _("Installing")
FINISHED = _("Installation finished")
PENDING = _("Pending update")
CHECKING = _("Checking for updates")
CANCELLED = _("Cancelled")


class UpdateInstallation(QWidget):
    """Update progress installation widget."""

    def __init__(self, parent):
        super(UpdateInstallation, self).__init__(parent)

        # Left side
        action_layout = QVBoxLayout()
        progress_layout = QHBoxLayout()
        self._progress_widget = QWidget(self)
        self._progress_widget.setFixedHeight(50)
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedWidth(180)
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(ima.icon('DialogCloseButton'))
        progress_layout.addWidget(self._progress_bar, alignment=Qt.AlignLeft)
        progress_layout.addWidget(self.cancel_button)
        self._progress_widget.setLayout(progress_layout)

        self._progress_label = QLabel(_('Downloading'))

        self.install_info = QLabel(
            _("Dowloading the latest Spyder version <br>"))

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(_('OK'))
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch()

        action_layout.addStretch()
        action_layout.addWidget(self._progress_label)
        action_layout.addWidget(self._progress_widget)
        action_layout.addWidget(self.install_info)
        action_layout.addSpacing(10)
        action_layout.addLayout(button_layout)
        action_layout.addStretch()

        # Layout
        general_layout = QHBoxLayout()
        general_layout.addLayout(action_layout)

        self.setLayout(general_layout)

    def update_installation_status(self, status):
        """Update installation status (downloading, installing, finished)."""
        self._progress_label.setText(status)
        self.install_info.setText(status + " the latest version of Spyder.")
        if status == INSTALLING:
            self._progress_bar.setRange(0, 0)
            self.cancel_button.hide()

    def update_installation_progress(self, current_value, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current_value)


class UpdateInstallerDialog(QDialog):
    """Spyder installer."""

    def __init__(self, parent, installation_thread):
        super(UpdateInstallerDialog, self).__init__(parent)
        self.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_2}")
        self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._parent = parent
        self._installation_thread = installation_thread
        self._installation_widget = UpdateInstallation(self)

        # Layout
        installer_layout = QVBoxLayout()
        installer_layout.addWidget(self._installation_widget)

        self.setLayout(installer_layout)

        # Signals
        self._installation_thread.sig_download_progress.connect(
            self._installation_widget.update_installation_progress)
        self._installation_thread.sig_installation_status.connect(
            self._installation_widget.update_installation_status)
        self._installation_thread.sig_installation_status.connect(
            self.finished_installation)

        self._installation_widget.ok_button.clicked.connect(
            self.close_installer)
        self._installation_widget.cancel_button.clicked.connect(
            self.cancel_install)

        # Show integration widget
        self.setup()

    def setup(self, installation=False):
        """Setup visibility of widgets."""
        self._installation_widget.setVisible(True)
        self.adjustSize()

    def cancel_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel Update installation?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._installation_thread.cancelled = True
            self._installation_thread.cancell_thread_install_update()
            self.setup()
            self.accept()
            return True
        return False

    def continue_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox(icon=QMessageBox.Question,
                            text=_('Do you want to download and'
                                   ' install the latest version of'
                                   'spyder?<br>'),
                            parent=self._parent)
        reply.setWindowTitle("Spyder")
        reply.setAttribute(Qt.WA_ShowWithoutActivating)
        reply.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        reply.buttonClicked.connect(
            self._installation_thread.installation_thread)
        reply.show()

    def finished_installation(self, status):
        """Handle finished installation."""
        if status == FINISHED or status == PENDING:
            self.setup()
            self.accept()

    def close_installer(self):
        """Close the installation dialog."""
        if (self._installation_thread.status == FINISHED
                or self._installation_thread.status == CANCELLED):
            self.setup()
            self.accept()
        else:
            self.hide()

    def reject(self):
        """Reimplement Qt method."""
        on_installation_widget = self._installation_widget.isVisible()
        if on_installation_widget:
            self.close_installer()
        else:
            super(UpdateInstallerDialog, self).reject()
