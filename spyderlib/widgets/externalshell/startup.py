# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Startup file used by ExternalPythonShell"""

import sys

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

def __create_banner():
    """Create shell banner"""
    print 'Python %s on %s\nType "copyright", "credits" or "license" ' \
          'for more information.'  % (sys.version, sys.platform)

def __remove_sys_argv__():
    """Remove arguments from sys.argv"""
    sys.argv = ['']
    
def __remove_from_syspath__():
    """Remove this module's path from sys.path"""
    import os.path as osp
    try:
        sys.path.remove(osp.dirname(__file__))
    except ValueError:
        pass


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
    

def debugfile(filename, args=None, wdir=None):
    """
    Debug filename
    args: command line arguments (string)
    wdir: working directory
    """
    import pdb
    debugger = pdb.Pdb()
    filename = debugger.canonic(filename)
    debugger._wait_for_mainpyfile = 1
    debugger.mainpyfile = filename
    debugger._user_requested_quit = 0
    debugger.run("runfile(%r, args=%r, wdir=%r)" % (filename, args, wdir))


if __name__ == "__main__":
    __remove_from_syspath__()
    
    if not __is_ipython():
        __remove_sys_argv__()
        __create_banner()
    __commands__ = __run_init_commands()

    if __commands__:
        for command in __commands__.split(';'):
            exec command
    __run_pythonstartup_script()

    for _name in ['__run_pythonstartup_script', '__run_init_commands',
                  '__create_banner', '__commands__', 'command', '__file__',
                  '__remove_sys_argv__']+['_name']:
        if _name in locals():
            locals().pop(_name)

    __doc__ = ''
    __name__ = '__main__'

    if __is_ipython():
        import os
        if os.name == 'nt':
            # Windows platforms: monkey-patching *pyreadline* module
            # to make IPython work in a remote process
            from pyreadline import unicode_helper
            unicode_helper.pyreadline_codepage = "ascii"
            # For pyreadline >= v1.7:
            from pyreadline import rlmain
            class Readline(rlmain.Readline):
                def __init__(self):
                    super(Readline, self).__init__()
                    self.console = None
            rlmain.Readline = Readline
            # For pyreadline v1.5-1.6 only:
            import pyreadline
            pyreadline.GetOutputFile = lambda: None
        del __is_ipython
        try:
            # IPython >=v0.11
            # Support for these recent versions of IPython is limited:
            # command line options are not parsed yet since there are still
            # major issues to be fixed on Windows platforms regarding pylab
            # support.
            from IPython.frontend.terminal.embed import InteractiveShellEmbed
            banner2 = None
            if os.name == 'nt':
                # Patching IPython to avoid enabling readline:
                # we can't simply disable readline in IPython options because
                # it would also mean no text coloring support in terminal
                from IPython.core.interactiveshell import InteractiveShell, io
                def patched_init_io(self):
                    io.stdout = io.IOStream(sys.stdout)
                    io.stderr = io.IOStream(sys.stderr)
                InteractiveShell.init_io = patched_init_io
                banner2 = """Warning:
Spyder does not support GUI interactions with IPython >=v0.11
on Windows platforms (only IPython v0.10 is fully supported).
"""
            __ipythonshell__ = InteractiveShellEmbed(user_ns={
                                                     'runfile': runfile,
                                                     'debugfile': debugfile},
                                                     banner2=banner2)#,
#                                                     display_banner=False)
#            __ipythonshell__.shell.show_banner()
#            __ipythonshell__.enable_pylab(gui='qt')
            #TODO: parse command line options using the two lines commented
            #      above (banner has to be shown afterwards)
            #FIXME: Windows platforms: pylab/GUI loop support is not working
            __ipythonshell__.stdin_encoding = os.environ['SPYDER_ENCODING']
            del banner2
        except ImportError:
            # IPython v0.10
            import IPython.Shell
            __ipythonshell__ = IPython.Shell.start(user_ns={
                                                   'runfile': runfile,
                                                   'debugfile': debugfile})
            __ipythonshell__.IP.stdin_encoding = os.environ['SPYDER_ENCODING']
        
        # Workaround #2 to make the HDF5 I/O variable explorer plugin work:
        # we import h5py only after initializing IPython in order to avoid 
        # a premature import of IPython *and* to enable the h5py/IPython 
        # completer (which wouldn't be enabled if we used the same approach 
        # as workaround #1)
        # (see sitecustomize.py for the Workaround #1)
        try:
            import h5py #@UnusedImport
        except ImportError:
            pass
        
        __ipythonshell__.mainloop()
