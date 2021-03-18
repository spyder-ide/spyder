# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handle communications between the IPython Console and
the Variable Explorer
"""

import logging
import time
try:
    time.monotonic  # time.monotonic new in 3.3
except AttributeError:
    time.monotonic = time.time

from pickle import PicklingError, UnpicklingError

from qtpy.QtWidgets import QMessageBox

from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.config.base import _
from spyder.py3compat import PY2, to_text_string, TimeoutError
from spyder_kernels.comms.commbase import CommError


logger = logging.getLogger(__name__)

# Max time before giving up when making a blocking call to the kernel
CALL_KERNEL_TIMEOUT = 30


class NamepaceBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle communications
    between the IPython Console and the Variable Explorer
    """

    # Reference to the nsb widget connected to this client
    namespacebrowser = None

    # To save the replies of kernel method executions (except
    # getting values of variables)
    _kernel_methods = {}

    # To save values and messages returned by the kernel
    _kernel_is_starting = True

    # --- Public API --------------------------------------------------
    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser widget"""
        self.namespacebrowser = namespacebrowser

    def refresh_namespacebrowser(self, interrupt=True):
        """Refresh namespace browser"""
        if self.kernel_client is None:
            return
        if self.namespacebrowser:
            self.call_kernel(
                interrupt=interrupt,
                callback=self.set_namespace_view
            ).get_namespace_view()
            self.call_kernel(
                interrupt=interrupt,
                callback=self.set_var_properties
            ).get_var_properties()

    def set_namespace_view(self, view):
        """Set the current namespace view."""
        if self.namespacebrowser is not None:
            self.namespacebrowser.process_remote_view(view)

    def set_var_properties(self, properties):
        """Set var properties."""
        if self.namespacebrowser is not None:
            self.namespacebrowser.set_var_properties(properties)

    def set_namespace_view_settings(self):
        """Set the namespace view settings"""
        if self.kernel_client is None:
            return
        if self.namespacebrowser:
            settings = self.namespacebrowser.get_view_settings()
            self.call_kernel(
                interrupt=True
            ).set_namespace_view_settings(settings)

    def get_value(self, name):
        """Ask kernel for a value"""
        reason_big = _("The variable is too big to be retrieved")
        reason_not_picklable = _("The variable is not picklable")
        reason_dead = _("The kernel is dead")
        reason_other = _("An error occured, see the console.")
        reason_comm = _("The comm channel is not working.")
        msg = _("%s.<br><br>"
                "Note: Please don't report this problem on Github, "
                "there's nothing to do about it.")
        try:
            return self.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT).get_value(name)
        except TimeoutError:
            raise ValueError(msg % reason_big)
        except (PicklingError, UnpicklingError, TypeError):
            raise ValueError(msg % reason_not_picklable)
        except RuntimeError:
            raise ValueError(msg % reason_dead)
        except KeyError:
            raise
        except CommError:
            raise ValueError(msg % reason_comm)
        except Exception:
            raise ValueError(msg % reason_other)

    def set_value(self, name, value):
        """Set value for a variable"""
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).set_value(name, value)

    def remove_value(self, name):
        """Remove a variable"""
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).remove_value(name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        self.call_kernel(
            interrupt=True,
            blocking=False,
            display_error=True,
            ).copy_value(orig_name, new_name)

    def load_data(self, filename, ext):
        """Load data from a file."""
        overwrite = False
        if self.namespacebrowser.editor.var_properties:
            message = _('Do you want to overwrite old '
                        'variables (if any) in the namespace '
                        'when loading the data?')
            buttons = QMessageBox.Yes | QMessageBox.No
            result = QMessageBox.question(
                self, _('Data loading'), message, buttons)
            overwrite = result == QMessageBox.Yes
        try:
            return self.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT).load_data(
                    filename, ext, overwrite=overwrite)
        except ImportError as msg:
            module = str(msg).split("'")[1]
            msg = _("Spyder is unable to open the file "
                    "you're trying to load because <tt>{module}</tt> is "
                    "not installed. Please install "
                    "this package in your working environment."
                    "<br>").format(module=module)
            return msg
        except TimeoutError:
            msg = _("Data is too big to be loaded")
            return msg
        except (UnpicklingError, RuntimeError, CommError):
            return None

    def save_namespace(self, filename):
        try:
            return self.call_kernel(
                blocking=True,
                display_error=True,
                timeout=CALL_KERNEL_TIMEOUT).save_namespace(filename)
        except TimeoutError:
            msg = _("Data is too big to be saved")
            return msg
        except (UnpicklingError, RuntimeError, CommError):
            return None

    # ---- Private API (overrode by us) ----------------------------
    def _handle_execute_reply(self, msg):
        """
        Reimplemented to handle communications between Spyder
        and the kernel
        """
        msg_id = msg['parent_header']['msg_id']
        info = self._request_info['execute'].get(msg_id)
        # unset reading flag, because if execute finished, raw_input can't
        # still be pending.
        self._reading = False

        # Refresh namespacebrowser after the kernel starts running
        exec_count = msg['content'].get('execution_count', '')
        if exec_count == 0 and self._kernel_is_starting:
            if self.namespacebrowser is not None:
                self.set_namespace_view_settings()
                self.refresh_namespacebrowser(interrupt=False)
            self._kernel_is_starting = False
            self.ipyclient.t0 = time.monotonic()

        # Handle silent execution of kernel methods
        if info and info.kind == 'silent_exec_method' and not self._hidden:
            self.handle_exec_method(msg)
            self._request_info['execute'].pop(msg_id)
        else:
            super(NamepaceBrowserWidget, self)._handle_execute_reply(msg)

    def _handle_status(self, msg):
        """
        Reimplemented to refresh the namespacebrowser after kernel
        restarts
        """
        state = msg['content'].get('execution_state', '')
        msg_type = msg['parent_header'].get('msg_type', '')
        if state == 'starting':
            # This is needed to show the time a kernel
            # has been alive in each console.
            self.ipyclient.t0 = time.monotonic()
            self.ipyclient.timer.timeout.connect(self.ipyclient.show_time)
            self.ipyclient.timer.start(1000)

            # This handles restarts when the kernel dies
            # unexpectedly
            if not self._kernel_is_starting:
                self._kernel_is_starting = True
        elif state == 'idle' and msg_type == 'shutdown_request':
            # This handles restarts asked by the user
            if self.namespacebrowser is not None:
                self.set_namespace_view_settings()
                self.refresh_namespacebrowser(interrupt=False)
            self.ipyclient.t0 = time.monotonic()
        else:
            super(NamepaceBrowserWidget, self)._handle_status(msg)
