"""
Build conda packages to local channel.

This module builds conda packages for spyder and external-deps for
inclusion in the conda-based installer. The Following classes are
provided for each package:
    SpyderCondaPkg
    PylspCondaPkg
    QdarkstyleCondaPkg
    QtconsoleCondaPkg
    SpyderKernelsCondaPkg

spyder will be packaged from this repository (in its checked-out state).
qdarkstyle, qtconsole, and spyder-kernels will be packaged from the
external-deps directory of this repository (in its checked-out state).
python-lsp-server, however, will be packaged from the upstream remote
at the same commit as the external-deps state.

Alternatively, any external-deps may be packaged from a local git repository
(in its checked out state) by setting the appropriate environment variable
from the following:
    PYTHON_LSP_SERVER_SOURCE
    QDARKSTYLE_SOURCE
    QTCONSOLE_SOURCE
    SPYDER_KERNELS_SOURCE
"""
import os
import re
from argparse import ArgumentParser
from configparser import ConfigParser
from datetime import timedelta
from git import Repo
from logging import Formatter, StreamHandler, getLogger
from pathlib import Path
from ruamel.yaml import YAML
from setuptools_scm import get_version
from shutil import rmtree
from subprocess import check_call
from textwrap import dedent
from time import time

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

DIST.mkdir(exist_ok=True)


def remove_readonly(func, path, exc):
    """
    Change readonly status of file.
    Windows file systems may require this if rmdir fails
    """
    import errno, stat
    excvalue = exc[1]
    if func in (os.rmdir, os.remove, os.unlink) and excvalue.errno == errno.EACCES:
        os.chmod(path, stat.S_IRWXU| stat.S_IRWXG| stat.S_IRWXO) # 0777
        func(path)
    else:
        raise


class BuildCondaPkg():
    name = None
    src_path = None
    feedstock = None
    shallow_ver = None

    _yaml = YAML(typ='jinja2')
    _yaml.indent(mapping=2, sequence=4, offset=2)

    def __init__(self, data={}, debug=False):
        # ---- Setup logger
        self.logger = getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.addHandler(h)
        self.logger.setLevel('INFO')

        self.debug = debug

        self._get_source()
        self._get_version()

        self.data = {'version': self.version}
        self.data.update(data)

        self.fdstk_path = HERE / self.feedstock.split("/")[-1]

        self.yaml = None

        self._patched_meta = False
        self._patched_build = False

    def _get_source(self):
        self._build_cleanup()  # Remove existing if HERE

        if not self.src_path.exists():
            cfg = ConfigParser()
            cfg.read(EXTDEPS / self.name / '.gitrepo')
            # Clone from remote
            repo = Repo.clone_from(
                cfg['subrepo']['remote'],
                to_path=self.src_path, shallow_exclude=self.shallow_ver
            )
            repo.git.checkout(cfg['subrepo']['commit'])

    def _build_cleanup(self):
        if self.src_path.exists() and self.src_path == HERE / self.name:
            logger.info(f"Removing {self.src_path}...")
            rmtree(self.src_path, onerror=remove_readonly)

    def _get_version(self):
        self.version = get_version(self.src_path).split('+')[0]

    def _clone_feedstock(self):
        if self.fdstk_path.exists():
            self.logger.info(f"Removing existing {self.fdstk_path}...")
            rmtree(self.fdstk_path, onerror=remove_readonly)

        self.logger.info(f"Cloning feedstock to {self.fdstk_path}...")
        check_call(["git", "clone", str(self.feedstock), str(self.fdstk_path)])

    def _patch_meta(self):
        pass

    def patch_meta(self):
        if self._patched_meta:
            return

        self.logger.info("Patching 'meta.yaml'...")

        file = self.fdstk_path / "recipe" / "meta.yaml"
        text = file.read_text()
        for k, v in self.data.items():
            text = re.sub(f".*set {k} =.*", f'{{% set {k} = "{v}" %}}', text)

        self.yaml = self._yaml.load(text)

        self.yaml['source'] = {'path': str(self.src_path)}

        self.yaml.pop('test', None)
        if 'outputs' in self.yaml:
            for out in self.yaml['outputs']:
                out.pop('test', None)

        self._patch_meta()

        self._yaml.dump_all([self.yaml], file)

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
            # self._git_init_src_path()
            self._clone_feedstock()
            self.patch_meta()
            self.patch_build()

            self.logger.info("Building conda package "
                             f"{self.name}={self.version}...")
            check_call(
                ["mamba", "mambabuild", str(self.fdstk_path / "recipe")]
            )

        finally:
            self._patched_meta = False
            self._patched_build = False
            if not self.debug:
                self.logger.info(f"Removing {self.fdstk_path}...")
                rmtree(self.fdstk_path, onerror=remove_readonly)

            self._build_cleanup()

            elapse = timedelta(seconds=int(time() - t0))
            self.logger.info(f"Build time = {elapse}")


class SpyderCondaPkg(BuildCondaPkg):
    name = "spyder"
    src_path = HERE.parent
    feedstock = "https://github.com/conda-forge/spyder-feedstock"
    shallow_ver = "v5.3.2"

    def _patch_meta(self):
        self.yaml['build'].pop('osx_is_app', None)
        self.yaml.pop('app', None)

        patches = self.yaml['source'].get('patches', [])
        patches.append(str(RESOURCES / "installers-conda.patch"))
        self.yaml['source']['patches'] = patches

    def _patch_build(self):
        if os.name == 'posix':
            file = self.fdstk_path / "recipe" / "build.sh"
            build_patch = RESOURCES / "build-patch.sh"
            text = file.read_text()
            text += build_patch.read_text()
            file.write_text(text)
        if os.name == 'nt':
            file = self.fdstk_path / "recipe" / "bld.bat"
            text = file.read_text()
            text = text.replace(
                r"copy %RECIPE_DIR%\menu-windows.json %MENU_DIR%\spyder_shortcut.json",
                """powershell -Command"""
                r""" "(gc %SRC_DIR%\installers-conda\resources\spyder-menu.json)"""
                r""" -replace '__PKG_VERSION__', '%PKG_VERSION%' | """
                r"""Out-File -encoding ASCII %MENU_DIR%\spyder-menu.json" """
            )
            file.write_text(text)

class PylspCondaPkg(BuildCondaPkg):
    name = "python-lsp-server"
    src_path = Path(
        os.environ.get('PYTHON_LSP_SERVER_SOURCE', HERE / name)
    )
    feedstock = "https://github.com/conda-forge/python-lsp-server-feedstock"
    shallow_ver = "v1.4.1"


class QdarkstyleCondaPkg(BuildCondaPkg):
    name = "qdarkstyle"
    src_path = Path(
        os.environ.get('QDARKSTYLE_SOURCE', HERE / name)
    )
    feedstock = "https://github.com/conda-forge/qdarkstyle-feedstock"
    shallow_ver = "v3.0.2"


class QtconsoleCondaPkg(BuildCondaPkg):
    name = "qtconsole"
    src_path = Path(
        os.environ.get('QTCONSOLE_SOURCE', HERE / name)
    )
    feedstock = "https://github.com/conda-forge/qtconsole-feedstock"
    shallow_ver = "5.3.1"

    def _patch_meta(self):
        for out in self.yaml['outputs']:
            out.pop("test", None)


class SpyderKernelsCondaPkg(BuildCondaPkg):
    name = "spyder-kernels"
    src_path = Path(
        os.environ.get('SPYDER_KERNELS_SOURCE', HERE / name)
    )
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
            Build conda packages from local spyder and external-deps sources.
            Alternative git repo for python-lsp-server may be provided by
            setting the environment variable PYTHON_LSP_SERVER_SOURCE,
            otherwise the upstream remote will be used. All other external-deps
            use the subrepo source within the spyder repo.
            """
        ),
        usage="python build_conda_pkgs.py "
              "[--build BUILD [BUILD] ...] [--debug]",
    )
    p.add_argument(
        '--debug', action='store_true', default=False,
        help="Do not remove cloned feedstocks"
    )
    p.add_argument(
        '--build', nargs="+", default=PKGS.keys(),
        help=("Space-separated list of packages to build. "
              f"Default is {list(PKGS.keys())}")
    )
    args = p.parse_args()

    logger.info(f"Building local conda packages {list(args.build)}...")
    t0 = time()

    yaml = YAML()
    yaml.indent(mapping=2, sequence=4, offset=2)

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
