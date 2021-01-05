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
    pygments :
        ModuleNotFoundError: No module named 'pygments.formatters.latex'
    pyls :
        <path>/Contents/MacOS/python: No module named pyls
        Note: still occurs in alias mode
    pyls_black :
        Mandatory: pyls_black >=0.4.6 : None (NOK)
    pyls_spyder :
        Mandatory: pyls_spyder >=0.1.1 : None (NOK)
    qtawesome :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resourses/lib/
        python38.zip/qtawesome/fonts/fontawesome4.7-webfont.ttf'
    setuptools :
        Mandatory: setuptools >=39.0.0 : None (NOK)
    sphinx :
        No module named 'sphinx.builders.changes'
    spyder :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
        python38.zip/spyder/app/mac_stylesheet.qss'
    textdistance :
        NotADirectoryError: [Errno 20] Not a directory: '<path>/Resources/lib/
        python39.zip/textdistance/libraries.json'
    """
    import shutil
    import pkg_resources

    from spyder import __version__ as SPYVER
    from spyder.config.utils import EDIT_FILETYPES, _get_extensions
    from spyder.config.base import MAC_APP_NAME

    build_type = 'lite' if make_lite else 'full'
    logger.info('Creating %s app bundle...', build_type)

    PACKAGES = ['alabaster', 'astroid', 'blib2to3', 'jedi', 'jinja2',
                'keyring', 'parso', 'pygments', 'pyls', 'pyls_black',
                'pyls_spyder', 'qtawesome', 'setuptools', 'sphinx', 'spyder',
                'textdistance',
                ]

    EXCLUDE_EGG = ['py2app']

    if make_lite:
        INCLUDES = []
        EXCLUDES = [
            'numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy', 'PIL'
        ]
        EXCLUDE_EGG.append('pillow')
    else:
        INCLUDES = [
            'numpy', 'scipy', 'pandas', 'matplotlib', 'cython', 'sympy'
        ]
        EXCLUDES = []
        PACKAGES.extend(['pandas', 'PIL'])

    EXCLUDE_EGG.extend(EXCLUDES)
    EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

    FRAMEWORKS = ['/usr/local/lib/libspatialindex.dylib',
                  '/usr/local/lib/libspatialindex_c.dylib']  # for rtree

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
            'CFBundleShortVersionString': SPYVER
        }
    }

    # Copy main application script
    app_script_name = MAC_APP_NAME.replace('.app', '.py')
    app_script_path = os.path.join(SPYREPO, 'scripts', app_script_name)
    shutil.copy2(os.path.join(SPYREPO, 'scripts', 'spyder'), app_script_path)

    try:
        os.symlink(os.path.join(SPYREPO, 'spyder'), SPYLINK)
        setup(app=[app_script_path], options={'py2app': OPTIONS})
    finally:
        os.remove(app_script_path)
        os.remove(SPYLINK)

    # Copy egg info from site-packages: fixes several pkg_resources issues
    dest_dir = os.path.join(dist_dir, MAC_APP_NAME, 'Contents', 'Resources',
                            'lib', f'python{PYVER[0]}.{PYVER[1]}')
    for dist in pkg_resources.working_set:
        if (dist.egg_info is None or dist.key.startswith('pyobjc')
                or dist.key in EXCLUDE_EGG):
            logger.info(f'Skipping egg {dist.key}')
            continue
        egg = os.path.basename(dist.egg_info)
        dest = os.path.join(dest_dir, egg)
        shutil.copytree(dist.egg_info, dest)
        logger.info(f'Copied {egg}')

    logger.info('App bundle complete.')

    return


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
    from spyder import __version__ as SPYVER
    from spyder.config.base import MAC_APP_NAME

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

    args, rem = parser.parse_known_args()

    # Groom sys.argv for py2app
    sys.argv = sys.argv[:1] + ['py2app'] + rem

    dist_dir = os.path.abspath(args.dist_dir)

    if args.make_app:
        make_app_bundle(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping app bundle.')

    if args.make_dmg:
        make_disk_image(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping disk image.')
