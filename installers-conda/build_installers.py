# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Create Spyder installers using `constructor`.

It creates a `construct.yaml` file with the needed settings
and then runs `constructor`.

Some environment variables we use:

CONSTRUCTOR_TARGET_PLATFORM:
    conda-style platform (as in `platform` in `conda info -a` output)
CONSTRUCTOR_CONDA_EXE:
    when the target platform is not the same as the host, constructor
    needs a path to a conda-standalone (or micromamba) executable for
    that platform. needs to be provided in this env var in that case!
CONSTRUCTOR_SIGNING_CERTIFICATE:
    Path to PFX certificate to sign the EXE installer on Windows
"""

# Standard library imports
from argparse import ArgumentParser
from datetime import timedelta
from functools import partial
import json
from logging import getLogger
import os
from packaging.version import parse
from pathlib import Path
import platform
import re
import shutil
from subprocess import run
import sys
from textwrap import dedent, indent
from time import time
import zipfile

# Third-party imports
from ruamel.yaml import YAML
from setuptools_scm import get_version

# Local imports
from build_conda_pkgs import HERE, BUILD, RESOURCES, SPECS, h

DIST = HERE / "dist"

logger = getLogger('BuildInstallers')
logger.addHandler(h)
logger.setLevel('INFO')

APP = "Spyder"
SPYREPO = HERE.parent
WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
CONDA_BLD_PATH = os.getenv("CONDA_BLD_PATH", "local")
PY_VER = "{v.major}.{v.minor}.{v.micro}".format(v=sys.version_info)
SPYVER = get_version(SPYREPO).split("+")[0]

if WINDOWS:
    OS = "Windows"
    TARGET_PLATFORM = "win-"
    INSTALL_CHOICES = ["exe"]
elif LINUX:
    OS = "Linux"
    TARGET_PLATFORM = "linux-"
    INSTALL_CHOICES = ["sh"]
elif MACOS:
    OS = "macOS"
    TARGET_PLATFORM = "osx-"
    INSTALL_CHOICES = ["pkg", "sh"]
else:
    raise RuntimeError(f"Unrecognized OS: {sys.platform}")

ARCH = (platform.machine() or "generic").lower().replace("amd64", "x86_64")
TARGET_PLATFORM = (TARGET_PLATFORM + ARCH).replace("x86_64", "64")
TARGET_PLATFORM = os.getenv("CONSTRUCTOR_TARGET_PLATFORM", TARGET_PLATFORM)

# ---- Parse arguments
p = ArgumentParser()
p.add_argument(
    "--no-local", action="store_true",
    help="Do not use local conda packages"
)
p.add_argument(
    "--debug", action="store_true",
    help="Do not delete build files"
)
p.add_argument(
    "--arch", action="store_true",
    help="Print machine architecture tag and exit.",
)
p.add_argument(
    "--ext", action="store_true",
    help="Print installer extension for this platform and exit.",
)
p.add_argument(
    "--artifact-name", action="store_true",
    help="Print computed artifact name and exit.",
)
p.add_argument(
    "--extra-specs", nargs="+", default=[],
    help="One or more extra conda specs to add to the installer.",
)
p.add_argument(
    "--licenses", action="store_true",
    help="Post-process licenses AFTER having built the installer. "
    "This must be run as a separate step.",
)
p.add_argument(
    "--images", action="store_true",
    help="Generate background images from the logo (test only)",
)
p.add_argument(
    "--cert-id", default=None,
    help="Apple Developer ID Application certificate common name."
)
p.add_argument(
    "--install-type", choices=INSTALL_CHOICES, default=INSTALL_CHOICES[0],
    help="Installer type."
)
p.add_argument(
    "--conda-lock", action="store_true",
    help="Create conda-lock file and exit."
)
p.add_argument(
    "--version", action="store_true",
    help="Print Spyder version and exit."
)
args = p.parse_args()

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
indent4 = partial(indent, prefix="    ")

base_specs = {
    "python": "=3.11.9",
    "conda": "=24.5.0",
    "menuinst": "=2.1.2",
    "mamba": "=1.5.8",
}
rt_specs = {
    "python": f"={PY_VER}",
    "spyder": f"={SPYVER}",
    "cython": "",
    "matplotlib-base": "",
    "numpy": "",
    "openpyxl": "",
    "pandas": "",
    "scipy": "",
    "sympy": "",
}

if SPECS.exists():
    logger.info(f"Reading specs from {SPECS}...")
    _rt_specs = yaml.load(SPECS.read_text())
    rt_specs.update(_rt_specs)
else:
    logger.info(f"Did not read specs from {SPECS}")

for spec in args.extra_specs:
    k, *v = re.split('([<>=]+)[ ]*', spec)
    rt_specs[k] = "".join(v).strip()

PY_VER = parse(re.split('([<>=]+)[ ]*', rt_specs['python'])[-1])
SPYVER = parse(re.split('([<>=]+)[ ]*', rt_specs['spyder'])[-1])

BASE_LOCK_FILE = BUILD / f"conda-base-{TARGET_PLATFORM}.lock"
RT_LOCK_FILE = BUILD / f"conda-runtime-{TARGET_PLATFORM}.lock"
OUTPUT_FILE = DIST / f"{APP}-{OS}-{ARCH}.{args.install_type}"
INSTALLER_DEFAULT_PATH_STEM = f"{APP.lower()}-{SPYVER.major}"

WELCOME_IMG_WIN = BUILD / "welcome_img_win.png"
HEADER_IMG_WIN = BUILD / "header_img_win.png"
WELCOME_IMG_MAC = BUILD / "welcome_img_mac.png"
CONSTRUCTOR_FILE = BUILD / "construct.yaml"


def _create_conda_lock(env_type='base'):
    specs = base_specs
    lock_file = BASE_LOCK_FILE
    if env_type == "runtime":
        specs = rt_specs
        lock_file = RT_LOCK_FILE

    definitions = {
        "channels": [
            "conda-forge",
            "conda-forge/label/spyder_rc",
            "conda-forge/label/spyder_dev",
            "conda-forge/label/spyder_kernels_rc",
            "conda-forge/label/spyder_kernels_dev",
            CONDA_BLD_PATH,
        ],
        "dependencies": [k + v for k, v in specs.items()],
        "platforms": [TARGET_PLATFORM]
    }

    if args.no_local:
        definitions['channels'].remove(CONDA_BLD_PATH)

    logger.info(f"Conda lock configuration ({env_type}):")
    if logger.getEffectiveLevel() <= 20:
        yaml.dump(definitions, sys.stdout)

    env_file = BUILD / f"{env_type}_env.yml"
    yaml.dump(definitions, env_file)

    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "flexible"

    cmd_args = [
        "conda-lock", "lock",
        "--kind", "explicit",
        "--file", str(env_file),
        "--filename-template", str(BUILD / f"conda-{env_type}-{{platform}}.lock")
        # Note conda-lock doesn't provide output file option, only template
    ]

    run(cmd_args, check=True, env=env)

    logger.info(f"Contents of {lock_file}:")
    if logger.getEffectiveLevel() <= 20:
        print(lock_file.read_text(), flush=True)

    # Write to dist directory also
    (DIST / lock_file.name).write_text(lock_file.read_text())


def _generate_background_images(installer_type):
    """This requires Pillow."""
    if installer_type == "sh":
        # shell installers are text-based, no graphics
        return

    from PIL import Image

    logo_path = SPYREPO / "img_src" / "spyder.png"
    logo = Image.open(logo_path, "r")

    if installer_type in ("exe", "all"):
        sidebar = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        sidebar.paste(logo.resize((101, 101)), (32, 180))
        output = WELCOME_IMG_WIN
        sidebar.save(output, format="png")

        banner = Image.new("RGBA", (150, 57), (0, 0, 0, 0))
        banner.paste(logo.resize((44, 44)), (8, 6))
        output = HEADER_IMG_WIN
        banner.save(output, format="png")

    if installer_type in ("pkg", "all"):
        _logo = Image.new("RGBA", logo.size, "WHITE")
        _logo.paste(logo, mask=logo)
        background = Image.new("RGBA", (1227, 600), (0, 0, 0, 0))
        background.paste(_logo.resize((148, 148)), (95, 418))
        output = WELCOME_IMG_MAC
        background.save(output, format="png")


def _get_condarc():
    contents = dedent(
        """
        channels:  #!final
          - conda-forge/label/spyder_rc
          - conda-forge/label/spyder_dev
          - conda-forge/label/spyder_kernels_rc
          # TODO: Add this channel when we create it
          # - conda-forge/label/spyder_kernels_dev
          - conda-forge
        repodata_fns:  #!final
          - repodata.json
        auto_update_conda: false  #!final
        notify_outdated_conda: false  #!final
        channel_priority: flexible  #!final
        env_prompt: '[spyder]({default_env}) '  #! final
        register_envs: false  #! final
        """
    )
    # the undocumented #!final comment is explained here
    # https://www.anaconda.com/blog/conda-configuration-engine-power-users
    file = BUILD / "condarc"
    file.write_text(contents)

    return str(file)


def _get_conda_bld_path_url():
    bld_path_url = "file://"
    if WINDOWS:
        bld_path_url += "/"
    bld_path_url += Path(os.getenv('CONDA_BLD_PATH')).as_posix()
    return bld_path_url


def _definitions():
    condarc = _get_condarc()
    definitions = {
        "name": APP,
        "company": "Spyder-IDE",
        "reverse_domain_identifier": "org.spyder-ide.Spyder",
        "version": str(SPYVER),
        "environment_file": str(BASE_LOCK_FILE),
        "installer_filename": OUTPUT_FILE.name,
        "installer_type": args.install_type,
        "initialize_by_default": False,
        "initialize_conda": False,
        "register_python": False,
        "register_envs": False,
        "extra_envs": {
            "spyder-runtime": {
                "environment_file": str(RT_LOCK_FILE),
            }
        },
        "channels_remap": [
            {
                "src": _get_conda_bld_path_url(),
                "dest": "https://conda.anaconda.org/conda-forge"
            }
        ]
    }

    definitions["license_file"] = str(RESOURCES / "bundle_license.rtf")
    if args.install_type == "sh":
        definitions["license_file"] = str(SPYREPO / "LICENSE.txt")

    if LINUX:
        definitions.update(
            {
                "default_prefix": os.path.join(
                    "$HOME", ".local", INSTALLER_DEFAULT_PATH_STEM
                ),
                "pre_install": str(RESOURCES / "pre-install.sh"),
                "post_install": str(RESOURCES / "post-install.sh"),
                "extra_files": [
                    {str(RESOURCES / "bundle_readme.md"): "README.txt"},
                    {condarc: ".condarc"},
                    {str(RESOURCES / "menuinst_cli.py"): "bin/menuinst_cli.py"},
                ],
            }
        )

    if MACOS:
        welcome_text_tmpl = \
            (RESOURCES / "osx_pkg_welcome.rtf.tmpl").read_text()
        welcome_file = BUILD / "osx_pkg_welcome.rtf"
        welcome_file.write_text(
            welcome_text_tmpl.replace("__VERSION__", str(SPYVER)))

        definitions.update(
            {
                "progress_notifications": True,
                "pre_install": str(RESOURCES / "pre-install.sh"),
                "post_install": str(RESOURCES / "post-install.sh"),
                "conclusion_text": "",
                "readme_text": "",
                # For sh installer
                "default_prefix": os.path.join(
                    "$HOME", "Library", INSTALLER_DEFAULT_PATH_STEM
                ),
                # For pkg installer
                "pkg_name": INSTALLER_DEFAULT_PATH_STEM,
                "default_location_pkg": "Library",
                "welcome_image": str(WELCOME_IMG_MAC),
                "welcome_file": str(welcome_file),
                "extra_files": [
                    {str(RESOURCES / "bundle_readme.md"): "README.txt"},
                    {condarc: ".condarc"},
                    {str(RESOURCES / "menuinst_cli.py"): "bin/menuinst_cli.py"},
                ],
            }
        )

        if args.cert_id:
            definitions["signing_identity_name"] = args.cert_id
            definitions["notarization_identity_name"] = args.cert_id

    if WINDOWS:
        definitions.update(
            {
                "uninstall_name": f"Spyder {SPYVER.major}",
                "welcome_image": str(WELCOME_IMG_WIN),
                "header_image": str(HEADER_IMG_WIN),
                "icon_image": str(SPYREPO / "img_src" / "spyder.ico"),
                "default_prefix": os.path.join(
                    "%LOCALAPPDATA%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "default_prefix_domain_user": os.path.join(
                    "%LOCALAPPDATA%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "default_prefix_all_users": os.path.join(
                    "%ALLUSERSPROFILE%", INSTALLER_DEFAULT_PATH_STEM
                ),
                "check_path_length": False,
                "pre_install": str(RESOURCES / "pre-install.bat"),
                "post_install": str(RESOURCES / "post-install.bat"),
                "extra_files": [
                    {str(RESOURCES / "bundle_readme.md"): "README.txt"},
                    {condarc: ".condarc"},
                    {str(RESOURCES / "menuinst_cli.py"): "Scripts/menuinst_cli.py"},
                ],
            }
        )

        signing_certificate = os.environ.get("CONSTRUCTOR_SIGNING_CERTIFICATE")
        if signing_certificate:
            definitions["signing_certificate"] = signing_certificate

    if definitions.get("welcome_image") or definitions.get("header_image"):
        _generate_background_images(definitions.get("installer_type", "all"))

    logger.info(f"Contents of {CONSTRUCTOR_FILE}:")
    if logger.getEffectiveLevel() <= 20:
        yaml.dump(definitions, sys.stdout)

    yaml.dump(definitions, CONSTRUCTOR_FILE)


def _constructor():
    """
    Create a temporary `construct.yaml` input file and
    run `constructor`.
    """
    constructor = shutil.which("constructor")
    if not constructor:
        raise RuntimeError("Constructor must be installed and in PATH.")

    _definitions()

    cmd_args = [
        constructor, "-v",
        "--output-dir", str(DIST),
        "--platform", TARGET_PLATFORM,
        str(CONSTRUCTOR_FILE.parent)
    ]
    if args.debug:
        cmd_args.append("--debug")
    conda_exe = os.getenv("CONSTRUCTOR_CONDA_EXE")
    if conda_exe:
        cmd_args.extend(["--conda-exe", conda_exe])

    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "flexible"

    logger.info("Command: " + " ".join(cmd_args))

    run(cmd_args, check=True, env=env)


def licenses():
    info_path = BUILD / "info.json"
    try:
        info = json.load(info_path)
    except FileNotFoundError:
        print(
            "!! Use `constructor --debug` to write info.json and get licenses",
            file=sys.stderr,
        )
        raise

    zipname = BUILD / f"licenses.{OS}-{ARCH}.zip"
    output_zip = zipfile.ZipFile(zipname, mode="w",
                                 compression=zipfile.ZIP_DEFLATED)
    output_zip.write(info_path)
    for package_id, license_info in info["_licenses"].items():
        package_name = package_id.split("::", 1)[1]
        for license_type, license_files in license_info.items():
            for i, license_file in enumerate(license_files, 1):
                arcname = (f"{package_name}.{license_type.replace(' ', '_')}"
                           f".{i}.txt")
                output_zip.write(license_file, arcname=arcname)
    output_zip.close()
    return zipname.resolve()


def main():
    t0 = time()
    try:
        DIST.mkdir(exist_ok=True)
        _create_conda_lock(env_type='base')
        assert BASE_LOCK_FILE.exists()
        _create_conda_lock(env_type='runtime')
        assert RT_LOCK_FILE.exists()
    finally:
        elapse = timedelta(seconds=int(time() - t0))
        logger.info(f"Build time: {elapse}")

    t0 = time()
    try:
        _constructor()
        assert OUTPUT_FILE.exists()
        logger.info(f"Created {OUTPUT_FILE}")
    finally:
        elapse = timedelta(seconds=int(time() - t0))
        logger.info(f"Build time: {elapse}")


if __name__ == "__main__":
    if args.arch:
        print(ARCH)
        sys.exit()
    if args.ext:
        print(args.install_type)
        sys.exit()
    if args.artifact_name:
        print(OUTPUT_FILE)
        sys.exit()
    if args.licenses:
        print(licenses())
        sys.exit()
    if args.images:
        _generate_background_images()
        sys.exit()
    if args.conda_lock:
        _create_conda_lock(env_type='base')
        _create_conda_lock(env_type='runtime')
        sys.exit()
    if args.version:
        print(SPYVER)
        sys.exit()

    main()
