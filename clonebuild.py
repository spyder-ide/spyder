# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Cloning Spyder mercurial repository
Building source and win32 executable distribution package
"""

import os, shutil, os.path as osp

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

## Building source and exe dist
os.chdir(version)
os.system('python setup.py build sdist bdist_wininst')

## Moving .exe and .egg files to the parent directory
os.chdir(parentdir)
dist = osp.join(version, "dist")
for name in ["%s.zip" % version, "%s.win32.exe" % version]:
    shutil.copy(osp.join(dist, name), osp.join(parentdir, name))

## Removing temporary directory
shutil.rmtree(version)
