# -*- coding: utf-8 -*-
"""External shell's monitor"""

import threading, socket, thread, struct, cPickle as pickle

from PyQt4.QtCore import QThread, SIGNAL

from spyderlib.config import str2type, get_conf_path
from spyderlib.utils import select_port, fix_reference_name, log_last_error
from spyderlib.utils.dochelpers import (getargtxt, getdoc, getsource, getobjdir,
                                        isdefined)
from spyderlib.widgets.dicteditor import (get_type, get_size, get_color_name,
                                          value_to_display, globalsfilter)


LOG_FILENAME = get_conf_path('monitor.log')

DEBUG = False

if DEBUG:
    import logging
    logging.basicConfig(filename=get_conf_path('monitor_debug.log'),
                        level=logging.DEBUG)

REMOTE_SETTINGS = ('filters', 'itermax', 'exclude_private', 'exclude_upper',
                   'exclude_unsupported', 'excluded_names',
                   'truncate', 'minmax', 'collvalue', 'inplace')


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
    assert all([name in REMOTE_SETTINGS for name in settings])
    data = get_remote_data(data, settings, more_excluded_names)
    remote = {}
    for key, value in data.iteritems():
        view = value_to_display(value, truncate=settings['truncate'],
                                minmax=settings['minmax'],
                                collvalue=settings['collvalue'])
        remote[key] = {'type':  get_type(value),
                       'size':  get_size(value),
                       'color': get_color_name(value),
                       'view':  view}
    return remote
    

SZ = struct.calcsize("l")
    
def write_packet(sock, data, already_pickled=False):
    """Write *data* to socket *sock*"""
    if already_pickled:
        sent_data = data
    else:
        sent_data = pickle.dumps(data, pickle.HIGHEST_PROTOCOL)
    sock.send(struct.pack("l", len(sent_data)) + sent_data)

def read_packet(sock, timeout=None):
    """
    Read data from socket *sock*
    Returns None if something went wrong
    """
    sock.settimeout(timeout)
    dlen, data = None, None
    try:
        datalen = sock.recv(SZ)
        dlen, = struct.unpack("l", datalen)
        data = ''
        while len(data) < dlen:
            data += sock.recv(dlen)
    except socket.timeout:
        raise
    except socket.error:
        data = None
    finally:
        sock.settimeout(None)
    if data is not None:
        try:
            return pickle.loads(data)
        except (EOFError, pickle.UnpicklingError):
            return

# old com implementation: (see solution (1) in Issue 434)
def communicate(sock, command, settings=[]):
## new com implementation: (see solution (2) in Issue 434)
#def communicate(sock, command, settings=[], timeout=None):
    """Communicate with monitor"""
    write_packet(sock, command)
    for option in settings:
        write_packet(sock, option)
    # old com implementation: (see solution (1) in Issue 434)
    return read_packet(sock)
#    # new com implementation: (see solution (2) in Issue 434)
#    if timeout == 0.:
#        # non blocking socket is not really supported:
#        # setting timeout to 0. here is equivalent (in current monitor's 
#        # implementation) to say 'I don't need to receive anything in return'
#        return
#    while True:
#        output = read_packet(sock, timeout=timeout)
#        if output is None:
#            return
#        output_command, output_data = output
#        if command == output_command:
#            return output_data
#        elif DEBUG:
#            logging.debug("###### communicate/warning /Begin ######")
#            logging.debug("was expecting '%s', received '%s'" \
#                          % (command, output_command))
#            logging.debug("###### communicate/warning /End   ######")

class PacketNotReceived(object):
    pass

PACKET_NOT_RECEIVED = PacketNotReceived()


def monitor_save_globals(sock, settings, filename):
    """Save globals() to file"""
    return communicate(sock, '__save_globals__(globals())',
                       settings=[settings, filename])

def monitor_load_globals(sock, filename):
    """Load globals() from file"""
    return communicate(sock, '__load_globals__(globals())',
                       settings=[filename])

def monitor_get_global(sock, name):
    """Get global variable *name* value"""
    return communicate(sock, '__get_global__(globals(), "%s")' % name)

def monitor_set_global(sock, name, value):
    """Set global variable *name* value to *value*"""
    return communicate(sock, '__set_global__(globals(), "%s")' % name,
                       settings=[value])

def monitor_del_global(sock, name):
    """Del global variable *name*"""
    return communicate(sock, '__del_global__(globals(), "%s")' % name)

def monitor_copy_global(sock, orig_name, new_name):
    """Copy global variable *orig_name* to *new_name*"""
    return communicate(sock, '__copy_global__(globals(), "%s", "%s")' \
                       % (orig_name, new_name))

def monitor_is_array(sock, name):
    """Return True if object is an instance of class numpy.ndarray"""
    return communicate(sock, 'is_array(globals(), "%s")' % name)

def monitor_is_image(sock, name):
    """Return True if object is an instance of class PIL.Image.Image"""
    return communicate(sock, 'is_image(globals(), "%s")' % name)


def _getcdlistdir():
    """Return current directory list dir"""
    import os
    return os.listdir(os.getcwdu())

class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, introspection_port, notification_port,
                 shell_id, timeout, auto_refresh):
        threading.Thread.__init__(self)
        self.ipython_shell = None
        self.setDaemon(True)
        
        self.timeout = None
        self.set_timeout(timeout)
        self.auto_refresh = auto_refresh
        self.refresh_after_eval = False
        
        # Connecting to introspection server
        self.i_request = socket.socket( socket.AF_INET )
        self.i_request.connect( (host, introspection_port) )
        write_packet(self.i_request, shell_id)
        
        # Connecting to notification server
        self.n_request = socket.socket( socket.AF_INET )
        self.n_request.connect( (host, notification_port) )
        write_packet(self.n_request, shell_id)
        
        self.locals = {"refresh": self.enable_refresh_after_eval,
                       "setlocal": self.setlocal,
                       "is_array": self.is_array,
                       "is_image": self.is_image,
                       "getcomplist": self.getcomplist,
                       "getcdlistdir": _getcdlistdir,
                       "getcwd": self.getcwd,
                       "setcwd": self.setcwd,
                       "isdefined": isdefined,
                       "thread": thread,
                       "set_monitor_timeout": self.set_timeout,
                       "set_monitor_auto_refresh": self.set_auto_refresh,
                       "__get_dir__": self.get_dir,
                       "__iscallable__": self.iscallable,
                       "__get_arglist__": self.get_arglist,
                       "__get__doc____": self.get__doc__,
                       "__get_doc__": self.get_doc,
                       "__get_source__": self.get_source,
                       "__get_global__": self.getglobal,
                       "__set_global__": self.setglobal,
                       "__del_global__": self.delglobal,
                       "__copy_global__": self.copyglobal,
                       "__save_globals__": self.saveglobals,
                       "__load_globals__": self.loadglobals,
                       "_" : None}
        
    def set_timeout(self, timeout):
        """Set monitor timeout (in milliseconds!)"""
        self.timeout = float(timeout)/1000.
        
    def set_auto_refresh(self, state):
        """Enable/disable namespace browser auto refresh feature"""
        self.auto_refresh = state
        
    def enable_refresh_after_eval(self):
        self.refresh_after_eval = True
        
    #------ Notifications
    def refresh(self):
        """Refresh variable explorer in ExternalPythonShell"""
        communicate(self.n_request, dict(command="refresh"))

    def notify_pdb_step(self, fname, lineno):
        """Notify the ExternalPythonShell regarding pdb current frame"""
        communicate(self.n_request,
                    dict(command="pdb_step", data=(fname, lineno)))
        
    def notify_pdb_breakpoints(self):
        """Notify the ExternalPythonShell to save all breakpoints"""
        communicate(self.n_request, dict(command="pdb_breakpoints"))
        
    #------ Code completion / Calltips
    def _eval(self, text, glbs):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        assert isinstance(text, (str, unicode))
        try:
            return eval(text, glbs), True
        except:
            return None, False
            
    def get_dir(self, objtxt, glbs):
        """Return dir(object)"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return getobjdir(obj)
                
    def iscallable(self, objtxt, glbs):
        """Is object callable?"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return callable(obj)
    
    def get_arglist(self, objtxt, glbs):
        """Get func/method argument list"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return getargtxt(obj)
    
    def get__doc__(self, objtxt, glbs):
        """Get object __doc__"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return obj.__doc__
    
    def get_doc(self, objtxt, glbs):
        """Get object documentation"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return getdoc(obj)
    
    def get_source(self, objtxt, glbs):
        """Get object source"""
        obj, valid = self._eval(objtxt, glbs)
        if valid:
            return getsource(obj)
    
    def getcomplist(self, name):
        """Return completion list for object named *name*
        ** IPython only **"""
        if self.ipython_shell:
            return self.ipython_shell.complete(name)
                
    #------ Other
    def is_array(self, glbs, name):
        """Return True if object is an instance of class numpy.ndarray"""
        try:
            import numpy
            return isinstance(glbs[name], numpy.ndarray)
        except ImportError:
            return False

    def is_image(self, glbs, name):
        """Return True if object is an instance of class PIL.Image.Image"""
        try:
            from PIL.Image import Image
            return isinstance(glbs[name], Image)
        except ImportError:
            return False

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
        
    def update_remote_view(self, glbs):
        """
        Return remote view of globals()
        """
        settings = communicate(self.n_request,
                               dict(command="get_remote_view_settings"))
        more_excluded_names = ['In', 'Out'] if self.ipython_shell else None
        remote_view = make_remote_view(glbs, settings, more_excluded_names)
        communicate(self.n_request,
                    dict(command="remote_view", data=remote_view))
        
    def saveglobals(self, glbs):
        """Save globals() into filename"""
        from spyderlib.utils.iofuncs import iofunctions
        settings = read_packet(self.i_request)
        filename = read_packet(self.i_request)
        more_excluded_names = ['In', 'Out'] if self.ipython_shell else None
        data = get_remote_data(glbs, settings, more_excluded_names).copy()
        return iofunctions.save(data, filename)
        
    def loadglobals(self, glbs):
        """Load globals() from filename"""
        from spyderlib.utils.iofuncs import iofunctions
        filename = read_packet(self.i_request)
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
        self.refresh_after_eval = True
        
    def getglobal(self, glbs, name):
        """
        Get global reference value
        """
        return glbs[name]
        
    def setglobal(self, glbs, name):
        """
        Set global reference value
        """
        glbs[name] = read_packet(self.i_request)
        self.refresh_after_eval = True
        
    def delglobal(self, glbs, name):
        """
        Del global reference
        """
        glbs.pop(name)
        self.refresh_after_eval = True
        
    def copyglobal(self, glbs, orig_name, new_name):
        """
        Copy global reference
        """
        glbs[new_name] = glbs[orig_name]
        self.refresh_after_eval = True
        
    def run(self):
        self.ipython_shell = None
        from __main__ import __dict__ as glbs
        while True:
            output = pickle.dumps(None, pickle.HIGHEST_PROTOCOL)
            try:
                if DEBUG:
                    logging.debug("****** Introspection request /Begin ******")
                command = PACKET_NOT_RECEIVED
                try:
                    timeout = self.timeout if self.auto_refresh else None
                    command = read_packet(self.i_request, timeout=timeout)
                    if command is None:
                        continue
                    timed_out = False
                except socket.timeout:
                    timed_out = True
                if self.ipython_shell is None and '__ipythonshell__' in glbs:
                    self.ipython_shell = glbs['__ipythonshell__'].IP
                    glbs = self.ipython_shell.user_ns
                if timed_out:
                    if DEBUG:
                        logging.debug("connection timed out -> updating remote view")
                    self.update_remote_view(glbs)
                    if DEBUG:
                        logging.debug("****** Introspection request /End ******")
                    continue
                if DEBUG:
                    logging.debug("command: %r" % command)
                result = eval(command, glbs, self.locals)
                if DEBUG:
                    logging.debug(" result: %r" % result)
                self.locals["_"] = result
                # old com implementation: (see solution (1) in Issue 434)
                output = pickle.dumps(result, pickle.HIGHEST_PROTOCOL)
#                # new com implementation: (see solution (2) in Issue 434)
#                output = pickle.dumps((command, result),
#                                      pickle.HIGHEST_PROTOCOL)
            except SystemExit:
                break
            except:
                if DEBUG:
                    logging.debug("error!")
                log_last_error(LOG_FILENAME, command)
            finally:
                if DEBUG:
                    logging.debug("updating remote view")
                if self.refresh_after_eval:
                    self.update_remote_view(glbs)
                    self.refresh_after_eval = False
                if DEBUG:
                    logging.debug("sending result")
                    logging.debug("****** Introspection request /End ******")
                if command is not PACKET_NOT_RECEIVED:
                    write_packet(self.i_request, output, already_pickled=True)


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
        nt = self.notification_threads[shell_id] = NotificationThread(shell)
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
    def __init__(self, shell):
        QThread.__init__(self, shell)
        self.shell = shell
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
                elif command == 'pdb_breakpoints':
                    # We must *not* use a SIGNAL here because we need this 
                    # to be done immediately (before running pdb)
                    self.shell.save_all_breakpoints()
                elif command == 'refresh':
                    self.emit(SIGNAL('refresh_namespace_browser()'))
                elif command == 'get_remote_view_settings':
                    output = self.shell.namespacebrowser.get_settings()
                elif command == 'remote_view':
                    self.emit(SIGNAL('process_remote_view(PyQt_PyObject)'),
                              data)
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
