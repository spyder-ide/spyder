# postinstall script for Spyder
"""Create Spyder start menu and desktop entries"""

from __future__ import print_function

import os
import sys
import os.path as osp
import struct
try:
    # Python 2
    import _winreg as winreg
except ImportError:
    # Python 3
    import winreg  # analysis:ignore


EWS = "Edit with Spyder"
KEY_C = r"Software\Classes\%s"
KEY_C0 = KEY_C % r"Python.%sFile\shell\%s"
KEY_C1 = KEY_C0 + r"\command"


# ability to run spyder-win-post-install outside of bdist_wininst installer
# copied from pywin32-win-post-install.py
# http://pywin32.hg.sourceforge.net/hgweb/pywin32/pywin32/file/default/pywin32_postinstall.py
ver_string = "%d.%d" % (sys.version_info[0], sys.version_info[1])
root_key_name = "Software\\Python\\PythonCore\\" + ver_string

try:
    # When this script is run from inside the bdist_wininst installer,
    # file_created() and directory_created() are additional builtin
    # functions which write lines to Python23\pywin32-install.log. This is
    # a list of actions for the uninstaller, the format is inspired by what
    # the Wise installer also creates.
    # https://docs.python.org/2/distutils/builtdist.html#the-postinstallation-script
    file_created  # analysis:ignore
    is_bdist_wininst = True
except NameError:
    is_bdist_wininst = False # we know what it is not - but not what it is :)

    # file_created() and directory_created() functions do nothing if post
    # install script isn't run from bdist_wininst installer, instead if
    # shortcuts and start menu directory exist, they are removed when the
    # post install script is called with the -remote option
    def file_created(file):
        pass
    def directory_created(directory):
        pass
    def get_root_hkey():
        try:
            winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE,
                           root_key_name, 0, winreg.KEY_CREATE_SUB_KEY)
            return winreg.HKEY_LOCAL_MACHINE
        except OSError:
            # Either not exist, or no permissions to create subkey means
            # must be HKCU
            return winreg.HKEY_CURRENT_USER
try:
    create_shortcut  # analysis:ignore
except NameError:
    # Create a function with the same signature as create_shortcut
    # provided by bdist_wininst
    def create_shortcut(path, description, filename,
                        arguments="", workdir="", iconpath="", iconindex=0):
        try:
            import pythoncom
        except ImportError:
            print("pywin32 is required to run this script manually",
                  file=sys.stderr)
            sys.exit(1)
        from win32com.shell import shell, shellcon  # analysis:ignore

        ilink = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None,
                                           pythoncom.CLSCTX_INPROC_SERVER,
                                           shell.IID_IShellLink)
        ilink.SetPath(path)
        ilink.SetDescription(description)
        if arguments:
            ilink.SetArguments(arguments)
        if workdir:
            ilink.SetWorkingDirectory(workdir)
        if iconpath or iconindex:
            ilink.SetIconLocation(iconpath, iconindex)
        # now save it.
        ipf = ilink.QueryInterface(pythoncom.IID_IPersistFile)
        ipf.Save(filename, 0)

    # Support the same list of "path names" as bdist_wininst.
    def get_special_folder_path(path_name):
        try:
            import pythoncom
        except ImportError:
            print("pywin32 is required to run this script manually",
                  file=sys.stderr)
            sys.exit(1)
        from win32com.shell import shell, shellcon

        path_names = ['CSIDL_COMMON_STARTMENU', 'CSIDL_STARTMENU',
                      'CSIDL_COMMON_APPDATA', 'CSIDL_LOCAL_APPDATA',
                      'CSIDL_APPDATA', 'CSIDL_COMMON_DESKTOPDIRECTORY',
                      'CSIDL_DESKTOPDIRECTORY', 'CSIDL_COMMON_STARTUP',
                      'CSIDL_STARTUP', 'CSIDL_COMMON_PROGRAMS',
                      'CSIDL_PROGRAMS', 'CSIDL_PROGRAM_FILES_COMMON',
                      'CSIDL_PROGRAM_FILES', 'CSIDL_FONTS']
        for maybe in path_names:
            if maybe == path_name:
                csidl = getattr(shellcon, maybe)
                return shell.SHGetSpecialFolderPath(0, csidl, False)
        raise ValueError("%s is an unknown path ID" % (path_name,))


def install():
    """Function executed when running the script with the -install switch"""
    # Create Spyder start menu folder
    # Don't use CSIDL_COMMON_PROGRAMS because it requres admin rights
    # This is consistent with use of CSIDL_DESKTOPDIRECTORY below
    # CSIDL_COMMON_PROGRAMS =
    # C:\ProgramData\Microsoft\Windows\Start Menu\Programs
    # CSIDL_PROGRAMS =
    # C:\Users\<username>\AppData\Roaming\Microsoft\Windows\Start Menu\Programs
    start_menu = osp.join(get_special_folder_path('CSIDL_PROGRAMS'),
                          'Spyder (Py%i.%i %i bit)' % (sys.version_info[0],
                                                       sys.version_info[1],
                                                       struct.calcsize('P')*8))
    if not osp.isdir(start_menu):
        os.mkdir(start_menu)
        directory_created(start_menu)

    # Create Spyder start menu entries
    python = osp.abspath(osp.join(sys.prefix, 'python.exe'))
    pythonw = osp.abspath(osp.join(sys.prefix, 'pythonw.exe'))
    script = osp.abspath(osp.join(sys.prefix, 'scripts', 'spyder'))
    if not osp.exists(script): # if not installed to the site scripts dir
        script = osp.abspath(osp.join(osp.dirname(osp.abspath(__file__)), 'spyder'))
    workdir = "%HOMEDRIVE%%HOMEPATH%"
    import distutils.sysconfig
    lib_dir = distutils.sysconfig.get_python_lib(plat_specific=1)
    ico_dir = osp.join(lib_dir, 'spyder', 'windows')
    # if user is running -install manually then icons are in Scripts/
    if not osp.isdir(ico_dir):
        ico_dir = osp.dirname(osp.abspath(__file__))

    desc = 'The Scientific Python Development Environment'
    fname = osp.join(start_menu, 'Spyder (full).lnk')
    create_shortcut(python, desc, fname, '"%s"' % script, workdir,
                    osp.join(ico_dir, 'spyder.ico'))
    file_created(fname)

    fname = osp.join(start_menu, 'Spyder-Reset all settings.lnk')
    create_shortcut(python, 'Reset Spyder settings to defaults',
                    fname, '"%s" --reset' % script, workdir)
    file_created(fname)

    current = True  # only affects current user
    root = winreg.HKEY_CURRENT_USER if current else winreg.HKEY_LOCAL_MACHINE
    winreg.SetValueEx(winreg.CreateKey(root, KEY_C1 % ("", EWS)),
                      "", 0, winreg.REG_SZ,
                      '"%s" "%s\Scripts\spyder" "%%1"' % (pythonw, sys.prefix))
    winreg.SetValueEx(winreg.CreateKey(root, KEY_C1 % ("NoCon", EWS)),
                      "", 0, winreg.REG_SZ,
                      '"%s" "%s\Scripts\spyder" "%%1"' % (pythonw, sys.prefix))

    # Create desktop shortcut file
    desktop_folder = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
    fname = osp.join(desktop_folder, 'Spyder.lnk')
    desc = 'The Scientific Python Development Environment'
    create_shortcut(pythonw, desc, fname, '"%s"' % script, workdir,
                    osp.join(ico_dir, 'spyder.ico'))
    file_created(fname)


def remove():
    """Function executed when running the script with the -remove switch"""
    current = True  # only affects current user
    root = winreg.HKEY_CURRENT_USER if current else winreg.HKEY_LOCAL_MACHINE
    for key in (KEY_C1 % ("", EWS), KEY_C1 % ("NoCon", EWS),
                KEY_C0 % ("", EWS), KEY_C0 % ("NoCon", EWS)):
        try:
            winreg.DeleteKey(root, key)
        except WindowsError:
            pass
        else:
            if not is_bdist_wininst:
                print("Successfully removed Spyder shortcuts from Windows "\
                      "Explorer context menu.", file=sys.stdout)
    if not is_bdist_wininst:
        # clean up desktop
        desktop_folder = get_special_folder_path("CSIDL_DESKTOPDIRECTORY")
        fname = osp.join(desktop_folder, 'Spyder.lnk')
        if osp.isfile(fname):
            try:
                os.remove(fname)
            except OSError:
                print("Failed to remove %s; you may be able to remove it "\
                      "manually." % fname, file=sys.stderr)
            else:
                print("Successfully removed Spyder shortcuts from your desktop.",
                      file=sys.stdout)
        # clean up startmenu
        start_menu = osp.join(get_special_folder_path('CSIDL_PROGRAMS'),
                              'Spyder (Py%i.%i %i bit)' % (sys.version_info[0],
                                                           sys.version_info[1],
                                                           struct.calcsize('P')*8))
        if osp.isdir(start_menu):
            for fname in os.listdir(start_menu):
                try:
                    os.remove(osp.join(start_menu,fname))
                except OSError:
                    print("Failed to remove %s; you may be able to remove it "\
                          "manually." % fname, file=sys.stderr)
                else:
                    print("Successfully removed Spyder shortcuts from your "\
                          " start menu.", file=sys.stdout)
            try:
                os.rmdir(start_menu)
            except OSError:
                print("Failed to remove %s; you may be able to remove it "\
                      "manually." % fname, file=sys.stderr)
            else:
                print("Successfully removed Spyder shortcut folder from your "\
                      " start menu.", file=sys.stdout)


if __name__=='__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '-install':
            try:
                install()
            except OSError:
                print("Failed to create Start Menu items.", file=sys.stderr)
        elif sys.argv[1] == '-remove':
            remove()
        else:
            print("Unknown command line option %s" % sys.argv[1],
                  file=sys.stderr)
    else:
        print("You need to pass either -install or -remove as options to "\
              "this script", file=sys.stderr)
