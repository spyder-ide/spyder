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
    import winreg


EWS = "Edit with Spyder"
KEY_C = r"Software\Classes\%s"
KEY_C0 = KEY_C % r"Python.%sFile\shell\%s"
KEY_C1 = KEY_C0 + r"\command"


def install():
    """Function executed when running the script with the -install switch"""
    # Create Spyder start menu folder
    start_menu = osp.join(get_special_folder_path('CSIDL_COMMON_PROGRAMS'),
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
    workdir = "%HOMEDRIVE%%HOMEPATH%"
    import distutils.sysconfig
    lib_dir = distutils.sysconfig.get_python_lib(plat_specific=1)
    ico_dir = osp.join(lib_dir, 'spyderlib', 'windows')

    desc = 'Scientific Python Development EnvironmEnt, an alternative to IDLE'
    fname = osp.join(start_menu, 'Spyder (full).lnk')
    create_shortcut(python, desc, fname, '"%s"' % script, workdir,
                    osp.join(ico_dir, 'spyder.ico'))
    file_created(fname)

    desc += '. Light configuration: console and variable explorer only.'
    fname = osp.join(start_menu, 'Spyder (light).lnk')
    create_shortcut(python, desc, fname,
                    '"%s" --light' % script, workdir,
                    osp.join(ico_dir, 'spyder_light.ico'))
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
    desc = 'Scientific Python Development EnvironmEnt, an alternative to IDLE'
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


if __name__=='__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '-install':
            try:
                install()
            except OSError:
                print("Failed to create Start Menu items, try running "\
                      "installer as administrator.", file=sys.stderr)
        elif sys.argv[1] == '-remove':
            remove()
        else:
            print("Unknown command line option %s" % sys.argv[1],
                  file=sys.stderr)
