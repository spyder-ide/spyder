# -*- coding: utf-8 -*-
"""External shell's monitor"""

import threading, socket, traceback, thread, StringIO, struct
import cPickle as pickle

from PyQt4.QtCore import QThread, SIGNAL

from spyderlib.config import str2type
from spyderlib.utils import select_port, fix_reference_name
from spyderlib.utils.dochelpers import (getargtxt, getdoc, getsource, getobjdir,
                                        isdefined)
from spyderlib.utils.iofuncs import iofunctions
from spyderlib.widgets.dicteditor import (get_type, get_size, get_color,
                                          value_to_display, globalsfilter)

DEBUG = False

def get_remote_data(data, settings, more_excluded_names=None):
    """Return globals according to filter described in *settings*"""
    excluded_names = settings['excluded_names']
    if more_excluded_names is not None:
        excluded_names += more_excluded_names
    return globalsfilter(data, itermax=settings['itermax'],
                         filters=tuple(str2type(settings['filters'])),
                         exclude_private=settings['exclude_private'],
                         exclude_upper=settings['exclude_upper'],
                         exclude_unsupported=settings['exclude_unsupported'],
                         excluded_names=excluded_names)

def make_remote_view(data, settings, more_excluded_names=None):
    """
    Make a remote view of dictionary *data*
    -> globals explorer
    """
    data = get_remote_data(data, settings, more_excluded_names)
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

def monitor_save_globals(sock, settings, filename):
    """Save globals() to file"""
    write_packet(sock, '__save_globals__(globals())')
    write_packet(sock, pickle.dumps(settings, pickle.HIGHEST_PROTOCOL))
    write_packet(sock, pickle.dumps(filename, pickle.HIGHEST_PROTOCOL))
    return pickle.loads( read_packet(sock) )

def monitor_load_globals(sock, filename):
    """Load globals() from file"""
    write_packet(sock, '__load_globals__(globals())')
    write_packet(sock, pickle.dumps(filename, pickle.HIGHEST_PROTOCOL))
    return pickle.loads( read_packet(sock) )

def monitor_get_global(sock, name):
    """Get global variable *name* value"""
    write_packet(sock, '__get_global__(globals(), "%s")' % name)
    return pickle.loads( read_packet(sock) )

def monitor_set_global(sock, name, value):
    """Set global variable *name* value to *value*"""
    write_packet(sock, '__set_global__(globals(), "%s")' % name)
    write_packet(sock, pickle.dumps(value, pickle.HIGHEST_PROTOCOL))
    read_packet(sock)

def monitor_del_global(sock, name):
    """Del global variable *name*"""
    write_packet(sock, '__del_global__(globals(), "%s")' % name)
    read_packet(sock)

def monitor_copy_global(sock, orig_name, new_name):
    """Copy global variable *orig_name* to *new_name*"""
    write_packet(sock, '__copy_global__(globals(), "%s", "%s")' % (orig_name,
                                                                   new_name))
    read_packet(sock)

def monitor_is_array(sock, name):
    """Return True if object is an instance of class numpy.ndarray"""
    return communicate(sock, 'is_array(globals(), "%s")' % name,
                       pickle_try=True)


def _getcdlistdir():
    """Return current directory list dir"""
    import os
    return os.listdir(os.getcwdu())

class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, port, shell_id):
        threading.Thread.__init__(self)
        self.ipython_shell = None
        self.setDaemon(True)
        self.request = socket.socket( socket.AF_INET )
        self.request.connect( (host, port) )
        write_packet(self.request, shell_id)
        self.locals = {"setlocal": self.setlocal,
                       "getobjdir": getobjdir,
                       "is_array": self.is_array,
                       "getcomplist": self.getcomplist,
                       "getcdlistdir": _getcdlistdir,
                       "getcwd": self.getcwd,
                       "setcwd": self.setcwd,
                       "getargtxt": getargtxt,
                       "getdoc": getdoc,
                       "getsource": getsource,
                       "isdefined": isdefined,
                       "iscallable": callable,
                       "__make_remote_view__": self.make_remote_view,
                       "thread": thread,
                       "__get_global__": self.getglobal,
                       "__set_global__": self.setglobal,
                       "__del_global__": self.delglobal,
                       "__copy_global__": self.copyglobal,
                       "__save_globals__": self.saveglobals,
                       "__load_globals__": self.loadglobals,
                       "_" : None}

    def is_array(self, glbs, name):
        """Return True if object is an instance of class numpy.ndarray"""
        import numpy
        return isinstance(glbs[name], numpy.ndarray)
    
    def getcomplist(self, name):
        """Return completion list for object named *name*
        IPython only"""
        if self.ipython_shell:
            return self.ipython_shell.complete(name)

    def getcwd(self):
        """Return current working directory"""
        if self.ipython_shell:
            return self.ipython_shell.magic_pwd()
        else:
            import os
            return os.getcwdu()
    
    def setcwd(self, dirname):
        """Set current working directory"""
        if self.ipython_shell:
            self.ipython_shell.magic_cd("-q "+dirname)
        else:
            import os
            return os.chdir(dirname)
        
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
        more_excluded_names = ['In', 'Out'] if self.ipython_shell else None
        return make_remote_view(glbs, settings, more_excluded_names)
        
    def saveglobals(self, glbs):
        """Save globals() into filename"""
        settings = pickle.loads( read_packet(self.request) )
        filename = pickle.loads( read_packet(self.request) )
        more_excluded_names = ['In', 'Out'] if self.ipython_shell else None
        data = get_remote_data(glbs, settings, more_excluded_names).copy()
        return iofunctions.save(data, filename)
        
    def loadglobals(self, glbs):
        """Load globals() from filename"""
        filename = pickle.loads( read_packet(self.request) )
        data, error_message = iofunctions.load(filename)
        if error_message:
            return error_message
        for key in data.keys():
            new_key = fix_reference_name(key, blacklist=glbs.keys())
            if new_key != key:
                data[new_key] = data.pop(key)
        try:
            glbs.update(data)
        except Exception, error:
            return str(error)
        
    def getglobal(self, glbs, name):
        """
        Get global reference value
        """
        return glbs[name]
        
    def setglobal(self, glbs, name):
        """
        Set global reference value
        """
        value = pickle.loads( read_packet(self.request) )
        glbs[name] = value
        
    def delglobal(self, glbs, name):
        """
        Del global reference
        """
        glbs.pop(name)
        
    def copyglobal(self, glbs, orig_name, new_name):
        """
        Copy global reference
        """
        glbs[new_name] = glbs[orig_name]
        
    def run(self):
        self.ipython_shell = None
        from __main__ import __dict__ as glbs
        while True:
            if self.ipython_shell is None and '__ipythonshell__' in glbs:
                self.ipython_shell = glbs['__ipythonshell__'].IP
                glbs = self.ipython_shell.user_ns
            try:
                command = read_packet(self.request)
                result = eval(command, glbs, self.locals)
                self.locals["_"] = result
                output = pickle.dumps(result, pickle.HIGHEST_PROTOCOL)
                write_packet(self.request, output)
            except StandardError:
                out = StringIO.StringIO()
                traceback.print_exc(file=out)
                if DEBUG:
                    from spyderlib.config import get_conf_path
                    import time
                    errors = open(get_conf_path('monitor_errors.txt'), 'a')
                    print >>errors, "*"*5, time.ctime(time.time()), "*"*49
                    print >>errors, "command:", command
                    print >>errors, "error:"
                    traceback.print_exc(file=errors)
                    print >>errors, " "
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
                try:
                    _d = self.shell.monitor_socket.recv(1, socket.MSG_OOB)
                    self.emit(SIGNAL('refresh()'))
                except socket.error:
                    # Connection closed: socket error during recv()
                    break
            except AttributeError:
                # Socket has been closed before recv()
                break
