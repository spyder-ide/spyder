# -*- coding: utf-8 -*-
#
# Copyright © Spyder Project Contributors
# Licensed under the terms of the MIT License
# (see spyder/__init__.py for details)

"""
Create a Spyder installer using `constructor`.
"""

# Standard library imports
from argparse import ArgumentParser
from datetime import timedelta
from functools import partial
import json
import os
from packaging.version import parse
from pathlib import Path
import platform
import re
from subprocess import run
import sys
from textwrap import dedent, indent
from time import time

# Third-party imports
from ruamel.yaml import YAML
from setuptools_scm import get_version

# Local imports
from utils import logger, SPYREPO, RESOURCES, BUILD, DIST, DocFormatter

WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")

if WINDOWS:
    OS = "Windows"
    PLATFORM = "win-"
    INSTALL_CHOICES = ["exe"]
elif LINUX:
    OS = "Linux"
    PLATFORM = "linux-"
    INSTALL_CHOICES = ["sh"]
elif MACOS:
    OS = "macOS"
    PLATFORM = "osx-"
    INSTALL_CHOICES = ["pkg", "sh"]
else:
    raise RuntimeError(f"Unrecognized OS: {sys.platform}")

yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
indent4 = partial(indent, prefix="    ")

ARCH = (platform.machine() or "generic").lower().replace("amd64", "x86_64")
PLATFORM = (PLATFORM + ARCH).replace("x86_64", "64")


def _process_extra_specs(extra_specs, no_local=False):
    # Default to current scm version, possible release tag.
    specs = {"spyder": ["=", parse(get_version(SPYREPO)).public]}

    if not no_local:
        # Use latest local channel package versions as default
        bld_path = os.getenv("CONDA_BLD_PATH", "")
        channel_file = Path(bld_path) / "channeldata.json"

        channel_data = {}
        if channel_file.exists():
            channel_data = json.loads(channel_file.read_text())

        packages = channel_data.get("packages", {})
        for pkg in (
            "spyder", "spyder-kernels", "qtconsole", "python-lsp-server"
        ):
            version = packages.get(pkg, {}).get("version")
            if version:
                specs.update({pkg: ["=", version]})

    for value in extra_specs:
        pkg, *spec = re.split("(=|>=|<=|!=)", value)
        specs.update({pkg: spec})

    if not specs.get("spyder"):
        raise ValueError("Spyder version must be specified.")

    new_extra_specs = [k + "".join(s) for k, s in specs.items() if s]

    return new_extra_specs, specs.get("spyder")[1]


def _generate_background_images(install_type, spy_ver):
    """This requires Pillow."""
    if install_type == "sh":
        # shell installers are text-based, no graphics
        return

    logger.info("Building background images...")

    from PIL import Image

    logo_path = SPYREPO / "img_src" / "spyder.png"
    logo = Image.open(logo_path, "r")

    BUILD.mkdir(exist_ok=True)

    if install_type == "exe":
        sidebar = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        sidebar.paste(logo.resize((101, 101)), (32, 180))
        output = BUILD / "welcome_img_win.png"
        sidebar.save(output, format="png")

        banner = Image.new("RGBA", (150, 57), (0, 0, 0, 0))
        banner.paste(logo.resize((44, 44)), (8, 6))
        output = BUILD / "header_img_win.png"
        banner.save(output, format="png")

    if install_type == "pkg":
        _logo = Image.new("RGBA", logo.size, "WHITE")
        _logo.paste(logo, mask=logo)
        background = Image.new("RGBA", (1227, 600), (0, 0, 0, 0))
        background.paste(_logo.resize((148, 148)), (95, 418))
        output = BUILD / "welcome_img_mac.png"
        background.save(output, format="png")

        welcome_file = RESOURCES / "osx_pkg_welcome.rtf"
        welcome_text = welcome_file.read_text()
        welcome_file = BUILD / welcome_file.name
        welcome_text = welcome_text.replace(
            "__VERSION__", str(spy_ver)
        ).replace("__MAJ_VER__", str(parse(spy_ver).major))
        welcome_file.write_text(welcome_text)


def _uninstall_shortcut(spy_ver):
    """Modify the uninstall shortcut specification file."""
    menu_file = RESOURCES / "uninstall-menu.json"
    menu_text = menu_file.read_text()
    menu_file = BUILD / "uninstall-menu.json"
    menu_file.write_text(
        menu_text.replace("__PKG_MAJOR_VER__", str(parse(spy_ver).major))
    )


def _create_conda_lock(env_type, extra_specs=[], no_local=False):
    env_file = RESOURCES / f"{env_type}_env.yml"

    if env_type == "runtime" and (extra_specs or not no_local):
        rt_specs = yaml.load(env_file.read_text())

        if not no_local and os.getenv("CONDA_BLD_PATH"):
            # Add local channel
            rt_specs["channels"].append(os.getenv("CONDA_BLD_PATH"))

        if extra_specs:
            # Update runtime environment dependencies
            rt_specs["dependencies"].extend(extra_specs)

        # Write to BUILD directory
        BUILD.mkdir(exist_ok=True)
        env_file = BUILD / env_file.name
        yaml.dump(rt_specs, env_file)

    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "flexible"

    lock_file_template = BUILD / f"conda-{env_type}-{{platform}}.lock"
    lock_file = BUILD / f"conda-{env_type}-{PLATFORM}.lock"

    cmd_args = [
        "conda-lock", "lock",
        "--kind", "explicit",
        "--file", str(env_file),
        # Note conda-lock doesn't provide output file option, only template
        "--filename-template",
        str(lock_file_template),
        "--platform", PLATFORM
    ]

    logger.info(f"Building {lock_file.name}...")
    logger.info(f"Conda lock configuration:\n{env_file.read_text()}\n")
    run(cmd_args, check=True, env=env)

    logger.info(f"Contents of {lock_file}:\n{lock_file.read_text()}")

    # Copy to dist directory
    DIST.mkdir(exist_ok=True)
    (DIST / lock_file.name).write_text(lock_file.read_text())


def _output_file(install_type):
    return DIST / f"Spyder-{OS}-{ARCH}.{install_type}"


def _constructor(install_type, spy_ver, debug=False):
    """Build installer from construct.yaml"""
    DIST.mkdir(exist_ok=True)

    cmd_args = [
        "constructor",
        "--output-dir", str(DIST),
        "--platform", PLATFORM,
        str(RESOURCES)
    ]
    if debug:
        cmd_args.append("--debug")

    env = os.environ.copy()
    env.update(
        {
            "OS": OS,
            "ARCH": ARCH,
            "INSTALL_TYPE": install_type,
            "INSTALL_VER": spy_ver,
            "REPO_PATH": str(SPYREPO),
            "CONDA_SHORTCUTS": "false", # Don't create shortcuts while building
        }
    )

    logger.info("Command: " + " ".join(cmd_args))

    run(cmd_args, check=True, env=env)
    logger.info(f"Created {_output_file(install_type)}")


def _cleanup_build(debug=False):
    if debug or not BUILD.exists():
        # Do not clean the build directory
        return

    exts = (".exe", ".json", ".lock", ".pkg", ".png", ".rtf", ".sh", ".yml")
    for f in BUILD.glob("*"):
        if f.suffix in exts:
            f.unlink()


def main(spy_ver, extra_specs, install_type, no_local, debug):
    BUILD.mkdir(exist_ok=True)
    DIST.mkdir(exist_ok=True)

    _cleanup_build()

    _generate_background_images(install_type, spy_ver)

    _uninstall_shortcut(spy_ver)

    t0 = time()
    try:
        _create_conda_lock('base', no_local=no_local)
        _create_conda_lock('runtime', extra_specs, no_local)
    finally:
        elapse = timedelta(seconds=int(time() - t0))
        logger.info(f"Build lock files time: {elapse} s")

    t0 = time()
    try:
        _constructor(install_type, spy_ver, debug)
        logger.info(f"Created {_output_file(args.install_type)}")
    finally:
        elapse = timedelta(seconds=int(time() - t0))
        logger.info(f"Build installer time: {elapse} s")

    _cleanup_build(debug)


if __name__ == "__main__":
    parser = ArgumentParser(
        description="Build conda-based installer.",
        epilog=dedent(
            """
            If building the installer using constructor directly, the
            constructor.yaml can be customized with the following environment
            variables:
                OS : {Windos, Linux, macOS}
                    The system name used for naming the installer file.
                ARCH : {x86_64, arm64}
                    The system architecture used for naming the installer file.
                INSTALL_TYPE : {exe, sh, pkg}
                    The installer type to build.
                INSTALL_VER
                    This should be the same as the Spyder version.
                REPO_PATH
                    Full path to the Spyder repository.
                CERT_ID
                    Apple developer certificate identifier.
                WIN_SIGN_CERT
                    Path to the PFX signing certificate for Windows.
            """
        ),
        formatter_class=DocFormatter
    )
    parser.add_argument(
        "--clean", action="store_true",
        help="Clean up the build directory."
    )
    parser.add_argument(
        "--conda-lock", action="store_true",
        help="Create conda-lock files."
    )
    parser.add_argument(
        "--debug", action="store_true",
        help="Do not delete build files after building the installer."
    )
    parser.add_argument(
        "--extra-specs", action="extend", nargs="+", default=[],
        help="One or more extra conda specs to add to the installer.",
    )
    parser.add_argument(
        "--build-images", action="store_true",
        help="Generate background images.",
    )
    parser.add_argument(
        "--install-type", choices=INSTALL_CHOICES, default=INSTALL_CHOICES[0],
        help=f"Installer type. Default is {INSTALL_CHOICES[0]}."
    )
    parser.add_argument(
        "--installer-path", action="store_true",
        help="Print artifact name.",
    )
    parser.add_argument(
        "--no-local", action="store_true",
        help="Do not use packages from the local conda channel."
    )
    parser.add_argument(
        "--version", action="store_true",
        help="Print Spyder version."
    )

    args = parser.parse_args()

    extra_specs, spy_ver = _process_extra_specs(
        args.extra_specs, args.no_local
    )

    if args.installer_path:
        print(_output_file(args.install_type))
    elif args.clean:
        _cleanup_build()
    elif args.conda_lock:
        _create_conda_lock('base', no_local=args.no_local)
        _create_conda_lock('runtime', extra_specs, args.no_local)
    elif args.build_images:
        _generate_background_images(args.install_type)
    elif args.version:
        print(spy_ver)
    else:
        main(
            spy_ver, extra_specs, args.install_type, args.no_local, args.debug
        )
