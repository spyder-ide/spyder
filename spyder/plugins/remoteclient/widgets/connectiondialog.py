# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog to handle remote connections."""

# Standard library imports
import uuid

# Third party imports
import qstylizer.style
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QStackedWidget,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.translations import _
from spyder.plugins.remoteclient.api.protocol import SSHClientOptions
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.plugins.remoteclient.widgets.connectionstatus import (
    ConnectionStatusWidget,
)
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle
from spyder.widgets.config import SpyderConfigPage
from spyder.widgets.sidebardialog import SidebarDialog


class MissingInfoLabel(QLabel):
    """Label to report to users that a field info is missing."""

    def __init__(self, parent):
        text = _(
            "You need to fill the required fields on this page in order to "
            "save your connection"
        )
        super().__init__(text, parent)

        # Set main attributes
        self.setWordWrap(True)
        self.setAlignment(Qt.AlignCenter)
        self.setVisible(False)

        # Set style
        css = qstylizer.style.StyleSheet()
        css.QLabel.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_4,
            # Top margin is set by the layout
            marginTop="0px",
            marginRight=f"{9 * AppStyle.MarginSize}px",
            # We don't need bottom margin because there are no other elements
            # below this one.
            marginBottom="0px",
            # The extra 5px are necessary because we need to add them to all
            # lineedits in this dialog to align them to the labels on top of
            # them (see SpyderConfigPage.create_lineedit).
            marginLeft=f"{9 * AppStyle.MarginSize + 5}px",
            padding=f"{3 * AppStyle.MarginSize}px {6 * AppStyle.MarginSize}px",
            borderRadius=SpyderPalette.SIZE_BORDER_RADIUS,
        )

        self.setStyleSheet(css.toString())


class BaseConnectionPage(SpyderConfigPage):
    """Base class to create connection pages."""

    NEW_CONNECTION = False
    CONF_SECTION = "remoteclient"
    host_id = None

    def __init__(self, parent):
        super().__init__(parent)

        self._widgets_for_validation = {}
        self._missing_info_labels = {}

    # ---- Public API
    # -------------------------------------------------------------------------
    @classmethod
    def set_host_id(cls, host_id):
        cls.host_id = host_id

    def auth_method(self, from_gui=False):
        if from_gui:
            if self._auth_methods.combobox.currentIndex() == 0:
                auth_method = AuthenticationMethod.Password
            elif self._auth_methods.combobox.currentIndex() == 1:
                auth_method = AuthenticationMethod.KeyFile
            else:
                auth_method = AuthenticationMethod.ConfigFile
        else:
            auth_method = self.get_option(f"{self.host_id}/auth_method")

        return auth_method

    def validate_page(self):
        """Validate contents before saving the connection."""
        # Hide label and clear status actions from all pages!

        # Get widgets we're going to interact with
        auth_method = self.auth_method(from_gui=True)
        widgets = self._widgets_for_validation[auth_method]
        missing_info_label = self._missing_info_labels[auth_method]

        # Hide label in case the validation pass
        missing_info_label.setVisible(False)

        # Validate that the required fields are not empty
        validation = True
        for widget in widgets:
            if not widget.textbox.text():
                widget.status_action.setVisible(True)
                if validation:
                    validation = False
            else:
                widget.status_action.setVisible(False)

        if not validation:
            missing_info_label.setVisible(True)

        return validation

    def create_connection_info_widget(self):
        """
        Create widget that contains all other widgets to receive or display
        connection info.
        """
        # Authentication methods
        methods = (
            (_('Password'), AuthenticationMethod.Password),
            (_('Key file'), AuthenticationMethod.KeyFile),
            (_('Configuration file'), AuthenticationMethod.ConfigFile),
        )

        self._auth_methods = self.create_combobox(
            _("Select your SSH authentication method:"),
            methods,
            f"{self.host_id}/auth_method"
        )

        # Subpages
        password_subpage = self._create_password_subpage()
        keyfile_subpage = self._create_keyfile_subpage()
        configfile_subpage = self._create_configfile_subpage()

        subpages = QStackedWidget(self)
        subpages.addWidget(password_subpage)
        subpages.addWidget(keyfile_subpage)
        subpages.addWidget(configfile_subpage)

        # Signals
        self._auth_methods.combobox.currentIndexChanged.connect(
            subpages.setCurrentIndex
        )

        # Show password subpage by default for new connections
        if self.NEW_CONNECTION:
            self._auth_methods.combobox.setCurrentIndex(0)

        # Final layout
        layout = QVBoxLayout()
        layout.addWidget(self._auth_methods)
        layout.addSpacing(7 * AppStyle.MarginSize)
        layout.addWidget(subpages)

        connection_info_widget = QWidget(self)
        connection_info_widget.setLayout(layout)

        return connection_info_widget

    # ---- Private API
    # -------------------------------------------------------------------------
    def _create_common_elements(self, auth_method):
        """Common elements for the password and keyfile subpages."""
        # Widgets
        name = self.create_lineedit(
            text=_("Name *"),
            option=f"{self.host_id}/{auth_method}/name",
            tip=_("Introduce a name to identify your connection"),
            status_icon=ima.icon("error"),
        )

        address = self.create_lineedit(
            text=_("Remote address *"),
            option=f"{self.host_id}/{auth_method}/address",
            tip=_("This is the IP address or URL of your remote machine"),
            status_icon=ima.icon("error"),
        )

        port = self.create_spinbox(
            prefix=_("Port"),
            suffix="",
            option=f"{self.host_id}/{auth_method}/port",
            min_=1,
            max_=65535
        )
        port.spinbox.setStyleSheet("margin-left: 5px")

        username = self.create_lineedit(
            text=_("Username *"),
            option=f"{self.host_id}/{auth_method}/username",
            status_icon=ima.icon("error"),
        )

        self._widgets_for_validation[f"{auth_method}"] = [
            name,
            address,
            username,
        ]

        # Set 22 as the default port for new conenctions
        if not self.LOAD_FROM_CONFIG:
            port.spinbox.setValue(22)

        # Hide the container widgets because we only use their components
        address.hide()
        port.hide()

        # Layout for the address label
        address_label_layout = QHBoxLayout()
        address_label_layout.setSpacing(0)
        address_label_layout.addWidget(address.label)
        address_label_layout.addWidget(address.help_label)
        address_label_layout.addStretch()

        # Address layout
        address_layout = QGridLayout()
        address_layout.setContentsMargins(0, 0, 0, 0)

        address_layout.addLayout(address_label_layout, 0, 0)
        address_layout.addWidget(address.textbox, 1, 0)
        address_layout.addWidget(port.plabel, 0, 1)
        address_layout.addWidget(port.spinbox, 1, 1)

        return name, address_layout, username

    def _create_password_subpage(self):
        # Widgets
        name, address_layout, username = self._create_common_elements(
            auth_method=AuthenticationMethod.Password
        )

        password = self.create_lineedit(
            text=_("Password *"),
            option=f"{self.host_id}/password",
            tip=(
                _("Your password will be saved securely by Spyder")
                if self.NEW_CONNECTION
                else _("Your password is saved securely by Spyder")
            ),
            status_icon=ima.icon("error"),
            password=True
        )

        missing_info_label = MissingInfoLabel(self)

        # Add widgets to their required dicts
        self._widgets_for_validation[AuthenticationMethod.Password].append(
            password
        )

        self._missing_info_labels[
            AuthenticationMethod.Password
        ] = missing_info_label

        # Layout
        password_layout = QVBoxLayout()
        password_layout.setContentsMargins(0, 0, 0, 0)

        password_layout.addWidget(name)
        password_layout.addSpacing(5 * AppStyle.MarginSize)
        password_layout.addLayout(address_layout)
        password_layout.addSpacing(5 * AppStyle.MarginSize)
        password_layout.addWidget(username)
        password_layout.addSpacing(5 * AppStyle.MarginSize)
        password_layout.addWidget(password)
        password_layout.addSpacing(7 * AppStyle.MarginSize)
        password_layout.addWidget(missing_info_label)
        password_layout.addStretch()

        password_subpage = QWidget(self)
        password_subpage.setLayout(password_layout)

        return password_subpage

    def _create_keyfile_subpage(self):
        # Widgets
        name, address_layout, username = self._create_common_elements(
            auth_method=AuthenticationMethod.KeyFile
        )

        keyfile = self.create_browsefile(
            text=_("Key file *"),
            option=f"{self.host_id}/keyfile",
            alignment=Qt.Vertical,
            status_icon=ima.icon("error"),
        )

        passpharse = self.create_lineedit(
            text=_("Passpharse"),
            option=f"{self.host_id}/passpharse",
            tip=(
                _("Your passphrase will be saved securely by Spyder")
                if self.NEW_CONNECTION
                else _("Your passphrase is saved securely by Spyder")
            ),
            password=True
        )

        missing_info_label = MissingInfoLabel(self)

        # Add widgets to their required dicts
        self._widgets_for_validation[AuthenticationMethod.KeyFile].append(
            keyfile
        )

        self._missing_info_labels[
            AuthenticationMethod.KeyFile
        ] = missing_info_label

        keyfile_layout = QVBoxLayout()
        keyfile_layout.setContentsMargins(0, 0, 0, 0)

        keyfile_layout.addWidget(name)
        keyfile_layout.addSpacing(5 * AppStyle.MarginSize)
        keyfile_layout.addLayout(address_layout)
        keyfile_layout.addSpacing(5 * AppStyle.MarginSize)
        keyfile_layout.addWidget(username)
        keyfile_layout.addSpacing(5 * AppStyle.MarginSize)
        keyfile_layout.addWidget(keyfile)
        keyfile_layout.addSpacing(5 * AppStyle.MarginSize)
        keyfile_layout.addWidget(passpharse)
        keyfile_layout.addSpacing(7 * AppStyle.MarginSize)
        keyfile_layout.addWidget(missing_info_label)
        keyfile_layout.addStretch()

        keyfile_subpage = QWidget(self)
        keyfile_subpage.setLayout(keyfile_layout)

        return keyfile_subpage

    def _create_configfile_subpage(self):
        # Widgets
        configfile = self.create_browsefile(
            text=_("Configuration file *"),
            option=f"{self.host_id}/configfile",
            alignment=Qt.Vertical,
            status_icon=ima.icon("error"),
        )

        missing_info_label = MissingInfoLabel(self)

        # Add widgets to their required dicts
        self._widgets_for_validation[AuthenticationMethod.ConfigFile] = [
            configfile
        ]

        self._missing_info_labels[
            AuthenticationMethod.ConfigFile
        ] = missing_info_label

        configfile_layout = QVBoxLayout()
        configfile_layout.setContentsMargins(0, 0, 0, 0)
        configfile_layout.addWidget(configfile)
        configfile_layout.addSpacing(7 * AppStyle.MarginSize)
        configfile_layout.addWidget(missing_info_label)
        configfile_layout.addStretch()

        configfile_widget = QWidget(self)
        configfile_widget.setLayout(configfile_layout)

        return configfile_widget


class NewConnectionPage(BaseConnectionPage):
    """Page to receive SSH credentials for a remote connection."""

    MIN_HEIGHT = 500
    LOAD_FROM_CONFIG = False

    NEW_CONNECTION = True
    host_id = str(uuid.uuid4())

    # ---- SidebarPage API
    # -------------------------------------------------------------------------
    def get_name(self):
        return _("New connection")

    def setup_page(self):
        info_widget = self.create_connection_info_widget()

        # Use a stacked layout so we can hide the current widgets and create
        # new ones in case users want to introduce more connections.
        self.layout = QStackedLayout()
        self.layout.addWidget(info_widget)
        self.setLayout(self.layout)

    def get_icon(self):
        return self.create_icon("add_server")

    # ---- Public API
    # -------------------------------------------------------------------------
    def reset_page(self):
        """
        Reset page by adding a new, clean set of widgets, which will allow
        users to introduce a new connection.
        """
        # Reset tracked widgets
        self.reset_widget_dicts()

        # Set a new host id
        new_id = str(uuid.uuid4())
        self.set_host_id(new_id)

        # Add a new set of widgets to the page
        clean_info_widget = self.create_connection_info_widget()
        self.layout.addWidget(clean_info_widget)
        self.layout.setCurrentWidget(clean_info_widget)


class ConnectionPage(BaseConnectionPage):
    """Page to display connection status and info for a remote machine."""

    #MAX_WIDTH = 900
    MIN_HEIGHT = 620

    # ---- SidebarPage API
    # -------------------------------------------------------------------------
    def get_name(self):
        return self.get_option(f"{self.host_id}/{self.auth_method()}/name")

    def setup_page(self):
        info_widget = self.create_connection_info_widget()
        status_widget = ConnectionStatusWidget(self, self.host_id)

        self.create_tab(_("Connection status"), status_widget)
        self.create_tab(_("Connection info"), info_widget)

    def get_icon(self):
        return self.create_icon("remote_server")

    # ---- Public API
    # -------------------------------------------------------------------------
    def save_server_info(self):
        options = SSHClientOptions(
            host=self.get_option(
                f"{self.host_id}/{self.auth_method()}/address"
            ),
            port=self.get_option(f"{self.host_id}/{self.auth_method()}/port"),
            username=self.get_option(
                f"{self.host_id}/{self.auth_method()}/username"
            ),
        )

        servers = self.get_option("servers", default={})
        servers[self.host_id] = options
        self.set_option("servers", servers)


class ConnectionDialog(SidebarDialog):
    """
    Dialog to handle and display remote connection information for different
    machines.
    """

    MIN_WIDTH = 620
    MIN_HEIGHT = 640
    PAGE_CLASSES = [NewConnectionPage]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.add_saved_connection_pages()

    def create_buttons(self):
        bbox = QDialogButtonBox(QDialogButtonBox.Cancel)

        button_save_connection = QPushButton(_("Save connection"))
        button_save_connection.clicked.connect(self.save_connection_info)

        button_connect = QPushButton(_("Connect"))
        button_connect.clicked.connect(
            lambda: None
        )

        layout = QHBoxLayout()
        layout.addWidget(button_save_connection)
        layout.addStretch(1)
        layout.addWidget(button_connect)
        layout.addWidget(bbox)

        return bbox, layout

    def save_connection_info(self):
        page = self.get_page()

        # Validate info
        if not page.validate_page():
            return

        if self.get_current_index() == 0:
            # Actions for the new connection page.

            # Save info provided by users
            page.save_to_conf()

            # Add separator
            if self.number_of_pages() == 1:
                self.add_separator()

            # Add connection page to the dialog with the new info
            self.add_connection_page(host_id=page.host_id, new=True)

            # Give focus to the new page
            self.set_current_index(self.number_of_pages() - 1)

            # Reset page in case users want to introduce another connection
            # page.reset_page()
        else:
            # Update connection info for the other pages.
            page.save_to_conf()

    def add_connection_page(self, host_id: str, new: bool):
        PageClass = ConnectionPage
        PageClass.set_host_id(host_id)

        page = PageClass(self)
        if new:
            page.save_server_info()

        self.add_page(page)

    def add_saved_connection_pages(self):
        page = self.get_page(index=0)
        servers = page.get_option("servers", default={})

        if servers:
            self.add_separator()

            for id_ in servers.keys():
                self.add_connection_page(host_id=id_, new=False)


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()  # noqa
    app.setStyleSheet(str(APP_STYLESHEET))

    dialog = ConnectionDialog()
    dialog.exec_()


if __name__ == "__main__":
    test()
