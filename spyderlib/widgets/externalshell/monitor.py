# -*- coding: utf-8 -*-
"""External shell's monitor"""

import threading, socket, traceback, thread, StringIO, pickle, struct
from PyQt4.QtCore import QThread, SIGNAL

from spyderlib.config import str2type
from spyderlib.utils import select_port
from spyderlib.utils.dochelpers import (getargtxt, getdoc, getsource, getobjdir,
                                        isdefined)
from spyderlib.widgets.dicteditor import (get_type, get_size, get_color,
                                          value_to_display, globalsfilter)


def make_remote_view(data, settings):
    """
    Make a remote view of dictionary *data*
    -> globals explorer
    """
    data = globalsfilter(data, itermax=settings['itermax'],
                         filters=tuple(str2type(settings['filters'])),
                         exclude_private=settings['exclude_private'],
                         exclude_upper=settings['exclude_upper'],
                         exclude_unsupported=settings['exclude_unsupported'],
                         excluded_names=settings['excluded_names'])
    remote = {}
    for key, value in data.iteritems():
        view = value_to_display(value, truncate=settings['truncate'],
                                minmax=settings['minmax'],
                                collvalue=settings['collvalue'])
        remote[key] = {'type': get_type(value),
                       'size': get_size(value),
                       'color': get_color(value),
                       'view': view}
    return remote
    

SZ = struct.calcsize("l")

def write_packet(sock, data):
    """Write *data* to socket *sock*"""
    sock.send(struct.pack("l", len(data)) + data)

def read_packet(sock):
    """Read data from socket *sock*"""
    datalen = sock.recv(SZ)
    dlen, = struct.unpack("l", datalen)
    data = ''
    while len(data) < dlen:
        data += sock.recv(dlen)
    return data

def communicate(sock, input, pickle_try=False):
    """Communicate with monitor"""
    write_packet(sock, input)
    output = read_packet(sock)
    if pickle_try:
        try:
            return pickle.loads(output)
        except EOFError:
            pass
    else:
        return output

def monitor_get_remote_view(sock, settings):
    """Get globals() remote view"""
    write_packet(sock, "__make_remote_view__(globals())")
    write_packet(sock, pickle.dumps(settings, pickle.HIGHEST_PROTOCOL))
    return pickle.loads( read_packet(sock) )

def monitor_get_global(sock, name):
    """Get global variable *name* value"""
    return communicate(sock, name, pickle_try=True)

def monitor_set_global(sock, name, value):
    """Set global variable *name* value to *value*"""
    write_packet(sock, '__set_global__()')
    write_packet(sock, name)
    write_packet(sock, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
    read_packet(sock)

def monitor_del_global(sock, name):
    """Del global variable *name*"""
    write_packet(sock, '__del_global__()')
    write_packet(sock, name)
    read_packet(sock)

def monitor_copy_global(sock, orig_name, new_name):
    """Copy global variable *orig_name* to *new_name*"""
    write_packet(sock, '__copy_global__()')
    write_packet(sock, orig_name)
    write_packet(sock, new_name)
    read_packet(sock)


def getcdlistdir():
    """Return current directory list dir"""
    import os
    return os.listdir(os.getcwdu())


class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, port, shell_id):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.request = socket.socket( socket.AF_INET )
        self.request.connect( (host, port) )
        write_packet(self.request, shell_id)
        from __main__ import __dict__ as glbs
        self.locals = {"setlocal": self.setlocal,
                       "getobjdir": getobjdir,
                       "getcdlistdir": getcdlistdir,
                       "getargtxt": getargtxt,
                       "getdoc": getdoc,
                       "getsource": getsource,
                       "isdefined": lambda objtxt, force_import: \
                                    isdefined(objtxt, force_import, glbs),
                       "__make_remote_view__": self.make_remote_view,
                       "thread": thread,
                       "__set_global__": self.setglobal,
                       "__del_global__": self.delglobal,
                       "__copy_global__": self.copyglobal,
                       "_" : None}
        
    def setlocal(self, name, value):
        """
        Set local reference value
        Not used right now - could be useful in the future
        """
        self.locals[name] = value
        
    def refresh(self):
        """
        Refresh Globals explorer in ExternalPythonShell
        """
        self.request.send("x", socket.MSG_OOB)
        
    def make_remote_view(self, glbs):
        """
        Return remote view of globals()
        """
        settings = pickle.loads( read_packet(self.request) )
        return make_remote_view(glbs, settings)
        
    def setglobal(self):
        """
        Set global reference value
        """
        from __main__ import __dict__ as glbs
        name = read_packet(self.request)
        value = pickle.loads( read_packet(self.request) )
        glbs[name] = value
        
    def delglobal(self):
        """
        Del global reference
        """
        from __main__ import __dict__ as glbs
        name = read_packet(self.request)
        glbs.pop(name)
        
    def copyglobal(self):
        """
        Copy global reference
        """
        from __main__ import __dict__ as glbs
        orig_name = read_packet(self.request)
        new_name = read_packet(self.request)
        glbs[new_name] = glbs[orig_name]
        
    def run(self):
        from __main__ import __dict__ as glbs
        while True:
            try:
                command = read_packet(self.request)
                result = eval(command, glbs, self.locals)
                self.locals["_"] = result
                output = pickle.dumps(result, pickle.HIGHEST_PROTOCOL)
                write_packet(self.request, output)
            except StandardError:
                out = StringIO.StringIO()
                traceback.print_exc(file=out)
                data = out.getvalue()
                write_packet(self.request, data)


SPYDER_PORT = 20128

class Server(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.shells = {}
        global SPYDER_PORT
        SPYDER_PORT = select_port(default_port=SPYDER_PORT)
        
    def register(self, shell_id, shell):
        nt = NotificationThread(shell)
        self.shells[shell_id] = nt
        return nt
        
    def run(self):
        s = socket.socket(socket.AF_INET)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind( ("127.0.0.1", SPYDER_PORT) )
        
        while True:
            s.listen(2)
            s2, _addr = s.accept()
            shell_id = read_packet(s2)
            self.shells[shell_id].shell.monitor_socket = s2
            self.shells[shell_id].start()

SERVER = None

def start_server():
    """Start server only one time"""
    global SERVER
    if SERVER is None:
        SERVER = Server()
        SERVER.start()
    return SERVER, SPYDER_PORT


class NotificationThread(QThread):
    def __init__(self, shell):
        QThread.__init__(self, shell)
        self.shell = shell
        
    def run(self):
        while True:
            try:
                _d = self.shell.monitor_socket.recv(1, socket.MSG_OOB)
                self.emit(SIGNAL('refresh()'))
            except socket.error:
                # Connection closed
                break
