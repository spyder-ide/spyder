# -*- coding: utf-8 -*-
# Spyder's ExternalPythonShell sitecustomize

try:
    import locale, win32console, pywintypes
    _t, _cp = locale.getdefaultlocale('LANG')
    _cp = int(_cp[2:])
    win32console.SetConsoleCP(_cp)
    win32console.SetConsoleOutputCP(_cp)
except (ImportError, ValueError, TypeError, pywintypes.error):
    # Pywin32 is not installed or Code page number in locale is not valid
    pass

# Set standard outputs encoding:
# (otherwise, for example, print u"é" will fail)
import sys, os
import os.path as osp
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

if os.name == 'nt':
    from PyQt4.QtCore import pyqtRemoveInputHook
    pyqtRemoveInputHook()

## Restoring original PYTHONPATH
#try:
#    os.environ['PYTHONPATH'] = os.environ['OLD_PYTHONPATH']
#    del os.environ['OLD_PYTHONPATH']
#except KeyError:
#    if os.environ.get('PYTHONPATH') is not None:
#        del os.environ['PYTHONPATH']
