# -*- coding: utf-8 -*-
"""External shell's introspection and notification servers"""

from spyderlib.qt.QtCore import QThread, SIGNAL, Signal

import threading, socket

from spyderlib.utils import select_port, log_last_error
from spyderlib.utils.bsdsocket import read_packet, write_packet



from spyderlib import __version__
from spyderlib.userconfig import get_home_dir
import os.path as osp, os

_subfolder = '.spyder%s' % __version__.split('.')[0]

def get_conf_path(filename=None):
    """Return absolute path for configuration file with specified filename"""
    conf_dir = osp.join(get_home_dir(), _subfolder)
    if not osp.isdir(conf_dir):
        os.mkdir(conf_dir)
    if filename is None:
        return conf_dir
    else:
        return osp.join(conf_dir, filename)



LOG_FILENAME = get_conf_path('introspection.log')

DEBUG = False

if DEBUG:
    import logging
    logging.basicConfig(filename=get_conf_path('introspection_debug.log'),
                        level=logging.DEBUG)

SPYDER_PORT = 20128

class IntrospectionServer(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.shells = {}
        self.setDaemon(True)
        global SPYDER_PORT
        self.port = SPYDER_PORT = select_port(default_port=SPYDER_PORT)
        SPYDER_PORT += 1
        
    def register(self, shell):
        shell_id = str(id(shell))
        self.shells[shell_id] = shell
    
    def send_socket(self, shell_id, sock):
        """Send socket to the appropriate object for later communication"""
        shell = self.shells[shell_id]
        shell.set_introspection_socket(sock)
        if DEBUG:
            logging.debug('Introspection server: shell [%r] port [%r]'
                          % (shell, self.port))
        
    def run(self):
        s = socket.socket(socket.AF_INET)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind( ("127.0.0.1", self.port) )
        
        while True:
            s.listen(2)
            s2, _addr = s.accept()
            shell_id = read_packet(s2)
            self.send_socket(shell_id, s2)

class NotificationServer(IntrospectionServer):
    def __init__(self):
        IntrospectionServer.__init__(self)
        self.notification_threads = {}
        
    def register(self, shell):
        IntrospectionServer.register(self, shell)
        shell_id = str(id(shell))
        nt = self.notification_threads[shell_id] = NotificationThread()
        return nt
    
    def send_socket(self, shell_id, sock):
        """Send socket to the appropriate object for later communication"""
        nt = self.notification_threads[shell_id]
        nt.set_notify_socket(sock)
        nt.start()
        if DEBUG:
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
        if DEBUG:
            import time
            TIME_STR = "Logging time: %s" % time.ctime(time.time())
            logging.debug("="*len(TIME_STR))
            logging.debug(TIME_STR)
            logging.debug("="*len(TIME_STR))
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
    process_remote_view_signal = Signal(object)
    def __init__(self):
        QThread.__init__(self)
        self.notify_socket = None
        
    def set_notify_socket(self, notify_socket):
        self.notify_socket = notify_socket
        
    def run(self):
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
                    self.process_remote_view_signal.emit(data)
                else:
                    raise RuntimeError('Unsupported command: %r' % command)
                if DEBUG:
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
