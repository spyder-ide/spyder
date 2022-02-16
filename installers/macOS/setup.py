# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Create a stand-alone macOS app using py2app

To be used like this:
$ python setup.py
"""

import os
import sys
import shutil
import pkg_resources
from logging import getLogger, StreamHandler, Formatter
from setuptools import setup

# Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('spyder-macOS')
logger.addHandler(h)
logger.setLevel('INFO')

# Define paths
HERE = os.path.abspath(__file__)
THISDIR = os.path.dirname(HERE)
SPYREPO = os.path.realpath(os.path.join(THISDIR, '..', '..'))
ICONFILE = os.path.join(SPYREPO, 'img_src', 'spyder.icns')
SPYLINK = os.path.join(THISDIR, 'spyder')

sys.path.append(SPYREPO)

from spyder import __version__ as SPYVER
from spyder.config.base import MAC_APP_NAME

# Python version
PYVER = [sys.version_info.major, sys.version_info.minor,
         sys.version_info.micro]


def make_app_bundle(dist_dir, make_lite=False):
    """
    Make macOS application bundle.

    Parameters
    ----------
    dist_dir : str
        Directory in which to put the application bundle.
    make_lite : bool, optional
        Whether to create the application bundle with minimal packages.
        The default is False.

    NOTES
    -----
    py2app includes all packages in Spyder.app/Contents/Resources/lib/
    python<ver>.zip, but some packages have issues when placed there.
    The following packages are included in py2app's PACKAGES option so that
    they will be placed in Spyder.app/Contents/Resources/lib/python<ver>
    instead.

    alabaster :
        Error message: [Errno 20] Not a directory: '<path>/Resources/lib/
        python38.zip/alabaster'
    astroid :
        ImportError: cannot import name 'context' from 'astroid'
        (<path>/Resources/lib/python38.zip/astroid/__init__.pyc)
    blib2to3 :
        File "<frozen zipimport>", line 177, in get_data
        KeyError: 'blib2to3/Users/rclary/Library/Caches/black/20.8b1/
        Grammar3.8.6.final.0.pickle'
    debugpy :
        NotADirectoryError: [Errno 20] Not a directory:
        '<path>/Resources/lib/python39.zip/debugpy/_vendored'
    docutils :
        [Errno 20] Not a directory: '<path>/Resources/lib/python39.zip/
        docutils/writers/latex2e/docutils.sty'
    IPython :
        [IPKernelApp] WARNING | Could not copy README_STARTUP to startup dir.
        Source file
        <path>/Resources/lib/python38.zip/IPython/core/profile/README_STARTUP
        does not exist
    jedi :
        jedi.api.environment.InvalidPythonEnvironment: Could not get version
        information for '<path>/Contents/MacOS/python': InternalError("The
        subprocess <path>/Contents/MacOS/python has crashed (EOFError('Ran out
        of input'), stderr=).")
    jinja2 :
        No module named 'jinja2.ext'
    keyring :
        ModuleNotFoundError: No module named 'keyring.backends.<mod>'
    pandas :
        From Variable explorer: KeyError('pandas._libs.interval')
    parso :
        jedi.api.environment.InvalidPythonEnvironment: Could not get version
        information for '/Users/rclary/opt/miniconda3/envs/c2w_37/bin/python':
        InternalError("The subprocess /Users/rclary/opt/miniconda3/envs/c2w_37/
        bin/python has crashed (EOFError('Ran out of input'), stderr=).")
    PIL :
        Library not loaded: @loader_path/.dylibs/libjpeg.9.dylib
        Note: only applicable to not-Lite build
    pkg_resources:
        ImportError: The 'more_itertools' package is required; normally this is
        bundled with this package so if you get this warning, consult the
        packager of your distribution.
    pygments :
        ModuleNotFoundError: No module named 'pygments.formatters.latex'
    pylint :
        <path>/Contents/MacOS/python: No module named pylint.__main__
    pylsp :
        <path>/Contents/MacOS/python: No module named pylsp
        Note: still occurs in alias mode
    pylsp_black :
        Mandatory: python-pyls-black >=1.0.0 : None (NOK)
    pyls_spyder :
        Mandatory: pyls_spyder >=0.1.1 : None (NOK)
    qtawesome :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resourses/lib/
        python38.zip/qtawesome/fonts/fontawesome4.7-webfont.ttf'
    setuptools :
        Mandatory: setuptools >=49.6.0 : None (NOK)
    sphinx :
        No module named 'sphinx.builders.changes'
    spyder :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
        python38.zip/spyder/app/mac_stylesheet.qss'
    spyder_kernels :
        No module named spyder_kernels.console.__main__
    textdistance :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
        python39.zip/textdistance/libraries.json'
    """
    from spyder.config.utils import EDIT_FILETYPES, _get_extensions

    # Patch py2app for IPython help()
    py2app_file = pkg_resources.pkgutil.get_loader('py2app').get_filename()
    site_file = os.path.join(os.path.dirname(py2app_file), 'apptemplate',
                             'lib', 'site.py')
    logger.info('Patching %s...', site_file)
    with open(site_file, 'a+') as f:
        f.seek(0)
        content = f.read()
        if 'builtins.help = _sitebuiltins._Helper()' not in content:
            f.write('\nimport builtins'
                    '\nimport _sitebuiltins'
                    '\nbuiltins.help = _sitebuiltins._Helper()\n')

    build_type = 'lite' if make_lite else 'full'
    logger.info('Creating %s app bundle...', build_type)

    PACKAGES = ['alabaster', 'astroid', 'blib2to3', 'docutils', 'IPython',
                'jedi', 'jinja2', 'keyring', 'parso', 'pygments', 'pylint',
                'pylsp', 'pylsp_black', 'pyls_spyder', 'qtawesome',
                'setuptools', 'sphinx', 'spyder', 'spyder_kernels',
                'textdistance', 'debugpy', 'pkg_resources'
                ]
    INCLUDES = ['_sitebuiltins',  # required for IPython help()
                'jellyfish',
                # required for sphinx
                'sphinxcontrib.applehelp', 'sphinxcontrib.devhelp',
                'sphinxcontrib.htmlhelp', 'sphinxcontrib.jsmath',
                'sphinxcontrib.qthelp', 'sphinxcontrib.serializinghtml',
                'platformdirs.macos',  # required for platformdirs
                ]
    EXCLUDES = []
    EXCLUDE_EGG = ['py2app']

    if make_lite:
        EXCLUDES.extend([
            'numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy', 'PIL'
        ])
        EXCLUDE_EGG.extend(['pillow'])
    else:
        INCLUDES.extend([
            'numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy'
        ])
        PACKAGES.extend(['pandas', 'PIL'])

    EXCLUDE_EGG.extend(EXCLUDES)
    EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

    # Get rtree dylibs
    rtree_loc = pkg_resources.get_distribution('rtree').module_path
    rtree_dylibs = os.scandir(os.path.join(rtree_loc, 'rtree', 'lib'))
    FRAMEWORKS = [lib.path for lib in rtree_dylibs]

    OPTIONS = {
        'optimize': 0,
        'packages': PACKAGES,
        'includes': INCLUDES,
        'excludes': EXCLUDES,
        'iconfile': ICONFILE,
        'dist_dir': dist_dir,
        'frameworks': FRAMEWORKS,
        'plist': {
            'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': EDIT_EXT,
                                       'CFBundleTypeName': 'Text File',
                                       'CFBundleTypeRole': 'Editor'}],
            'CFBundleIdentifier': 'org.spyder-ide',
            'CFBundleShortVersionString': SPYVER,
            'NSRequiresAquaSystemAppearance': False  # Darkmode support
        }
    }

    # Copy main application script
    app_script_name = MAC_APP_NAME.replace('.app', '.py')
    app_script_path = os.path.join(SPYREPO, 'scripts', app_script_name)
    shutil.copy2(os.path.join(SPYREPO, 'scripts', 'spyder'), app_script_path)

    # Build the application
    try:
        os.symlink(os.path.join(SPYREPO, 'spyder'), SPYLINK)
        setup(app=[app_script_path], options={'py2app': OPTIONS})
    finally:
        os.remove(app_script_path)
        os.remove(SPYLINK)

    # Copy egg info: fixes several pkg_resources issues
    copy_egg_info(dist_dir)

    return


def copy_egg_info(dist_dir):
    from zipfile import ZipFile

    pkg_resources.working_set.add_entry(SPYREPO)
    egg_map = {}
    for dist in pkg_resources.working_set:
        if dist.egg_info is None:
            continue

        try:
            tops = dist.get_metadata('top_level.txt').strip().split('\n')
            for top in tops:
                egg_map.update({top: dist.egg_info})
        except FileNotFoundError:
            egg_map.update({dist.project_name: dist.egg_info})

    base_dir = os.path.join(dist_dir, MAC_APP_NAME,
                            'Contents', 'Resources', 'lib')
    pkg_dir = os.path.join(base_dir, 'python{}.{}'.format(*PYVER))
    lib_dir = os.path.join(pkg_dir, 'lib-dynload')
    zip_dir = os.path.join(base_dir, 'python{}{}.zip'.format(*PYVER))

    pkgs = set(f.name for f in os.scandir(pkg_dir))
    pkgs.update(f.name for f in os.scandir(lib_dir))
    pkgs.update(item.split(os.sep)[0] for item in ZipFile(zip_dir).namelist())

    eggs = set()
    for pkg in pkgs:
        top = pkg.split('.')[0]

        egg = None
        try:
            dist = pkg_resources.get_distribution(top)
            egg = dist.egg_info
        except Exception:
            egg = egg_map.get(top, None)

        if egg is not None:
            eggs.add(egg)

    for egg in eggs:
        egg_name = os.path.basename(egg)
        dest = os.path.join(pkg_dir, egg_name)
        shutil.copytree(egg, dest)
        logger.info(f'Copied {egg_name}')

def make_disk_image(dist_dir, make_lite=False):
    """
    Make macOS disk image containing Spyder.app application bundle.

    Parameters
    ----------
    dist_dir : str
        Directory in which to put the disk image.
    make_lite : bool, optional
        Whether to append the disk image file and volume name with 'Lite'.
        The default is False.

    """
    logger.info('Creating disk image...')

    from dmgbuild import build_dmg
    from dmgbuild.core import DMGError

    volume_name = '{}-{} Py-{}.{}.{}'.format(MAC_APP_NAME[:-4], SPYVER, *PYVER)
    dmgfile = os.path.join(dist_dir, 'Spyder')
    if make_lite:
        volume_name += ' Lite'
        dmgfile += '-Lite'
    dmgfile += '.dmg'

    settings_file = os.path.join(THISDIR, 'dmg_settings.py')
    settings = {
        'files': [os.path.join(dist_dir, MAC_APP_NAME)],
        'badge_icon': ICONFILE,
        'icon_locations': {MAC_APP_NAME: (140, 120),
                           'Applications': (500, 120)}
    }

    try:
        build_dmg(dmgfile, volume_name, settings_file=settings_file,
                  settings=settings, detach_retries=30)
        logger.info('Building disk image complete.')
    except DMGError as exc:
        if exc.args[0] == 'Unable to detach device cleanly':
            # don't raise this error since the dmg is forced to detach
            logger.warning(exc.args[0])
        else:
            raise exc

    return


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('-n', '--no-app', dest='make_app',
                        action='store_false', default=True,
                        help='Do not create application bundle')
    parser.add_argument('-l', '--lite', dest='make_lite', action='store_true',
                        default=False,
                        help='Build with minimal internal packages')
    parser.add_argument('-i', '--dmg', dest='make_dmg', action='store_true',
                        default=False, help='Create disk image')
    parser.add_argument('-d', '--dist-dir', dest='dist_dir', default='dist',
                        help='Distribution directory; passed to py2app')
    parser.add_argument('-b', '--bdist-base', dest='build_dir',
                        default='build',
                        help='Build directory; passed to py2app')

    args, rem = parser.parse_known_args()

    # Groom sys.argv for py2app
    sys.argv = sys.argv[:1] + ['py2app'] + rem

    dist_dir = os.path.abspath(args.dist_dir)
    build_dir = os.path.abspath(args.build_dir)

    if args.make_app:
        shutil.rmtree(build_dir, ignore_errors=True)
        make_app_bundle(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping app bundle.')

    if args.make_dmg:
        make_disk_image(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping disk image.')
