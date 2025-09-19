# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Pages for the dialog that handles remote connections."""

# Standard library imports
from __future__ import annotations
from collections.abc import Iterable
import re
from typing import TypedDict
import uuid

# Third party imports
from qtpy.QtCore import Qt
from qtpy.QtWidgets import (
    QButtonGroup,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QStackedWidget,
    QStackedLayout,
    QVBoxLayout,
    QWidget,
)

# Local imports
from spyder.api.fonts import SpyderFontType, SpyderFontsMixin
from spyder.api.translations import _
from spyder.api.utils import get_class_values
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
    ClientType,
    RemoteClientLog,
)
from spyder.plugins.remoteclient.widgets import AuthenticationMethod
from spyder.plugins.remoteclient.widgets.connectionstatus import (
    ConnectionStatusWidget,
)
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import AppStyle, MAC, WIN
from spyder.widgets.config import SpyderConfigPage
from spyder.widgets.helperwidgets import MessageLabel, TipWidget

try:
    from spyder_env_manager.spyder.widgets.new_environment import (
        NewEnvironment,
    )
    from spyder_env_manager.spyder.widgets.edit_environment import (
        EditEnvironment,
    )
    ENV_MANAGER = True
except Exception:
    ENV_MANAGER = False


# =============================================================================
# ---- Constants
# =============================================================================
class ValidationReasons(TypedDict):
    repeated_name: bool | None
    missing_info: bool | None
    invalid_address: bool | None
    invalid_url: bool | None


class CreateEnvMethods:
    NewEnv = 1
    ImportEnv = 2
    NoEnv = 4


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
            self.client_type = None
        else:
            self.host_id = host_id
            self.status = self.get_option(
                f"{host_id}/status", default=ConnectionStatus.Inactive
            )
            self.client_type = self.get_option(
                f"{host_id}/client_type", default=ClientType.SSH
            )

        self._auth_methods = None
        self._widgets_for_validation = {}
        self._validation_labels = {}
        self._name_widgets = {}
        self._address_widgets = {}
        self._url_widgets = {}

    # ---- Public API
    # -------------------------------------------------------------------------
    def auth_method(self, from_gui=False):
        if from_gui:
            if self.client_type == ClientType.SSH or (
                self._auth_methods and self._auth_methods.combobox.isVisible()
            ):
                if self._auth_methods.combobox.currentIndex() == 0:
                    auth_method = AuthenticationMethod.Password
                elif self._auth_methods.combobox.currentIndex() == 1:
                    auth_method = AuthenticationMethod.KeyFile
                else:
                    auth_method = AuthenticationMethod.ConfigFile
            else:
                auth_method = AuthenticationMethod.JupyterHub
        else:
            auth_method = self.get_option(f"{self.host_id}/auth_method")

        return auth_method

    def validate_page(self):
        """Validate contents before saving the connection."""
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
            elif widget == self._url_widgets.get(auth_method):
                # Validate URL
                widget.status_action.setVisible(False)
                url = widget.textbox.text()
                if not self._validate_url(url):
                    reasons["invalid_url"] = True
                    widget.status_action.setVisible(True)
            else:
                widget.status_action.setVisible(False)

        if reasons:
            validate_label.set_text(
                self._compose_failed_validation_text(reasons)
            )
            validate_label.setVisible(True)

        return False if reasons else True

    def create_jupyterhub_connection_info_widget(self):
        """
        Create widget that contains all other widgets to receive or display
        JupyterHub server based connection info.
        """
        if self.NEW_CONNECTION:
            # Widgets
            intro_label = QLabel(
                _("Configure settings for connecting to a JupyterHub server")
            )
            intro_tip_text = _(
                "Spyder will use this connection to start remote kernels in "
                "the IPython Console. This allows you to use Spyder locally "
                "while running code remotely via a JupyterHub server."
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

        # Final layout
        layout = QVBoxLayout()
        layout.setContentsMargins(
            3 * AppStyle.MarginSize, 0, 3 * AppStyle.MarginSize, 0
        )
        if self.NEW_CONNECTION:
            layout.addLayout(intro_layout)
            layout.addSpacing(8 * AppStyle.MarginSize)
        layout.addWidget(self._create_jupyterhub_subpage())

        jupyterhub_connection_info_widget = QWidget(self)
        jupyterhub_connection_info_widget.setLayout(layout)

        return jupyterhub_connection_info_widget

    def create_ssh_connection_info_widget(self):
        """
        Create widget that contains all other widgets to receive or display
        SSH based connection info.
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
        right_margin = 3
        if ENV_MANAGER and self.NEW_CONNECTION:
            right_margin = 4 if MAC else (6 if WIN else 5)

        layout = QVBoxLayout()
        layout.setContentsMargins(
            3 * AppStyle.MarginSize, 0, right_margin * AppStyle.MarginSize, 0
        )
        if self.NEW_CONNECTION:
            layout.addLayout(intro_layout)
            layout.addSpacing(8 * AppStyle.MarginSize)
        layout.addWidget(self._auth_methods)
        layout.addSpacing(5 * AppStyle.MarginSize)
        layout.addWidget(subpages)

        ssh_connection_info_widget = QWidget(self)
        ssh_connection_info_widget.setLayout(layout)

        return ssh_connection_info_widget

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

        validation_label = MessageLabel(self)

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

        passphrase = self.create_lineedit(
            text=_("Passphrase"),
            option=f"{self.host_id}/passphrase",
            tip=(
                _("Your passphrase will be saved securely by Spyder")
                if self.NEW_CONNECTION
                else _("Your passphrase is saved securely by Spyder")
            ),
            password=True
        )

        validation_label = MessageLabel(self)

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
        keyfile_layout.addWidget(passphrase)
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

        validation_label = MessageLabel(self)

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

    def _create_jupyterhub_subpage(self):
        # Widgets
        name = self.create_lineedit(
            text=_("Name *"),
            option=f"{self.host_id}/{AuthenticationMethod.JupyterHub}/name",
            tip=_("Introduce a name to identify your connection"),
            status_icon=ima.icon("error"),
        )

        url = self.create_lineedit(
            text=_("Server URL *"),
            option=f"{self.host_id}/url",
            tip=_("This is the URL of the JupyterHub server"),
            validate_callback=self._validate_url,
            validate_reason=_("The URL is not a valid one"),
        )

        token = self.create_lineedit(
            text=_("Token *"),
            option=f"{self.host_id}/token",
            tip=(
                _("Your token will be saved securely by Spyder")
                if self.NEW_CONNECTION
                else _("Your token is saved securely by Spyder")
            ),
            status_icon=ima.icon("error"),
            password=True
        )

        validation_label = MessageLabel(self)

        # Add widgets to their required dicts
        self._name_widgets[AuthenticationMethod.JupyterHub] = name
        self._widgets_for_validation[AuthenticationMethod.JupyterHub] = [
            name,
            url,
            token,
        ]
        self._url_widgets[f"{AuthenticationMethod.JupyterHub}"] = url
        self._validation_labels[
            AuthenticationMethod.JupyterHub
        ] = validation_label

        # Layout
        jupyterhub_layout = QVBoxLayout()
        jupyterhub_layout.setContentsMargins(0, 0, 0, 0)
        jupyterhub_layout.addWidget(name)
        jupyterhub_layout.addSpacing(5 * AppStyle.MarginSize)
        jupyterhub_layout.addWidget(url)
        jupyterhub_layout.addSpacing(5 * AppStyle.MarginSize)
        jupyterhub_layout.addWidget(token)
        jupyterhub_layout.addSpacing(7 * AppStyle.MarginSize)
        jupyterhub_layout.addWidget(validation_label)
        jupyterhub_layout.addStretch()

        jupyterhub_widget = QWidget(self)
        jupyterhub_widget.setLayout(jupyterhub_layout)

        return jupyterhub_widget

    def _validate_name(self, name):
        """Check connection name is not taken by a previous connection."""
        servers = self.get_option("servers", default={})
        for server in servers:
            # Don't check repeated name with the same server
            if server == self.host_id:
                continue

            names = [
                self.get_option(f"{server}/{method}/name", default="")
                for method in get_class_values(AuthenticationMethod)
            ]

            if name in names:
                return False

        return True

    def _validate_url(self, url):
        # Regex pattern for a valid URL.
        # See https://learn.microsoft.com/en-us/previous-versions/msp-n-p/
        # ff650303(v=pandp.10)#common-regular-expressions
        url_pattern = (
            r'^(ht|f)tp(s?)\:\/\/'
            r'[0-9a-zA-Z]([-.\w]*[0-9a-zA-Z])*(:(0-9)*)*(\/?)'
            r'([a-zA-Z0-9\-\.\?\,\'\/\\\+&amp;%\$#_]*)?$'
        )
        url_re = re.compile(url_pattern)

        return True if url_re.match(url) else False

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

    def _compose_failed_validation_text(self, reasons: ValidationReasons):
        """
        Compose validation text from a dictionary of reasons for which it
        failed.
        """
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

        if reasons.get("invalid_url"):
            text += (
                prefix + _("The URL you provided is not valid.") + suffix
            )

        if reasons.get("missing_info"):
            text += (
                prefix
                + _("There are missing fields on this page.")
            )

        return text


class NewConnectionPage(BaseConnectionPage):
    """Page to receive SSH credentials for a remote connection."""

    MAX_WIDTH = 600 if MAC else 580
    LOAD_FROM_CONFIG = False
    NEW_CONNECTION = True

    # ---- SidebarPage API
    # -------------------------------------------------------------------------
    def get_name(self):
        return _("New connection")

    def setup_page(self):
        # Attributes
        self.env_method_group = QButtonGroup(self)
        self._radio_buttons_to_info_widgets: dict[
            CreateEnvMethods, QWidget
        ] = {}

        # Widgets
        self.ssh_info_widget = self.create_ssh_connection_info_widget()
        jupyterhub_info_widget = self.create_jupyterhub_connection_info_widget()

        if ENV_MANAGER:
            self.env_creation_widget = self._create_env_creation_widget()
            self.env_packages_widget = self._create_env_packages_widget()

        # Use a stacked widget/layout so we can hide the current widgets and
        # create new ones in case users want to introduce more connections.
        self.ssh_widget = QStackedWidget(self)
        self.ssh_widget.addWidget(self.ssh_info_widget)
        if ENV_MANAGER:
            self.ssh_widget.addWidget(self.env_creation_widget)
            self.ssh_widget.addWidget(self.env_packages_widget)

        self.jupyterhub_widget = QWidget(self)
        jupyterhub_layout = QStackedLayout()
        jupyterhub_layout.addWidget(jupyterhub_info_widget)
        self.jupyterhub_widget.setLayout(jupyterhub_layout)

        self.create_tab("SSH", self.ssh_widget)
        self.create_tab("JupyterHub", self.jupyterhub_widget)

    def get_icon(self):
        return self.create_icon("add_server")

    # ---- SpyderConfigPage API
    # -------------------------------------------------------------------------
    def save_to_conf(self):
        super().save_to_conf()

        if self.NEW_CONNECTION:
            # Set the client type for new connections following current tab
            # index
            client_type = (
                ClientType.SSH
                if self.tabs.currentIndex() == 0
                else ClientType.JupyterHub
            )
            self.set_option(f"{self.host_id}/client_type", client_type)
            if client_type == ClientType.JupyterHub:
                # Set correct auth_method option following client type detected
                self.set_option(
                    f"{self.host_id}/auth_method",
                    AuthenticationMethod.JupyterHub,
                )

    # ---- BaseConnectionPage API
    # -------------------------------------------------------------------------
    def validate_page(self):
        # Skip this because it means the info validation was already done
        if (
            ENV_MANAGER
            and self.get_current_tab() == "SSH"
            and not self.is_ssh_info_widget_shown()
        ):
            return True
        else:
            return super().validate_page()

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
            ssh_clean_info_widget = self.create_ssh_connection_info_widget()
            self.ssh_widget.layout().addWidget(ssh_clean_info_widget)
            self.ssh_widget.layout().setCurrentWidget(ssh_clean_info_widget)

            jupyterhub_clean_info_widget = (
                self.create_ssh_connection_info_widget()
            )
            self.jupyterhub_widget.layout().addWidget(
                jupyterhub_clean_info_widget
            )
            self.jupyterhub_widget.layout().setCurrentWidget(
                jupyterhub_clean_info_widget
            )
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

    def get_current_tab(self, index: int | None = None) -> str:
        if index is None:
            index = self.tabs.currentIndex()

        if index == 0:
            return "SSH"
        else:
            return "JupyterHub"

    def show_ssh_info_widget(self):
        self.ssh_widget.setCurrentWidget(self.ssh_info_widget)

    def show_env_creation_widget(self):
        self.ssh_widget.setCurrentWidget(self.env_creation_widget)

    def show_env_packages_widget(self):
        self.ssh_widget.setCurrentWidget(self.env_packages_widget)

    def is_ssh_info_widget_shown(self) -> bool:
        return self.ssh_widget.currentWidget() == self.ssh_info_widget

    def is_env_creation_widget_shown(self) -> bool:
        return self.ssh_widget.currentWidget() == self.env_creation_widget

    def is_env_packages_widget_shown(self) -> bool:
        return self.ssh_widget.currentWidget() == self.env_packages_widget

    def selected_env_creation_method(self) -> CreateEnvMethods:
        return self.env_method_group.checkedId()

    def validate_env_creation(self):
        method_id = self.env_method_group.checkedId()
        if method_id != CreateEnvMethods.NoEnv:
            env_method_widget = self._radio_buttons_to_info_widgets[method_id]
            if env_method_widget.validate_contents(env_names=[]):
                return True
            else:
                return False

        return True

    def get_create_env_info(self):
        method_id = self.env_method_group.checkedId()
        env_method_widget = self._radio_buttons_to_info_widgets[method_id]
        if method_id == CreateEnvMethods.NewEnv:
            return (
                env_method_widget.get_env_name(),
                env_method_widget.get_python_version()
            )
        elif method_id == CreateEnvMethods.ImportEnv:
            return (
                env_method_widget.get_zip_file(),
                env_method_widget.get_env_name()
            )

    def get_env_packages_list(self):
        return self._packages_info.get_changed_packages()

    def setup_env_packages_widget(self):
        env_name, python_version = self.get_create_env_info()
        self._packages_info.setup(
            env_name,
            python_version,
            f"~/.envs-manager/backends/pixi/{env_name}"
        )

    # ---- Private API
    # -------------------------------------------------------------------------
    def _create_env_creation_widget(self):
        # Intro text
        intro_label = QLabel(
            _("Create a Python environment on the remote host")
        )
        intro_tip_text = _(
            "Decide whether you want to create a remote environment to run "
            "your code and how to do it"
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

        # Available methods
        methods_group = QGroupBox(_("Available methods"))

        self.env_method_group.idToggled.connect(
            self._on_env_creation_method_changed
        )

        new_env_radio = self.create_radiobutton(
            _("Create a new environment"),
            option=None,
            button_group=self.env_method_group,
            id_=CreateEnvMethods.NewEnv,
        )
        import_env_radio = self.create_radiobutton(
            _("Import an existing environment"),
            option=None,
            button_group=self.env_method_group,
            id_=CreateEnvMethods.ImportEnv,
        )
        no_env_radio = self.create_radiobutton(
            _("Don't create an environment"),
            option=None,
            button_group=self.env_method_group,
            id_=CreateEnvMethods.NoEnv,
        )

        methods_layout = QVBoxLayout()
        methods_layout.addSpacing(3)
        methods_layout.addWidget(new_env_radio)
        methods_layout.addWidget(import_env_radio)
        methods_layout.addWidget(no_env_radio)
        methods_group.setLayout(methods_layout)

        # Required info
        info_group = QGroupBox(_("Required information"))

        new_env_info = NewEnvironment(
            self,
            max_width_for_content=470,
            show_in_remote_connections_dialog=True
        )
        new_env_info.setMaximumWidth(470)

        import_env_info = NewEnvironment(
            self,
            max_width_for_content=470,
            import_env=True,
            show_in_remote_connections_dialog=True
        )
        import_env_info.setMaximumWidth(470)

        no_env_info = QLabel(
            _(
                "You can set up an environment later by going to the menu "
                "entry <i>Tools > Environment manager</i>."
            )
        )
        no_env_info.setWordWrap(True)

        info_layout = QVBoxLayout()
        info_layout.addWidget(new_env_info)
        info_layout.addWidget(import_env_info)
        info_layout.addWidget(no_env_info)
        info_group.setLayout(info_layout)

        # Hide all info widgets to only show the one that's checked
        for widget in [new_env_info, import_env_info, no_env_info]:
            widget.setVisible(False)

        # Use the following mapping to show/hide info widgets when the
        # corresponding radio button is toggled
        self._radio_buttons_to_info_widgets = {
            CreateEnvMethods.NewEnv: new_env_info,
            CreateEnvMethods.ImportEnv: import_env_info,
            CreateEnvMethods.NoEnv: no_env_info,
        }

        # Set new env as the default method
        new_env_radio.radiobutton.setChecked(True)

        # Final layout
        layout = QVBoxLayout()
        layout.setContentsMargins(
            3 * AppStyle.MarginSize, 0, 3 * AppStyle.MarginSize, 0
        )
        layout.addLayout(intro_layout)
        layout.addSpacing(8 * AppStyle.MarginSize)
        layout.addWidget(methods_group)
        layout.addWidget(info_group)
        layout.addStretch()

        env_creation_widget = QWidget(self)
        env_creation_widget.setLayout(layout)

        return env_creation_widget

    def _on_env_creation_method_changed(
        self, id_: CreateEnvMethods, checked: bool
    ):
        self._radio_buttons_to_info_widgets[id_].setVisible(checked)

    def _create_env_packages_widget(self):
        # Intro text
        intro_label = QLabel(_("Select packages for your remote environment"))
        intro_tip_text = _(
            "Choose the packages you want to install in your remote Python "
            "environment"
        )
        intro_tip = TipWidget(
            tip_text=intro_tip_text,
            icon=ima.icon("info_tip"),
            hover_icon=ima.icon("info_tip_hover"),
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

        self._packages_info = EditEnvironment(
            self, show_in_remote_connections_dialog=True
        )
        self._packages_info.set_empty_message_visible(True)
        self._packages_info.setMaximumWidth(
            525 if MAC else (485 if WIN else 500)
        )

        # Final layout
        layout = QVBoxLayout()
        layout.setContentsMargins(
            3 * AppStyle.MarginSize,
            0,
            3 * AppStyle.MarginSize,
            # Add bottom margin to let the packages table take the available
            # vertical space
            (2 if MAC else (3 if WIN else 4)) * AppStyle.MarginSize,
        )
        layout.addLayout(intro_layout)
        layout.addSpacing(8 * AppStyle.MarginSize)
        layout.addWidget(self._packages_info)

        env_packages_widget = QWidget(self)
        env_packages_widget.setLayout(layout)

        return env_packages_widget


class ConnectionPage(BaseConnectionPage):
    """Page to display connection status and info for a remote machine."""

    MAX_WIDTH = 600 if MAC else 580

    def __init__(self, parent, host_id):
        super().__init__(parent, host_id)
        self.new_name = None

    # ---- SidebarPage API
    # -------------------------------------------------------------------------
    def get_name(self):
        return self.get_option(f"{self.host_id}/{self.auth_method()}/name")

    def setup_page(self):
        if self.client_type == ClientType.SSH:
            info_widget = self.create_ssh_connection_info_widget()
        else:
            info_widget = self.create_jupyterhub_connection_info_widget()

        self.status_widget = ConnectionStatusWidget(self, self.host_id)

        self.create_tab(_("Connection status"), self.status_widget)
        self.create_tab(_("Connection info"), info_widget)

    def get_icon(self):
        return self.create_icon("remote_server")

    # ---- Public API
    # -------------------------------------------------------------------------
    def save_server_id(self):
        servers = self.get_option("servers", default={})
        servers[self.host_id] = {}
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
            "configfile_login/name",
            "jupyterhub_login/name",
            "keyfile",
            "configfile",
            "status",
            "status_message",
            "url",
            "client_type",
        ]
        for option in options:
            self.remove_option(f"{self.host_id}/{option}")

        # Remove secure options
        for secure_option in ["password", "passphrase", "token"]:
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

    def update_connection_info(self):
        self.status_widget.update_info()
