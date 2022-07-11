# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite installation widget."""

# Standard library imports
import sys

# Third-party imports
from qtpy.QtCore import QEvent, QObject, Qt, Signal
from qtpy.QtGui import QPixmap
from qtpy.QtWidgets import (QApplication, QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.utils.stylesheet import DialogStyle

INSTALLING = _("Installing")
FINISHED = _("Installation finished")
ERRORED = _("Installation errored")
CANCELLED = _("Cancelled")
class HoverEventFilter(QObject):
    """QObject to handle event filtering."""
    # Signal to trigger on a HoverEnter event
    sig_hover_enter = Signal()
    # Signal to trigger on a HoverLeave event
    sig_hover_leave = Signal()

    def eventFilter(self, widget, event):
        """Reimplemented Qt method."""
        if event.type() == QEvent.HoverEnter:
            self.sig_hover_enter.emit()
        elif event.type() == QEvent.HoverLeave:
            self.sig_hover_leave.emit()

        return super(HoverEventFilter, self).eventFilter(widget, event)

class UpdateInstallation(QWidget):
    """Update progress installation widget."""

    def __init__(self, parent):
        super(UpdateInstallation, self).__init__(parent)

        # Left side
        action_layout = QVBoxLayout()
        progress_layout = QHBoxLayout()
        self._progress_widget = QWidget(self)
        self._progress_widget.setFixedHeight(50)
        self._progress_filter = HoverEventFilter()
        self._progress_bar = QProgressBar(self)
        self._progress_bar.setFixedWidth(180)
        self._progress_widget.installEventFilter(self._progress_filter)
        self.cancel_button = QPushButton()
        self.cancel_button.setIcon(ima.icon('DialogCloseButton'))
        self.cancel_button.hide()
        progress_layout.addWidget(self._progress_bar, alignment=Qt.AlignLeft)
        progress_layout.addWidget(self.cancel_button)
        self._progress_widget.setLayout(progress_layout)

        self._progress_label = QLabel(_('Downloading'))
        install_info = QLabel(
            _("Dowloading the latest Spyder version <br>"
              "which provides you with real time <br>"
              "documentation as you code.<br><br>"
              "When Kite is done installing, the Copilot will <br>"
              "launch automatically and guide you through the <br>"
              "rest of the setup process."))

        button_layout = QHBoxLayout()
        self.ok_button = QPushButton(_('OK'))
        button_layout.addStretch()
        button_layout.addWidget(self.ok_button)
        button_layout.addStretch()

        action_layout.addStretch()
        action_layout.addWidget(self._progress_label)
        action_layout.addWidget(self._progress_widget)
        action_layout.addWidget(install_info)
        action_layout.addSpacing(10)
        action_layout.addLayout(button_layout)
        action_layout.addStretch()

        # Right side
        copilot_image_source = get_image_path('kite_copilot')

        copilot_image = QPixmap(copilot_image_source)
        copilot_label = QLabel()
        screen = QApplication.primaryScreen()
        device_pixel_ratio = screen.devicePixelRatio()
        if device_pixel_ratio > 1:
            copilot_image.setDevicePixelRatio(device_pixel_ratio)
            copilot_label.setPixmap(copilot_image)
        else:
            image_height = int(copilot_image.height() * 0.4)
            image_width = int(copilot_image.width() * 0.4)
            copilot_label.setPixmap(
                copilot_image.scaled(image_width, image_height,
                                     Qt.KeepAspectRatio,
                                     Qt.SmoothTransformation))

        # Layout
        general_layout = QHBoxLayout()
        general_layout.addLayout(action_layout)
        general_layout.addWidget(copilot_label)

        self.setLayout(general_layout)

        # Signals
        self._progress_filter.sig_hover_enter.connect(
            lambda: self.cancel_button.show())
        self._progress_filter.sig_hover_leave.connect(
            lambda: self.cancel_button.hide())

    def update_installation_status(self, status):
        """Update installation status (downloading, installing, finished)."""
        self._progress_label.setText(status)
        if status == INSTALLING:
            self._progress_bar.setRange(0, 0)

    def update_installation_progress(self, current_value, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(current_value)


class UpdateInstallerDialog(QDialog):
    """Kite installer."""

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

        
        #self._installation_thread.sig_error_msg.connect(self._handle_error_msg)

        self._installation_widget.ok_button.clicked.connect(
            self.close_installer)
        self._installation_widget.cancel_button.clicked.connect(
            self.cancel_install)

        # Show integration widget
        self.setup()

    def _handle_error_msg(self, msg):
        """Handle error message with an error dialog."""
        '''QMessageBox.critical(
            self._parent,
            _('Kite installation error'),
            _("<b>An error ocurred while installing Kite!</b><br><br>"
              "Please try to "
              "<a href=\"{kite_url}\">install it manually</a> or "
              "<a href=\"{kite_contact}\">contact Kite</a> for help")
            .format(kite_url=KITE_SPYDER_URL, kite_contact=KITE_CONTACT_URL))'''
        self.accept()

    def setup(self,installation=False):
        """Setup visibility of widgets."""
        self._installation_widget.setVisible(False)
        self.adjustSize()


    def cancel_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel Update installation?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes:
            self._installation_thread.cancelled = True
            self._installation_thread._cancell_thread_install_update()
            self.setup()
            self.accept()
            return True
        return False



    def close_installer(self):
        """Close the installation dialog."""
        if (self._installation_thread.status == ERRORED
                or self._installation_thread.status == FINISHED
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

if __name__ == "__main__":
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    install_progress = UpdateInstallation(None)
    install_progress.show()
    app.exec_()