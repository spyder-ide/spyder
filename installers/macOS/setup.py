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
from logging import getLogger, StreamHandler, Formatter
from pathlib import Path
from setuptools import setup

# Setup logger
fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('spyder-macOS')
logger.addHandler(h)
logger.setLevel('INFO')

# Define paths
THISDIR = Path(__file__).resolve().parent
SPYREPO = (THISDIR / '..' / '..').resolve()
ICONFILE = SPYREPO / 'img_src' / 'spyder.icns'
SPYLINK = THISDIR / 'spyder'

sys.path.append(SPYREPO.as_posix())

from spyder import __version__ as SPYVER
from spyder.config.base import MAC_APP_NAME

# Python version
PYVER = [sys.version_info.major, sys.version_info.minor,
         sys.version_info.micro]


def fix_zip_entry_points(zfile):
    """
    Fix zip archive so that pkg_resources will find entry points.
    Remove if a better solution emerges.

    Parameters
    ----------
    zfile : pathlib.Path
        Path to zip archive.
    """
    import os
    from zipfile import ZipFile

    logger.info('Converting zip file...')

    file = zfile.parent / 'temp'
    ZipFile(zfile).extractall(file)
    os.remove(zfile)
    file.replace(zfile)


def patch_py2app():
    """
    Patch py2app PyQt recipe and site.py for version 0.27.
    Remove after version 0.28 is available.
    """
    from importlib.util import find_spec
    from importlib.metadata import version
    from packaging.version import parse

    logger.info('Patching py2app...')

    py2app_ver = version('py2app')
    if parse(py2app_ver) > parse('0.27'):
        raise DeprecationWarning(f'py2app version {py2app_ver} > 0.27; '
                                 'stop using patch_py2app.')

    root = Path(find_spec('py2app').origin).parent

    # Patch site.py
    site_file = root / 'apptemplate' / 'lib' / 'site.py'
    append_text = ("builtins.quit = "
                   "_sitebuiltins.Quitter('quit', 'Ctrl-D (i.e. EOF)')\n"
                   "builtins.exit = "
                   "_sitebuiltins.Quitter('exit', 'Ctrl-D (i.e. EOF)')\n")
    text = site_file.read_text()
    if append_text not in text:
        site_file.write_text(text + append_text)

    # Patch qt5.py
    qt5_file = root / 'recipes' / 'qt5.py'
    search_text = "if qtdir != os.path.dirname(PyQt5.__file__):"
    replace_text = "if os.path.dirname(PyQt5.__file__) not in qtdir:"
    text = qt5_file.read_text()
    if replace_text not in text:
        qt5_file.write_text(text.replace(search_text, replace_text))


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
            'CFBundleIdentifier': 'org.spyder-ide',
            'CFBundleShortVersionString': SPYVER,
            'NSRequiresAquaSystemAppearance': False  # Darkmode support
        }
    }

    # Copy main application script
    app_script_name = MAC_APP_NAME.replace('.app', '.py')
    app_script_path = SPYREPO / 'scripts' / app_script_name
    shutil.copy2(SPYREPO / 'scripts' / 'spyder', app_script_path)

    # Build the application
    try:
        patch_py2app()
        os.symlink(SPYREPO / 'spyder', SPYLINK)
        setup(app=[app_script_path.as_posix()], options={'py2app': OPTIONS})
        fix_zip_entry_points(
            dist_dir / MAC_APP_NAME / 'Contents' / 'Resources' / 'lib' /
            'python{}{}.zip'.format(*PYVER[:2]))
    finally:
        os.remove(app_script_path)
        os.remove(SPYLINK)

    # Copy Spyder egg-info
    egg = SPYREPO / 'spyder.egg-info'
    dest = (dist_dir / MAC_APP_NAME / 'Contents' / 'Resources' / 'lib' /
            'python{}.{}'.format(*PYVER) / 'spyder.egg-info')
    shutil.copytree(egg, dest)

    return


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

    volume_name = '{}-{} Py-{}.{}.{}'.format(MAC_APP_NAME[:-4], SPYVER, *PYVER)
    dmg_name = 'Spyder'
    if make_lite:
        volume_name += ' Lite'
        dmg_name += '-Lite'
    dmg_name += '.dmg'
    dmgfile = (dist_dir / dmg_name).as_posix()


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

    args, rem = parser.parse_known_args()

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
