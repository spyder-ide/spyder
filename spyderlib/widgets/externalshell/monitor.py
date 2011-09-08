# -*- coding: utf-8 -*-
"""External shell's monitor"""

#TODO: The "disable auto-refresh when variable explorer is hidden" feature 
#      broken since we removed the "shell" widget reference from notification 
#      thread. We must find another mechanism to avoid refreshing systematically
#      remote views for all consoles...!

import os, threading, socket, thread, struct, cPickle as pickle

# Local imports
from spyderlib.utils import fix_reference_name, log_last_error
from spyderlib.utils.dochelpers import (getargtxt, getdoc, getsource,
                                        getobjdir, isdefined)
from spyderlib.utils.bsdsocket import (communicate, read_packet, write_packet,
                                       PACKET_NOT_RECEIVED)
from spyderlib.utils.module_completion import moduleCompletion
from spyderlib.baseconfig import get_conf_path, get_supported_types

SUPPORTED_TYPES = get_supported_types()

LOG_FILENAME = get_conf_path('monitor.log')

DEBUG = False

if DEBUG:
    import logging
    logging.basicConfig(filename=get_conf_path('monitor_debug.log'),
                        level=logging.DEBUG)

REMOTE_SETTINGS = ('itermax', 'exclude_private', 'exclude_uppercase',
                   'exclude_capitalized', 'exclude_unsupported',
                   'excluded_names', 'truncate', 'minmax', 'collvalue',
                   'inplace', 'remote_editing', 'autorefresh')

def monitor_set_remote_view_settings(sock, namespacebrowser):
    """Set monitor's remote view settings from namespacebrowser instance"""
    settings = {}
    for name in REMOTE_SETTINGS:
        settings[name] = getattr(namespacebrowser, name)
    communicate(sock, '__set_remote_view_settings__()', settings=[settings])

def get_remote_data(data, settings, mode, more_excluded_names=None):
    """
    Return globals according to filter described in *settings*:
        * data: data to be filtered (dictionary)
        * settings: variable explorer settings (dictionary)
        * mode (string): 'editable' or 'picklable'
        * more_excluded_names: additional excluded names (list)
        * itermax: maximum iterations when walking in sequences
          (dict, list, tuple)
    """
    from spyderlib.widgets.dicteditorutils import globalsfilter
    assert mode in SUPPORTED_TYPES.keys()
    excluded_names = settings['excluded_names']
    if more_excluded_names is not None:
        excluded_names += more_excluded_names
    return globalsfilter(data, itermax=settings['itermax'],
                         filters=tuple(SUPPORTED_TYPES[mode]),
                         exclude_private=settings['exclude_private'],
                         exclude_uppercase=settings['exclude_uppercase'],
                         exclude_capitalized=settings['exclude_capitalized'],
                         exclude_unsupported=settings['exclude_unsupported'],
                         excluded_names=excluded_names)

def make_remote_view(data, settings, more_excluded_names=None):
    """
    Make a remote view of dictionary *data*
    -> globals explorer
    """
    from spyderlib.widgets.dicteditorutils import (get_type, get_size,
                                              get_color_name, value_to_display)
    assert all([name in REMOTE_SETTINGS for name in settings])
    data = get_remote_data(data, settings, mode='editable',
                           more_excluded_names=more_excluded_names)
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
    

def monitor_save_globals(sock, settings, filename):
    """Save globals() to file"""
    return communicate(sock, '__save_globals__(globals())',
                       settings=[settings, filename])

def monitor_load_globals(sock, filename, ext):
    """Load globals() from file"""
    return communicate(sock, '__load_globals__(globals())',
                       settings=[filename, ext])

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

def monitor_is_none(sock, name):
    """Return True if object is None"""
    return communicate(sock, "globals()['%s'] is None" % name)

def monitor_is_array(sock, name):
    """Return True if object is an instance of class numpy.ndarray"""
    return communicate(sock, 'is_array(globals(), "%s")' % name)

def monitor_is_image(sock, name):
    """Return True if object is an instance of class PIL.Image.Image"""
    return communicate(sock, 'is_image(globals(), "%s")' % name)


def _getcdlistdir():
    """Return current directory list dir"""
    return os.listdir(os.getcwdu())

class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, introspection_port, notification_port,
                 shell_id, timeout, auto_refresh):
        threading.Thread.__init__(self)
        self.ipython_shell = None
        self.ipython_kernel = None
        self.setDaemon(True)
        
        self.pdb_obj = None
        
        self.timeout = None
        self.set_timeout(timeout)
        self.auto_refresh = auto_refresh
        self.refresh_after_eval = False
        self.remote_view_settings = None
        
        self.inputhook_flag = False
        
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
                       "getmodcomplist": self.getmodcomplist,
                       "getcdlistdir": _getcdlistdir,
                       "getcwd": self.getcwd,
                       "setcwd": self.setcwd,
                       "getsyspath": self.getsyspath,
                       "getenv": self.getenv,
                       "setenv": self.setenv,
                       "isdefined": isdefined,
                       "thread": thread,
                       "toggle_inputhook_flag": self.toggle_inputhook_flag,
                       "set_monitor_timeout": self.set_timeout,
                       "set_monitor_auto_refresh": self.set_auto_refresh,
                       "__set_remote_view_settings__":
                                                self.set_remote_view_settings,
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
                       
    def toggle_inputhook_flag(self, state):
        """Toggle the input hook flag
        
        The only purpose of this flag is to unblock the PyOS_InputHook
        callback when text is available in stdin (see sitecustomize.py)"""
        self.inputhook_flag = state
        
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
        
    def register_pdb_session(self, pdb_obj):
        self.pdb_obj = pdb_obj

    def notify_pdb_step(self, fname, lineno):
        """Notify the ExternalPythonShell regarding pdb current frame"""
        communicate(self.n_request,
                    dict(command="pdb_step", data=(fname, lineno)))
        
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
            complist = self.ipython_shell.complete(name)
            if len(complist) == 2 and isinstance(complist[1], list):
                # IPython v0.11
                return complist[1]
            else:
                # IPython v0.10
                return complist
            
    def getmodcomplist(self, name):
        """Return module completion list for object named *name*"""
        if self.ipython_shell:
            return self.ipython_shell.modcompletion(name)
        else:
            return moduleCompletion(name)
                
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
            return os.getcwdu()
    
    def setcwd(self, dirname):
        """Set current working directory"""
        if self.ipython_shell:
            self.ipython_shell.magic_cd("-q "+dirname)
        else:
            return os.chdir(dirname)
            
    def getenv(self):
        """Return os.environ"""
        return os.environ.copy()
        
    def setenv(self):
        """Set os.environ"""
        env = read_packet(self.i_request)
        os.environ = env

    def getsyspath(self):
        """Return sys.path[:]"""
        import sys
        return sys.path[:]        
        
    def setlocal(self, name, value):
        """
        Set local reference value
        Not used right now - could be useful in the future
        """
        self.locals[name] = value
        
    def set_remote_view_settings(self):
        """
        Set the namespace remote view settings
        (see the namespace browser widget)
        """
        self.remote_view_settings = read_packet(self.i_request)
        self.enable_refresh_after_eval()
        
    def update_remote_view(self, glbs):
        """
        Return remote view of globals()
        """
        settings = self.remote_view_settings
        if settings:
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
        data = get_remote_data(glbs, settings, mode='picklable',
                               more_excluded_names=more_excluded_names).copy()
        return iofunctions.save(data, filename)
        
    def loadglobals(self, glbs):
        """Load globals() from filename"""
        from spyderlib.utils.iofuncs import iofunctions
        filename = read_packet(self.i_request)
        ext = read_packet(self.i_request)
        load_func = iofunctions.load_funcs[ext]
        data, error_message = load_func(filename)
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
                except struct.error:
                    # This should mean that Spyder GUI has crashed
                    if DEBUG:
                        logging.debug("struct.error -> quitting monitor")
                    break
                if self.ipython_kernel is None and '__ipythonkernel__' in glbs:
                    self.ipython_kernel = glbs['__ipythonkernel__']
                    argv = ['--existing'] +\
                           ['--%s=%d' % (name, port) for name, port
                            in self.ipython_kernel.ports.items()]
                    opts = ' '.join(argv)
                    communicate(self.n_request,
                                dict(command="ipython_kernel", data=opts))
                if self.ipython_shell is None and '__ipythonshell__' in glbs:
                    # IPython >=v0.11
                    self.ipython_shell = glbs['__ipythonshell__']
                    if not hasattr(self.ipython_shell, 'user_ns'):
                        # IPython v0.10
                        self.ipython_shell = self.ipython_shell.IP
                    self.ipython_shell.modcompletion = moduleCompletion
                    glbs = self.ipython_shell.user_ns
                namespace = {}
                if self.pdb_obj is not None and self.pdb_obj.curframe is None:
                    self.pdb_obj = None
                if self.pdb_obj is not None:
                    namespace.update(self.pdb_obj.curframe.f_globals)
                    namespace.update(self.pdb_obj.curframe.f_locals)
                else:
                    namespace.update(glbs)
                if timed_out:
                    if DEBUG:
                        logging.debug("connection timed out -> updating remote view")
                    self.update_remote_view(namespace)
                    if DEBUG:
                        logging.debug("****** Introspection request /End ******")
                    continue
                if DEBUG:
                    logging.debug("command: %r" % command)
                if self.pdb_obj and self.pdb_obj.curframe:
                    local_ns = {}
                    local_ns.update(self.pdb_obj.curframe.f_locals)
                    local_ns.update(self.locals)
                    result = eval(command,
                                  self.pdb_obj.curframe.f_globals, local_ns)
                else:
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
                try:
                    if DEBUG:
                        logging.debug("updating remote view")
                    if self.refresh_after_eval:
                        self.update_remote_view(namespace)
                        self.refresh_after_eval = False
                    if DEBUG:
                        logging.debug("sending result")
                        logging.debug("****** Introspection request /End ******")
                    if command is not PACKET_NOT_RECEIVED:
                        if write_packet is None:
                            # This may happen during interpreter shutdown
                            break
                        else:
                            write_packet(self.i_request, output,
                                         already_pickled=True)
                except AttributeError, error:
                    if "'NoneType' object has no attribute" in str(error):
                        # This may happen during interpreter shutdown
                        break
                    else:
                        raise
                except TypeError, error:
                    if "'NoneType' object is not subscriptable" in str(error):
                        # This may happen during interpreter shutdown
                        break
                    else:
                        raise

        self.i_request.close()
        self.n_request.close()
