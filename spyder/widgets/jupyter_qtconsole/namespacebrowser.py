# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Widgets that handle communications between QtConsole and the Variable
Explorer
"""

from __future__ import absolute_import

import ast
import uuid

from qtpy.QtCore import QEventLoop, Signal

from ipykernel.pickleutil import CannedObject
from ipykernel.serialize import deserialize_object
from qtconsole.rich_jupyter_widget import RichJupyterWidget

from spyder.py3compat import to_text_string


class NamepaceBrowserWidget(RichJupyterWidget):
    """
    Widget with the necessary attributes and methods to handle communications
    between QtConsole and the Variable Explorer
    """
    sig_namespace_view = Signal(object)
    sig_var_properties = Signal(object)
    sig_get_value = Signal()
    sig_error_message = Signal()

    def __init__(self, *args, **kw):
        super(NamepaceBrowserWidget, self).__init__(*args, **kw)

        # Reference to the nsb widget connected to this client
        self.namespacebrowser = None

        # To save the replies of kernel method executions (except
        # getting values of variables)
        self._kernel_methods = {}

        # To save values and messages returned by the kernel
        self.kernel_value = None
        self.kernel_message = None
        self._kernel_is_starting = True

    # --- Public API --------------------------------------------------
    def set_namespacebrowser(self, namespacebrowser):
        """Set namespace browser widget"""
        self.namespacebrowser = namespacebrowser
        self.configure_namespacebrowser()

    def configure_namespacebrowser(self):
        """Configure associated namespace browser widget"""
        # Tell it that we are connected to client
        self.namespacebrowser.is_ipyclient = True

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

    def silent_exec_method(self, code):
        """Silently execute a kernel method and save its reply

        The methods passed here **don't** involve getting the value
        of a variable but instead replies that can be handled by
        ast.literal_eval.

        To get a value see `get_value`

        Parameters
        ----------
        code : string
            Code that contains the kernel method as part of its
            string

        See Also
        --------
        handle_exec_method : Method that deals with the reply

        Note
        ----
        This is based on the _silent_exec_callback method of
        RichJupyterWidget. Therefore this is licensed BSD
        """
        # Generate uuid, which would be used as an indication of whether or
        # not the unique request originated from here
        local_uuid = to_text_string(uuid.uuid1())
        code = to_text_string(code)
        msg_id = self.kernel_client.execute('', silent=True,
                                            user_expressions={ local_uuid:code })
        self._kernel_methods[local_uuid] = code
        self._request_info['execute'][msg_id] = self._ExecutionRequest(msg_id,
                                                          'silent_exec_method')

    def handle_exec_method(self, msg):
        """
        Handle data returned by silent executions of kernel methods

        This is based on the _handle_exec_callback of RichJupyterWidget.
        Therefore this is licensed BSD.
        """
        user_exp = msg['content'].get('user_expressions')
        if not user_exp:
            return
        for expression in user_exp:
            if expression in self._kernel_methods:
                # Process kernel reply
                method = self._kernel_methods[expression]
                reply = user_exp[expression]
                data = reply.get('data')
                if 'get_namespace_view' in method:
                    view = ast.literal_eval(data['text/plain'])
                    self.sig_namespace_view.emit(view)
                elif 'get_var_properties' in method:
                    properties = ast.literal_eval(data['text/plain'])
                    self.sig_var_properties.emit(properties)
                elif 'load_data' in method or 'save_namespace' in method:
                    self.kernel_message = ast.literal_eval(data['text/plain'])
                    self.sig_error_message.emit()

                # Remove method after being processed
                self._kernel_methods.pop(expression)

    def get_value(self, name):
        """Ask kernel for a value"""
        # Wait until the kernel returns the value
        wait_loop = QEventLoop()
        self.sig_get_value.connect(wait_loop.quit)
        self.silent_execute("get_ipython().kernel.get_value('%s')" % name)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_get_value.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_value

    def set_value(self, name, value):
        """Set value for a variable"""
        value = to_text_string(value)
        self.silent_execute("get_ipython().kernel.set_value('%s', %s)" %
                            (name, value))

    def remove_value(self, name):
        """Remove a variable"""
        self.silent_execute("get_ipython().kernel.remove_value('%s')" % name)

    def copy_value(self, orig_name, new_name):
        """Copy a variable"""
        self.silent_execute("get_ipython().kernel.copy_value('%s', '%s')" %
                            (orig_name, new_name))

    def load_data(self, filename, ext):
        # Wait until the kernel tries to load the file
        wait_loop = QEventLoop()
        self.sig_error_message.connect(wait_loop.quit)
        self.silent_exec_method(
                "get_ipython().kernel.load_data('%s', '%s')" % (filename, ext))
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_error_message.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_message

    def save_namespace(self, filename):
        # Wait until the kernel tries to save the file
        wait_loop = QEventLoop()
        self.sig_error_message.connect(wait_loop.quit)
        self.silent_exec_method("get_ipython().kernel.save_namespace('%s')" %
                                filename)
        wait_loop.exec_()

        # Remove loop connection and loop
        self.sig_error_message.disconnect(wait_loop.quit)
        wait_loop = None

        return self.kernel_message

    # ---- Private API (defined by us) ------------------------------
    def _handle_data_message(self, msg):
        """
        Handle raw (serialized) data sent by the kernel

        We only handle data asked by Spyder, in case people use
        publish_data for other purposes.
        """
        # Deserialize data
        data = deserialize_object(msg['buffers'])[0]

        # We only handle data asked by Spyder
        value = data.get('__spy_data__', None)
        if value is not None:
            if isinstance(value, CannedObject):
                value = value.get_object()
            self.kernel_value = value
            self.sig_get_value.emit()

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
        exec_count = msg['content']['execution_count']
        if exec_count == 0 and self._kernel_is_starting:
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
            self.set_namespace_view_settings()
            self.refresh_namespacebrowser()
        else:
            super(NamepaceBrowserWidget, self)._handle_status(msg)
