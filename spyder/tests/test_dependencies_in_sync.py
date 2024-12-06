# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
from ast import literal_eval
import os.path as osp

# Third party imports
import pytest
import yaml

# Local imports
from spyder.dependencies import DESCRIPTIONS, OPTIONAL, PY38

# Constants
HERE = osp.abspath(osp.dirname(__file__))
ROOT_PATH = osp.dirname(osp.dirname(HERE))
ENV_FPATH = osp.join(ROOT_PATH, 'binder', 'environment.yml')
REQ_FPATH = osp.join(ROOT_PATH, 'requirements', 'main.yml')
REQ_WINDOWS_FPATH = osp.join(ROOT_PATH, 'requirements', 'windows.yml')
REQ_MAC_FPATH = osp.join(ROOT_PATH, 'requirements', 'macos.yml')
REQ_LINUX_FPATH = osp.join(ROOT_PATH, 'requirements', 'linux.yml')
REQ_TEST_FPATH = osp.join(ROOT_PATH, 'requirements', 'tests.yml')
SETUP_FPATH = osp.join(ROOT_PATH, 'setup.py')


def parse_environment_yaml(fpath):
    """
    Parse an environment yaml file and return a dict of deps and versions.
    """
    with open(fpath, 'r') as fh:
        data = yaml.load(fh, Loader=yaml.FullLoader)

    deps = {}
    yaml_deps = data.get('dependencies')
    for dep in yaml_deps:
        if isinstance(dep, dict):
            continue
        elif dep == 'websockify':
            continue
        else:
            parts = dep.split(' ')
            if len(parts) > 1:
                ver = parts[-1]
                if ver[0] == '=':
                    ver = '=' + ver

                deps[parts[0]] = ver
            else:
                deps[parts[0]] = None

    return deps


def parse_spyder_dependencies():
    """
    Parse Spyder dependencies and return a dict of deps and versions.
    """
    deps = {}
    for dep in DESCRIPTIONS:
        if dep.get('kind', None) == OPTIONAL:
            continue

        ver = dep['required_version']
        if ver:
            if ';' in ver:
                ver = ver.replace(';', ',')
            elif ver[0] == '=':
                ver = '=' + ver

        deps[dep['package_name'].lower()] = ver

    return deps


def parse_setup_install_requires(fpath):
    """
    Parse Spyder setup.py and return a dict of deps and versions.
    """
    with open(fpath, 'r') as fh:
        data = fh.read()

    # Extract dependencies
    lines = data.split('\n')
    is_dep_line = False
    deps_list = []
    for line in lines:
        if is_dep_line:
            if line.strip() in ('],', ']'):
                # End of dependency lines
                is_dep_line = False
            elif not line.strip().startswith('#'):
                # Add dependency
                deps_list.append(line.strip().strip(',').strip("'"))
        if (
            line.strip() in ("'pyqt5': [", "install_requires += [")
            and not is_dep_line
        ):
            # Depencies begin on next line
            is_dep_line = True

    # Process dependencies
    deps = {}
    for dep in deps_list:
        dep = dep.split(';')[0]
        name, ver = None, None

        for sep in ['>=', '==', '<=', '<', '>']:
            if sep in dep:
                name, ver = dep.split(sep)
                name = name.split('[')[0]  # Discard e.g. [all]
                ver = sep + ver  # Include comparator
                break

        # Transform pypi to conda name
        if name == 'pyqt5':
            name = 'pyqt'

        deps[name] = ver

    return deps


def parse_setup_extra_requires(fpath):
    """
    Parse Spyder setup.py and return a dict of deps and versions.
    """
    deps = {}
    with open(fpath, 'r') as fh:
        data = fh.read()

    lines = data.split('\n')
    start = None
    end = None
    for idx, line in enumerate(lines):
        if line.startswith('extras_require = '):
            start = idx + 1

        if start is not None and line.startswith('}'):
            end = idx
            break

    dep_dict = literal_eval('{' + '\n'.join(lines[start:end + 1]))
    dep_list = dep_dict.get('test')
    dep_list = [item for item in dep_list if item[0] != '#']
    for dep in dep_list:
        dep = dep.split(';')[0]
        name, ver = None, None

        for sep in ['>=', '==', '<=', '<', '>']:
            if sep in dep:
                idx = dep.index(sep)
                name = dep[:idx]
                ver = dep[idx:]
                break

        if name is not None:
            name = name.split('[')[0]
        else:
            name = dep.split('[')[0]

        # Transform pypi to conda name
        if name == 'pyqt5':
            name = 'pyqt'

        deps[name] = ver
    print(deps)
    return deps


def test_dependencies_for_binder_in_sync():
    """
    Binder environment yaml should be the sum of main.yml and tests.yml
    requirements.
    """
    spyder_env = parse_environment_yaml(ENV_FPATH)
    main_reqs = parse_environment_yaml(REQ_FPATH)
    test_reqs = parse_environment_yaml(REQ_TEST_FPATH)
    linux_reqs = parse_environment_yaml(REQ_LINUX_FPATH)

    # Check that the requirement files match the environment yaml file
    full_reqs = {}
    full_reqs.update(main_reqs)
    full_reqs.update(linux_reqs)
    full_reqs.update(test_reqs)

    assert spyder_env == full_reqs


@pytest.mark.skipif(PY38, reason="Fails in Python 3.8")
def test_dependencies_for_spyder_dialog_in_sync():
    """
    Spyder dependencies dialog should share deps with main.yml.
    """
    spyder_deps = parse_spyder_dependencies()
    main_reqs = parse_environment_yaml(REQ_FPATH)
    windows_reqs = parse_environment_yaml(REQ_WINDOWS_FPATH)
    mac_reqs = parse_environment_yaml(REQ_MAC_FPATH)
    linux_reqs = parse_environment_yaml(REQ_LINUX_FPATH)

    full_reqs = {}
    full_reqs.update(main_reqs)
    full_reqs.update(windows_reqs)
    full_reqs.update(mac_reqs)
    full_reqs.update(linux_reqs)

    # These packages are not declared in our dependencies dialog
    for dep in ['pyqt', 'pyqtwebengine', 'python.app', 'fzf', 'fcitx-qt5']:
        full_reqs.pop(dep)

    assert spyder_deps == full_reqs


def test_dependencies_for_spyder_setup_install_requires_in_sync():
    """
    Spyder setup.py should share deps with main.yml.
    """
    spyder_setup = parse_setup_install_requires(SETUP_FPATH)
    main_reqs = parse_environment_yaml(REQ_FPATH)
    windows_reqs = parse_environment_yaml(REQ_WINDOWS_FPATH)
    mac_reqs = parse_environment_yaml(REQ_MAC_FPATH)
    linux_reqs = parse_environment_yaml(REQ_LINUX_FPATH)

    full_reqs = {}
    full_reqs.update(main_reqs)
    full_reqs.update(windows_reqs)
    full_reqs.update(mac_reqs)
    full_reqs.update(linux_reqs)

    # We can't declare these as dependencies in setup.py
    for dep in ['python.app', 'fzf', 'fcitx-qt5']:
        full_reqs.pop(dep)
    # Ignored `pyqt5-sip` constraint on conda
    spyder_setup.pop('pyqt5-sip')

    assert spyder_setup == full_reqs


def test_dependencies_for_spyder_setup_extras_requires_in_sync():
    """
    Spyder setup.py extra_requires should share deps with tests.yml.
    """
    spyder_extras_setup = parse_setup_extra_requires(SETUP_FPATH)
    spyder_test_reqs = parse_environment_yaml(REQ_TEST_FPATH)

    assert spyder_extras_setup == spyder_test_reqs
