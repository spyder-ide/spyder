# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Dialog to handle remote connections."""

# Standard library imports
from __future__ import annotations

# Third party imports
from qtpy.QtCore import Signal
from qtpy.QtWidgets import (
    QDialogButtonBox,
    QHBoxLayout,
    QMessageBox,
    QPushButton,
)

# Local imports
from spyder.api.translations import _
from spyder.api.widgets.dialogs import SpyderDialogButtonBox
from spyder.plugins.remoteclient.api.protocol import (
    ConnectionInfo,
    ConnectionStatus,
)
from spyder.plugins.remoteclient.widgets.connectionpages import (
    ConnectionPage,
    CreateEnvMethods,
    ENV_MANAGER,
    NewConnectionPage,
)
from spyder.utils.icon_manager import ima
from spyder.utils.stylesheet import MAC, WIN
from spyder.widgets.sidebardialog import SidebarDialog


class ConnectionDialog(SidebarDialog):
    """
    Dialog to handle and display remote connection information for different
    machines.
    """

    TITLE = _("Remote connections")
    FIXED_SIZE = True
    MIN_WIDTH = 895 if MAC else (810 if WIN else 860)
    MIN_HEIGHT = 730 if MAC else (655 if WIN else 670)
    PAGE_CLASSES = [NewConnectionPage]

    sig_start_server_requested = Signal(str)
    sig_stop_server_requested = Signal(str)
    sig_server_renamed = Signal(str)
    sig_connections_changed = Signal()
    sig_server_updated = Signal(str)
    sig_create_env_requested = Signal(str, str, str, list)
    sig_import_env_requested = Signal(str, str, str)

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

        if ENV_MANAGER:
            self._new_connection_page: NewConnectionPage = self.get_page(0)
            self._new_connection_page.tabs.currentChanged.connect(
                self._on_new_connection_page_tab_changed
            )
            self._new_connection_page.env_method_group.idToggled.connect(
                self._set_buttons_for_env_creation_method
            )

    # ---- SidebarDialog API
    # -------------------------------------------------------------------------
    def create_buttons(self):
        bbox = SpyderDialogButtonBox(QDialogButtonBox.Cancel)

        self._button_cancel = bbox.button(QDialogButtonBox.Cancel)

        self._button_save_connection = QPushButton(_("Save"))
        self._button_save_connection.clicked.connect(
            self._save_connection_info
        )
        bbox.addButton(
            self._button_save_connection, QDialogButtonBox.ResetRole
        )

        self._button_remove_connection = QPushButton(_("Remove"))
        self._button_remove_connection.clicked.connect(
            self._remove_connection_info
        )
        bbox.addButton(
            self._button_remove_connection, QDialogButtonBox.ResetRole
        )

        self._button_clear_settings = QPushButton(_("Clear"))
        self._button_clear_settings.clicked.connect(self._clear_settings)
        bbox.addButton(
            self._button_clear_settings, QDialogButtonBox.ActionRole
        )

        self._button_stop = QPushButton(_("Stop"))
        self._button_stop.clicked.connect(self._stop_server)
        bbox.addButton(self._button_stop, QDialogButtonBox.ActionRole)

        self._button_connect = QPushButton(_("Connect"))
        self._button_connect.clicked.connect(self._start_server)
        bbox.addButton(self._button_connect, QDialogButtonBox.ActionRole)

        self._button_next = QPushButton(_("Next"))
        self._button_next.clicked.connect(self._on_button_next_clicked)
        bbox.addButton(self._button_next, QDialogButtonBox.ActionRole)

        self._button_back = QPushButton(_("Back"))
        self._button_back.clicked.connect(self._on_back_button_clicked)
        bbox.addButton(self._button_back, QDialogButtonBox.ResetRole)

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
            self._button_cancel.setText("Cancel")

            if ENV_MANAGER:
                if page.get_current_tab() == "SSH":
                    if page.is_ssh_info_widget_shown():
                        self._button_connect.setHidden(True)
                        self._button_next.setHidden(False)
                        self._button_back.setHidden(True)
                        self._button_save_connection.setEnabled(False)
                    elif page.is_env_creation_widget_shown():
                        self._set_buttons_for_env_creation_method()
                    else:
                        self._set_buttons_for_env_packages_list()
                else:
                    self._button_connect.setHidden(False)
                    self._button_next.setHidden(True)
                    self._button_back.setHidden(True)
                    self._button_save_connection.setEnabled(True)
            else:
                self._button_connect.setHidden(False)
                self._button_next.setHidden(True)
                self._button_back.setHidden(True)
        else:
            if page.is_modified:
                self._button_save_connection.setEnabled(True)
                self._button_cancel.setText("Cancel")
            else:
                self._button_save_connection.setEnabled(False)
                self._button_cancel.setText("Close")

            self._button_clear_settings.setHidden(True)
            self._button_remove_connection.setHidden(False)
            self._button_stop.setHidden(False)
            self._button_connect.setHidden(False)
            self._button_next.setHidden(True)
            self._button_back.setHidden(True)

            if page.status in [
                ConnectionStatus.Inactive,
                ConnectionStatus.Error,
            ]:
                self._button_connect.setHidden(False)
            else:
                self._button_connect.setHidden(True)

        # TODO: Check if it's possible to stop a connection while it's
        # connecting
        if page.status == ConnectionStatus.Active:
            self._button_stop.setHidden(False)
            self._button_remove_connection.setEnabled(False)
        else:
            self._button_stop.setHidden(True)
            self._button_remove_connection.setEnabled(True)

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
                self.sig_server_renamed.emit(page.host_id)
                page.new_name = None

            # Mark page as not modified and disable save button
            page.set_modified(False)
            self._button_save_connection.setEnabled(False)

            # Update connection info if necessary
            page.update_connection_info()
            self.sig_server_updated.emit(page.host_id)

        # Inform container that a change in connections took place
        self.sig_connections_changed.emit()

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
        if ENV_MANAGER and page.NEW_CONNECTION:
            if (
                self._new_connection_page.is_env_creation_widget_shown()
                and not self._new_connection_page.validate_env_creation()
            ):
                return
            elif (
                self._new_connection_page.is_env_packages_widget_shown()
                and not self._new_connection_page.get_env_packages_list()
            ):
                return
        elif not page.validate_page():
            return

        # This uses the current host_id in case users want to start a
        # connection directly from the new connection page (
        # _save_connection_info generates a new id fo that page at the end).
        host_id = page.host_id

        if page.NEW_CONNECTION or page.is_modified:
            # Save connection info if necessary
            self._save_connection_info()

        if ENV_MANAGER and page.NEW_CONNECTION:
            if page.selected_env_creation_method() == CreateEnvMethods.NewEnv:
                env_name, python_version = page.get_create_env_info()
                packages_list = page.get_env_packages_list()
                self.sig_create_env_requested.emit(
                    host_id, env_name, python_version, packages_list
                )
            elif (
                page.selected_env_creation_method()
                == CreateEnvMethods.ImportEnv
            ):
                import_file_path, env_name = page.get_create_env_info()
                self.sig_import_env_requested.emit(
                    host_id, import_file_path, env_name
                )
            elif page.selected_env_creation_method() == CreateEnvMethods.NoEnv:
                self.sig_start_server_requested.emit(host_id)

            # Show again info widget in case users want to enter another
            # connection with similar settings.
            page.show_ssh_info_widget()
        else:
            self.sig_start_server_requested.emit(host_id)

    def _stop_server(self):
        """Stop the server corresponding to a given page."""
        page = self.get_page()

        # The stop button is not visible in the new connection page
        if not page.NEW_CONNECTION:
            self._button_stop.setHidden(True)
            self.sig_stop_server_requested.emit(page.host_id)

    def _add_connection_page(self, host_id: str, new: bool):
        """Add a new connection page to the dialog."""
        page = ConnectionPage(self, host_id=host_id)

        # This is necessary to make button_save_connection enabled when there
        # are config changes in the page
        page.apply_button_enabled.connect(
            self._update_buttons_state_on_info_change
        )

        if new:
            page.save_server_id()

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

    def _update_buttons_state_on_info_change(self, state: bool):
        """Update the state of buttons when connection info changes."""
        self._button_save_connection.setEnabled(state)
        self._button_cancel.setText("Cancel")

    def _update_connection_buttons_state(self, info: ConnectionInfo):
        """Update the state of the Connect/Stop buttons."""
        page = self.get_page()
        if page.host_id == info["id"]:
            if info["status"] in [
                ConnectionStatus.Inactive,
                ConnectionStatus.Error,
            ]:
                self._button_connect.setHidden(False)
            else:
                self._button_connect.setHidden(True)

            # TODO: Check if it's possible to stop a connection while it's
            # connecting
            if info["status"] == ConnectionStatus.Active:
                self._button_stop.setHidden(False)
            else:
                self._button_stop.setHidden(True)

            if info["status"] in [
                ConnectionStatus.Active,
                ConnectionStatus.Connecting,
                ConnectionStatus.Stopping,
            ]:
                self._button_remove_connection.setEnabled(False)
            else:
                self._button_remove_connection.setEnabled(True)

    def _set_buttons_for_env_creation_method(
        self, id_: CreateEnvMethods | None = None
    ):
        if id_ is None:
            id_ = self._new_connection_page.selected_env_creation_method()

        # When creating a new env, users need to provide a list of packages for
        # it, so the connection can't be established yet
        if id_ == CreateEnvMethods.NewEnv:
            self._button_connect.setHidden(True)
            self._button_next.setHidden(False)
        else:
            self._button_connect.setHidden(False)
            self._button_next.setHidden(True)

        # Connection info can be saved if users decide to create no env
        if id_ == CreateEnvMethods.NoEnv:
            self._button_save_connection.setEnabled(True)
        else:
            self._button_save_connection.setEnabled(False)

        # The back button will always be visible in this case.
        self._button_back.setHidden(False)

    def _set_buttons_for_env_packages_list(self):
        # We can create a connection at this point
        self._button_connect.setHidden(False)

        # There are no additional subpages to go with Next
        self._button_next.setHidden(True)

        # We can't save the connection info if users are selecting packages for
        # their remote env.
        self._button_save_connection.setEnabled(False)

        # The back button will always be visible in this case.
        self._button_back.setHidden(False)

    def _on_button_next_clicked(self):
        page = self._new_connection_page

        if page.is_ssh_info_widget_shown():
            # Validate info
            if not page.validate_page():
                return

            page.show_env_creation_widget()
            self._set_buttons_for_env_creation_method()
        else:
            # Validate env creation info
            if not page.validate_env_creation():
                return

            page.setup_env_packages_widget()
            page.show_env_packages_widget()
            self._set_buttons_for_env_packages_list()

    def _on_back_button_clicked(self):
        page = self._new_connection_page

        if page.is_env_packages_widget_shown():
            page.show_env_creation_widget()
            self._set_buttons_for_env_creation_method()
        else:
            page.show_ssh_info_widget()
            self._button_back.setHidden(True)
            self._button_connect.setHidden(True)
            self._button_next.setHidden(False)

        self._button_save_connection.setEnabled(False)

    def _on_new_connection_page_tab_changed(self, index):
        page = self._new_connection_page
        if page.get_current_tab(index) == "SSH":
            if page.is_ssh_info_widget_shown():
                self._button_connect.setHidden(True)
                self._button_next.setHidden(False)
                self._button_back.setHidden(True)
                self._button_save_connection.setEnabled(False)
            elif page.is_env_creation_widget_shown():
                self._set_buttons_for_env_creation_method()
            else:
                self._set_buttons_for_env_packages_list()
        else:
            self._button_connect.setHidden(False)
            self._button_next.setHidden(True)
            self._button_back.setHidden(True)
            self._button_save_connection.setEnabled(True)


def test():
    from spyder.utils.qthelpers import qapplication
    from spyder.utils.stylesheet import APP_STYLESHEET

    app = qapplication()  # noqa
    app.setStyleSheet(str(APP_STYLESHEET))

    dialog = ConnectionDialog()
    dialog.exec_()


if __name__ == "__main__":
    test()
