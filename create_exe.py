# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""Create a stand-alone executable"""

try:
    from guidata.disthelpers import Distribution
except ImportError:
    raise ImportError("This script requires guidata 1.5+")

import os.path as osp
import imp
import spyder


def create_executable():
    """Build executable using ``guidata.disthelpers``"""
    dist = Distribution()
    name = "spyder"
    ver = spyder.__version__
    try:
        imp.find_module('PyQt4')
        python_qt = 'pyqt'
    except ImportError:
        python_qt = 'pyside'
    dist.setup(name="Spyder", version=ver, script="spyder/spyder.py",
               description="The Scientific Python Development Environment",
               target_name="%s.exe" % name, icon="%s.ico" % name,
               target_dir="%s-win32-%s-sa-%s" % (name, python_qt, ver))
    spyder.add_to_distribution(dist)
    dist.add_modules('matplotlib', 'h5py', 'scipy.io', 'guidata', 'pygments')
    try:
        import guiqwt  # analysis:ignore
        dist.add_modules('guiqwt')
    except ImportError:
        pass
    dist.includes += ['spyder.utils.site.sitecustomize']

    #XXX: ...until we are able to distribute them (see guidata.disthelpers)
    dist.excludes += ['sphinx', 'zmq', 'IPython']

    if osp.isfile("Spyderdoc.chm"):
        dist.add_data_file("Spyderdoc.chm")
    dist.add_data_file(osp.join("rope", "base", "default_config.py"))
    # Building executable
    dist.build('cx_Freeze')#, create_archive='move')


if __name__ == '__main__':
    create_executable()
