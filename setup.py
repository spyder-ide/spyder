# -*- coding: utf-8 -*-
#
# Copyright © 2009-2010 Pierre Raybaut
# Licensed under the terms of the MIT License
# (see spyderlib/__init__.py for details)

"""
Spyder
======

The Scientific PYthon Development EnviRonment
"""

from distutils.core import setup
from distutils.command.build import build
from sphinx import setup_command
import os
import os.path as osp
import sys


def get_package_data(name, extlist):
    """Return data files for package *name* with extensions in *extlist*"""
    flist = []
    # Workaround to replace os.path.relpath (not available until Python 2.6):
    offset = len(name)+len(os.pathsep)
    for dirpath, _dirnames, filenames in os.walk(name):
        for fname in filenames:
            if not fname.startswith('.') and osp.splitext(fname)[1] in extlist:
                flist.append(osp.join(dirpath, fname)[offset:])
    return flist


def get_subpackages(name):
    """Return subpackages of package *name*"""
    splist = []
    for dirpath, _dirnames, _filenames in os.walk(name):
        if osp.isfile(osp.join(dirpath, '__init__.py')):
            splist.append(".".join(dirpath.split(os.sep)))
    return splist


# Sphinx build (documentation)
class MyBuild(build):
    def has_doc(self):
        setup_dir = os.path.dirname(os.path.abspath(__file__))
        return os.path.isdir(os.path.join(setup_dir, 'doc'))
    sub_commands = build.sub_commands + [('build_doc', has_doc)]


class MyBuildDoc(setup_command.BuildDoc):
    def run(self):
        build = self.get_finalized_command('build')
        sys.path.insert(0, os.path.abspath(build.build_lib))
        dirname = self.distribution.get_command_obj('build').build_purelib
        self.builder_target_dir = osp.join(dirname, 'spyderlib', 'doc')
        try:
            setup_command.BuildDoc.run(self)
        except UnicodeDecodeError:
            print >>sys.stderr, "ERROR: unable to build documentation "\
                                "because Sphinx do not handle source path "\
                                "with non-ASCII characters. Please try to "\
                                "move the source package to another location "\
                                "(path with *only* ASCII characters)."        
        sys.path.pop(0)


cmdclass = {'build': MyBuild, 'build_doc': MyBuildDoc}


NAME = 'spyder'
LIBNAME = 'spyderlib'
from spyderlib import __version__, __project_url__


def get_packages():
    """Return package list"""
    packages = get_subpackages(LIBNAME)+get_subpackages('spyderplugins')
    if os.name == 'nt':
        # Adding pyflakes and rope to the package if available in the 
        # repository (this is not conventional but Spyder really need 
        # those tools and there is not decent package manager on 
        # Windows platforms, so...)
        for name in ('rope', 'pyflakes'):
            if osp.isdir(name):
                packages += get_subpackages(name)
    return packages
    

setup(name=NAME,
      version=__version__,
      description='Scientific PYthon Development EnviRonment',
      long_description=\
"""The spyderlib library includes Spyder, a free open-source Python 
development environment providing MATLAB-like features in a simple 
and light-weighted software.
It also provides ready-to-use pure-Python widgets to your PyQt4 or 
PySide application: source code editor with syntax highlighting and 
code introspection/analysis features, NumPy array editor, dictionary 
editor, Python console, etc.""",
      download_url='%s/files/%s-%s.zip' % (__project_url__, NAME, __version__),
      author="Pierre Raybaut",
      url=__project_url__,
      license='MIT',
      keywords='PyQt4 PySide editor shell console widgets IDE',
      platforms=['any'],
      packages=get_packages(),
      package_data={LIBNAME:
                    get_package_data(LIBNAME, ('.mo', '.svg', '.png', '.css',
                                               '.html', '.js')),
                    'spyderplugins':
                    get_package_data('spyderplugins',
                                     ('.mo', '.svg', '.png'))},
      requires=["rope (>=0.9.2)", "sphinx (>=0.6.0)", "PyQt4 (>=4.4)"],
      scripts=[osp.join('scripts', fname) for fname in 
               (['spyder', 'spyder.bat', "%s_win_post_install.py" % NAME,
                 'spyder.ico', 'spyder_light.ico']
                if os.name == 'nt' else ['spyder'])],
      options={"bdist_wininst":
               {"install_script": "%s_win_post_install.py" % NAME,
                "title": "%s-%s" % (NAME, __version__),
                "user_access_control": "auto"},
               "bdist_msi":
               {"install_script": "%s_win_post_install.py" % NAME}},
      classifiers=['License :: OSI Approved :: MIT License',
                   'Operating System :: MacOS',
                   'Operating System :: Microsoft :: Windows',
                   'Operating System :: OS Independent',
                   'Operating System :: POSIX',
                   'Operating System :: Unix',
                   'Programming Language :: Python :: 2.5',
                   'Programming Language :: Python :: 2.6',
                   'Programming Language :: Python :: 2.7',
                   'Development Status :: 5 - Production/Stable',
                   'Topic :: Scientific/Engineering',
                   'Topic :: Software Development :: Widget Sets'],
      cmdclass=cmdclass)
