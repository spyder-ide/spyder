"""
Build local conda packages
"""

import re
from textwrap import dedent
from argparse import ArgumentParser
from shutil import rmtree
from pathlib import Path
from ruamel.yaml import YAML
from subprocess import check_call
from importlib.util import spec_from_file_location, module_from_spec
from logging import Formatter, StreamHandler, getLogger
from datetime import timedelta
from time import time

fmt = Formatter('%(asctime)s [%(levelname)s] [%(name)s] -> %(message)s')
h = StreamHandler()
h.setFormatter(fmt)
logger = getLogger('BuildCondaPkgs')
logger.addHandler(h)
logger.setLevel('INFO')

HERE = Path(__file__).parent
EXTDEPS = HERE.parent / "external-deps"


class BuildCondaPkg():
    src_path = None
    feedstock = None
    ver_path = None

    def __init__(self, data={}, debug=False):
        # ---- Setup logger
        self.logger = getLogger(self.__class__.__name__)
        if not self.logger.handlers:
            self.logger.addHandler(h)
        self.logger.setLevel('INFO')

        self.debug = debug

        self.data = {'version': self._get_version()}
        self.data.update(data)

        self.fdstk_path = HERE / self.feedstock.split("/")[-1]

        self._yaml = YAML(typ='jinja2')
        self._yaml.indent(mapping=2, sequence=4, offset=2)
        self.yaml = None

        self._patched_meta = False
        self._patched_build = False

    def _get_version(self):
        spec = spec_from_file_location(self.ver_path.parent.name,
                                       self.ver_path)
        mod = module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod.__version__

    def _git_init_src_path(self):
        if (self.src_path / ".git").exists():
            rmtree(self.src_path / ".git", ignore_errors=True)

        self.logger.info(f"Initializing git repo at {self.src_path}...")
        check_call(["git", "init", "-q", str(self.src_path)])
        check_call(["git", "-C", str(self.src_path), "add", "-A"])
        check_call(["git", "-C", str(self.src_path), "commit", "-qm", "build"])

    def _git_clean_src_path(self):
        git_path = self.src_path / ".git"
        self.logger.info(f"Removing {git_path}...")
        rmtree(git_path, ignore_errors=True)

    def _clone_feedstock(self):
        if self.fdstk_path.exists():
            self.logger.info(f"Removing existing {self.fdstk_path}...")
            rmtree(self.fdstk_path, ignore_errors=True)

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

        patches = self.yaml["source"].pop("patches", None)
        self.yaml['source'] = {'path': str(self.src_path)}
        if patches:
            self.yaml['source']['patches'] = patches

        self.yaml.pop('test', None)

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
            self._git_init_src_path()
            self._clone_feedstock()
            self.patch_meta()
            self.patch_build()

            self.logger.info("Building conda package...")
            check_call(
                ["mamba", "mambabuild", str(self.fdstk_path / "recipe")]
            )

        finally:
            self._patched_meta = False
            self._patched_build = False
            if not self.debug:
                self.logger.info(f"Removing {self.fdstk_path}...")
                rmtree(self.fdstk_path, ignore_errors=True)

            self._git_clean_src_path()

            elapse = timedelta(seconds=int(time() - t0))
            self.logger.info(f"Build time = {elapse}")


class SpyderCondaPkg(BuildCondaPkg):
    src_path = HERE.parent
    feedstock = "https://github.com/conda-forge/spyder-feedstock"
    ver_path = src_path / "spyder" / "__init__.py"

    def _git_init_src_path(self):
        # Do not initialize repo
        pass

    def _git_clean_src_path(self):
        # Do not remove .git
        pass

    def _patch_meta(self):
        self.yaml['build'].pop('osx_is_app', None)
        self.yaml.pop('app', None)

        patches = self.yaml['source'].get('patches', [])
        patches.append("../../installers-conda.patch")
        self.yaml['source']['patches'] = patches

    def _patch_build(self):
        file = self.fdstk_path / "recipe" / "build.sh"
        text = file.read_text()
        text += dedent(
            """
            mkdir -p "${PREFIX}/Menu"
            sed "s/__PKG_VERSION__/${PKG_VERSION}/" "${SRC_DIR}/installers-conda/menuinst_config.json" > "${PREFIX}/Menu/spyder-menu.json"
            cp "${SRC_DIR}/img_src/spyder.png" "${PREFIX}/Menu/spyder.png"
            cp "${SRC_DIR}/img_src/spyder.icns" "${PREFIX}/Menu/spyder.icns"
            cp "${SRC_DIR}/img_src/spyder.ico" "${PREFIX}/Menu/spyder.ico"

            """
        )

        file.write_text(text)


class PylspCondaPkg(BuildCondaPkg):
    src_path = EXTDEPS / "python-lsp-server"
    feedstock = "https://github.com/conda-forge/python-lsp-server-feedstock"
    ver_path = src_path / "pylsp" / "_version.py"


class QdarkstyleCondaPkg(BuildCondaPkg):
    src_path = EXTDEPS / "qdarkstyle"
    feedstock = "https://github.com/conda-forge/qdarkstyle-feedstock"
    ver_path = src_path / "qdarkstyle" / "__init__.py"

    def _get_version(self):
        text = self.ver_path.read_text()
        return re.search('__version__ = "(.*)"', text).group(1)


class QtconsoleCondaPkg(BuildCondaPkg):
    src_path = EXTDEPS / "qtconsole"
    feedstock = "https://github.com/conda-forge/qtconsole-feedstock"
    ver_path = src_path / "qtconsole" / "_version.py"

    def _patch_meta(self):
        for out in self.yaml['outputs']:
            out.pop("test", None)


class SpyderKernelsCondaPkg(BuildCondaPkg):
    src_path = EXTDEPS / "spyder-kernels"
    feedstock = "https://github.com/conda-forge/spyder-kernels-feedstock"
    ver_path = src_path / "spyder_kernels" / "_version.py"


if __name__ == "__main__":
    p = ArgumentParser(
        usage="python build_conda_pkgs.py [--skip-external-deps] [--debug]",
        epilog=dedent(
            """
            Build conda packages from local spyder and external-deps sources.
            """
        )
    )
    p.add_argument('--skip-external-deps', action='store_true', default=False,
                   help="Do not build conda packages for external-deps.")
    p.add_argument('--debug', action='store_true', default=False,
                   help="Do not remove cloned feedstocks")
    args = p.parse_args()

    logger.info("Building local conda packages...")
    t0 = time()

    SpyderCondaPkg(debug=args.debug).build()

    if not args.skip_external_deps:
        PylspCondaPkg(debug=args.debug).build()
        QdarkstyleCondaPkg(debug=args.debug).build()
        QtconsoleCondaPkg(debug=args.debug).build()
        SpyderKernelsCondaPkg(debug=args.debug).build()

    elapse = timedelta(seconds=int(time() - t0))
    logger.info(f"Total build time = {elapse}")
