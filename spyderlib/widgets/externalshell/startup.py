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
    __create_banner()
    __commands__ = __run_init_commands()
    if __commands__:
        for command in __commands__.split(';'):
            exec command
    else:
        __run_pythonstartup_script()
    __remove_sys_argv__()

    for name in ('__run_pythonstartup_script', '__run_init_commands', 'name',
                 '__create_banner', '__commands__', 'command', '__file__',
                 '__remove_sys_argv__'):
        locals().pop(name)

    __doc__ = ''
    __name__ = '__main__'
