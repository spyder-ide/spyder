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
from textwrap import indent
from time import time

# Third-party imports
from ruamel.yaml import YAML
from setuptools_scm import get_version

# Local imports
from utils import logger, SPYREPO, RESOURCES, BUILD, DIST

# ---- Parse arguments
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

p = ArgumentParser()
p.add_argument(
    "--debug", action="store_true",
    help="Do not delete build files after building the installer."
)
p.add_argument(
    "--artifact-name", action="store_true",
    help="Print artifact name.",
)
p.add_argument(
    "--extra-specs", action="extend", nargs="+", default=[],
    help="One or more extra conda specs to add to the installer.",
)
p.add_argument(
    "--no-local", action="store_true",
    help="Do not use packages from the local conda channel."
)
p.add_argument(
    "--images", action="store_true",
    help="Generate background images.",
)
p.add_argument(
    "--install-type", choices=INSTALL_CHOICES, default=INSTALL_CHOICES[0],
    help=f"Installer type. Default is {INSTALL_CHOICES[0]}."
)
p.add_argument(
    "--conda-lock", action="store_true",
    help="Create conda-lock files."
)
p.add_argument(
    "--version", action="store_true",
    help="Print Spyder version."
)
args = p.parse_args()

# ---- Set module constants
yaml = YAML()
yaml.indent(mapping=2, sequence=4, offset=2)
indent4 = partial(indent, prefix="    ")

ARCH = (platform.machine() or "generic").lower().replace("amd64", "x86_64")
PLATFORM = (PLATFORM + ARCH).replace("x86_64", "64")

BASE_LOCK_FILE = BUILD / f"conda-base-{PLATFORM}.lock"
RT_LOCK_FILE = BUILD / f"conda-runtime-{PLATFORM}.lock"
OUTPUT_FILE = DIST / f"Spyder-{OS}-{ARCH}.{args.install_type}"


def _process_extra_specs():
    # Default to current scm version, possible release tag.
    specs = {"spyder": ["=", parse(get_version(SPYREPO)).public]}

    if not args.no_local:
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

    for value in args.extra_specs:
        pkg, *spec = re.split("(=|>=|<=|!=)", value)
        specs.update({pkg: spec})

    if not specs.get("spyder"):
        raise ValueError("Spyder version must be specified.")

    extra_specs = [k + "".join(s) for k, s in specs.items() if s]

    return extra_specs, specs.get("spyder")[1]


extra_specs, spy_ver = _process_extra_specs()


# ---- Module functions
def _generate_background_images():
    """This requires Pillow."""
    if args.install_type == "sh":
        # shell installers are text-based, no graphics
        return

    logger.info("Building background images...")

    from PIL import Image

    logo_path = SPYREPO / "img_src" / "spyder.png"
    logo = Image.open(logo_path, "r")

    BUILD.mkdir(exist_ok=True)

    if args.install_type == "exe":
        sidebar = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        sidebar.paste(logo.resize((101, 101)), (32, 180))
        output = BUILD / "welcome_img_win.png"
        sidebar.save(output, format="png")

        banner = Image.new("RGBA", (150, 57), (0, 0, 0, 0))
        banner.paste(logo.resize((44, 44)), (8, 6))
        output = BUILD / "header_img_win.png"
        banner.save(output, format="png")

    if args.install_type == "pkg":
        _logo = Image.new("RGBA", logo.size, "WHITE")
        _logo.paste(logo, mask=logo)
        background = Image.new("RGBA", (1227, 600), (0, 0, 0, 0))
        background.paste(_logo.resize((148, 148)), (95, 418))
        output = BUILD / "welcome_img_mac.png"
        background.save(output, format="png")

        welcome_text = RESOURCES / "osx_pkg_welcome.rtf"
        (BUILD / welcome_text.name).write_text(
            welcome_text.read_text().replace("__VERSION__", str(spy_ver))
        )


def _create_conda_lock(env_type='base'):
    env_file = RESOURCES / f"{env_type}_env.yml"

    lock_file = BASE_LOCK_FILE
    if env_type == "runtime":
        lock_file = RT_LOCK_FILE
        if extra_specs or args.no_local:
            rt_specs = yaml.load(env_file.read_text())

            if not args.no_local:
                # Add local channel
                rt_specs["channels"].append(os.getenv("CONDA_BLD_PATH", ""))

            if extra_specs:
                # Update runtime environment dependencies
                rt_specs["dependencies"].extend(extra_specs)

            # Write to BUILD directory
            env_file = BUILD / env_file.name
            yaml.dump(rt_specs, env_file)

    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "flexible"

    cmd_args = [
        "conda-lock", "lock",
        "--kind", "explicit",
        "--file", str(env_file),
        # Note conda-lock doesn't provide output file option, only template
        "--filename-template",
        str(BUILD / f"conda-{env_type}-{{platform}}.lock"),
        "--platform", PLATFORM
    ]

    logger.info(f"Building {lock_file.name}...")
    logger.info("Conda lock configuration:\n{env_file.read_text()}\n")
    run(cmd_args, check=True, env=env)

    logger.info(f"Contents of {lock_file}:\n{lock_file.read_text()}")

    # Copy to dist directory
    (DIST / lock_file.name).write_text(lock_file.read_text())


def _constructor():
    """Build installer from construct.yaml"""

    cmd_args = [
        "constructor",
        "--output-dir", str(DIST),
        "--platform", PLATFORM,
        str(RESOURCES)
    ]
    if args.debug:
        cmd_args.append("--debug")

    env = os.environ.copy()
    env.update(
        {
            "OS": OS,
            "ARCH": ARCH,
            "INSTALL_TYPE": args.install_type,
            "INSTALL_VER": spy_ver,
            "REPO_PATH": str(SPYREPO),
        }
    )

    logger.info("Command: " + " ".join(cmd_args))

    run(cmd_args, check=True, env=env)


def main():
    _generate_background_images()
    t0 = time()
    try:
        BUILD.mkdir(exist_ok=True)
        DIST.mkdir(exist_ok=True)
        _create_conda_lock(env_type='base')
        assert BASE_LOCK_FILE.exists()
        logger.info(f"Created {BASE_LOCK_FILE}")
        _create_conda_lock(env_type='runtime')
        assert RT_LOCK_FILE.exists()
        logger.info(f"Created {RT_LOCK_FILE}")

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


if args.artifact_name:
    print(OUTPUT_FILE)
elif args.version:
    print(spy_ver)
elif args.images:
    _generate_background_images()
elif args.conda_lock:
    _create_conda_lock(env_type='base')
    _create_conda_lock(env_type='runtime')
else:
    main()
