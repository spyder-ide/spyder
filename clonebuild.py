# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Cloning Spyder mercurial orig_repo_name
Building source and win32 executable distribution package
"""

# pylint: disable=C0103

import os
import os.path as osp
import shutil
import re
import sys

import spyderlib as mod
from spyderlib.py3compat import getcwd

name = 'spyder'
version = mod.__version__
parentdir = osp.abspath(osp.join(os.getcwd(), osp.pardir))
clone_repo_name = '%s-%s' % (name, version)
orig_repo_name = osp.basename(osp.dirname(osp.abspath(__file__)))

os.chdir(parentdir)
if osp.isdir(clone_repo_name):
    ## Removing temporary directory if it already exists
    shutil.rmtree(clone_repo_name)
os.system('hg clone %s %s' % (orig_repo_name, clone_repo_name))

## Building source and exe dist
os.chdir(clone_repo_name)
os.system('python setup.py build sdist bdist_wininst')

## Moving .exe and .egg files to the parent directory
os.chdir(parentdir)
dist = osp.join(clone_repo_name, "dist")
src_dist = "%s.zip" % clone_repo_name
exe_dist = "%s.win32.exe" % clone_repo_name
for fname in (src_dist, exe_dist):
    shutil.copy(osp.join(dist, fname), osp.join(parentdir, fname))

## Removing temporary directory
shutil.rmtree(clone_repo_name)


def extract_exe_dist(plugin_dir, exe_dist):
    """Extract distutils self-extractable archive in Python(x,y) plugin dir"""
    dist_dirs = ('PURELIB', 'SCRIPTS')
    ## Removing previous version directories
    for dirname in dist_dirs:
        dirpath = osp.join(plugin_dir, dirname)
        if osp.isdir(dirpath):
            shutil.rmtree(dirpath)
    ## Unzipping the distutils self-extractable archive
    os.system('%s %s -d %s' % (unzip_exe, exe_dist, plugin_dir))

def include_chm_doc(plugin_dir):
    """Build and replace Spyder's html doc by .chm doc"""
    curdir = getcwd()
    os.chdir(osp.dirname(__file__))
    os.system('sphinx-build -b htmlhelp doc doctmp')
    for hhc_exe in (r'C:\Program Files\HTML Help Workshop\hhc.exe',
                    r'C:\Program Files (x86)\HTML Help Workshop\hhc.exe'):
        if osp.isfile(hhc_exe):
            break
    else:
        print >>sys.stderr, "Warning: HTML Help Workshop is not installed "\
                            "on this computer."
        return
    fname = osp.join('doctmp', 'Spyderdoc.chm')
    os.system('"%s" %s' % (hhc_exe, fname))
    docdir = osp.join(plugin_dir, 'PURELIB', 'spyderlib', 'doc')
    shutil.rmtree(docdir)
    os.mkdir(docdir)
    shutil.copy(fname, osp.join(docdir, 'Spyderdoc.chm'))
    os.chdir(curdir)

def build_pythonxy_plugin(plugin_dir, plugin_version):
    """Build Python(x,y) plugin -- requires Python(x,y) 2.7+
    For Windows platforms only"""
    nsis_files = [osp.join(plugin_dir, fname)
                  for fname in os.listdir(plugin_dir)
                  if osp.splitext(fname)[1] == '.nsi'
                  and fname.startswith('install')]

    vi_version = re.sub(r'[^0-9\.]*', '', plugin_version)
    while len(vi_version.split('.')) < 4:
        # VI_VERSION must match X.X.X.X
        vi_version += '.0'
        
    for fname in nsis_files:
        text = re.sub(r'!define VERSION \"[0-9\.a-zA-Z\_]*\"',
                      '!define VERSION "%s"' % plugin_version,
                      open(fname, 'rb').read())
        text = re.sub(r'!define VI_VERSION \"[\$\{\}0-9\.a-zA-Z\_]*\"',
                      '!define VI_VERSION "%s"' % vi_version, text)
        open(fname, 'wb').write(text)

    for nsis_exe in (r'C:\Program Files\NSIS\makensis.exe',
                     r'C:\Program Files (x86)\NSIS\makensis.exe'):
        if osp.isfile(nsis_exe):
            break
    else:
        raise RuntimeError("NSIS is not installed on this computer.")

    for fname in nsis_files:
        os.system('"%s" %s' % (nsis_exe, fname))

def get_pythonxy_plugindir(name):
    """Searching Python(x,y) plugin directory in current working directory"""
    for fname in os.listdir(getcwd()):
        path = osp.abspath(osp.join(fname, 'src', 'python', name))
        if osp.isdir(path):
            # Also create the binary directory if it does not exist yet:
            def create_dir(path):
                if not osp.isdir(path):
                    os.mkdir(path)
            create_dir(osp.join(fname, 'bin'))
            create_dir(osp.join(fname, 'bin', 'python'))
            return path

## Building Python(x,y) plugin on Windows platforms, if 'unzip.exe' is available
## and if the `pythonxy` repository exists:
from spyderlib.utils import programs
unzip_exe = 'unzip.exe'
plugin_dir = get_pythonxy_plugindir(name)
if programs.is_program_installed(unzip_exe) and plugin_dir:
    extract_exe_dist(plugin_dir, exe_dist)
    include_chm_doc(plugin_dir)
    build_pythonxy_plugin(plugin_dir, version)
