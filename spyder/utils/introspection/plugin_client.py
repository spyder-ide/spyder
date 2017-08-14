# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Local imports
import imp
import os
import os.path as osp
import sys
import uuid

# Third party imports
from qtpy.QtCore import (QObject, QProcess, QProcessEnvironment,
                         QSocketNotifier, QTimer, Signal)
from qtpy.QtWidgets import QApplication
import zmq

# Local imports
from spyder.config.base import debug_print, get_module_path


# Heartbeat timer in milliseconds
HEARTBEAT = 1000


class AsyncClient(QObject):

    """
    A class which handles a connection to a client through a QProcess.
    """

    # Emitted when the client has initialized.
    initialized = Signal()

    # Emitted when the client errors.
    errored = Signal()

    # Emitted when a request response is received.
    received = Signal(object)

    def __init__(self, target, executable=None, name=None,
                 extra_args=None, libs=None, cwd=None, env=None,
                 extra_path=None):
        super(AsyncClient, self).__init__()
        self.executable = executable or sys.executable
        self.extra_args = extra_args
        self.target = target
        self.name = name or self
        self.libs = libs
        self.cwd = cwd
        self.env = env
        self.extra_path = extra_path
        self.is_initialized = False
        self.closing = False
        self.notifier = None
        self.process = None
        self.context = zmq.Context()
        QApplication.instance().aboutToQuit.connect(self.close)

        # Set up the heartbeat timer.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._heartbeat)

    def run(self):
        """Handle the connection with the server.
        """
        # Set up the zmq port.
        self.socket = self.context.socket(zmq.PAIR)
        self.port = self.socket.bind_to_random_port('tcp://*')

        # Set up the process.
        self.process = QProcess(self)
        if self.cwd:
            self.process.setWorkingDirectory(self.cwd)
        p_args = ['-u', self.target, str(self.port)]
        if self.extra_args is not None:
            p_args += self.extra_args

        # Set up environment variables.
        processEnvironment = QProcessEnvironment()
        env = self.process.systemEnvironment()
        if (self.env and 'PYTHONPATH' not in self.env) or self.env is None:
            python_path = osp.dirname(get_module_path('spyder'))
            # Add the libs to the python path.
            for lib in self.libs:
                try:
                    path = osp.dirname(imp.find_module(lib)[1])
                    python_path = osp.pathsep.join([python_path, path])
                except ImportError:
                    pass
            if self.extra_path:
                try:
                    python_path = osp.pathsep.join([python_path] +
                                                   self.extra_path)
                except Exception as e:
                    debug_print("Error when adding extra_path to plugin env")
                    debug_print(e)
            env.append("PYTHONPATH=%s" % python_path)
        if self.env:
            env.update(self.env)
        for envItem in env:
            envName, separator, envValue = envItem.partition('=')
            processEnvironment.insert(envName, envValue)
        self.process.setProcessEnvironment(processEnvironment)

        # Start the process and wait for started.
        self.process.start(self.executable, p_args)
        self.process.finished.connect(self._on_finished)
        running = self.process.waitForStarted()
        if not running:
            raise IOError('Could not start %s' % self)

        # Set up the socket notifer.
        fid = self.socket.getsockopt(zmq.FD)
        self.notifier = QSocketNotifier(fid, QSocketNotifier.Read, self)
        self.notifier.activated.connect(self._on_msg_received)

    def change_extra_path(self, extra_path):
        """Setting up a new extra path.

        It requieres the plugin to be restarted.
        """
        self.extra_path = extra_path
        if not self.is_initialized:
            return
        self.restart()

    def restart(self):
        """Restart plugin client.

        Close process, reset socket and setup the plugin process again.
        """
        debug_print("Restarting plugin client, process and connection.")
        self.close()
        self.context = zmq.Context()
        self.run()

    def request(self, func_name, *args, **kwargs):
        """Send a request to the server.

        The response will be a dictionary the 'request_id' and the
        'func_name' as well as a 'result' field with the object returned by
        the function call or or an 'error' field with a traceback.
        """
        if not self.is_initialized:
            return
        request_id = uuid.uuid4().hex
        request = dict(func_name=func_name,
                       args=args,
                       kwargs=kwargs,
                       request_id=request_id)
        self._send(request)
        return request_id

    def close(self):
        """Cleanly close the connection to the server.
        """
        self.closing = True
        self.is_initialized = False
        self.timer.stop()

        if self.notifier is not None:
            self.notifier.activated.disconnect(self._on_msg_received)
            self.notifier.setEnabled(False)
            self.notifier = None

        self.request('server_quit')

        if self.process is not None:
            self.process.waitForFinished(1000)
            self.process.close()
        self.context.destroy()
        self.socket = None

    def _on_finished(self):
        """Handle a finished signal from the process.
        """
        if self.closing:
            return
        if self.is_initialized:
            debug_print('Restarting %s' % self.name)
            debug_print(self.process.readAllStandardOutput())
            debug_print(self.process.readAllStandardError())
            self.is_initialized = False
            self.notifier.setEnabled(False)
            self.run()
        else:
            debug_print('Errored %s' % self.name)
            debug_print(self.process.readAllStandardOutput())
            debug_print(self.process.readAllStandardError())
            self.errored.emit()

    def _on_msg_received(self):
        """Handle a message trigger from the socket.
        """
        self.notifier.setEnabled(False)
        while 1:
            try:
                resp = self.socket.recv_pyobj(flags=zmq.NOBLOCK)
            except zmq.ZMQError:
                self.notifier.setEnabled(True)
                return
            if not self.is_initialized:
                self.is_initialized = True
                debug_print('Initialized %s' % self.name)
                self.initialized.emit()
                self.timer.start(HEARTBEAT)
                continue
            resp['name'] = self.name
            self.received.emit(resp)

    def _heartbeat(self):
        """Send a heartbeat to keep the server alive.
        """
        self._send(dict(func_name='server_heartbeat'))

    def _send(self, obj):
        """Send an object to the server.
        """
        try:
            self.socket.send_pyobj(obj, zmq.NOBLOCK)
        except Exception as e:
            debug_print(e)
            self.is_initialized = False
            self._on_finished()


class PluginClient(AsyncClient):

    def __init__(self, plugin_name, executable=None, env=None,
                 extra_path=None):
        cwd = os.path.dirname(__file__)
        super(PluginClient, self).__init__('plugin_server.py',
            executable=executable, cwd=cwd, env=env,
            extra_args=[plugin_name], libs=[plugin_name],
            extra_path=extra_path)
        self.name = plugin_name


if __name__ == '__main__':
    app = QApplication(sys.argv)
    plugin = PluginClient('jedi')
    plugin.run()

    def handle_return(value):
        print(value)  # spyder: test-skip
        if value['func_name'] == 'foo':
            app.quit()
        else:
            plugin.request('foo')

    def handle_errored():
        print('errored')  # spyder: test-skip
        sys.exit(1)

    def start():
        print('start')  # spyder: test-skip
        plugin.request('validate')

    plugin.errored.connect(handle_errored)
    plugin.received.connect(handle_return)
    plugin.initialized.connect(start)

    app.exec_()
