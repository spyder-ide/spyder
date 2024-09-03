# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog to handle remote connections."""

# Standard library imports
from __future__ import annotations
from collections.abc import Iterable
import re
from typing import TypedDict
import uuid

# Third party imports
import qstylizer.style
from qtpy.QtCore import Qt, Signal
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPushButton,
    QStackedWidget,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.translations import _
from spyder.api.utils import get_class_values
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
    RemoteClientLog,
    SSHClientOptions,
)
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.plugins.remoteclient.widgets.connectionstatus import (
    ConnectionStatusWidget,
)
from spyder.utils.icon_manager import ima
from spyder.utils.palette import SpyderPalette
from spyder.utils.stylesheet import AppStyle, MAC, WIN
from spyder.widgets.config import SpyderConfigPage
from spyder.widgets.helperwidgets import TipWidget
from spyder.widgets.sidebardialog import SidebarDialog


# =============================================================================
# ---- Constants
# =============================================================================
class ValidationReasons(TypedDict):
    repeated_name: bool | None
    missing_info: bool | None
    invalid_address: bool | None


# =============================================================================
# ---- Auxiliary widgets
# =============================================================================
class ValidationLabel(QLabel):
    """Label to report to users that info failed to be validated."""

    def __init__(self, parent):
        super().__init__("", parent)

        # Set main attributes
        self.setWordWrap(True)
        self.setVisible(False)

        # Set style
        css = qstylizer.style.StyleSheet()
        css.QLabel.setValues(
            backgroundColor=SpyderPalette.COLOR_BACKGROUND_2,
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

    def set_text(self, reasons: ValidationReasons):
        n_reasons = list(reasons.values()).count(True)
        prefix = "- " if n_reasons > 1 else ""
        suffix = "<br>" if n_reasons > 1 else ""

        text = ""
        if reasons.get("repeated_name"):
            text += (
                prefix
                + _(
                    "The name you selected is already used by another "
                    "connection."
                )
                + suffix
            )

        if reasons.get("invalid_address"):
            text += (
                prefix
                + _(
                    "The address you provided is not a valid IP or domain "
                    "name."
                )
                + suffix
            )

        if reasons.get("missing_info"):
            text += (
                prefix
                + _("There are missing fields on this page.")
            )

        self.setAlignment(Qt.AlignCenter if n_reasons == 1 else Qt.AlignLeft)
        self.setText(text)


# =============================================================================
# ---- Pages
# =============================================================================
class BaseConnectionPage(SpyderConfigPage, SpyderFontsMixin):
    """Base class to create connection pages."""

    MIN_HEIGHT = 450
    NEW_CONNECTION = False
    CONF_SECTION = "remoteclient"

    def __init__(self, parent, host_id=None):
        super().__init__(parent)

        # host_id is None only for the new connection page
        if host_id is None:
            self.host_id = str(uuid.uuid4())
            self.status = ConnectionStatus.Inactive
        else:
            self.host_id = host_id
            self.status = self.get_option(
                f"{host_id}/status", default=ConnectionStatus.Inactive
            )

        self._widgets_for_validation = {}
        self._validation_labels = {}
        self._name_widgets = {}
        self._address_widgets = {}

    # ---- Public API
    # -------------------------------------------------------------------------
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
        validate_label = self._validation_labels[auth_method]

        # Hide label in case the validation pass
        validate_label.setVisible(False)

        reasons: ValidationReasons = {}
        for widget in widgets:
            if not widget.textbox.text():
                # Validate that the required fields are not empty
                widget.status_action.setVisible(True)
                widget.status_action.setToolTip(_("This field is empty"))
                reasons["missing_info"] = True
            elif widget == self._name_widgets[auth_method]:
                # Validate the server name is different from the ones already
                # introduced
                widget.status_action.setVisible(False)
                current_name = widget.textbox.text()
                if not self._validate_name(current_name):
                    reasons["repeated_name"] = True
                    widget.status_action.setVisible(True)
            elif widget == self._address_widgets.get(auth_method):
                # Validate address
                widget.status_action.setVisible(False)
                address = widget.textbox.text()
                if not self._validate_address(address):
                    reasons["invalid_address"] = True
                    widget.status_action.setVisible(True)
            else:
                widget.status_action.setVisible(False)

        if reasons:
            validate_label.set_text(reasons)
            validate_label.setVisible(True)

        return False if reasons else True

    def create_connection_info_widget(self):
        """
        Create widget that contains all other widgets to receive or display
        connection info.
        """
        # Show intro text and tip for new connections
        if self.NEW_CONNECTION:
            # Widgets
            intro_label = QLabel(
                _("Configure SSH settings for connecting to remote hosts")
            )
            intro_tip_text = _(
                "Spyder will use this connection to start remote kernels in "
                "the IPython Console. This allows you to use Spyder locally "
                "while running code remotely, such as on a cloud instance, "
                "office workstation or high-performance cluster."
            )
            intro_tip = TipWidget(
                tip_text=intro_tip_text,
                icon=ima.icon('info_tip'),
                hover_icon=ima.icon('info_tip_hover'),
                size=AppStyle.ConfigPageIconSize + 2,
                wrap_text=True,
            )

            # Increase font size to make it more relevant
            font = self.get_font(SpyderFontType.Interface)
            font.setPointSize(font.pointSize() + 1)
            intro_label.setFont(font)

            # Layout
            intro_layout = QHBoxLayout()
            intro_layout.setContentsMargins(0, 0, 0, 0)
            intro_layout.setSpacing(0)
            intro_layout.setAlignment(Qt.AlignCenter)
            intro_layout.addWidget(intro_label)
            intro_layout.addWidget(intro_tip)

        # Authentication methods
        # TODO: The config file method is not implemented yet, so we need to
        # disable it for now.
        methods = (
            (_('Password'), AuthenticationMethod.Password),
            (_('Key file'), AuthenticationMethod.KeyFile),
            # (_('Configuration file'), AuthenticationMethod.ConfigFile),
        )

        self._auth_methods = self.create_combobox(
            _("Authentication method:"),
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
        layout.setContentsMargins(
            3 * AppStyle.MarginSize, 0, 3 * AppStyle.MarginSize, 0
        )
        if self.NEW_CONNECTION:
            layout.addLayout(intro_layout)
            layout.addSpacing(8 * AppStyle.MarginSize)
        layout.addWidget(self._auth_methods)
        layout.addSpacing(5 * AppStyle.MarginSize)
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
            validate_callback=self._validate_name,
            validate_reason=_("This connection name is already taken"),
        )

        address = self.create_lineedit(
            text=_("Remote address *"),
            option=f"{self.host_id}/{auth_method}/address",
            tip=_(
                "This is the IP address or domain name of your remote machine"
            ),
            validate_callback=self._validate_address,
            validate_reason=_("The address is not a valid IP or domain name"),
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
        self._name_widgets[f"{auth_method}"] = name
        self._address_widgets[f"{auth_method}"] = address

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

        validation_label = ValidationLabel(self)

        # Add widgets to their required dicts
        self._widgets_for_validation[AuthenticationMethod.Password].append(
            password
        )

        self._validation_labels[
            AuthenticationMethod.Password
        ] = validation_label

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
        password_layout.addWidget(validation_label)
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

        validation_label = ValidationLabel(self)

        # Add widgets to their required dicts
        self._widgets_for_validation[AuthenticationMethod.KeyFile].append(
            keyfile
        )

        self._validation_labels[
            AuthenticationMethod.KeyFile
        ] = validation_label

        # Layout
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
        keyfile_layout.addWidget(validation_label)
        keyfile_layout.addStretch()

        keyfile_subpage = QWidget(self)
        keyfile_subpage.setLayout(keyfile_layout)

        return keyfile_subpage

    def _create_configfile_subpage(self):
        # Widgets
        name = self.create_lineedit(
            text=_("Name *"),
            option=f"{self.host_id}/{AuthenticationMethod.ConfigFile}/name",
            tip=_("Introduce a name to identify your connection"),
            status_icon=ima.icon("error"),
        )

        configfile = self.create_browsefile(
            text=_("Configuration file *"),
            option=f"{self.host_id}/configfile",
            alignment=Qt.Vertical,
            status_icon=ima.icon("error"),
        )

        validation_label = ValidationLabel(self)

        # Add widgets to their required dicts
        self._name_widgets[AuthenticationMethod.ConfigFile] = name
        self._widgets_for_validation[AuthenticationMethod.ConfigFile] = [
            name,
            configfile,
        ]
        self._validation_labels[
            AuthenticationMethod.ConfigFile
        ] = validation_label

        # Layout
        configfile_layout = QVBoxLayout()
        configfile_layout.setContentsMargins(0, 0, 0, 0)
        configfile_layout.addWidget(name)
        configfile_layout.addSpacing(5 * AppStyle.MarginSize)
        configfile_layout.addWidget(configfile)
        configfile_layout.addSpacing(7 * AppStyle.MarginSize)
        configfile_layout.addWidget(validation_label)
        configfile_layout.addStretch()

        configfile_widget = QWidget(self)
        configfile_widget.setLayout(configfile_layout)

        return configfile_widget

    def _validate_name(self, name):
        """Check connection name is not taken by a previous connection."""
        servers = self.get_option("servers", default={})
        for server in servers:
            # Don't check repeated name with the same server
            if server == self.host_id:
                continue

            names = [
                self.get_option(f"{server}/{method}/name")
                for method in get_class_values(AuthenticationMethod)
            ]

            if name in names:
                return False

        return True

    def _validate_address(self, address):
        """Validate if address introduced by users is correct."""
        # Regex pattern for a valid domain name (simplified version)
        domain_pattern = (
            r'^([a-zA-Z0-9][a-zA-Z0-9-]{0,61}[a-zA-Z0-9]\.){1,}[a-zA-Z]{2,}$'
        )

        # Regex pattern for a valid IPv4 address
        ipv4_pattern = r'^(\d{1,3}\.){3}\d{1,3}$'

        # Regex pattern for a valid IPv6 address (simplified version)
        ipv6_pattern = r'^([\da-fA-F]{1,4}:){7}[\da-fA-F]{1,4}$'

        # Combined pattern to check all three formats
        combined_pattern = (
            f'({domain_pattern})|({ipv4_pattern})|({ipv6_pattern})'
        )

        address_re = re.compile(combined_pattern)
        return True if address_re.match(address) else False


class NewConnectionPage(BaseConnectionPage):
    """Page to receive SSH credentials for a remote connection."""

    LOAD_FROM_CONFIG = False
    NEW_CONNECTION = True

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
    def reset_page(self, clear=False):
        """Reset page to allow users to introduce a new connection."""
        # Set a new host id
        self.host_id = str(uuid.uuid4())

        if clear:
            # Reset tracked widgets
            self.reset_widget_dicts()

            # Add a new, clean set of widgets to the page
            clean_info_widget = self.create_connection_info_widget()
            self.layout.addWidget(clean_info_widget)
            self.layout.setCurrentWidget(clean_info_widget)
        else:
            # Change option names associated to all widgets present in the page
            # to reference the new host_id
            for widgets in [self.comboboxes, self.lineedits, self.spinboxes]:
                for widget in widgets:
                    section, option, default = widgets[widget]
                    new_option = "/".join(
                        [self.host_id] + option.split("/")[1:]
                    )
                    widgets[widget] = (section, new_option, default)


class ConnectionPage(BaseConnectionPage):
    """Page to display connection status and info for a remote machine."""

    def __init__(self, parent, host_id):
        super().__init__(parent, host_id)
        self.new_name = None

    # ---- SidebarPage API
    # -------------------------------------------------------------------------
    def get_name(self):
        return self.get_option(f"{self.host_id}/{self.auth_method()}/name")

    def setup_page(self):
        info_widget = self.create_connection_info_widget()
        self.status_widget = ConnectionStatusWidget(self, self.host_id)

        self.create_tab(_("Connection status"), self.status_widget)
        self.create_tab(_("Connection info"), info_widget)

    def get_icon(self):
        return self.create_icon("remote_server")

    # ---- Public API
    # -------------------------------------------------------------------------
    def save_server_info(self):
        # Mapping from options in our config system to those accepted by
        # asyncssh
        options = SSHClientOptions(
            host=self.get_option(
                f"{self.host_id}/{self.auth_method()}/address"
            ),
            port=self.get_option(f"{self.host_id}/{self.auth_method()}/port"),
            username=self.get_option(
                f"{self.host_id}/{self.auth_method()}/username"
            ),
            client_keys=self.get_option(f"{self.host_id}/keyfile"),
            config=self.get_option(f"{self.host_id}/configfile"),
        )

        servers = self.get_option("servers", default={})
        servers[self.host_id] = options
        self.set_option("servers", servers)

    def remove_config_options(self):
        """Remove config options associated to this connection."""
        # Remove current server from the dict of them
        servers = self.get_option("servers")
        servers.pop(self.host_id)
        self.set_option("servers", servers)

        # Remove regular options
        options = [
            "auth_method",
            "password_login/name",
            "password_login/address",
            "password_login/port",
            "password_login/username",
            "keyfile_login/name",
            "keyfile_login/address",
            "keyfile_login/port",
            "keyfile_login/username",
            "keyfile",
            "configfile",
        ]
        for option in options:
            self.remove_option(f"{self.host_id}/{option}")

        # Remove secure options
        for secure_option in ["password", "passpharse"]:
            # One of these options was saved securely and other as empty in our
            # config system, so we try to remove them both.
            for secure in [True, False]:
                self.remove_option(
                    f"{self.host_id}/{secure_option}", secure=secure
                )

    def update_status(self, info: ConnectionInfo):
        if info["id"] == self.host_id:
            self.status = info["status"]
            self.status_widget.update_status(info)

    def add_log(self, log: RemoteClientLog):
        if log["id"] == self.host_id:
            self.status_widget.add_log(log)

    def add_logs(self, logs: Iterable):
        self.status_widget.add_logs(logs)

    def has_new_name(self):
        """Check if users changed the connection name."""
        current_auth_method = self.auth_method(from_gui=True)
        current_name = self._name_widgets[current_auth_method].textbox.text()

        if self.get_name() != current_name:
            self.new_name = current_name
            return True
        else:
            self.new_name = None
            return False


# =============================================================================
# ---- Dialog
# =============================================================================
class ConnectionDialog(SidebarDialog):
    """
    Dialog to handle and display remote connection information for different
    machines.
    """

    TITLE = _("Remote connections")
    MIN_WIDTH = 900 if MAC else (850 if WIN else 860)
    MIN_HEIGHT = 700 if MAC else (635 if WIN else 650)
    PAGE_CLASSES = [NewConnectionPage]

    sig_start_server_requested = Signal(str)
    sig_stop_server_requested = Signal(str)
    sig_server_renamed = Signal(str)
    sig_connections_changed = Signal()

    def __init__(self, parent=None):
        self.ICON = ima.icon('remote_server')
        super().__init__(parent)
        self._container = parent

        # -- Setup
        self._add_saved_connection_pages()

        # If there's more than one page, give focus to the first server because
        # users will probably want to interact with servers here rather than
        # create new connections.
        if self.number_of_pages() > 1:
            # Index 1 is the separator added after the new connection page
            self.set_current_index(2)

        # -- Signals
        if self._container is not None:
            self._container.sig_connection_status_changed.connect(
                self._update_connection_buttons_state
            )

    # ---- SidebarDialog API
    # -------------------------------------------------------------------------
    def create_buttons(self):
        bbox = SpyderDialogButtonBox(QDialogButtonBox.Cancel)

        self._button_save_connection = QPushButton(_("Save connection"))
        self._button_save_connection.clicked.connect(
            self._save_connection_info
        )
        bbox.addButton(
            self._button_save_connection, QDialogButtonBox.ResetRole
        )

        self._button_remove_connection = QPushButton(_("Remove connection"))
        self._button_remove_connection.clicked.connect(
            self._remove_connection_info
        )
        bbox.addButton(
            self._button_remove_connection, QDialogButtonBox.ResetRole
        )

        self._button_clear_settings = QPushButton(_("Clear settings"))
        self._button_clear_settings.clicked.connect(self._clear_settings)
        bbox.addButton(
            self._button_clear_settings, QDialogButtonBox.ActionRole
        )

        self._button_connect = QPushButton(_("Connect"))
        self._button_connect.clicked.connect(self._start_server)
        bbox.addButton(self._button_connect, QDialogButtonBox.ActionRole)

        self._button_stop = QPushButton(_("Stop"))
        self._button_stop.clicked.connect(self._stop_server)
        bbox.addButton(self._button_stop, QDialogButtonBox.ActionRole)

        layout = QHBoxLayout()
        layout.addWidget(bbox)

        return bbox, layout

    def current_page_changed(self, index):
        """Update the state of buttons when moving from page to page."""
        page = self.get_page(index)
        if page.NEW_CONNECTION:
            self._button_save_connection.setEnabled(True)
            self._button_clear_settings.setHidden(False)
            self._button_remove_connection.setHidden(True)
            self._button_stop.setHidden(True)
        else:
            if page.is_modified:
                self._button_save_connection.setEnabled(True)
            else:
                self._button_save_connection.setEnabled(False)

            self._button_clear_settings.setHidden(True)
            self._button_remove_connection.setHidden(False)
            self._button_stop.setHidden(False)

        if page.status in [
            ConnectionStatus.Inactive,
            ConnectionStatus.Error,
        ]:
            self._button_connect.setEnabled(True)
        else:
            self._button_connect.setEnabled(False)

        # TODO: Check if it's possible to stop a connection while it's
        # connecting
        if page.status == ConnectionStatus.Active:
            self._button_stop.setEnabled(True)
        else:
            self._button_stop.setEnabled(False)

    # ---- Private API
    # -------------------------------------------------------------------------
    def _save_connection_info(self):
        """Save the connection info stored in a page."""
        page = self.get_page()

        # Validate info
        if not page.validate_page():
            return

        if page.NEW_CONNECTION:
            # Save info provided by users
            page.save_to_conf()

            # Add separator if needed
            if self.number_of_pages() == 1:
                self.add_separator()

            # Add connection page to the dialog with the new info
            self._add_connection_page(host_id=page.host_id, new=True)

            # Give focus to the new page
            self.set_current_index(self.number_of_pages() - 1)

            # Reset page in case users want to introduce another connection
            page.reset_page()

            # Inform container that a change in connections took place
            self.sig_connections_changed.emit()
        else:
            # Update name in the dialog if it was changed by users. This needs
            # to be done before calling save_to_conf so that we can compare the
            # saved name with the current one.
            if page.has_new_name():
                self.get_item().setText(page.new_name)

            # Update connection info
            page.save_to_conf()

            # After saving to our config system, we can inform the container
            # that a change in connections took place.
            if page.new_name is not None:
                self.sig_connections_changed.emit()
                self.sig_server_renamed.emit(page.host_id)
                page.new_name = None

            # Mark page as not modified and disable save button
            page.set_modified(False)
            self._button_save_connection.setEnabled(False)

    def _remove_connection_info(self):
        """
        Remove the connection info stored in a given page and hide it as well.
        """
        page = self.get_page()
        if not page.NEW_CONNECTION:
            reply = QMessageBox.question(
                self,
                _("Remove connection"),
                _(
                    "Do you want to remove the connection called <b>{}</b>?"
                ).format(page.get_name()),
                QMessageBox.Yes,
                QMessageBox.No,
            )

            if reply == QMessageBox.Yes:
                self.hide_page()
                page.remove_config_options()

                # Inform container that a change in connections took place
                self.sig_connections_changed.emit()

    def _clear_settings(self):
        """Clear the setting introduced in the new connection page."""
        page = self.get_page()
        if page.NEW_CONNECTION:
            page.reset_page(clear=True)

    def _start_server(self):
        """Start the server corresponding to a given page."""
        page = self.get_page()

        # Validate info
        if not page.validate_page():
            return

        # This uses the current host_id in case users want to start a
        # connection directly from the new connection page (
        # _save_connection_info generates a new id fo that page at the end).
        host_id = page.host_id

        if page.NEW_CONNECTION or page.is_modified:
            # Save connection info if necessary
            self._save_connection_info()

            # TODO: Handle the case when the connection info is active and
            # users change its info.

        self.sig_start_server_requested.emit(host_id)

    def _stop_server(self):
        """Stop the server corresponding to a given page."""
        page = self.get_page()

        # The stop button is not visible in the new connection page
        if not page.NEW_CONNECTION:
            self._button_stop.setEnabled(False)
            self.sig_stop_server_requested.emit(page.host_id)

    def _add_connection_page(self, host_id: str, new: bool):
        """Add a new connection page to the dialog."""
        page = ConnectionPage(self, host_id=host_id)

        # This is necessary to make button_save_connection enabled when there
        # are config changes in the page
        page.apply_button_enabled.connect(
            self._update_button_save_connection_state
        )

        if new:
            page.save_server_info()

        self.add_page(page)

        # Add saved logs to the page
        if self._container is not None:
            page.add_logs(self._container.client_logs.get(host_id, []))

            # This updates the info shown in the "Connection info" tab of pages
            self._container.sig_connection_status_changed.connect(
                page.update_status
            )
            self._container.sig_client_message_logged.connect(page.add_log)

    def _add_saved_connection_pages(self):
        """Add a connection page for each server saved in our config system."""
        page = self.get_page(index=0)
        servers = page.get_option("servers", default={})

        if servers:
            self.add_separator()

            for id_ in servers.keys():
                self._add_connection_page(host_id=id_, new=False)

    def _update_button_save_connection_state(self, state: bool):
        """Update the state of the 'Save connection' button."""
        self._button_save_connection.setEnabled(state)

    def _update_connection_buttons_state(self, info: ConnectionInfo):
        """Update the state of the 'Connect' button."""
        page = self.get_page()
        if page.host_id == info["id"]:
            if info["status"] in [
                ConnectionStatus.Inactive,
                ConnectionStatus.Error,
            ]:
                self._button_connect.setEnabled(True)
            else:
                self._button_connect.setEnabled(False)

            # TODO: Check if it's possible to stop a connection while it's
            # connecting
            if info["status"] == ConnectionStatus.Active:
                self._button_stop.setEnabled(True)
            else:
                self._button_stop.setEnabled(False)


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()  # noqa
    app.setStyleSheet(str(APP_STYLESHEET))

    dialog = ConnectionDialog()
    dialog.exec_()


if __name__ == "__main__":
    test()
