# -*- coding: utf-8 -*-
#
# Copyright © 2009 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Cloning Spyder mercurial repository
Building:
    .tar.gz source distribution package
    .exe and .egg installers
"""

import os, shutil, tarfile
import os.path as osp

import spyderlib as mod
name = 'spyder'
parentdir = osp.join(os.getcwd(), osp.pardir)
version = '%s-%s' % (name, mod.__version__)

os.chdir(parentdir)
if osp.isdir(version):
    ## Removing temporary directory if it already exists
    shutil.rmtree(version)
basename = osp.basename(osp.dirname(__file__))
os.system('hg clone %s %s' % (basename, version))

## Creating source distribution archive
tar = tarfile.open("%s.tar.gz" % version, "w|gz")
tar.add(version, recursive=True,
        exclude=lambda fn: osp.relpath(fn, version).startswith('.hg'))
tar.close()

## Building .exe and .egg installers
os.chdir(version)
build_cmd = 'python setup.py build_ext --compiler=mingw32'
os.system('%s bdist_wininst' % build_cmd)
os.system('%s bdist_egg' % build_cmd)
# No longer building the .msi installer since it does not support
# prerelease version numbering (e.g. 1.0.0beta1):
#os.system('%s bdist_msi' % build_cmd)

## Moving .exe and .egg files to the parent directory
os.chdir(parentdir)
dist = osp.join(version, "dist")
info = osp.join(version, "%s.egg-info" % name)
# No longer building the .msi installer since it does not support
# prerelease version numbering (e.g. 1.0.0beta1):
#for name in ["%s.win32-py2.5.msi" % version,
#             "%s.win32.exe" % version,
for name in ["%s.win32.exe" % version,
             "%s-py2.6.egg" % version]:
    shutil.copy(osp.join(dist, name), osp.join(parentdir, name))
name = "PKG-INFO"
shutil.copy(osp.join(info, name), osp.join(parentdir, "%s-info" % version))

## Removing temporary directory
shutil.rmtree(version)
