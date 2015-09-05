# -*- coding: utf-8 -*-
"""
Inputhook management for GUI event loop integration

Copyright (C) The IPython Development Team
Distributed under the terms of the modified BSD license
"""

# Stdlib imports
import ctypes
import os
import sys

# Qt imports
if os.environ["QT_API"] == 'pyqt':
    from PyQt4 import QtCore, QtGui
elif os.environ["QT_API"] == 'pyside':
    from PySide import QtCore, QtGui   # analysis:ignore

#-----------------------------------------------------------------------------
# Utilities
#-----------------------------------------------------------------------------
def _stdin_ready_posix():
    """Return True if there's something to read on stdin (posix version)."""
    infds, outfds, erfds = select.select([sys.stdin],[],[],0)
    return bool(infds)

def _stdin_ready_nt():
    """Return True if there's something to read on stdin (nt version)."""
    return msvcrt.kbhit()

def _stdin_ready_other():
    """Return True, assuming there's something to read on stdin."""
    return True


def _ignore_CTRL_C_posix():
    """Ignore CTRL+C (SIGINT)."""
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def _allow_CTRL_C_posix():
    """Take CTRL+C into account (SIGINT)."""
    signal.signal(signal.SIGINT, signal.default_int_handler)

def _ignore_CTRL_C_other():
    """Ignore CTRL+C (not implemented)."""
    pass

def _allow_CTRL_C_other():
    """Take CTRL+C into account (not implemented)."""
    pass


if os.name == 'posix':
    import select
    import signal
    stdin_ready = _stdin_ready_posix
    ignore_CTRL_C = _ignore_CTRL_C_posix
    allow_CTRL_C = _allow_CTRL_C_posix
elif os.name == 'nt':
    import msvcrt
    stdin_ready = _stdin_ready_nt
    ignore_CTRL_C = _ignore_CTRL_C_other
    allow_CTRL_C = _allow_CTRL_C_other
else:
    stdin_ready = _stdin_ready_other
    ignore_CTRL_C = _ignore_CTRL_C_other
    allow_CTRL_C = _allow_CTRL_C_other


def clear_inputhook():
    """Set PyOS_InputHook to NULL and return the previous one"""
    pyos_inputhook_ptr = ctypes.c_void_p.in_dll(ctypes.pythonapi,
                                                "PyOS_InputHook")
    pyos_inputhook_ptr.value = ctypes.c_void_p(None).value
    allow_CTRL_C()

def get_pyos_inputhook():
    """Return the current PyOS_InputHook as a ctypes.c_void_p."""
    return ctypes.c_void_p.in_dll(ctypes.pythonapi, "PyOS_InputHook")

def set_pyft_callback(callback):
    callback = ctypes.PYFUNCTYPE(ctypes.c_int)(callback)
    return callback

def remove_pyqt_inputhook():
    if os.environ["QT_API"] == 'pyqt':
        QtCore.pyqtRemoveInputHook()

#------------------------------------------------------------------------------
# Input hooks
#------------------------------------------------------------------------------
def qt4():
    """PyOS_InputHook python hook for Qt4.

    Process pending Qt events and if there's no pending keyboard
    input, spend a short slice of time (50ms) running the Qt event
    loop.

    As a Python ctypes callback can't raise an exception, we catch
    the KeyboardInterrupt and temporarily deactivate the hook,
    which will let a *second* CTRL+C be processed normally and go
    back to a clean prompt line.
    """
    try:
        allow_CTRL_C()
        app = QtCore.QCoreApplication.instance()
        if not app:
            app = QtGui.QApplication([" "])
        app.processEvents(QtCore.QEventLoop.AllEvents, 300)
        if not stdin_ready():
            # Generally a program would run QCoreApplication::exec()
            # from main() to enter and process the Qt event loop until
            # quit() or exit() is called and the program terminates.
            #
            # For our input hook integration, we need to repeatedly
            # enter and process the Qt event loop for only a short
            # amount of time (say 50ms) to ensure that Python stays
            # responsive to other user inputs.
            #
            # A naive approach would be to repeatedly call
            # QCoreApplication::exec(), using a timer to quit after a
            # short amount of time. Unfortunately, QCoreApplication
            # emits an aboutToQuit signal before stopping, which has
            # the undesirable effect of closing all modal windows.
            #
            # To work around this problem, we instead create a
            # QEventLoop and call QEventLoop::exec(). Other than
            # setting some state variables which do not seem to be
            # used anywhere, the only thing QCoreApplication adds is
            # the aboutToQuit signal which is precisely what we are
            # trying to avoid.
            timer = QtCore.QTimer()
            event_loop = QtCore.QEventLoop()
            timer.timeout.connect(event_loop.quit)
            while not stdin_ready():
                timer.start(50)
                event_loop.exec_()
                timer.stop()
    except KeyboardInterrupt:
        print("\nKeyboardInterrupt - Press Enter for new prompt")
    except: # NO exceptions are allowed to escape from a ctypes callback
        ignore_CTRL_C()
        from traceback import print_exc
        print_exc()
        print("Got exception from inputhook, unregistering.")
        clear_inputhook()
    finally:
        allow_CTRL_C()
    return 0
