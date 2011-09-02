# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""External Python Shell's input hook manager

As of today, only PyQt4 and Tkinter are supported this way.

This workaround is intended to be used on Windows platforms only.
On Windows platforms, no real console is attached to a subprocess Python 
interpreter opened by Spyder's console. As a consequence, some basic Windows 
functions won't work: msvcrt.getch, msvcrt.kbhit, ...
This is the reason why the original PyQt's input hook does not work within 
Spyder's console. PyQt's input hook uses msvcrt's kbhit function to check if 
keyboard input is waiting to be processed: this function always returns False 
if there is no console attached to the process.

Spyder's input hook uses a non-blocking readline mechanism to check if entered 
text is available, and in the meantime it processes Qt events.

see `generic_inputhook` docstring for more details."""

import sys
import ctypes
import Queue
import threading


def readline_and_queue(fd, queue):
    """Read line from standard input (blocking process) then queue it"""
    line = fd.readline()
    queue.put(line)
    queue.task_done()


def create_queue_and_thread():
    """Create non-blocking readline queue and thread"""
    queue = Queue.Queue()
    readline_thread = threading.Thread(target=readline_and_queue,
                                       args=(sys.stdin, queue))
    readline_thread.setDaemon(True)
    return queue, readline_thread


def tk_inputhook(update_callback):
    """Tkinter input hook for Spyder's console
    
    This input hook uses a non-blocking readline mechanism to check if entered 
    text is available, and in the meantime it processes Tkinter events.
    """
    manager.initialize_tkinter()
    app = manager.tk_application
    queue, thread = create_queue_and_thread()
    thread.start()
    while True:
        try:
            _line = queue.get(timeout=.1) #analysis:ignore
            # _line contains an arbitrary text that should be ignored:
            # see spyderlib/widgets/externalshell/pythonshell.py
        except Queue.Empty:
            if app:
                app.update()
        else:
            break
    queue.join()
    return 0


def qt_inputhook():
    """Qt input hook for Spyder's console
    
    This input hook uses a non-blocking readline mechanism to check if entered 
    text is available, and in the meantime it processes Qt events.
    """
    from PyQt4 import QtCore
    app = QtCore.QCoreApplication.instance()
    if app and app.thread() is QtCore.QThread.currentThread():
        timer = QtCore.QTimer()
        QtCore.QObject.connect(timer, QtCore.SIGNAL('timeout()'),
                               app, QtCore.SLOT('quit()'))
    else:
        timer = None
    queue, thread = create_queue_and_thread()
    thread.start()
    while True:
        try:
            _line = queue.get(timeout=.1) #analysis:ignore
            # _line contains an arbitrary text that should be ignored:
            # see spyderlib/widgets/externalshell/pythonshell.py
        except Queue.Empty:
            if timer is not None:
                timer.start(50)
                QtCore.QCoreApplication.exec_()
                timer.stop()
        else:
            break
    queue.join()
    return 0


class InputHookManager(object):
    """Installs input hook callback in Python's PyOS_InputHook variable
    
    This class was a little bit inspired by the IPython v0.11 script:
    IPython/lib/inputhook.py"""
    
    def __init__(self):
        self.PYFUNC = ctypes.PYFUNCTYPE(ctypes.c_int)
        self.tk_application = None # Tk application instance
        self._callback_pyfunctype = None
        self._callback = None

    def get_pyos_inputhook(self):
        """Return the current PyOS_InputHook as a ctypes.c_void_p"""
        return ctypes.c_void_p.in_dll(ctypes.pythonapi,"PyOS_InputHook")

    def get_pyos_inputhook_as_func(self):
        """Return the current PyOS_InputHook as a ctypes.PYFUNCYPE"""
        return self.PYFUNC.in_dll(ctypes.pythonapi,"PyOS_InputHook")

    def set_inputhook(self, callback):
        """Set PyOS_InputHook to callback and return the previous one"""
        self._callback = callback
        self._callback_pyfunctype = self.PYFUNC(callback)
        pyos_inputhook_ptr = self.get_pyos_inputhook()
        original = self.get_pyos_inputhook_as_func()
        pyos_inputhook_ptr.value = \
            ctypes.cast(self._callback_pyfunctype, ctypes.c_void_p).value
        return original

    def clear_inputhook(self, app=None):
        """Set PyOS_InputHook to NULL and return the previous one"""
        pyos_inputhook_ptr = self.get_pyos_inputhook()
        original = self.get_pyos_inputhook_as_func()
        pyos_inputhook_ptr.value = ctypes.c_void_p(None).value
        self._callback_pyfunctype = None
        self._callback = None
        return original

    def install_qt_inputhook(self):
        """Install PyQt4 input hook"""
        from PyQt4 import QtCore
        QtCore.pyqtRemoveInputHook()
        self.set_inputhook(qt_inputhook)
        
    def initialize_tkinter(self):
        """Initialize Tkinter and return tk application instance"""
        if self.tk_application is None:
            import Tkinter
            try:
                app = Tkinter.Tk()
            except AttributeError:
                # Happens when Tkinter is imported in sitecustomize
                pass
            else:
                app.withdraw()
                self.tk_application = app

    def install_tk_inputhook(self, app=None):
        """Install Tkinter input hook"""
        self.set_inputhook(tk_inputhook)
        
        # Short-circuit the Tkinter event loops
        import Tkinter
        def misc_mainloop(self, n=0):
            pass
        def tkinter_mainloop(n=0):
            pass
        Tkinter.Misc.mainloop = misc_mainloop
        Tkinter.mainloop = tkinter_mainloop
        
        self.initialize_tkinter()


manager = InputHookManager()
