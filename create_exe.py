# -*- coding: utf-8 -*-
#
# Copyright © 2011 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""Create a stand-alone executable"""

try:
    from guidata.disthelpers import Distribution
except ImportError:
    raise ImportError, "This script requires guidata 1.4+"

import os.path as osp
import spyderlib


def create_executable():
    """Build executable using ``guidata.disthelpers``"""
    dist = Distribution()
    dist.setup(name="Spyder", version=spyderlib.__version__,
               description=u"Scientific PYthon Development EnviRonment",
               script="spyderlib/spyder.py",
               target_name="spyder.exe", icon="spyder.ico")
    spyderlib.add_to_distribution(dist)
    dist.add_modules('matplotlib', 'h5py', 'scipy.io')
    dist.includes += ['spyderlib.widgets.externalshell.startup',
                      'spyderlib.widgets.externalshell.sitecustomize',
                      'IPython']
    dist.excludes += ['sphinx']  #XXX: ...until we are able to distribute it
    if osp.isfile("Spyderdoc.chm"):
        dist.add_data_file("Spyderdoc.chm")
    dist.add_data_file(osp.join("rope", "base", "default_config.py"))
    # Building executable
    dist.build('cx_Freeze')


if __name__ == '__main__':
    create_executable()
