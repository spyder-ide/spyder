# -*- coding: utf-8 -*-
"""
MIT License
===========

The spyder/images dir and some source files under other terms (see NOTICE.txt).

Copyright (c) 2009- Spyder Project Contributors and others (see AUTHORS.txt)

Permission is hereby granted, free of charge, to any person
obtaining a copy of this software and associated documentation
files (the "Software"), to deal in the Software without
restriction, including without limitation the rights to use,
copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following
conditions:

The above copyright notice and this permission notice shall be
included in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

version_info = (5, 5, 0)

__version__ = '.'.join(map(str, version_info))
__installer_version__ = __version__
__title__ = 'Spyder'
__author__ = 'Spyder Project Contributors and others'
__license__ = __doc__
__project_url__ = 'https://github.com/spyder-ide/spyder'
__forum_url__   = 'https://groups.google.com/group/spyderlib'
__trouble_url__ = 'https://tinyurl.com/spyder-first-steps'
__trouble_url_short__ = 'https://tinyurl.com/SpyderHelp'
__website_url__ = 'https://www.spyder-ide.org/'
__docs_url__ = 'https://docs.spyder-ide.org/'

# Dear (Debian, RPM, ...) package makers, please feel free to customize the
# following path to module's data (images) and translations:
DATAPATH = LOCALEPATH = DOCPATH = MATHJAXPATH = JQUERYPATH = ''


import os
# Directory of the current file
__current_directory__ = os.path.dirname(os.path.abspath(__file__))


def get_versions(reporev=True):
    """Get version information for components used by Spyder"""
    import sys
    import platform

    import qtpy
    import qtpy.QtCore

    from spyder.utils.conda import is_conda_env
    from spyder.config.base import is_pynsist, running_in_mac_app

    revision = branch = None
    if reporev:
        if running_in_mac_app():
            revision = os.environ.get('SPY_COMMIT', None)
            branch = os.environ.get('SPY_BRANCH', None)
        else:
            from spyder.utils import vcs
            revision, branch = vcs.get_git_revision(
                os.path.dirname(__current_directory__))

    if is_pynsist() or running_in_mac_app():
        installer = 'standalone'
    elif is_conda_env(pyexec=sys.executable):
        installer = 'conda'
    else:
        installer = 'pip'

    versions = {
        'spyder': __version__,
        'installer': installer,
        'python': platform.python_version(),  # "2.7.3"
        'bitness': 64 if sys.maxsize > 2**32 else 32,
        'qt': qtpy.QtCore.__version__,
        'qt_api': qtpy.API_NAME,      # PyQt5
        'qt_api_ver': (qtpy.PYSIDE_VERSION if qtpy.API == "pyside2"
                       else qtpy.PYQT_VERSION),
        'system': platform.system(),   # Linux, Windows, ...
        'release': platform.release(),  # XP, 10.6, 2.2.0, etc.
        'revision': revision,  # '9fdf926eccce',
        'branch': branch,  # '4.x' or master,
        'machine': platform.machine(),  # 'arm64', 'x86_64', 'AMD64', ...
        'platform': platform.platform(aliased=True),
    }
    if sys.platform == 'darwin':
        versions.update(system='macOS', release=platform.mac_ver()[0])

    return versions


def get_versions_text(reporev=True):
    """Create string of version information for components used by Spyder"""
    versions = get_versions(reporev=reporev)

    # Get git revision for development version
    revision = versions['revision'] or ''

    return f"""\
* Spyder version: {versions['spyder']} {revision} ({versions['installer']})
* Python version: {versions['python']} {versions['bitness']}-bit
* Qt version: {versions['qt']}
* {versions['qt_api']} version: {versions['qt_api_ver']}
* Operating System: {versions['platform']}
"""
