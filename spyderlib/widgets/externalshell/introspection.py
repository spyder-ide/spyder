# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External shell's introspection and notification servers"""

from spyderlib.qt.QtCore import QThread, SIGNAL, Signal

import threading
import socket
import errno
import os

# Local imports
from spyderlib.baseconfig import get_conf_path, DEBUG
from spyderlib.utils.misc import select_port
from spyderlib.utils.debug import log_last_error
from spyderlib.utils.bsdsocket import read_packet, write_packet


LOG_FILENAME = get_conf_path('introspection.log')

DEBUG_INTROSPECTION = DEBUG >= 2

if DEBUG_INTROSPECTION:
    import logging
    logging.basicConfig(filename=get_conf_path('introspection_debug.log'),
                        level=logging.DEBUG)

SPYDER_PORT = 20128

class IntrospectionServer(threading.Thread):
    """Introspection server"""
    def __init__(self):
        threading.Thread.__init__(self)
        self.shells = {}
        self.setDaemon(True)
        global SPYDER_PORT
        self.port = SPYDER_PORT = select_port(default_port=SPYDER_PORT)
        SPYDER_PORT += 1
        
    def register(self, shell):
        """Register introspection server
        See notification server below"""
        shell_id = str(id(shell))
        self.shells[shell_id] = shell
    
    def send_socket(self, shell_id, sock):
        """Send socket to the appropriate object for later communication"""
        shell = self.shells[shell_id]
        shell.set_introspection_socket(sock)
        if DEBUG_INTROSPECTION:
            logging.debug('Introspection server: shell [%r] port [%r]'
                          % (shell, self.port))
        
    def run(self):
        """Start server"""
        sock = socket.socket(socket.AF_INET)
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        sock.bind( ("127.0.0.1", self.port) )
        
        while True:
            sock.listen(2)
            try:
                conn, _addr = sock.accept()
            except socket.error as e:
                # See Issue 1275 for details on why errno EINTR is
                # silently ignored here.
                eintr = errno.WSAEINTR if os.name == 'nt' else errno.EINTR
                if e.args[0] == eintr:
                    continue
                raise
            shell_id = read_packet(conn)
            if shell_id is not None:
                self.send_socket(shell_id, conn)

class NotificationServer(IntrospectionServer):
    """Notification server"""
    def __init__(self):
        IntrospectionServer.__init__(self)
        self.notification_threads = {}
        
    def register(self, shell):
        """Register notification server
        See pythonshell.ExternalPythonShell.create_process"""
        IntrospectionServer.register(self, shell)
        shell_id = str(id(shell))
        n_thread = self.notification_threads[shell_id] = NotificationThread()
        return n_thread
    
    def send_socket(self, shell_id, sock):
        """Send socket to the appropriate object for later communication"""
        n_thread = self.notification_threads[shell_id]
        n_thread.set_notify_socket(sock)
        n_thread.start()
        if DEBUG_INTROSPECTION:
            logging.debug('Notification server: shell [%r] port [%r]'
                          % (self.shells[shell_id], self.port))

INTROSPECTION_SERVER = None

def start_introspection_server():
    """
    Start introspection server (only one time)
    This server is dedicated to introspection features, i.e. Spyder is calling 
    it to retrieve informations on remote objects
    """
    global INTROSPECTION_SERVER
    if INTROSPECTION_SERVER is None:
        if DEBUG_INTROSPECTION:
            import time
            time_str = "Logging time: %s" % time.ctime(time.time())
            logging.debug("="*len(time_str))
            logging.debug(time_str)
            logging.debug("="*len(time_str))
        INTROSPECTION_SERVER = IntrospectionServer()
        INTROSPECTION_SERVER.start()
    return INTROSPECTION_SERVER

NOTIFICATION_SERVER = None

def start_notification_server():
    """
    Start notify server (only one time)
    This server is dedicated to notification features, i.e. remote objects 
    are notifying Spyder about anything relevant like debugging data (pdb) 
    or "this is the right moment to refresh variable explorer" (syshook)
    """
    global NOTIFICATION_SERVER
    if NOTIFICATION_SERVER is None:
        NOTIFICATION_SERVER = NotificationServer()
        NOTIFICATION_SERVER.start()
    return NOTIFICATION_SERVER


class NotificationThread(QThread):
    """Notification thread"""
    sig_process_remote_view = Signal(object)
    def __init__(self):
        QThread.__init__(self)
        self.notify_socket = None
        
    def set_notify_socket(self, notify_socket):
        """Set the notification socket"""
        self.notify_socket = notify_socket
        
    def run(self):
        """Start notification thread"""
        while True:
            if self.notify_socket is None:
                continue
            output = None
            try:
                try:
                    cdict = read_packet(self.notify_socket)
                except:
                    # This except statement is intended to handle a struct.error
                    # (but when writing 'except struct.error', it doesn't work)
                    # Note: struct.error is raised when the communication has 
                    # been interrupted and the received data is not a string 
                    # of length 8 as required by struct.unpack (see read_packet)
                    break
                if cdict is None:
                    # Another notification thread has just terminated and 
                    # then wrote 'None' in the notification socket
                    # (see the 'finally' statement below)
                    continue
                if not isinstance(cdict, dict):
                    raise TypeError("Invalid data type: %r" % cdict)
                command = cdict['command']
                data = cdict.get('data')
                if command == 'pdb_step':
                    fname, lineno = data
                    self.emit(SIGNAL('pdb(QString,int)'), fname, lineno)
                    self.emit(SIGNAL('refresh_namespace_browser()'))
                elif command == 'refresh':
                    self.emit(SIGNAL('refresh_namespace_browser()'))
                elif command == 'remote_view':
                    self.sig_process_remote_view.emit(data)
                elif command == 'ipykernel':
                    self.emit(SIGNAL('new_ipython_kernel(QString)'), data)
                elif command == 'open_file':
                    fname, lineno = data
                    self.emit(SIGNAL('open_file(QString,int)'), fname, lineno)
                else:
                    raise RuntimeError('Unsupported command: %r' % command)
                if DEBUG_INTROSPECTION:
                    logging.debug("received command: %r" % command)
            except:
                log_last_error(LOG_FILENAME, "notification thread")
            finally:
                try:
                    write_packet(self.notify_socket, output)
                except:
                    # The only reason why it should fail is that Spyder is 
                    # closing while this thread is still alive
                    break
