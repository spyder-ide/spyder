# -*- coding: utf-8 -*-

# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Update Manager widgets."""

# Standard library imports
import json
import logging
import os
import os.path as osp
import subprocess
import sys
from sysconfig import get_path

# Third-party imports
from qtpy.QtCore import Qt, QThread, QTimer, Signal
from qtpy.QtWidgets import (
    QGridLayout,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QTextEdit,
    QWidget,
)
from spyder_kernels.utils.pythonenv import is_conda_env

# Local imports
from spyder import __version__
from spyder.api.config.mixins import SpyderConfigurationAccessor
from spyder.api.fonts import SpyderFontsMixin, SpyderFontType
from spyder.api.translations import _
from spyder.config.base import is_conda_based_app, is_installed_all_users
from spyder.config.gui import is_dark_interface
from spyder.plugins.updatemanager.workers import (
    UpdateType,
    validate_download,
    WorkerUpdate,
    WorkerUpdateUpdater,
    WorkerDownloadInstaller
)
from spyder.plugins.updatemanager.utils import get_updater_info
from spyder.utils.conda import find_conda, is_anaconda_pkg
from spyder.utils.palette import SpyderPalette
from spyder.utils.programs import (
    get_temp_dir,
    is_program_installed,
    find_program
)
from spyder.widgets.helperwidgets import MessageCheckBox

# Logger setup
logger = logging.getLogger(__name__)

# Update manager process statuses
NO_STATUS = __version__
UPDATING_UPDATER = _("Updating Spyder-updater")
DOWNLOADING_INSTALLER = _("Downloading update")
DOWNLOAD_FINISHED = _("Download finished")
PENDING = _("Update available")
CHECKING = _("Checking for updates")
INSTALL_ON_CLOSE = _("Install on close")

HEADER = _("<h3>Spyder {} is available!</h3><br>")
URL_I = 'https://docs.spyder-ide.org/current/installation.html'

SKIP_CHECK_UPDATE = (
    sys.executable.startswith(('/usr/bin/', '/usr/local/bin/'))
    or (
        not is_conda_env(sys.prefix)
        and osp.exists(osp.join(get_path('stdlib'), 'EXTERNALLY-MANAGED'))
    )
    or sys.platform not in ('linux', 'darwin', 'win32')  # Supported platforms
)


class UpdateManagerWidget(QWidget, SpyderConfigurationAccessor):
    """Check for updates widget."""

    CONF_SECTION = "update_manager"

    sig_disable_actions = Signal(bool)
    """
    Signal to disable plugin actions during check for update.

    Parameters
    ----------
    disable: bool
        True to disable, False to re-enable.
    """

    sig_block_status_signals = Signal(bool)
    """
    Signal to block signals from update manager status during
    check for update.

    Parameters
    ----------
    block: bool
        True to block, False to unblock.
    """

    sig_download_progress = Signal(int)
    """
    Signal to send the download progress.

    Parameters
    ----------
    percent_progress: int
        Percent of the data downloaded until now.
    """

    sig_set_status = Signal(str, str)
    """
    Signal to set the status of update manager.

    Parameters
    ----------
    status: str
        Status string.
    latest_release: str
        Latest release version detected.
    """

    sig_exception_occurred = Signal(dict)
    """
    Pass untracked exceptions from workers to error reporter.
    """

    sig_install_on_close = Signal(bool)
    """
    Signal to request running the install process on close.

    Parameters
    ----------
    install_on_close: bool
        Whether to install on close.
    """

    sig_quit_requested = Signal()
    """
    This signal can be emitted to request the main application to quit.
    """

    def __init__(self, parent):
        super().__init__(parent)

        self.startup = None
        self.update_thread = None
        self.update_worker = None
        self.update_timer = None
        self.asset_info = None

        self.update_updater_thread = None
        self.update_updater_worker = None

        self.cancelled = False
        self.download_thread = None
        self.download_worker = None
        self.progress_dialog = None
        self.installer_path = None

        self.restart_spyder = True

    # ---- General

    def set_status(self, status=NO_STATUS):
        """Set the update manager status."""
        version = None
        if self.asset_info is not None:
            version = self.asset_info["version"]
        self.sig_set_status.emit(status, str(version))

    def cleanup_threads(self):
        """Clean up QThreads"""
        if self.update_timer is not None:
            self.update_timer.stop()
        if self.update_thread is not None:
            self.update_thread.quit()
            self.update_thread.wait()
        if self.download_thread is not None:
            self.download_worker.cancelled = True
            self.download_thread.quit()
            self.download_thread.wait()

    def handle_exception(self, exc):
        """Cleanup if exception occurs"""
        if self.progress_dialog is not None:
            self.progress_dialog.accept()
            self.progress_dialog = None

        self.cleanup_threads()

        self.set_status(NO_STATUS)

        self.sig_exception_occurred.emit(exc)

    # ---- Check Update

    def start_check_update(self, startup=False):
        """
        Check for Spyder updates using a QThread.

        Do not check for updates if the environment is a system or a managed
        environment.

        Update actions are disabled in the menubar and statusbar while
        checking for updates.

        If startup is True, then checking for updates is delayed 1 min;
        actions are disabled during this time as well.
        """
        if SKIP_CHECK_UPDATE:
            logger.debug(
                "Skip check for updates: system or managed environment."
            )
            return

        logger.debug(f"Checking for updates. startup = {startup}.")

        # Disable check_update_action while the thread is working
        self.sig_disable_actions.emit(True)

        self.startup = startup
        self.cleanup_threads()

        self.update_thread = QThread(None)
        self.update_worker = WorkerUpdate(self.get_conf('check_stable_only'))
        self.update_worker.sig_exception_occurred.connect(
            self.handle_exception
        )
        self.update_worker.sig_ready.connect(self._process_check_update)
        self.update_worker.sig_ready.connect(self.update_thread.quit)
        self.update_worker.sig_ready.connect(
            lambda: self.sig_disable_actions.emit(False)
        )
        self.update_worker.moveToThread(self.update_thread)
        self.update_thread.started.connect(lambda: self.set_status(CHECKING))
        self.update_thread.started.connect(self.update_worker.start)

        # Delay starting this check to avoid blocking the main window
        # while loading.
        # Fixes spyder-ide/spyder#15839
        if self.startup:
            self.update_timer = QTimer(self)
            self.update_timer.setInterval(60000)
            self.update_timer.setSingleShot(True)
            self.sig_block_status_signals.emit(True)
            self.update_timer.timeout.connect(
                lambda: self.sig_block_status_signals.emit(False)
            )
            self.update_timer.timeout.connect(self.update_thread.start)
            self.update_timer.start()
        else:
            # Otherwise, start immediately
            self.update_thread.start()

    def _process_check_update(self):
        """Process the results of check update."""
        # Get results from worker
        update_available = self.update_worker.asset_info is not None
        error_msg = self.update_worker.error
        checkbox = self.update_worker.checkbox

        # Always set status, regardless of error, DEV, or startup
        self.set_status(PENDING if update_available else NO_STATUS)

        # self.startup = True is used on startup, so only positive feedback is
        # given. self.startup = False is used after startup when using the menu
        # action, and gives feeback if updates are or are not found.
        if (
            self.startup and           # startup and...
            (error_msg is not None     # there is an error
             or not update_available)  # or no updates available
        ):
            # Do not alert the user to anything
            pass
        elif error_msg is not None:
            error_messagebox(self, error_msg, checkbox)
        elif update_available:
            self.start_update()
        else:
            info_messagebox(self, _("Spyder is up to date."), checkbox=True)

    # ---- Download Update

    def _set_installer_path(self):
        dirname = osp.join(
            get_temp_dir(), 'updates', str(self.asset_info["version"])
        )
        self.installer_path = osp.join(dirname, self.asset_info['filename'])

        logger.info(f"Update type: {self.asset_info['update_type']}")

    def _validate_download(self):
        update_downloaded = False
        if osp.exists(self.installer_path):
            update_downloaded = validate_download(
                self.installer_path, self.asset_info["checksum"]
            )

        logger.debug(f"Update already downloaded: {update_downloaded}")

        return update_downloaded

    def start_update(self):
        """
        Start the update process

        Request input from user whether to download the installer; upon
        affirmation, proceed with download then to confirm install.

        If the installer is already downloaded, proceed to confirm install.
        """
        self.asset_info = self.update_worker.asset_info
        self._set_installer_path()
        version = self.asset_info["version"]

        if self._validate_download():
            if self.asset_info["update_type"] == UpdateType.Major:
                # Major updates don't need Updater, start install
                self.set_status(DOWNLOAD_FINISHED)
                self._confirm_install()
            else:
                # Minor/micro updates need the Updater
                self._start_update_updater()
        elif not is_conda_based_app():
            msg = _(
                "Would you like to download and install the update "
                "using Spyder's installer?<br><br>"
                "We <a href='{}'>recommend our own installer</a> "
                "because it's more stable and makes updating easy. "
                "This will leave your existing Spyder installation "
                "untouched."
            ).format(URL_I + "#standalone-installers")

            box = confirm_messagebox(
                self, msg, _('Spyder update'), version=version, checkbox=True
            )
            if box.result() == QMessageBox.Yes:
                self._start_download()
            else:
                manual_update_messagebox(
                    self, version, self.update_worker.channel
                )
        else:
            msg = _("Would you like to download the update?")
            box = confirm_messagebox(
                self, msg, _('Spyder update'), version=version, checkbox=True
            )
            if box.result() == QMessageBox.Yes:
                if self.asset_info["update_type"] == UpdateType.Major:
                    self._start_download()
                else:
                    self._start_update_updater()

    def _start_update_updater(self):
        """Check for and install updates for Spyder-updater."""
        self.sig_disable_actions.emit(True)
        self.set_status(UPDATING_UPDATER)

        self.progress_dialog = ProgressDialog(
            self, _("Updating Spyder's updater..."),
            cancel_btn=False
        )
        # Show progress bar as busy
        self.progress_dialog.update_progress(0, 0)

        self.update_updater_thread = QThread(None)
        self.update_updater_worker = WorkerUpdateUpdater(
            self.get_conf('check_stable_only')
        )
        self.update_updater_worker.sig_exception_occurred.connect(
            self.handle_exception
        )

        self.update_updater_worker.sig_ready.connect(
            self._process_update_updater
        )
        self.update_updater_worker.sig_ready.connect(
            self.update_updater_thread.quit
        )
        self.update_updater_worker.sig_ready.connect(
            lambda: self.sig_disable_actions.emit(False)
        )
        self.update_updater_worker.moveToThread(self.update_updater_thread)
        self.update_updater_thread.started.connect(
            self.update_updater_worker.start
        )
        self.update_updater_thread.start()

    def _process_update_updater(self):
        """Process possible errors when updating the updater"""
        error = self.update_updater_worker.error
        if error is None:
            self._start_download()
            return

        self.set_status(PENDING)
        if self.progress_dialog is not None:
            self.progress_dialog.accept()
            self.progress_dialog = None

        if isinstance(error, subprocess.CalledProcessError):
            error_msg = _("Error updating Spyder-updater.")
            details = [
                "*** COMMAND ***",
                error.cmd.strip(),
                "\n*** STDOUT ***",
                error.output.strip(),
                "\n*** STDERR ***",
                error.stderr.strip(),
            ]
            detailed_error_messagebox(
                self, error_msg, details="\n".join(details)
            )

    def _start_download(self):
        """
        Start downloading the installer in a QThread
        and set downloading status.
        """
        if self._validate_download():
            # Update already downloaded, start install
            self._confirm_install()
            return

        self.cancelled = False
        if self.progress_dialog is not None:
            self.progress_dialog.accept()
            self.progress_dialog = None

        self.download_worker = WorkerDownloadInstaller(
            self.asset_info, self.installer_path
        )

        self.sig_disable_actions.emit(True)
        self.set_status(DOWNLOADING_INSTALLER)

        # Only show progress bar for installers
        if not self.installer_path.endswith('zip'):
            self.progress_dialog = ProgressDialog(
                self,
                _("Downloading Spyder {} ...").format(
                    self.asset_info["version"]
                )
            )
            self.progress_dialog.cancel.clicked.connect(self._cancel_download)

        self.download_thread = QThread(None)
        self.download_worker.sig_exception_occurred.connect(
            self.handle_exception
        )
        self.download_worker.sig_ready.connect(self._confirm_install)
        self.download_worker.sig_ready.connect(self.download_thread.quit)
        self.download_worker.sig_ready.connect(
            lambda: self.sig_disable_actions.emit(False)
        )
        self.download_worker.sig_download_progress.connect(
            self._update_download_progress
        )
        self.download_worker.moveToThread(self.download_thread)
        self.download_thread.started.connect(self.download_worker.start)
        self.download_thread.start()

    def show_progress_dialog(self):
        """Show download progress if previously hidden"""
        if self.progress_dialog is not None:
            if not self.progress_dialog.isVisible():
                self.progress_dialog.show()
            else:
                self.progress_dialog.hide()

    def _update_download_progress(self, progress, total):
        """Update download progress in dialog and status bar"""
        if self.progress_dialog is not None:
            self.progress_dialog.update_progress(progress, total)

        percent_progress = 0
        if total > 0:
            percent_progress = round((progress / total) * 100)
        self.sig_download_progress.emit(percent_progress)

    def _cancel_download(self):
        """Cancel the installation in progress."""
        self.download_worker.paused = True
        msg = _('Do you really want to cancel the download?')
        box = confirm_messagebox(
            self, msg, _('Spyder download'), critical=True
        )
        if box.result() == QMessageBox.Yes:
            self.cancelled = True
            self.cleanup_threads()
            self.set_status(PENDING)
        else:
            self.progress_dialog.show()
            self.download_worker.paused = False

    def _confirm_install(self):
        """
        Ask users if they want to proceed with the install immediately
        or on close.
        """
        if self.progress_dialog is not None:
            self.progress_dialog.accept()

        if self.cancelled:
            return

        if self.download_worker and self.download_worker.error:
            # If download error, do not proceed with install
            if self.progress_dialog is not None:
                self.progress_dialog.reject()
            self.set_status(PENDING)
            error_messagebox(self, self.download_worker.error)
            return

        if self.download_worker:
            self.set_status(DOWNLOAD_FINISHED)

        msg = _("Would you like to install it?")
        box = confirm_messagebox(
            self,
            msg,
            _('Spyder install'),
            version=self.asset_info["version"],
            on_close=True
        )
        if box.result() == QMessageBox.Yes:
            self.restart_spyder = True
            self.sig_install_on_close.emit(True)
            self.sig_quit_requested.emit()
        elif box.result() == 0:  # 0 is result of 3rd push-button
            self.restart_spyder = False
            self.sig_install_on_close.emit(True)
            self.set_status(INSTALL_ON_CLOSE)

    def start_install(self):
        """Install from downloaded installer or update through conda."""
        if self.asset_info["update_type"] == UpdateType.Major:
            self._start_major_install()
        else:
            self._start_updater()

    def _start_major_install(self):
        """
        Install major update from downloaded installer.

        Major updates are performed using the installers directly.
        macOS and Windows installers have GUI interfaces; Linux requires
        a terminal for the GUI.
        """
        if os.name == 'nt':
            cmd = ['start', '"Update Spyder"']
        elif sys.platform == 'darwin':
            cmd = ["open"]
        else:
            programs = [
                {'cmd': 'gnome-terminal', 'exe-opt': '--window --'},
                {'cmd': 'konsole', 'exe-opt': '-e'},
                {'cmd': 'xfce4-terminal', 'exe-opt': '-x'},
                {'cmd': 'xterm', 'exe-opt': '-e'}
            ]
            for program in programs:
                if is_program_installed(program['cmd']):
                    cmd = [program['cmd'], program['exe-opt']]
                    break

        cmd.append(self.installer_path)

        env = os.environ.copy()
        if sys.platform == "darwin":
            # PKG installers will not pass environment variables in the GUI.
            # To communicate whether to start Spyder, create dummy file.
            no_start_file = osp.join(
                osp.dirname(self.installer_path), "no-start-spyder"
            )
            if self.restart_spyder and osp.exists(no_start_file):
                os.remove(no_start_file)
            if not self.restart_spyder:
                open(no_start_file, 'w').close()
        else:
            # EXE and SH installers will pass environment variables
            env.update({"START_SPYDER": str(self.restart_spyder)})

        logger.debug(f"Restart Spyder after install: {self.restart_spyder}")

        logger.debug(f"""Update command: "{' '.join(cmd)}" """)

        subprocess.Popen(' '.join(cmd), shell=True, env=env)

    def _start_updater(self):
        """
        Start updater application.

        For minor/micro updates, Spyder Updater provides the GUI showing
        progress for updating the runtime environment.
        """
        if self.get_conf('high_dpi_custom_scale_factor', section='main'):
            scale_factors = self.get_conf(
                'high_dpi_custom_scale_factors',
                section='main'
            )
            scale_factor = float(scale_factors.split(";")[0])
        else:
            scale_factor = 1

        info = {
            "install_file": self.installer_path,
            "conda_exec": find_conda(),
            "env_path": sys.prefix,
            "update_type": self.asset_info["update_type"],
            "window_title": _("Spyder update"),
            "scale_factor": scale_factor,
            "initial_message": _(
                "Updating Spyder, this will take a few minutes ..."
            ),
            "success_message": _(
                "The update was succesful! Spyder will be launched shortly"
            ),
            "failure_message": _("Unfortunately the update failed"),
            "error_message": _("There was an error in the update process"),
            "details_title": _("Show details"),
            "font_family": self.get_conf(
                "app_font/family", section="appearance"
            ),
            "font_size": int(
                self.get_conf("app_font/size", section="appearance")
            ),
            "monospace_font_family": self.get_conf(
                "monospace_app_font/family", section="appearance"
            ),
            "monospace_font_size": int(
                self.get_conf("monospace_app_font/size", section="appearance")
            ),
            "interface_theme": "dark" if is_dark_interface() else "light",
            "icon_color": SpyderPalette.ICON_1,
        }

        info_file = osp.join(
            osp.dirname(self.installer_path), "update-info.json"
        )
        with open(info_file, "w") as f:
            json.dump(info, f, indent=4)

        # Launch updater
        updater_path, __ = get_updater_info()
        cmd = [updater_path, "--update-info-file", info_file]
        if self.restart_spyder:
            cmd.append("--start-spyder")

        kwargs = dict(shell=True)
        if os.name == "nt" and is_installed_all_users():
            # Elevate UAC
            kwargs.update(executable=find_program("powershell"))
            cmd = [
                "start",
                "-FilePath",
                f'"{updater_path}"',
                "-ArgumentList",
                ",".join([f"'{a}'" for a in cmd[1:]]),
                "-WindowStyle",
                "Hidden",
                "-Verb",
                "RunAs",
            ]

        subprocess.Popen(" ".join(cmd), **kwargs)


class UpdateMessageBox(QMessageBox):
    def __init__(self, icon=None, text=None, parent=None):
        super().__init__(icon=icon, text=text, parent=parent)
        self.setWindowModality(Qt.NonModal)
        self.setTextFormat(Qt.RichText)


class DetailedUpdateMessageBox(UpdateMessageBox, SpyderFontsMixin):
    def __init__(self, icon=None, text=None, parent=None, details=None):
        super().__init__(icon=icon, text=text, parent=parent)
        self.setSizeGripEnabled(True)
        self.details = None
        self.setDetailedText(details)

    def setDetailedText(self, details=None):
        """
        Override setDetailedText.

        Note: It is critical that QGridLayout.setRowStretch is called after
        QMessageBox.setDetailedText in order for the stretch behavior to work
        properly. That is the primary reason for overriding setDetailedText.
        """
        if self.details is not None:
            self.details.setText(details)
            return

        super().setDetailedText(details)
        self.details = self.findChild(QTextEdit)

        self.details.setFont(self.get_font(SpyderFontType.Monospace))
        self.details.setLineWrapMode(self.details.NoWrap)
        self.details.setMinimumSize(400, 110)
        self.details.setLineWrapMode(0)

        qgl = self.findChild(QGridLayout)
        qgl.setRowStretch(1, 0)
        qgl.setRowStretch(3, 100)  # QTextEdit should take all the stretch

    def event(self, event):
        """Override to allow resizing the dialog when details are visible."""
        if event.type() in (event.LayoutRequest, event.Resize):
            if event.type() == event.Resize:
                result = super().event(event)
            else:
                result = False

            # Allow resize only if details is available and visible.
            if self.details and self.details.isVisible():
                self.details.setMaximumSize(10000, 10000)
                self.setMaximumSize(10000, 10000)

            return result
        return super().event(event)


class UpdateMessageCheckBox(MessageCheckBox):
    def __init__(self, icon=None, text=None, parent=None):
        super().__init__(icon=icon, text=text, parent=parent)
        self.setTextFormat(Qt.RichText)
        self._parent = parent
        self.set_checkbox_text(_("Check for updates at startup"))
        self.option = 'check_updates_on_startup'
        self.accepted.connect(self.on_close)
        self.rejected.connect(self.on_close)
        if self._parent is not None:
            self.set_checked(parent.get_conf(self.option))

    def on_close(self):
        if self._parent is not None:
            self._parent.set_conf(self.option, self.is_checked())


class ProgressDialog(UpdateMessageBox):
    """Update progress installation dialog."""

    def __init__(self, parent, text, cancel_btn=True):
        super().__init__(icon=QMessageBox.NoIcon, text=text, parent=parent)
        self.setWindowTitle(_("Spyder update"))

        self._progress_bar = QProgressBar(self)
        self._progress_bar.setMinimumWidth(250)
        self._progress_bar.setFixedHeight(15)

        layout = self.layout()
        layout.addWidget(self._progress_bar, 1, 1)

        self.okay = QPushButton(_("OK"))
        self.addButton(self.okay, QMessageBox.YesRole)
        if cancel_btn:
            self.cancel = QPushButton(_("Cancel"))
            self.addButton(self.cancel, QMessageBox.NoRole)
        self.setDefaultButton(self.okay)

        self.show()

    def update_progress(self, progress, total):
        """Update installation progress bar."""
        self._progress_bar.setMaximum(total)
        self._progress_bar.setValue(progress)


def error_messagebox(parent, error_msg, checkbox=False):
    # Use a message box with a checkbox to disable updates when required, or a
    # standard one otherwise.
    box_class = UpdateMessageCheckBox if checkbox else UpdateMessageBox
    box = box_class(icon=QMessageBox.Warning, text=error_msg, parent=parent)
    box.setWindowTitle(_("Spyder update error"))
    box.show()
    return box


def detailed_error_messagebox(parent, msg, details):
    box = DetailedUpdateMessageBox(
        icon=QMessageBox.Warning, text=msg, parent=parent, details=details
    )
    box.show()
    return box


def info_messagebox(parent, message, version=None, checkbox=False):
    box_class = UpdateMessageCheckBox if checkbox else UpdateMessageBox
    message = HEADER.format(version) + message if version else message
    box = box_class(icon=QMessageBox.Information, text=message, parent=parent)
    box.setWindowTitle(_("New Spyder version"))
    box.show()
    return box


def confirm_messagebox(parent, message, title, version=None, critical=False,
                       checkbox=False, on_close=False):
    box_class = UpdateMessageCheckBox if checkbox else UpdateMessageBox
    message = HEADER.format(version) + message if version else message
    box = box_class(
        icon=QMessageBox.Critical if critical else QMessageBox.Question,
        text=message, parent=parent
    )
    box.setWindowTitle(title)
    box.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
    box.setDefaultButton(QMessageBox.Yes)
    if on_close:
        box.addButton(_("After closing"), QMessageBox.YesRole)
    box.exec()
    return box


def manual_update_messagebox(parent, latest_release, channel):
    msg = ""
    if os.name == "nt":
        if is_conda_env(sys.prefix):
            msg += _("Run the following command or commands in "
                     "the Anaconda prompt to update manually:"
                     "<br><br>")
        else:
            msg += _("Run the following command in a cmd prompt "
                     "to update manually:<br><br>")
    else:
        if is_conda_env(sys.prefix):
            msg += _("Run the following command or commands in a "
                     "terminal to update manually:<br><br>")
        else:
            msg += _("Run the following command in a terminal to "
                     "update manually:<br><br>")

    if is_conda_env(sys.prefix):
        is_pypi = channel == 'pypi'

        if is_anaconda_pkg() and not is_pypi:
            msg += "<code>conda update anaconda</code><br>"

        if is_pypi:
            dont_mix_pip_conda_video = (
                "https://youtu.be/Ul79ihg41Rs"
            )

            msg += (
                "<code>pip install --upgrade spyder</code>"
                "<br><br><br>"
            )

            msg += _(
                "<b>Important note:</b> You installed Spyder with "
                "pip in a Conda environment, which is not a good "
                "idea. See <a href=\"{}\">our video</a> for more "
                "details about it."
            ).format(dont_mix_pip_conda_video)
        else:
            if channel == 'pkgs/main':
                channel = '-c defaults'
            elif channel is not None:
                channel = f'-c {channel}'
            else:
                channel = ''

            msg += (
                f"<code>conda install {channel} "
                f"spyder={latest_release}"
                f"</code><br><br><br>"
            )

            msg += _(
                "<b>Important note:</b> Since you installed "
                "Spyder with Anaconda, please don't use pip "
                "to update it as that will break your "
                "installation."
            )
    else:
        msg += "<code>pip install --upgrade spyder</code><br>"

    msg += _(
        "<br><br>For more information, visit our "
        "<a href=\"{}\">installation guide</a>."
    ).format(URL_I)
    return info_messagebox(parent, msg)
