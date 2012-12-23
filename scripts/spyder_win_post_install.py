# postinstall script for Spyder
"""Create Spyder start menu entries"""

import os
import sys
import os.path as osp
import struct


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
    python = osp.join(sys.prefix, 'python.exe')
    script = osp.join(sys.prefix, 'scripts', 'spyder')
    workdir = "%HOMEDRIVE%%HOMEPATH%"

    desc = 'Scientific Python Development EnvironmEnt, an alternative to IDLE'
    fname = osp.join(start_menu, 'Spyder (full).lnk')
    iconpath = osp.join(sys.prefix, 'scripts', 'spyder.ico')
    create_shortcut(python, desc, fname, '"%s"' % script, workdir, iconpath)
    file_created(fname)

    desc += '. Light configuration: console and variable explorer only.'
    fname = osp.join(start_menu, 'Spyder (light).lnk')
    iconpath = osp.join(sys.prefix, 'scripts', 'spyder_light.ico')
    create_shortcut(python, desc, fname,
                    '"%s" --light' % script, workdir, iconpath)
    file_created(fname)

    fname = osp.join(start_menu, 'Spyder-Reset all settings.lnk')
    create_shortcut(python, 'Reset Spyder settings to defaults',
                    fname, '"%s" --reset' % script, workdir)
    file_created(fname)
    
def remove():
    """Function executed when running the script with the -install switch"""
    pass


if __name__=='__main__':
    if len(sys.argv) > 1:
        if sys.argv[1] == '-install':
            try:
                install()
            except OSError:
                print >>sys.stderr, "Failed to create Start Menu items, "\
                                    "try running installer as administrator."
        elif sys.argv[1] == '-remove':
            remove()
        else:
            print >>sys.stderr, "Unknown command line option %s" % sys.argv[1]
