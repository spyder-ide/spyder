# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Build conda packages to local channel.

This module builds conda packages for Spyder and external-deps for
inclusion in the conda-based installer. The Following classes are
provided for each package:
    SpyderCondaPkg
    PylspCondaPkg
    QdarkstyleCondaPkg
    QtconsoleCondaPkg
    SpyderKernelsCondaPkg

Spyder will be packaged from this repository (in its checked-out state).
qdarkstyle, qtconsole, and spyder-kernels will be packaged from the
external-deps directory of this repository (in its checked-out state).
Python-lsp-server, however, will be packaged from the upstream remote
at the same commit as the external-deps state.

Alternatively, any external-deps may be packaged from a local git repository
(in its checked out state) by setting the appropriate environment variable
from the following:
    SPYDER_SOURCE
    PYTHON_LSP_SERVER_SOURCE
    QDARKSTYLE_SOURCE
    QTCONSOLE_SOURCE
    SPYDER_KERNELS_SOURCE
"""

# Standard library imports
import os
import re
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from datetime import timedelta
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path
from subprocess import check_call
from textwrap import dedent
from time import time

# Third-party imports
from git import Repo, rmtree
from ruamel.yaml import YAML
from setuptools_scm import get_version

fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('BuildCondaPkgs')
logger.addHandler(h)
logger.setLevel('INFO')

HERE = Path(__file__).parent
DIST = HERE / "dist"
RESOURCES = HERE / "resources"
EXTDEPS = HERE.parent / "external-deps"
SPECS = DIST / "specs.yaml"
REQUIREMENTS = HERE.parent / "requirements"
REQ_MAIN = REQUIREMENTS / 'main.yml'
REQ_WINDOWS = REQUIREMENTS / 'windows.yml'
REQ_MAC = REQUIREMENTS / 'macos.yml'
REQ_LINUX = REQUIREMENTS / 'linux.yml'

DIST.mkdir(exist_ok=True)

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
yamlj = YAML(typ='jinja2')
yamlj.indent(mapping=2, sequence=4, offset=2)


class BuildCondaPkg:
    name = None
    source = None
    feedstock = None
    shallow_ver = None

    def __init__(self, data={}, debug=False):
        self.logger = getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.addHandler(h)
        self.logger.setLevel('INFO')

        self.debug = debug

        self._bld_src = DIST / self.name
        self._fdstk_path = DIST / self.feedstock.split("/")[-1]

        self._get_source()
        self._get_version()

        self.data = {'version': self.version}
        self.data.update(data)

        self.yaml = None

        self._patched_meta = False
        self._patched_build = False

    def _get_source(self):
        self._build_cleanup()

        # Determine source and commit
        if self.source is not None:
            remote = self.source
            commit = 'HEAD'
        else:
            cfg = ConfigParser()
            cfg.read(EXTDEPS / self.name / '.gitrepo')
            remote = cfg['subrepo']['remote']
            commit = cfg['subrepo']['commit']

        # Clone from source
        repo = Repo.clone_from(remote, to_path=self._bld_src,
                               shallow_exclude=self.shallow_ver)
        repo.git.checkout(commit)

        # Clone feedstock
        self.logger.info("Cloning feedstock...")
        Repo.clone_from(self.feedstock, to_path=self._fdstk_path)

    def _build_cleanup(self):
        """Remove cloned source and feedstock repositories"""
        for src in [self._bld_src, self._fdstk_path]:
            if src.exists():
                logger.info(f"Removing {src}...")
                rmtree(src)

    def _get_version(self):
        self.version = get_version(self._bld_src).split('+')[0]

    def _patch_meta(self):
        pass

    def patch_meta(self):
        if self._patched_meta:
            return

        self.logger.info("Patching 'meta.yaml'...")

        file = self._fdstk_path / "recipe" / "meta.yaml"
        text = file.read_text()
        for k, v in self.data.items():
            text = re.sub(f".*set {k} =.*", f'{{% set {k} = "{v}" %}}', text)

        self.yaml = yamlj.load(text)

        self.yaml['source'] = {'path': str(self._bld_src)}

        self.yaml.pop('test', None)
        if 'outputs' in self.yaml:
            for out in self.yaml['outputs']:
                out.pop('test', None)

        self._patch_meta()

        yamlj.dump_all([self.yaml], file)

        self.logger.info(f"Patched 'meta.yaml' contents:\n{file.read_text()}")

        self._patched_meta = True

    def _patch_build(self):
        pass

    def patch_build(self):
        if self._patched_build:
            return

        self.logger.info("Patching build script...")
        self._patch_build()
        self._patched_build = True

    def build(self):
        t0 = time()
        try:
            self.patch_meta()
            self.patch_build()

            self.logger.info("Building conda package "
                             f"{self.name}={self.version}...")
            check_call(
                ["mamba", "mambabuild", str(self._fdstk_path / "recipe")]
            )
        finally:
            self._patched_meta = False
            self._patched_build = False
            if self.debug:
                self.logger.info("Keeping cloned source and feedstock")
            else:
                self._build_cleanup()

            elapse = timedelta(seconds=int(time() - t0))
            self.logger.info(f"Build time = {elapse}")


class SpyderCondaPkg(BuildCondaPkg):
    name = "spyder"
    source = os.environ.get('SPYDER_SOURCE', HERE.parent)
    feedstock = "https://github.com/conda-forge/spyder-feedstock"
    shallow_ver = "v5.3.2"

    def _patch_meta(self):
        self.yaml['build'].pop('osx_is_app', None)
        self.yaml.pop('app', None)

        current_requirements = ['python']
        current_requirements += yaml.load(
            REQ_MAIN.read_text())['dependencies']
        if os.name == 'nt':
            win_requirements =  yaml.load(
                REQ_WINDOWS.read_text())['dependencies']
            current_requirements += win_requirements
            current_requirements.append('ptyprocess >=0.5')
        elif sys.platform == 'darwin':
            mac_requirements =  yaml.load(
                REQ_MAC.read_text())['dependencies']
            current_requirements += mac_requirements
        else:
            linux_requirements = yaml.load(
                REQ_LINUX.read_text())['dependencies']
            current_requirements += linux_requirements
        self.yaml['requirements']['run'] = current_requirements

        patches = self.yaml['source'].get('patches', [])
        patches.append(str(RESOURCES / "installers-conda.patch"))
        self.yaml['source']['patches'] = patches

    def _patch_build(self):
        if os.name == 'posix':
            file = self._fdstk_path / "recipe" / "build.sh"
            build_patch = RESOURCES / "build-patch.sh"
            text = file.read_text()
            text += build_patch.read_text()
            file.write_text(text)
        if os.name == 'nt':
            file = self._fdstk_path / "recipe" / "bld.bat"
            text = file.read_text()
            text = text.replace(
                r"copy %RECIPE_DIR%\menu-windows.json %MENU_DIR%\spyder_shortcut.json",
                r"""powershell -Command"""
                r""" "(gc %SRC_DIR%\installers-conda\resources\spyder-menu.json)"""
                r""" -replace '__PKG_VERSION__', '%PKG_VERSION%' | """
                r"""Out-File -encoding ASCII %MENU_DIR%\spyder-menu.json" """
            )
            file.write_text(text)


class PylspCondaPkg(BuildCondaPkg):
    name = "python-lsp-server"
    source = os.environ.get('PYTHON_LSP_SERVER_SOURCE')
    feedstock = "https://github.com/conda-forge/python-lsp-server-feedstock"
    shallow_ver = "v1.4.1"


class QdarkstyleCondaPkg(BuildCondaPkg):
    name = "qdarkstyle"
    source = os.environ.get('QDARKSTYLE_SOURCE')
    feedstock = "https://github.com/conda-forge/qdarkstyle-feedstock"
    shallow_ver = "v3.0.2"


class QtconsoleCondaPkg(BuildCondaPkg):
    name = "qtconsole"
    source = os.environ.get('QTCONSOLE_SOURCE')
    feedstock = "https://github.com/conda-forge/qtconsole-feedstock"
    shallow_ver = "5.3.1"


class SpyderKernelsCondaPkg(BuildCondaPkg):
    name = "spyder-kernels"
    source = os.environ.get('SPYDER_KERNELS_SOURCE')
    feedstock = "https://github.com/conda-forge/spyder-kernels-feedstock"
    shallow_ver = "v2.3.1"


PKGS = {
    SpyderCondaPkg.name: SpyderCondaPkg,
    PylspCondaPkg.name: PylspCondaPkg,
    QdarkstyleCondaPkg.name: QdarkstyleCondaPkg,
    QtconsoleCondaPkg.name: QtconsoleCondaPkg,
    SpyderKernelsCondaPkg.name: SpyderKernelsCondaPkg
}

if __name__ == "__main__":
    p = ArgumentParser(
        description=dedent(
            """
            Build conda packages from local Spyder and external-deps sources.
            Alternative git repo for python-lsp-server may be provided by
            setting the environment variable PYTHON_LSP_SERVER_SOURCE,
            otherwise the upstream remote will be used. All other external-deps
            use the subrepo source within the Spyder repo.
            """
        ),
        usage="python build_conda_pkgs.py "
              "[--build BUILD [BUILD] ...] [--debug]",
    )
    p.add_argument(
        '--debug', action='store_true', default=False,
        help="Do not remove cloned sources and feedstocks"
    )
    p.add_argument(
        '--build', nargs="+", default=PKGS.keys(),
        help=("Space-separated list of packages to build. "
              f"Default is {list(PKGS.keys())}")
    )
    args = p.parse_args()

    logger.info(f"Building local conda packages {list(args.build)}...")
    t0 = time()

    for k in args.build:
        if SPECS.exists():
            specs = yaml.load(SPECS.read_text())
        else:
            specs = {k: "" for k in PKGS}

        pkg = PKGS[k](debug=args.debug)
        pkg.build()
        specs[k] = "=" + pkg.version

        yaml.dump(specs, SPECS)

    elapse = timedelta(seconds=int(time() - t0))
    logger.info(f"Total build time = {elapse}")
