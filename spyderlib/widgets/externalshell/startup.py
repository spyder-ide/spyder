# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Startup file used by ExternalPythonShell"""

def __run_pythonstartup_script():
    import os
    filename = os.environ.get('PYTHONSTARTUP')
    if filename and os.path.isfile(filename):
        execfile(filename)

def __run_init_commands():
    import os
    return os.environ.get('PYTHONINITCOMMANDS')

def __is_ipython():
    import os
    return os.environ.get('IPYTHON')

def __patching_matplotlib__():
    import imp
    try:
        imp.find_module('matplotlib')
    except ImportError:
        return
    from spyderlib import mpl_patch
    mpl_patch.apply()

def __create_banner():
    """Create shell banner"""
    import sys
    print 'Python %s on %s\nType "copyright", "credits" or "license" ' \
          'for more information.'  % (sys.version, sys.platform)

def __remove_sys_argv__():
    """Remove arguments from sys.argv"""
    import sys
    sys.argv = ['']

if __name__ == "__main__":
    if not __is_ipython():
        __remove_sys_argv__()
        __create_banner()
    __commands__ = __run_init_commands()
    if __commands__:
        for command in __commands__.split(';'):
            exec command
    else:
        __run_pythonstartup_script()

    __patching_matplotlib__()

    for _name in ['__run_pythonstartup_script', '__run_init_commands',
                  '__create_banner', '__commands__', 'command', '__file__',
                  '__remove_sys_argv__', '__patching_matplotlib__']+['_name']:
        if _name in locals():
            locals().pop(_name)

    __doc__ = ''
    __name__ = '__main__'

    if __is_ipython():
        import sys
        __real_platform__ = sys.platform
        if sys.platform == 'win32':
            # Patching readline to avoid any error
            from pyreadline import unicode_helper
            unicode_helper.pyreadline_codepage = "ascii"
            # Faking non-win32 to avoid any IPython error
            sys.platform = 'fake'
        import IPython.Shell
        sys.platform = __real_platform__
        del __real_platform__, __is_ipython
        __ipythonshell__ = IPython.Shell.start()
        __ipythonshell__.mainloop()
