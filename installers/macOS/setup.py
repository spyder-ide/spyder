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
    """
    from spyder.config.utils import EDIT_FILETYPES, _get_extensions

    build_type = 'lite' if make_lite else 'full'
    logger.info('Creating %s app bundle...', build_type)

    from packages import PACKAGES, INCLUDES, EXCLUDES, SCIENTIFIC

    EXCLUDE_EGG = ['py2app']

    if make_lite:
        EXCLUDES.extend(SCIENTIFIC)
        EXCLUDES.append('PIL')
        EXCLUDE_EGG.extend(['pillow'])
    else:
        INCLUDES.extend(SCIENTIFIC)
        PACKAGES.extend(['PIL'])

    EXCLUDE_EGG.extend(EXCLUDES)
    EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

    OPTIONS = {
        'optimize': 0,
        'packages': PACKAGES,
        'includes': INCLUDES,
        'excludes': EXCLUDES,
        'iconfile': ICONFILE,
        'dist_dir': dist_dir,
        'emulate_shell_environment': True,
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
