# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os
import re
import sys
from argparse import ArgumentParser, RawTextHelpFormatter
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
BUILD = HERE / "build"
RESOURCES = HERE / "resources"
EXTDEPS = HERE.parent / "external-deps"
SPECS = BUILD / "specs.yaml"
REQUIREMENTS = HERE.parent / "requirements"
REQ_MAIN = REQUIREMENTS / 'main.yml'
REQ_WINDOWS = REQUIREMENTS / 'windows.yml'
REQ_MAC = REQUIREMENTS / 'macos.yml'
REQ_LINUX = REQUIREMENTS / 'linux.yml'

BUILD.mkdir(exist_ok=True)
SPYPATCHFILE = BUILD / "installers-conda.patch"


class BuildCondaPkg:
    """Base class for building a conda package for conda-based installer"""
    name = None
    norm = True
    source = None
    feedstock = None
    feedstock_branch = None
    shallow_ver = None

    def __init__(self, data={}, debug=False, shallow=False):
        self.logger = getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.addHandler(h)
        self.logger.setLevel('INFO')

        self.debug = debug

        self._bld_src = BUILD / self.name
        self._fdstk_path = BUILD / self.feedstock.split("/")[-1]

        self._get_source(shallow=shallow)
        self._get_version()

        self.data = {'version': self.version}
        self.data.update(data)

        self._patch_source()

        self._recipe_patched = False

    def _get_source(self, shallow=False):
        """Clone source and feedstock to distribution directory for building"""
        self._build_cleanup()

        if self.source == HERE.parent:
            self._bld_src = self.source
            self.repo = Repo(self.source)
        else:
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
            kwargs = dict(to_path=self._bld_src)
            if shallow:
                kwargs.update(shallow_exclude=self.shallow_ver)
                self.logger.info(
                    f"Cloning source shallow from tag {self.shallow_ver}...")
            else:
                self.logger.info("Cloning source...")
            self.repo = Repo.clone_from(remote, **kwargs)
            self.repo.git.checkout(commit)

        # Clone feedstock
        self.logger.info("Cloning feedstock...")
        kwargs = dict(to_path=self._fdstk_path)
        if self.feedstock_branch:
            kwargs.update(branch=self.feedstock_branch)
        Repo.clone_from(self.feedstock, **kwargs)

    def _build_cleanup(self):
        """Remove cloned source and feedstock repositories"""
        for src in [self._bld_src, self._fdstk_path]:
            if src.exists() and src != HERE.parent:
                logger.info(f"Removing {src}...")
                rmtree(src)

    def _get_version(self):
        """Get source version using setuptools_scm"""
        v = get_version(self._bld_src, normalize=self.norm)
        self.version = v.lstrip('v').split('+')[0]

    def _patch_source(self):
        pass

    def _patch_meta(self, meta):
        return meta

    def patch_recipe(self):
        """
        Patch conda build recipe

        1. Patch meta.yaml
        2. Patch build script
        """
        if self._recipe_patched:
            return

        self.logger.info("Patching 'meta.yaml'...")

        file = self._fdstk_path / "recipe" / "meta.yaml"
        meta = file.read_text()

        # Replace jinja variable values
        for k, v in self.data.items():
            meta = re.sub(f".*set {k} =.*", f'{{% set {k} = "{v}" %}}', meta)

        # Replace source, but keep patches
        meta = re.sub(r'^(source:\n)(  (url|sha256):.*\n)*',
                      rf'\g<1>  path: {self._bld_src.as_posix()}\n',
                      meta, flags=re.MULTILINE)

        meta = self._patch_meta(meta)

        file.rename(file.parent / ("_" + file.name))  # keep copy of original
        file.write_text(meta)

        self.logger.info(f"Patched 'meta.yaml' contents:\n{file.read_text()}")

        self._recipe_patched = True

    def build(self):
        """
        Build the conda package.

        1. Patch the recipe
        2. Build the package
        3. Remove cloned repositories
        """
        t0 = time()
        try:
            self.patch_recipe()

            self.logger.info("Building conda package "
                             f"{self.name}={self.version}...")
            check_call([
                "conda", "mambabuild",
                "--no-test", "--skip-existing", "--build-id-pat={n}",
                str(self._fdstk_path / "recipe")
            ])
        finally:
            self._recipe_patched = False
            if self.debug:
                self.logger.info("Keeping cloned source and feedstock")
            else:
                self._build_cleanup()

            elapse = timedelta(seconds=int(time() - t0))
            self.logger.info(f"Build time = {elapse}")


class SpyderCondaPkg(BuildCondaPkg):
    name = "spyder"
    norm = False
    source = os.environ.get('SPYDER_SOURCE', HERE.parent)
    feedstock = "https://github.com/conda-forge/spyder-feedstock"
    feedstock_branch = "dev"
    shallow_ver = "v5.3.2"

    def _patch_source(self):
        self.logger.info("Patching Spyder source...")
        file = self._bld_src / "spyder/__init__.py"
        file_text = file.read_text()
        ver_str = tuple(self.version.split('.'))
        file_text = re.sub(
            r'^(version_info = ).*',
            rf'\g<1>{ver_str}',
            file_text,
            flags=re.MULTILINE
        )
        file.write_text(file_text)

        self.repo.git.diff(
            output=(self._fdstk_path / "recipe" / "version.patch").as_posix()
        )
        self.repo.git.stash()

    def _patch_meta(self, meta):
        # Get current Spyder requirements
        yaml = YAML()
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
            if 'python.app' in mac_requirements:
                mac_requirements.remove('python.app')
            current_requirements += mac_requirements
        else:
            linux_requirements = yaml.load(
                REQ_LINUX.read_text())['dependencies']
            current_requirements += linux_requirements

        # Replace run requirements
        cr_string = '\n    - '.join(current_requirements)
        meta = re.sub(r'^(requirements:\n(.*\n)+  run:\n)(    .*\n)+',
                      rf'\g<1>    - {cr_string}\n', meta, flags=re.MULTILINE)

        # Add version patch
        meta = re.sub(r'^(source:\n(.*\n)*  patches:\n)',
                      r'\g<1>    - version.patch\n',
                      meta, flags=re.MULTILINE)
        return meta


class PylspCondaPkg(BuildCondaPkg):
    name = "python-lsp-server"
    source = os.environ.get('PYTHON_LSP_SERVER_SOURCE')
    feedstock = "https://github.com/conda-forge/python-lsp-server-feedstock"
    feedstock_branch = "main"
    shallow_ver = "v1.4.1"


class QtconsoleCondaPkg(BuildCondaPkg):
    name = "qtconsole"
    source = os.environ.get('QTCONSOLE_SOURCE')
    feedstock = "https://github.com/conda-forge/qtconsole-feedstock"
    feedstock_branch = "main"
    shallow_ver = "5.3.1"


class SpyderKernelsCondaPkg(BuildCondaPkg):
    name = "spyder-kernels"
    source = os.environ.get('SPYDER_KERNELS_SOURCE')
    feedstock = "https://github.com/conda-forge/spyder-kernels-feedstock"
    feedstock_branch = "rc"
    shallow_ver = "v2.3.1"


PKGS = {
    SpyderCondaPkg.name: SpyderCondaPkg,
    PylspCondaPkg.name: PylspCondaPkg,
    QtconsoleCondaPkg.name: QtconsoleCondaPkg,
    SpyderKernelsCondaPkg.name: SpyderKernelsCondaPkg
}

if __name__ == "__main__":
    p = ArgumentParser(
        description=dedent(
            """
            Build conda packages to local channel.

            This module builds conda packages for Spyder and external-deps for
            inclusion in the conda-based installer. The following classes are
            provided for each package:
                SpyderCondaPkg
                PylspCondaPkg
                QdarkstyleCondaPkg
                QtconsoleCondaPkg
                SpyderKernelsCondaPkg

            Spyder will be packaged from this repository (in its checked-out
            state). qtconsole, spyder-kernels, and python-lsp-server will be
            packaged from the remote and commit specified in their respective
            .gitrepo files in external-deps.

            Alternatively, any external-deps may be packaged from an arbitrary
            git repository (in its checked out state) by setting the
            appropriate environment variable from the following:
                SPYDER_SOURCE
                PYTHON_LSP_SERVER_SOURCE
                QDARKSTYLE_SOURCE
                QTCONSOLE_SOURCE
                SPYDER_KERNELS_SOURCE
            """
        ),
        usage="python build_conda_pkgs.py "
              "[--build BUILD [BUILD] ...] [--debug] [--shallow]",
        formatter_class=RawTextHelpFormatter
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
    p.add_argument(
        '--shallow', action='store_true', default=False,
        help="Perform shallow clone for build")
    args = p.parse_args()

    logger.info(f"Building local conda packages {list(args.build)}...")
    t0 = time()

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

    if SPECS.exists():
        specs = yaml.load(SPECS.read_text())
    else:
        specs = {k: "" for k in PKGS}

    for k in args.build:
        pkg = PKGS[k](debug=args.debug, shallow=args.shallow)
        pkg.build()
        specs[k] = "=" + pkg.version

    yaml.dump(specs, SPECS)

    elapse = timedelta(seconds=int(time() - t0))
    logger.info(f"Total build time = {elapse}")
