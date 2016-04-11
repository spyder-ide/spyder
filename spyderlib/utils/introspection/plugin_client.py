# -*- coding: utf-8 -*-
#
# Copyright © 2016 The Spyder development team
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

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
from spyderlib.config.base import debug_print, DEV, get_module_path


# Heartbeat timer in milliseconds
HEARTBEAT = 5000


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
                 extra_args=None, libs=None, cwd=None, env=None):
        super(AsyncClient, self).__init__()
        self.executable = executable or sys.executable
        self.extra_args = extra_args
        self.target = target
        self.name = name or self
        self.libs = libs
        self.cwd = cwd
        self.env = env
        self.is_initialized = False
        self.closing = False
        self.context = zmq.Context()
        QApplication.instance().aboutToQuit.connect(self.close)

        # Set up the heartbeat timer.
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._heartbeat)
        self.timer.start(HEARTBEAT)

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
        if (self.env and 'PYTHONPATH' not in self.env) or DEV:
            python_path = osp.dirname(get_module_path('spyderlib'))
            # Add the libs to the python path.
            for lib in self.libs:
                try:
                    path = osp.dirname(imp.find_module(lib)[1])
                    python_path = osp.pathsep.join([python_path, path])
                except ImportError:
                    pass
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
        try:
            self.socket.send_pyobj(request)
        except zmq.ZMQError:
            pass
        return request_id

    def close(self):
        """Cleanly close the connection to the server.
        """
        self.closing = True
        self.timer.stop()
        self.request('server_quit')
        self.process.waitForFinished(1000)
        self.context.destroy(0)

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
                continue
            resp['name'] = self.name
            self.received.emit(resp)

    def _heartbeat(self):
        """Send a heartbeat to keep the server alive.
        """
        if not self.is_initialized:
            return
        self.socket.send_pyobj(dict(func_name='server_heartbeat'))


class PluginClient(AsyncClient):

    def __init__(self, plugin_name, executable=None, env=None):
        cwd = os.path.dirname(__file__)
        super(PluginClient, self).__init__('plugin_server.py',
            executable=executable, cwd=cwd, env=env,
            extra_args=[plugin_name], libs=[plugin_name])
        self.name = plugin_name


if __name__ == '__main__':
    app = QApplication(sys.argv)
    plugin = PluginClient('jedi')
    plugin.run()

    def handle_return(value):
        print(value)
        if value['func_name'] == 'foo':
            app.quit()
        else:
            plugin.request('foo')

    def handle_errored():
        print('errored')
        sys.exit(1)

    def start():
        print('start')
        plugin.request('validate')

    plugin.errored.connect(handle_errored)
    plugin.received.connect(handle_return)
    plugin.initialized.connect(start)

    app.exec_()
