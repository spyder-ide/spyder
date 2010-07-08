# -*- coding: utf-8 -*-
# Spyder's ExternalPythonShell sitecustomize

import sys, os, os.path as osp

if os.name == 'nt':
    # Windows platforms
    
    # Removing PyQt4 input hook which is not working well on Windows
    from PyQt4.QtCore import pyqtRemoveInputHook
    pyqtRemoveInputHook()
    
    # Setting console encoding (otherwise Python does not recognize encoding)
    try:
        import locale, ctypes
        _t, _cp = locale.getdefaultlocale('LANG')
        try:
            _cp = int(_cp[2:])
            ctypes.windll.kernel32.SetConsoleCP(_cp)
            ctypes.windll.kernel32.SetConsoleOutputCP(_cp)
        except (ValueError, TypeError):
            # Code page number in locale is not valid
            pass
    except ImportError:
        pass
        
    # Workaround for IPython thread issues with win32 comdlg32
    try:
        import win32gui, win32api
        try:
            win32gui.GetOpenFileNameW(File=win32api.GetSystemDirectory()[:2])
        except win32gui.error:
            # This error is triggered intentionally
            pass
    except ImportError:
        # Unfortunately, pywin32 is not installed...
        pass

# Set standard outputs encoding:
# (otherwise, for example, print u"é" will fail)
encoding = None
try:
    import locale
except ImportError:
    pass
else:
    loc = locale.getdefaultlocale()
    if loc[1]:
        encoding = loc[1]

if encoding is None:
    encoding = "UTF-8"

sys.setdefaultencoding(encoding)

import spyderlib.widgets.externalshell as extsh
scpath = osp.dirname(osp.abspath(extsh.__file__))
if scpath in sys.path:
    sys.path.remove(scpath)

try:
    import sitecustomize #@UnusedImport
except ImportError:
    pass

# Communication between ExternalShell and the QProcess
from spyderlib.widgets.externalshell.monitor import Monitor
monitor = Monitor("127.0.0.1", int(os.environ['SPYDER_PORT']),
                  os.environ['SHELL_ID'])
monitor.start()

# Quite limited feature: notify only when a result is displayed in console
# (does not notify at every prompt)
def displayhook(obj):
    sys.__displayhook__(obj)
    monitor.refresh()

sys.displayhook = displayhook

## Restoring original PYTHONPATH
#try:
#    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
#    del os.environ['OLD_PYTHONPATH']
#except KeyError:
#    if os.environ.get('PYTHONPATH') is not None:
#        del os.environ['PYTHONPATH']
