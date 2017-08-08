# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widget that handle communications between the IPython Console and
the Variable Explorer
"""

from qtpy.QtCore import QEventLoop
from qtpy.QtWidgets import QMessageBox

from ipykernel.pickleutil import CannedObject
from ipykernel.serialize import deserialize_object
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.config.base import _
from spyder.py3compat import to_text_string


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
    _kernel_value = None
    _kernel_is_starting = True

    # --- Public API --------------------------------------------------
    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser widget"""
        self.namespacebrowser = namespacebrowser
        self.configure_namespacebrowser()

    def configure_namespacebrowser(self):
        """Configure associated namespace browser widget"""
        # Update namespace view
        self.sig_namespace_view.connect(lambda data:
            self.namespacebrowser.process_remote_view(data))

        # Update properties of variables
        self.sig_var_properties.connect(lambda data:
            self.namespacebrowser.set_var_properties(data))

    def refresh_namespacebrowser(self):
        """Refresh namespace browser"""
        if self.namespacebrowser:
            self.silent_exec_method(
                'get_ipython().kernel.get_namespace_view()')
            self.silent_exec_method(
                'get_ipython().kernel.get_var_properties()')

    def set_namespace_view_settings(self):
        """Set the namespace view settings"""
        settings = to_text_string(self.namespacebrowser.get_view_settings())
        code = u"get_ipython().kernel.namespace_view_settings = %s" % settings
        self.silent_execute(code)

    def get_value(self, name):
        """Ask kernel for a value"""
        code = u"get_ipython().kernel.get_value('%s')" % name
        if self._reading:
            method = self.kernel_client.input
            code = u'!' + code
        else:
            method = self.silent_execute

        # Wait until the kernel returns the value
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        method(code)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        # Handle exceptions
        if self._kernel_value is None:
            if self._kernel_reply:
                msg = self._kernel_reply[:]
                self._kernel_reply = None
                raise ValueError(msg)

        return self._kernel_value

    def set_value(self, name, value):
        """Set value for a variable"""
        value = to_text_string(value)
        code = u"get_ipython().kernel.set_value('%s', %s)" % (name, value)
        if self._reading:
            self.kernel_client.input(u'!' + code)
        else:
            self.silent_execute(code)

    def remove_value(self, name):
        """Remove a variable"""
        code = u"get_ipython().kernel.remove_value('%s')" % name
        if self._reading:
            self.kernel_client.input(u'!' + code)
        else:
            self.silent_execute(code)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        code = u"get_ipython().kernel.copy_value('%s', '%s')" % (orig_name,
                                                                 new_name)
        if self._reading:
            self.kernel_client.input(u'!' + code)
        else:
            self.silent_execute(code)

    def load_data(self, filename, ext):
        if self._reading:
            message = _("Loading this kind of data while debugging is not "
                        "supported.")
            QMessageBox.warning(self, _("Warning"), message)
            return
        # Wait until the kernel tries to load the file
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        self.silent_exec_method(
                r"get_ipython().kernel.load_data('%s', '%s')" % (filename, ext))
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        return self._kernel_reply

    def save_namespace(self, filename):
        if self._reading:
            message = _("Saving data while debugging is not supported.")
            QMessageBox.warning(self, _("Warning"), message)
            return
        # Wait until the kernel tries to save the file
        wait_loop = QEventLoop()
        self.sig_got_reply.connect(wait_loop.quit)
        self.silent_exec_method(r"get_ipython().kernel.save_namespace('%s')" %
                                filename)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_got_reply.disconnect(wait_loop.quit)
        wait_loop = None

        return self._kernel_reply

    # ---- Private API (defined by us) ------------------------------
    def _handle_data_message(self, msg):
        """
        Handle raw (serialized) data sent by the kernel

        We only handle data asked by Spyder, in case people use
        publish_data for other purposes.
        """
        # Deserialize data
        try:
            data = deserialize_object(msg['buffers'])[0]
        except Exception as msg:
            self._kernel_value = None
            self._kernel_reply = repr(msg)
            self.sig_got_reply.emit()
            return

        # Receive values asked for Spyder
        value = data.get('__spy_data__', None)
        if value is not None:
            if isinstance(value, CannedObject):
                value = value.get_object()
            self._kernel_value = value
            self.sig_got_reply.emit()
            return

        # Receive Pdb state and dispatch it
        pdb_state = data.get('__spy_pdb_state__', None)
        if pdb_state is not None and isinstance(pdb_state, dict):
            self.refresh_from_pdb(pdb_state)

    # ---- Private API (overrode by us) ----------------------------
    def _handle_error(self, msg):
        """
        Reimplemented to reset the prompt if the error comes after the reply
        """
        super()._handle_error(msg)
        self._show_interpreter_prompt()
    
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
                self.refresh_namespacebrowser()
            self._kernel_is_starting = False

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
        if state == 'starting' and not self._kernel_is_starting:
            # This handles restarts when the kernel dies
            # unexpectedly
            self._kernel_is_starting = True
        elif state == 'idle' and msg_type == 'shutdown_request':
            # This handles restarts asked by the user
            if self.namespacebrowser is not None:
                self.set_namespace_view_settings()
                self.refresh_namespacebrowser()
        else:
            super(NamepaceBrowserWidget, self)._handle_status(msg)
