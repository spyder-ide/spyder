# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

# Standard library imports
import os
import re
import sys
from argparse import ArgumentParser
from configparser import ConfigParser
from datetime import timedelta
from subprocess import check_call
from textwrap import dedent
from time import time

# Third-party imports
from git import Repo, rmtree
from ruamel.yaml import YAML
from setuptools_scm import get_version

# Local imports
from utils import logger as logger, HERE, BUILD, DocFormatter

EXTDEPS = HERE.parent / "external-deps"
REQUIREMENTS = HERE.parent / "requirements"
REQ_MAIN = REQUIREMENTS / 'main.yml'
REQ_WINDOWS = REQUIREMENTS / 'windows.yml'
REQ_MAC = REQUIREMENTS / 'macos.yml'
REQ_LINUX = REQUIREMENTS / 'linux.yml'

SPYPATCHFILE = BUILD / "installers-conda.patch"
PARENT_BRANCH = os.getenv("MATRIX_BRANCH", os.getenv("GITHUB_BASE_REF"))


yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)


class BuildCondaPkg:
    """Base class for building a conda package for conda-based installer"""
    name = None
    norm = True
    source = None
    feedstock = None
    feedstock_branch = None

    def __init__(self, data=None, debug=False):
        data = {} if data is None else data
        self.logger = logger.getChild(self.__class__.__name__)

        self.debug = debug

        self._bld_src = BUILD / self.name
        self._fdstk_path = BUILD / self.feedstock.split("/")[-1]
        self._patchfile = self._fdstk_path / "recipe" / "version.patch"

        self._get_source()
        self._get_version()

        self.data = {'version': self.version}
        self.data.update(data)

        self.recipe_append = {}
        self.recipe_clobber = {}

        self._recipe_patched = False

    def _get_source(self):
        """Clone source and feedstock for building"""
        BUILD.mkdir(exist_ok=True)
        self._cleanup_build()

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
            self.logger.info("Cloning source...")
            self.repo = Repo.clone_from(remote, **kwargs)
            self.repo.git.checkout(commit)

        # Clone feedstock
        self.logger.info("Cloning feedstock...")
        kwargs = dict(to_path=self._fdstk_path)
        if self.feedstock_branch:
            kwargs.update(branch=self.feedstock_branch)
        feedstock_repo = Repo.clone_from(self.feedstock, **kwargs)
        self.logger.info(
            f"Feedstock branch: {feedstock_repo.active_branch.name}"
        )

    def _cleanup_build(self, debug=False):
        """Remove cloned source and feedstock repositories"""
        if debug:
            self.logger.info("Keeping cloned source and feedstock")
            return

        for src in [self._bld_src, self._fdstk_path]:
            if src.exists() and src != HERE.parent:
                self.logger.info(f"Removing {src}...")
                rmtree(src)

    def _get_version(self):
        """Get source version using setuptools_scm"""
        v = get_version(self._bld_src, normalize=self.norm)
        self.version = v.lstrip('v').split('+')[0]

    def _patch_source(self):
        pass

    def _patch_conda_build_config(self):
        file = self._fdstk_path / "recipe" / "conda_build_config.yaml"
        if not file.exists():
            return

        contents = yaml.load(file.read_text())
        file.rename(file.parent / ("_" + file.name))  # copy of original

        pyver = sys.version_info
        contents['python'] = [f"{pyver.major}.{pyver.minor}.* *_cpython"]
        yaml.dump(contents, file)

        self.logger.info(
            f"Patched 'conda_build_config.yaml' contents:\n{file.read_text()}"
        )

    def _patch_meta(self):
        file = self._fdstk_path / "recipe" / "meta.yaml"
        meta = file.read_text()

        # Replace jinja variable values
        for k, v in self.data.items():
            meta = re.sub(f".*set {k} =.*", f'{{% set {k} = "{v}" %}}', meta)

        # Remove temporary patches
        meta = re.sub(r"^\s*- temp-.+\.patch\n", "", meta, flags=re.MULTILINE)

        file.rename(file.parent / ("_" + file.name))  # keep copy of original
        file.write_text(meta)

        self.logger.info(f"Patched 'meta.yaml' contents:\n{file.read_text()}")

    def _add_recipe_append(self):
        if self._patchfile.exists():
            self.recipe_append.update(
                {"source": {"patches": [self._patchfile.name]}}
            )

        if self.recipe_append:
            file = self._fdstk_path / "recipe" / "recipe_append.yaml"
            yaml.dump(self.recipe_append, file)
            self.logger.info(
                f"'recipe_append.yaml' contents:\n{file.read_text()}"
            )
        else:
            self.logger.info("Skipping 'recipe_append.yaml'.")

    def _add_recipe_clobber(self):
        self.recipe_clobber.update({
            "source": {
                "url": None,
                "sha256": None,
                "path": self._bld_src.as_posix()},
        })

        if self.recipe_clobber:
            file = self._fdstk_path / "recipe" / "recipe_clobber.yaml"
            yaml.dump(self.recipe_clobber, file)
            self.logger.info(
                f"'recipe_clobber.yaml' contents:\n{file.read_text()}"
            )
        else:
            self.logger.info("Skipping 'recipe_clobber.yaml'.")

    def patch_recipe(self):
        """
        Patch conda build recipe

        1. Patch conda_build_config.yaml
        2. Patch meta.yaml
        3. Add recipe_append.yaml
        4. Add recipe_clobber.yaml
        """
        if self._recipe_patched:
            return

        self._patch_conda_build_config()
        self._patch_meta()
        self._add_recipe_append()
        self._add_recipe_clobber()

        self._recipe_patched = True

    def build(self):
        """
        Build the conda package.

        1. Patch source
        2. Patch the recipe
        3. Build the package
        4. Remove cloned repositories
        """
        t0 = time()
        try:
            self._patch_source()
            self.patch_recipe()

            self.logger.info("Building conda package "
                             f"{self.name}={self.version}...")
            check_call([
                "conda", "build",
                "--skip-existing", "--build-id-pat={n}",
                "--no-test", "--no-anaconda-upload",
                str(self._fdstk_path / "recipe")
            ])
        finally:
            self._recipe_patched = False
            self._cleanup_build(self.debug)

            elapse = timedelta(seconds=int(time() - t0))
            self.logger.info(f"Build time = {elapse}")


class SpyderCondaPkg(BuildCondaPkg):
    name = "spyder"
    norm = False
    source = os.environ.get('SPYDER_SOURCE', HERE.parent)
    feedstock = "https://github.com/conda-forge/spyder-feedstock"

    feedstock_branch = "dev"  # Default branch, or if Spyder branch is master
    if PARENT_BRANCH == "6.x":
        feedstock_branch = "main"

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

        # Only write patch if necessary
        if self.repo.git.diff():
            self.logger.info(f"Creating {self._patchfile.name}...")
            self.repo.git.diff(output=self._patchfile.as_posix())
            self.repo.git.stash()

    def patch_recipe(self):
        # Get current Spyder requirements
        spyder_base_reqs = ['python']
        spyder_base_reqs += yaml.load(
            REQ_MAIN.read_text())['dependencies']
        if os.name == 'nt':
            win_requirements =  yaml.load(
                REQ_WINDOWS.read_text())['dependencies']
            spyder_base_reqs += win_requirements
            spyder_base_reqs.append('ptyprocess >=0.5')
        elif sys.platform == 'darwin':
            mac_requirements =  yaml.load(
                REQ_MAC.read_text())['dependencies']
            if 'python.app' in mac_requirements:
                mac_requirements.remove('python.app')
            spyder_base_reqs += mac_requirements
            spyder_base_reqs.append('__osx')
        else:
            linux_requirements = yaml.load(
                REQ_LINUX.read_text())['dependencies']
            spyder_base_reqs += linux_requirements
            spyder_base_reqs.append('__linux')

        spyder_reqs = [f"spyder-base =={self.version}"]
        for req in spyder_base_reqs.copy():
            if req.startswith(
                ('pyqt ', 'pyqtwebengine ', 'qtconsole ', 'fcitx-qt5 ')
            ):
                spyder_reqs.append(req)
                spyder_base_reqs.remove(req)

            if req.startswith('qtconsole '):
                spyder_base_reqs.append(
                    req.replace('qtconsole', 'qtconsole-base')
                )

        if sys.platform == "darwin":
            spyder_base_reqs.append("__osx")
        if sys.platform.startswith("linux"):
            spyder_base_reqs.append("__linux")
            spyder_reqs.append("__linux")

        self.recipe_clobber.update({
            "requirements": {"run": spyder_base_reqs},
            # Since outputs is a list, the entire list must be reproduced with
            # the current run requirements
            "outputs": [
                {
                    "name": "spyder-base"
                },
                {
                    "name": "spyder",
                    "build": {"noarch": "python"},
                    "requirements": {"run": spyder_reqs},
                    "test": {
                        "requires": ["pip"],
                        "commands": ["spyder -h", "python -m pip check"],
                        "imports": ["spyder"]
                    }
                }
            ]
        })

        super().patch_recipe()


class PylspCondaPkg(BuildCondaPkg):
    name = "python-lsp-server"
    source = os.environ.get('PYTHON_LSP_SERVER_SOURCE')
    feedstock = "https://github.com/conda-forge/python-lsp-server-feedstock"
    feedstock_branch = "main"


class QtconsoleCondaPkg(BuildCondaPkg):
    name = "qtconsole"
    source = os.environ.get('QTCONSOLE_SOURCE')
    feedstock = "https://github.com/conda-forge/qtconsole-feedstock"
    feedstock_branch = "main"


class SpyderKernelsCondaPkg(BuildCondaPkg):
    name = "spyder-kernels"
    source = os.environ.get('SPYDER_KERNELS_SOURCE')
    feedstock = "https://github.com/conda-forge/spyder-kernels-feedstock"

    feedstock_branch = "dev"  # Default branch, or if Spyder branch is master
    if PARENT_BRANCH == "6.x":
        feedstock_branch = "main"


PKGS = {
    SpyderCondaPkg.name: SpyderCondaPkg,
    PylspCondaPkg.name: PylspCondaPkg,
    QtconsoleCondaPkg.name: QtconsoleCondaPkg,
    SpyderKernelsCondaPkg.name: SpyderKernelsCondaPkg
}

if __name__ == "__main__":
    parser = ArgumentParser(
        description="Build conda packages to local channel.",
        epilog=dedent(
            """
            This module builds conda packages for Spyder and external-deps for
            inclusion in the conda-based installer. The following classes are
            provided for each package:
                SpyderCondaPkg
                PylspCondaPkg
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
                QTCONSOLE_SOURCE
                SPYDER_KERNELS_SOURCE
            """
        ),
        formatter_class=DocFormatter
    )
    parser.add_argument(
        '--build', nargs="+", default=list(PKGS.keys()),
        help="Space-separated list of packages to build."
    )
    parser.add_argument(
        '--debug', action='store_true', default=False,
        help="Do not remove cloned sources and feedstocks"
    )

    args = parser.parse_args()

    logger.info(f"Building local conda packages {list(args.build)}...")
    t0 = time()

    for k in args.build:
        pkg = PKGS[k](debug=args.debug)
        pkg.build()

    elapse = timedelta(seconds=int(time() - t0))
    logger.info(f"Total build time = {elapse}")
