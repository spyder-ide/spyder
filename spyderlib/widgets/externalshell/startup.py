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
    return os.environ.get('IPYTHON', False)

def __patching_matplotlib__():
    import os
    if os.environ.get("MATPLOTLIB_PATCH", "").lower() == "true":
        try:
            from spyderlib import mpl_patch
            mpl_patch.apply()
        except ImportError:
            return

def __create_banner():
    """Create shell banner"""
    import sys
    print 'Python %s on %s\nType "copyright", "credits" or "license" ' \
          'for more information.'  % (sys.version, sys.platform)

def __remove_sys_argv__():
    """Remove arguments from sys.argv"""
    import sys
    sys.argv = ['']


class UserModuleDeleter(object):
    """
    User Module Deleter (UMD) aims at deleting user modules 
    to force Python to deeply reload them during import
    
    pathlist [list]: blacklist in terms of module path
    namelist [list]: blacklist in terms of module name
    """
    def __init__(self, namelist=None, pathlist=None):
        if namelist is None:
            namelist = []
        self.namelist = namelist+['sitecustomize', 'spyderlib', 'spyderplugins']
        if pathlist is None:
            pathlist = []
        self.pathlist = pathlist
        self.previous_modules = sys.modules.keys()

    def is_module_blacklisted(self, modname, modpath):
        for path in [sys.prefix]+self.pathlist:
            if modpath.startswith(path):
                return True
        else:
            return set(modname.split('.')) & set(self.namelist)
        
    def run(self, verbose=False):
        """
        Del user modules to force Python to deeply reload them
        
        Do not del modules which are considered as system modules, i.e. 
        modules installed in subdirectories of Python interpreter's binary
        Do not del C modules
        """
        log = []
        for modname, module in sys.modules.items():
            if modname not in self.previous_modules:
                modpath = getattr(module, '__file__', None)
                if modpath is None:
                    # *module* is a C module that is statically linked into the 
                    # interpreter. There is no way to know its path, so we 
                    # choose to ignore it.
                    continue
                if not self.is_module_blacklisted(modname, modpath):
                    log.append(modname)
                    del sys.modules[modname]
        if verbose and log:
            print "\x1b[4;33m%s\x1b[24m%s\x1b[0m" % ("UMD has deleted",
                                                     ": "+", ".join(log))

__umd__ = None

def runfile(filename, args=None, wdir=None):
    """
    Run filename
    args: command line arguments (string)
    wdir: working directory
    """
    global __umd__
    import os
    if os.environ.get("UMD_ENABLED", "").lower() == "true":
        if __umd__ is None:
            namelist = os.environ.get("UMD_NAMELIST", None)
            if namelist is not None:
                namelist = namelist.split(',')
            __umd__ = UserModuleDeleter(namelist=namelist)
        else:
            verbose = os.environ.get("UMD_VERBOSE", "").lower() == "true"
            __umd__.run(verbose=verbose)
    if args is not None and not isinstance(args, basestring):
        raise TypeError("expected a character buffer object")
    glbs = globals()
    if '__ipythonshell__' in glbs:
        glbs = glbs['__ipythonshell__'].IP.user_ns
    glbs['__file__'] = filename
    sys.argv = [filename]
    if args is not None:
        for arg in args.split():
            sys.argv.append(arg)
    if wdir is not None:
        os.chdir(wdir)
    execfile(filename, glbs)
    sys.argv = ['']
    glbs.pop('__file__')


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
        __ipythonshell__ = IPython.Shell.start(user_ns={'runfile': runfile})
        __ipythonshell__.mainloop()
