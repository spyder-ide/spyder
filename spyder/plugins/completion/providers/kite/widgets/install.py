# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Kite installation widget."""

# Standard library imports
import sys

# Third-party imports
from qtpy.QtCore import QEvent, QObject, QSize, Qt, QUrl, Signal
from qtpy.QtGui import QDesktopServices, QMovie, QPixmap
from qtpy.QtWidgets import (QApplication, QDialog, QHBoxLayout, QMessageBox,
                            QLabel, QProgressBar, QPushButton, QVBoxLayout,
                            QWidget)

# Local imports
from spyder.config.base import _
from spyder.utils.image_path_manager import get_image_path
from spyder.utils.icon_manager import ima
from spyder.utils.palette import QStylePalette
from spyder.plugins.completion.providers.kite.utils.install import (
    ERRORED, INSTALLING, FINISHED, CANCELLED)


KITE_SPYDER_URL = "https://kite.com/integrations/spyder"
KITE_CONTACT_URL = "https://kite.com/contact/"
MAC = sys.platform == 'darwin'


class KiteIntegrationInfo(QWidget):
    """Initial Widget with info about the integration with Kite."""
    ICON_SCALE_FACTOR = 0.5
    TITLE_FONT_SIZE = '19pt' if MAC else '14pt'
    CONTENT_FONT_SIZE = '15pt' if MAC else '11pt'
    BUTTONS_FONT_SIZE = '15pt' if MAC else '13pt'
    BUTTONS_PADDING = '6px' if MAC else '4px 10px'
    # Signal triggered for the 'Install Kite' button
    sig_install_button_clicked = Signal()
    # Signal triggered for the 'Dismiss' button
    sig_dismiss_button_clicked = Signal()

    def __init__(self, parent):
        super(KiteIntegrationInfo, self).__init__(parent)
        # Images
        images_layout = QHBoxLayout()
        icon_filename = 'kite_completions'
        image_path = get_image_path(icon_filename)
        image = QPixmap(image_path)
        image_label = QLabel()
        screen = QApplication.primaryScreen()
        image_label = QLabel()
        image_height = int(image.height() * self.ICON_SCALE_FACTOR)
        image_width = int(image.width() * self.ICON_SCALE_FACTOR)
        image = image.scaled(image_width, image_height, Qt.KeepAspectRatio,
                             Qt.SmoothTransformation)
        image_label.setPixmap(image)

        images_layout.addStretch()
        images_layout.addWidget(image_label)
        images_layout.addStretch()

        ilayout = QHBoxLayout()
        ilayout.addLayout(images_layout)

        # Label
        integration_label_title = QLabel(
           "Get better code completions in Spyder")
        integration_label_title.setStyleSheet(
           f"font-size: {self.TITLE_FONT_SIZE}")
        integration_label_title.setWordWrap(True)
        integration_label = QLabel(
            _("Now Spyder can use Kite to provide better code "
              "completions for key packages in the scientific Python "
              "Ecosystem. Install Kite for a better editor experience in "
              "Spyder. <br><br>Kite is free to use but is not open "
              "source. <a href=\"{kite_url}\">Learn more about Kite </a>")
            .format(kite_url=KITE_SPYDER_URL))
        integration_label.setStyleSheet(f"font-size: {self.CONTENT_FONT_SIZE}")
        integration_label.setOpenExternalLinks(True)
        integration_label.setWordWrap(True)
        integration_label.setFixedWidth(360)
        label_layout = QVBoxLayout()
        label_layout.addWidget(integration_label_title)
        label_layout.addWidget(integration_label)

        # Buttons
        install_button_color = QStylePalette.COLOR_ACCENT_2
        install_button_hover = QStylePalette.COLOR_ACCENT_3
        install_button_pressed = QStylePalette.COLOR_ACCENT_4
        dismiss_button_color = QStylePalette.COLOR_BACKGROUND_4
        dismiss_button_hover = QStylePalette.COLOR_BACKGROUND_5
        dismiss_button_pressed = QStylePalette.COLOR_BACKGROUND_6
        font_color = QStylePalette.COLOR_TEXT_1
        buttons_layout = QHBoxLayout()
        install_button = QPushButton(_('Install Kite'))
        install_button.setAutoDefault(False)
        install_button.setStyleSheet((
          "QPushButton {{ "
          "background-color: {background_color};"
          "border-color: {border_color};"
          "font-size: {font_size};"
          "color: {font_color};"
          "padding: {padding}}}"
          "QPushButton:hover:!pressed {{ "
          "background-color: {color_hover}}}"
          "QPushButton:pressed {{ "
          "background-color: {color_pressed}}}"
        ).format(background_color=install_button_color,
                 border_color=install_button_color,
                 font_size=self.BUTTONS_FONT_SIZE,
                 font_color=font_color,
                 padding=self.BUTTONS_PADDING,
                 color_hover=install_button_hover,
                 color_pressed=install_button_pressed))
        dismiss_button = QPushButton(_('Dismiss'))
        dismiss_button.setAutoDefault(False)
        dismiss_button.setStyleSheet((
          "QPushButton {{ "
          "background-color: {background_color};"
          "border-color: {border_color};"
          "font-size: {font_size};"
          "color: {font_color};"
          "padding: {padding}}}"
          "QPushButton:hover:!pressed {{ "
          "background-color: {color_hover}}}"
          "QPushButton:pressed {{ "
          "background-color: {color_pressed}}}"
        ).format(background_color=dismiss_button_color,
                 border_color=dismiss_button_color,
                 font_size=self.BUTTONS_FONT_SIZE,
                 font_color=font_color,
                 padding=self.BUTTONS_PADDING,
                 color_hover=dismiss_button_hover,
                 color_pressed=dismiss_button_pressed))
        buttons_layout.addStretch()
        buttons_layout.addWidget(install_button)
        if not MAC:
            buttons_layout.addSpacing(10)
        buttons_layout.addWidget(dismiss_button)

        # Buttons with label
        vertical_layout = QVBoxLayout()
        if not MAC:
            vertical_layout.addStretch()
            vertical_layout.addLayout(label_layout)
            vertical_layout.addSpacing(20)
            vertical_layout.addLayout(buttons_layout)
            vertical_layout.addStretch()
        else:
            vertical_layout.addLayout(label_layout)
            vertical_layout.addLayout(buttons_layout)

        general_layout = QHBoxLayout()
        general_layout.addStretch()
        general_layout.addLayout(ilayout)
        general_layout.addSpacing(15)
        general_layout.addLayout(vertical_layout)
        general_layout.addStretch()

        self.setLayout(general_layout)

        # Signals
        install_button.clicked.connect(self.sig_install_button_clicked)
        dismiss_button.clicked.connect(self.sig_dismiss_button_clicked)

        self.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_2}")
        self.setContentsMargins(18, 40, 18, 40)
        if not MAC:
            self.setFixedSize(800, 350)


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


class KiteInstallation(QWidget):
    """Kite progress installation widget."""

    def __init__(self, parent):
        super(KiteInstallation, self).__init__(parent)

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
            _("Kite comes with a native app called the Copilot <br>"
              "which provides you with real time <br>"
              "documentation as you code.<br><br>"
              "When Kite is done installing, the Copilot will <br>"
              "launch automatically and guide you throught the <br>"
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


class KiteInstallerDialog(QDialog):
    """Kite installer."""

    def __init__(self, parent, installation_thread):
        super(KiteInstallerDialog, self).__init__(parent)
        self.setStyleSheet(
            f"background-color: {QStylePalette.COLOR_BACKGROUND_2}")
        if sys.platform == 'darwin':
            self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint
                                | Qt.Tool)
        else:
            self.setWindowFlags(Qt.Dialog | Qt.MSWindowsFixedSizeDialogHint)
        self._parent = parent
        self._installation_thread = installation_thread
        self._integration_widget = KiteIntegrationInfo(self)
        self._installation_widget = KiteInstallation(self)

        # Layout
        installer_layout = QVBoxLayout()
        installer_layout.addWidget(self._integration_widget)
        installer_layout.addWidget(self._installation_widget)

        self.setLayout(installer_layout)

        # Signals
        self._installation_thread.sig_download_progress.connect(
            self._installation_widget.update_installation_progress)
        self._installation_thread.sig_installation_status.connect(
            self._installation_widget.update_installation_status)
        self._installation_thread.sig_installation_status.connect(
            self.finished_installation)
        self._installation_thread.sig_error_msg.connect(self._handle_error_msg)
        self._integration_widget.sig_install_button_clicked.connect(
            self.install)
        self._integration_widget.sig_dismiss_button_clicked.connect(
            self.reject)
        self._installation_widget.ok_button.clicked.connect(
            self.close_installer)
        self._installation_widget.cancel_button.clicked.connect(
            self.cancel_install)

        # Show integration widget
        self.setup()

    def _handle_error_msg(self, msg):
        """Handle error message with an error dialog."""
        QMessageBox.critical(
            self._parent,
            _('Kite installation error'),
            _("<b>An error ocurred while installing Kite!</b><br><br>"
              "Please try to "
              "<a href=\"{kite_url}\">install it manually</a> or "
              "<a href=\"{kite_contact}\">contact Kite</a> for help")
            .format(kite_url=KITE_SPYDER_URL, kite_contact=KITE_CONTACT_URL))
        self.accept()

    def setup(self, integration=True, installation=False):
        """Setup visibility of widgets."""
        self._integration_widget.setVisible(integration)
        self._installation_widget.setVisible(installation)
        self.adjustSize()

    def install(self):
        """Initialize installation process and show install widget."""
        self.setup(integration=False, installation=True)
        self._installation_thread.cancelled = False
        self._installation_thread.install()

    def cancel_install(self):
        """Cancel the installation in progress."""
        reply = QMessageBox.critical(
            self._parent, 'Spyder',
            _('Do you really want to cancel Kite installation?'),
            QMessageBox.Yes, QMessageBox.No)
        if reply == QMessageBox.Yes and self._installation_thread.isRunning():
            self._installation_thread.cancelled = True
            self._installation_thread.quit()
            self.setup()
            self.accept()
            return True
        return False

    def finished_installation(self, status):
        """Handle finished installation."""
        if status == FINISHED:
            self.setup()
            self.accept()

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
            super(KiteInstallerDialog, self).reject()


if __name__ == "__main__":
    from spyder.utils.qthelpers import qapplication
    app = qapplication()
    install_progress = KiteInstallation(None)
    install_progress.show()
    app.exec_()
