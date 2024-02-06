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

import sys
import shutil
from logging import getLogger, StreamHandler, Formatter
from pathlib import Path
from setuptools import setup
from platform import machine

from spyder import get_versions

# Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('macOS-installer')
logger.addHandler(h)
logger.setLevel('INFO')

# Define paths
THISDIR = Path(__file__).resolve().parent
SPYREPO = (THISDIR / '..' / '..').resolve()
ICONFILE = SPYREPO / 'img_src' / 'spyder.icns'
APPSCRIPT = SPYREPO / 'scripts' / 'spyder'

MAC_APP_NAME = 'Spyder.app'
APP_BASE_NAME = MAC_APP_NAME[:-4]

# Python version
PYVER = [sys.version_info.major, sys.version_info.minor,
         sys.version_info.micro]

version = get_versions()
SPYVER = version['spyder']
SPYCOM = version['revision']
SPYBRA = version['branch']


def make_app_bundle(dist_dir, make_lite=False):
    """
    Make macOS application bundle.

    Parameters
    ----------
    dist_dir : pathlib.Path
        Directory in which to put the application bundle.
    make_lite : bool, optional
        Whether to create the application bundle with minimal packages.
        The default is False.
    """
    from spyder.config.utils import EDIT_FILETYPES, _get_extensions

    build_type = 'lite' if make_lite else 'full'
    logger.info('Creating %s app bundle...', build_type)

    from packages import PACKAGES, INCLUDES, EXCLUDES, SCIENTIFIC

    if make_lite:
        EXCLUDES.extend(SCIENTIFIC)
    else:
        INCLUDES.extend(SCIENTIFIC)

    EDIT_EXT = [ext[1:] for ext in _get_extensions(EDIT_FILETYPES)]

    OPTIONS = {
        'optimize': 0,
        'packages': PACKAGES,
        'includes': INCLUDES,
        'excludes': EXCLUDES,
        'iconfile': ICONFILE.as_posix(),
        'dist_dir': dist_dir.as_posix(),
        'emulate_shell_environment': True,
        'plist': {
            'CFBundleDocumentTypes': [{'CFBundleTypeExtensions': EDIT_EXT,
                                       'CFBundleTypeName': 'Text File',
                                       'CFBundleTypeRole': 'Editor'}],
            'CFBundleIdentifier': 'org.spyder-ide.Spyder',
            'CFBundleShortVersionString': SPYVER,
            'NSRequiresAquaSystemAppearance': False,  # Darkmode support
            'LSEnvironment': {'SPY_COMMIT': SPYCOM, 'SPY_BRANCH': SPYBRA}
        }
    }

    # Build the application
    setup(name=APP_BASE_NAME, app=[APPSCRIPT.as_posix()],
          options={'py2app': OPTIONS})

    return


def disk_image_name(make_lite=False):
    """
    Return disk image name
    """
    dmg_name = f'Spyder-{SPYVER}_{machine()}'
    if make_lite:
        dmg_name += '-Lite'
    dmg_name += '.dmg'

    return dmg_name


def make_disk_image(dist_dir, make_lite=False):
    """
    Make macOS disk image containing Spyder.app application bundle.

    Parameters
    ----------
    dist_dir : pathlib.Path
        Directory in which to put the disk image.
    make_lite : bool, optional
        Whether to append the disk image file and volume name with 'Lite'.
        The default is False.

    """
    logger.info('Creating disk image...')

    from dmgbuild import build_dmg
    from dmgbuild.core import DMGError

    volume_name = '{}-{} Py-{}.{}.{}'.format(APP_BASE_NAME, SPYVER, *PYVER)
    if make_lite:
        volume_name += ' Lite'
    dmgfile = (dist_dir / disk_image_name(make_lite)).as_posix()

    settings_file = (THISDIR / 'dmg_settings.py').as_posix()
    settings = {
        'files': [(dist_dir / MAC_APP_NAME).as_posix()],
        'badge_icon': ICONFILE.as_posix(),
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
    parser.add_argument(
        '-m', '--dmg-name', dest='dmg_name', action='store_true',
        help='Return the DMG name: Spyder-{VER}_{ARCH}-{LITE}.dmg'
    )

    args, rem = parser.parse_known_args()

    if args.dmg_name:
        print(disk_image_name(args.make_lite))
        sys.exit()

    # Groom sys.argv for py2app
    sys.argv = sys.argv[:1] + ['py2app'] + rem

    dist_dir = Path(args.dist_dir).resolve()
    build_dir = Path(args.build_dir).resolve()

    if args.make_app:
        shutil.rmtree(build_dir, ignore_errors=True)
        make_app_bundle(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping app bundle.')

    if args.make_dmg:
        make_disk_image(dist_dir, make_lite=args.make_lite)
    else:
        logger.info('Skipping disk image.')
