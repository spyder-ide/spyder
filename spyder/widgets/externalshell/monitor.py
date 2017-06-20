# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""External shell's monitor"""

#TODO: The "disable auto-refresh when variable explorer is hidden" feature
#      broken since we removed the "shell" widget reference from notification
#      thread. We must find another mechanism to avoid refreshing systematically
#      remote views for all consoles...!

import os
import socket
import struct
import threading

# Local imports
from spyder.config.base import get_conf_path, DEBUG
from spyder.py3compat import getcwd, is_text_string, pickle, _thread
from spyder.utils.misc import fix_reference_name
from spyder.utils.debug import log_last_error
from spyder.utils.dochelpers import (getargtxt, getdoc, getsource,
                                     getobjdir, isdefined)
from spyder.utils.bsdsocket import (communicate, read_packet, write_packet,
                                    PACKET_NOT_RECEIVED, PICKLE_HIGHEST_PROTOCOL)
from spyder.utils.introspection.module_completion import module_completion
from spyder.plugins.variableexplorer.utils import (get_remote_data,
                                                   make_remote_view)


LOG_FILENAME = get_conf_path('monitor.log')
DEBUG_MONITOR = DEBUG >= 2
if DEBUG_MONITOR:
    import logging
    logging.basicConfig(filename=get_conf_path('monitor_debug.log'),
                        level=logging.DEBUG)


def monitor_save_globals(sock, settings, filename):
    """Save globals() to file"""
    return communicate(sock, '__save_globals__()',
                       settings=[settings, filename])

def monitor_load_globals(sock, filename, ext):
    """Load globals() from file"""
    return communicate(sock, '__load_globals__()', settings=[filename, ext])

def monitor_get_global(sock, name):
    """Get global variable *name* value"""
    return communicate(sock, '__get_global__("%s")' % name)

def monitor_set_global(sock, name, value):
    """Set global variable *name* value to *value*"""
    return communicate(sock, '__set_global__("%s")' % name,
                       settings=[value])

def monitor_del_global(sock, name):
    """Del global variable *name*"""
    return communicate(sock, '__del_global__("%s")' % name)

def monitor_copy_global(sock, orig_name, new_name):
    """Copy global variable *orig_name* to *new_name*"""
    return communicate(sock, '__copy_global__("%s", "%s")' \
                       % (orig_name, new_name))

def _getcdlistdir():
    """Return current directory list dir"""
    return os.listdir(getcwd())


class Monitor(threading.Thread):
    """Monitor server"""
    def __init__(self, host, introspection_port, notification_port,
                 shell_id, timeout=2000, auto_refresh=False):
        threading.Thread.__init__(self)
        self.setDaemon(True)
        
        self.pdb_obj = None
        
        self.timeout = None
        self.set_timeout(timeout)
        self.auto_refresh = auto_refresh
        self.refresh_after_eval = False
        self.remote_view_settings = None
        
        self.inputhook_flag = False
        self.first_inputhook_call = True
        
        # Connecting to introspection server
        self.i_request = socket.socket( socket.AF_INET )
        self.i_request.connect( (host, introspection_port) )
        write_packet(self.i_request, shell_id)
        
        # Connecting to notification server
        self.n_request = socket.socket( socket.AF_INET )
        self.n_request.connect( (host, notification_port) )
        write_packet(self.n_request, shell_id)
        
        self._mlocals = {
                       "refresh": self.enable_refresh_after_eval,
                       "setlocal": self.setlocal,
                       "is_array": self.is_array,
                       "is_image": self.is_image,
                       "get_globals_keys": self.get_globals_keys,
                       "getmodcomplist": self.getmodcomplist,
                       "getcdlistdir": _getcdlistdir,
                       "getcwd": self.getcwd,
                       "setcwd": self.setcwd,
                       "getsyspath": self.getsyspath,
                       "getenv": self.getenv,
                       "setenv": self.setenv,
                       "isdefined": self.isdefined,
                       "thread": _thread,
                       "toggle_inputhook_flag": self.toggle_inputhook_flag,
                       "set_monitor_timeout": self.set_timeout,
                       "set_monitor_auto_refresh": self.set_auto_refresh,
                       "set_remote_view_settings":
                                                self.set_remote_view_settings,
                       "set_spyder_breakpoints": self.set_spyder_breakpoints,
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
        self._mglobals = None

    @property
    def pdb_frame(self):
        """Return current Pdb frame if there is any"""
        if self.pdb_obj is not None and self.pdb_obj.curframe is not None:
            return self.pdb_obj.curframe

    @property
    def pdb_locals(self):
        """Return current Pdb frame locals if available
        Otherwise return an empty dictionary"""
        if self.pdb_frame:
            return self.pdb_obj.curframe_locals
        else:
            return {}

    def mlocals(self):
        """Return current locals -- handles Pdb frames"""
        ns = {}
        ns.update(self._mlocals)
        ns.update(self.pdb_locals)
        return ns

    def mglobals(self):
        """Return current globals -- handles Pdb frames"""
        if self.pdb_frame is not None:
            return self.pdb_frame.f_globals
        else:
            if self._mglobals is None:
                from __main__ import __dict__ as glbs
                self._mglobals = glbs
            else:
                glbs = self._mglobals
            self._mglobals = glbs
            return glbs
    
    def get_current_namespace(self):
        """Return current namespace, i.e. globals() if not debugging,
        or a dictionary containing both locals() and globals() 
        for current frame when debugging"""
        ns = {}
        glbs = self.mglobals()

        if self.pdb_frame is None:
            ns.update(glbs)
        else:
            ns.update(glbs)
            ns.update(self.pdb_locals)

        return ns
    
    def get_reference_namespace(self, name):
        """Return namespace where reference name is defined,
        eventually returns the globals() if reference has not yet been defined"""
        glbs = self.mglobals()
        if self.pdb_frame is None:
            return glbs
        else:
            lcls = self.pdb_locals
            if name in lcls:
                return lcls
            else:
                return glbs
    
    def get_globals_keys(self):
        """Return globals() keys or globals() and locals() keys if debugging"""
        ns = self.get_current_namespace()
        return list(ns.keys())
    
    def isdefined(self, obj, force_import=False):
        """Return True if object is defined in current namespace"""
        ns = self.get_current_namespace()
        return isdefined(obj, force_import=force_import, namespace=ns)

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
        
    def refresh_from_inputhook(self):
        """Refresh variable explorer from the PyOS_InputHook.
        See sitecustomize.py"""
        # Refreshing variable explorer, except on first input hook call
        # (otherwise, on slow machines, this may freeze Spyder)
        if self.first_inputhook_call:
            self.first_inputhook_call = False
        else:
            self.refresh()
        
    def register_pdb_session(self, pdb_obj):
        self.pdb_obj = pdb_obj

    def notify_pdb_step(self, fname, lineno):
        """Notify the ExternalPythonShell regarding pdb current frame"""
        communicate(self.n_request,
                    dict(command="pdb_step", data=(fname, lineno)))

    def set_spyder_breakpoints(self):
        """Set all Spyder breakpoints in active pdb session"""
        if not self.pdb_obj:
            return
        self.pdb_obj.set_spyder_breakpoints()    
    
    def notify_open_file(self, fname, lineno=1):
        """Open file in Spyder's editor"""
        communicate(self.n_request,
                    dict(command="open_file", data=(fname, lineno)))
        
    #------ Code completion / Calltips
    def _eval(self, text):
        """
        Evaluate text and return (obj, valid)
        where *obj* is the object represented by *text*
        and *valid* is True if object evaluation did not raise any exception
        """
        assert is_text_string(text)
        ns = self.get_current_namespace()
        try:
            return eval(text, ns), True
        except:
            return None, False
            
    def get_dir(self, objtxt):
        """Return dir(object)"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getobjdir(obj)
                
    def iscallable(self, objtxt):
        """Is object callable?"""
        obj, valid = self._eval(objtxt)
        if valid:
            return callable(obj)
    
    def get_arglist(self, objtxt):
        """Get func/method argument list"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getargtxt(obj)
    
    def get__doc__(self, objtxt):
        """Get object __doc__"""
        obj, valid = self._eval(objtxt)
        if valid:
            return obj.__doc__
    
    def get_doc(self, objtxt):
        """Get object documentation dictionary"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getdoc(obj)
    
    def get_source(self, objtxt):
        """Get object source"""
        obj, valid = self._eval(objtxt)
        if valid:
            return getsource(obj)
            
    def getmodcomplist(self, name, path):
        """Return module completion list for object named *name*"""
        return module_completion(name, path)
                
    #------ Other
    def is_array(self, name):
        """Return True if object is an instance of class numpy.ndarray"""
        ns = self.get_current_namespace()
        try:
            import numpy
            return isinstance(ns[name], numpy.ndarray)
        except ImportError:
            return False

    def is_image(self, name):
        """Return True if object is an instance of class PIL.Image.Image"""
        ns = self.get_current_namespace()
        try:
            from spyder.pil_patch import Image
            return isinstance(ns[name], Image.Image)
        except ImportError:
            return False

    def getcwd(self):
        """Return current working directory"""
        return getcwd()

    def setcwd(self, dirname):
        """Set current working directory"""
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
        self._mlocals[name] = value
        
    def set_remote_view_settings(self):
        """
        Set the namespace remote view settings
        (see the namespace browser widget)
        """
        self.remote_view_settings = read_packet(self.i_request)
        self.enable_refresh_after_eval()
        
    def update_remote_view(self):
        """
        Return remote view of globals()
        """
        settings = self.remote_view_settings
        if settings:
            ns = self.get_current_namespace()
            remote_view = make_remote_view(ns, settings)
            communicate(self.n_request,
                        dict(command="remote_view", data=remote_view))
        
    def saveglobals(self):
        """Save globals() into filename"""
        ns = self.get_current_namespace()
        from spyder.utils.iofuncs import iofunctions
        settings = read_packet(self.i_request)
        filename = read_packet(self.i_request)
        data = get_remote_data(ns, settings, mode='picklable').copy()
        return iofunctions.save(data, filename)
        
    def loadglobals(self):
        """Load globals() from filename"""
        glbs = self.mglobals()
        from spyder.utils.iofuncs import iofunctions
        filename = read_packet(self.i_request)
        ext = read_packet(self.i_request)
        load_func = iofunctions.load_funcs[ext]
        data, error_message = load_func(filename)
        if error_message:
            return error_message
        for key in list(data.keys()):
            new_key = fix_reference_name(key, blacklist=list(glbs.keys()))
            if new_key != key:
                data[new_key] = data.pop(key)
        try:
            glbs.update(data)
        except Exception as error:
            return str(error)
        self.refresh_after_eval = True
        
    def getglobal(self, name):
        """
        Get global reference value
        """
        ns = self.get_current_namespace()
        return ns[name]
        
    def setglobal(self, name):
        """
        Set global reference value
        """
        ns = self.get_reference_namespace(name)
        ns[name] = read_packet(self.i_request)
        self.refresh_after_eval = True
        
    def delglobal(self, name):
        """
        Del global reference
        """
        ns = self.get_reference_namespace(name)
        ns.pop(name)
        self.refresh_after_eval = True
        
    def copyglobal(self, orig_name, new_name):
        """
        Copy global reference
        """
        ns = self.get_reference_namespace(orig_name)
        ns[new_name] = ns[orig_name]
        self.refresh_after_eval = True
        
    def run(self):
        while True:
            output = pickle.dumps(None, PICKLE_HIGHEST_PROTOCOL)
            glbs = self.mglobals()
            try:
                if DEBUG_MONITOR:
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
                    if DEBUG_MONITOR:
                        logging.debug("struct.error -> quitting monitor")
                    break
                if timed_out:
                    if DEBUG_MONITOR:
                        logging.debug("connection timed out -> updating remote view")
                    self.update_remote_view()
                    if DEBUG_MONITOR:
                        logging.debug("****** Introspection request /End ******")
                    continue
                if DEBUG_MONITOR:
                    logging.debug("command: %r" % command)
                lcls = self.mlocals()
                result = eval(command, glbs, lcls)
                if DEBUG_MONITOR:
                    logging.debug(" result: %r" % result)
                if self.pdb_obj is None:
                    lcls["_"] = result
                # old com implementation: (see solution (1) in Issue 434)
                output = pickle.dumps(result, PICKLE_HIGHEST_PROTOCOL)
#                # new com implementation: (see solution (2) in Issue 434)
#                output = pickle.dumps((command, result),
#                                      PICKLE_HIGHEST_PROTOCOL)
            except SystemExit:
                break
            except:
                if DEBUG_MONITOR:
                    logging.debug("error!")
                log_last_error(LOG_FILENAME, command)
            finally:
                try:
                    if DEBUG_MONITOR:
                        logging.debug("updating remote view")
                    if self.refresh_after_eval:
                        self.update_remote_view()
                        self.refresh_after_eval = False
                    if DEBUG_MONITOR:
                        logging.debug("sending result")
                        logging.debug("****** Introspection request /End ******")
                    if command is not PACKET_NOT_RECEIVED:
                        if write_packet is None:
                            # This may happen during interpreter shutdown
                            break
                        else:
                            write_packet(self.i_request, output,
                                         already_pickled=True)
                except AttributeError as error:
                    if "'NoneType' object has no attribute" in str(error):
                        # This may happen during interpreter shutdown
                        break
                    else:
                        raise
                except TypeError as error:
                    if "'NoneType' object is not subscriptable" in str(error):
                        # This may happen during interpreter shutdown
                        break
                    else:
                        raise

        self.i_request.close()
        self.n_request.close()
