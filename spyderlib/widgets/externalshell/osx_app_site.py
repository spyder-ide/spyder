#
# IMPORTANT NOTE: Don't add a coding line here! It's not necessary for
# site files
#
# Spyder's MacOS X App site.py additions
#
# It includes missing variables and paths that are not added by
# py2app to its own site.py
#
# These functions were taken verbatim from Python 2.7.3 site.py
#

import sys
import os
try:
    import __builtin__ as builtins
except ImportError:
    # Python 3
    import builtins

# for distutils.commands.install
# These values are initialized by the getuserbase() and getusersitepackages()
# functions.
USER_SITE = None
USER_BASE = None


def getuserbase():
    """Returns the `user base` directory path.

    The `user base` directory can be used to store data. If the global
    variable ``USER_BASE`` is not initialized yet, this function will also set
    it.
    """
    global USER_BASE
    if USER_BASE is not None:
        return USER_BASE
    from sysconfig import get_config_var
    USER_BASE = get_config_var('userbase')
    return USER_BASE

def getusersitepackages():
    """Returns the user-specific site-packages directory path.

    If the global variable ``USER_SITE`` is not initialized yet, this
    function will also set it.
    """
    global USER_SITE
    user_base = getuserbase() # this will also set USER_BASE

    if USER_SITE is not None:
        return USER_SITE

    from sysconfig import get_path

    if sys.platform == 'darwin':
        from sysconfig import get_config_var
        if get_config_var('PYTHONFRAMEWORK'):
            USER_SITE = get_path('purelib', 'osx_framework_user')
            return USER_SITE

    USER_SITE = get_path('purelib', '%s_user' % os.name)
    return USER_SITE


class _Printer(object):
    """interactive prompt objects for printing the license text, a list of
    contributors and the copyright notice."""

    MAXLINES = 23

    def __init__(self, name, data, files=(), dirs=()):
        self.__name = name
        self.__data = data
        self.__files = files
        self.__dirs = dirs
        self.__lines = None

    def __setup(self):
        if self.__lines:
            return
        data = None
        for dir in self.__dirs:
            for filename in self.__files:
                filename = os.path.join(dir, filename)
                try:
                    fp = open(filename, "rU")
                    data = fp.read()
                    fp.close()
                    break
                except IOError:
                    pass
            if data:
                break
        if not data:
            data = self.__data
        self.__lines = data.split('\n')
        self.__linecnt = len(self.__lines)

    def __repr__(self):
        self.__setup()
        if len(self.__lines) <= self.MAXLINES:
            return "\n".join(self.__lines)
        else:
            return "Type %s() to see the full %s text" % ((self.__name,)*2)

    def __call__(self):
        self.__setup()
        prompt = 'Hit Return for more, or q (and Return) to quit: '
        lineno = 0
        while 1:
            try:
                for i in range(lineno, lineno + self.MAXLINES):
                    print(self.__lines[i])
            except IndexError:
                break
            else:
                lineno += self.MAXLINES
                key = None
                while key is None:
                    try:
                        key = raw_input(prompt)
                    except NameError:
                        # Python 3
                        key = input(prompt)
                    if key not in ('', 'q'):
                        key = None
                if key == 'q':
                    break

def setcopyright():
    """Set 'copyright' and 'credits' in builtins"""
    builtins.copyright = _Printer("copyright", sys.copyright)
    if sys.platform[:4] == 'java':
        builtins.credits = _Printer(
            "credits",
            "Jython is maintained by the Jython developers (www.jython.org).")
    else:
        builtins.credits = _Printer("credits", """\
    Thanks to CWI, CNRI, BeOpen.com, Zope Corporation and a cast of thousands
    for supporting Python development.  See www.python.org for more information.""")
    here = os.path.dirname(os.__file__)
    builtins.license = _Printer(
        "license", "See http://www.python.org/%.3s/license.html" % sys.version,
        ["LICENSE.txt", "LICENSE"],
        [os.path.join(here, os.pardir), here, os.curdir])


class _Helper(object):
    """Define the builtin 'help'.
    This is a wrapper around pydoc.help (with a twist).

    """

    def __repr__(self):
        return "Type help() for interactive help, " \
               "or help(object) for help about object."
    def __call__(self, *args, **kwds):
        import pydoc
        return pydoc.help(*args, **kwds)

def sethelper():
    builtins.help = _Helper()
