"""
Create Spyder installers using `constructor`.

It creates a `construct.yaml` file with the needed settings
and then runs `constructor`.

Some environment variables we use:

CONSTRUCTOR_APP_NAME:
    in case you want to build a non-default distribution that is not
    named `spyder`
CONSTRUCTOR_INSTALLER_DEFAULT_PATH_STEM:
    The last component of the default installation path. Defaults to
    {CONSTRUCTOR_APP_NAME}-{_version()}
CONSTRUCTOR_INSTALLER_VERSION:
    Version for the installer, separate from the app being installed.
    This will have an effect on the default install locations in future
    releases.
CONSTRUCTOR_TARGET_PLATFORM:
    conda-style platform (as in `platform` in `conda info -a` output)
CONSTRUCTOR_USE_LOCAL:
    whether to use the local channel (populated by `conda-build` actions)
CONSTRUCTOR_CONDA_EXE:
    when the target platform is not the same as the host, constructor
    needs a path to a conda-standalone (or micromamba) executable for
    that platform. needs to be provided in this env var in that case!
CONSTRUCTOR_SIGNING_IDENTITY:
    Apple ID Installer Certificate identity (common name) that should
    be use to productsign the resulting PKG (macOS only)
CONSTRUCTOR_NOTARIZATION_IDENTITY:
    Apple ID Developer Certificate identity (common name) that should
    be use to codesign some binaries bundled in the pkg (macOS only)
CONSTRUCTOR_SIGNING_CERTIFICATE:
    Path to PFX certificate to sign the EXE installer on Windows
CONSTRUCTOR_PFX_CERTIFICATE_PASSWORD:
    Password to unlock the PFX certificate. This is not used here but
    it might be needed by constructor.
"""

import json
import os
import platform
import sys
import zipfile
from argparse import ArgumentParser
from distutils.spawn import find_executable
from pathlib import Path
from tempfile import NamedTemporaryFile
from textwrap import dedent, indent
from functools import lru_cache, partial
from subprocess import check_call, check_output

from ruamel.yaml import YAML

# import spyder

yaml = YAML()
yaml.indent(mapping=2)
indent4 = partial(indent, prefix="    ")

APP = os.environ.get("CONSTRUCTOR_APP_NAME", "Spyder")
# bump this when something in the installer infrastructure changes
# note that this will affect the default installation path across platforms!
INSTALLER_VERSION = os.environ.get("CONSTRUCTOR_INSTALLER_VERSION", "0.1")
SPYREPO = Path(__file__).parent.parent
WINDOWS = os.name == "nt"
MACOS = sys.platform == "darwin"
LINUX = sys.platform.startswith("linux")
if os.environ.get("CONSTRUCTOR_TARGET_PLATFORM") == "osx-arm64":
    ARCH = "arm64"
else:
    ARCH = (platform.machine() or "generic").lower().replace("amd64", "x86_64")
TARGET_PLATFORM = os.environ.get("CONSTRUCTOR_TARGET_PLATFORM")
PY_VER = f"{sys.version_info.major}.{sys.version_info.minor}"
if WINDOWS:
    EXT, OS = "exe", "Windows"
elif LINUX:
    EXT, OS = "sh", "Linux"
elif MACOS:
    EXT, OS = "pkg", "macOS"
else:
    raise RuntimeError(f"Unrecognized OS: {sys.platform}")


def _use_local():
    """
    Detect whether we need to build Spyder locally
    (dev snapshots). This env var is set in the GHA workflow.
    """
    return os.environ.get("CONSTRUCTOR_USE_LOCAL")


@lru_cache
def _version():
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("spyder", SPYREPO / "spyder" / "__init__.py")
    mod = module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod.__version__


OUTPUT_FILENAME = f"{APP}-{_version()}-{OS}-{ARCH}.{EXT}"
INSTALLER_DEFAULT_PATH_STEM = os.environ.get(
    "CONSTRUCTOR_INSTALLER_DEFAULT_PATH_STEM", f"{APP}-{_version()}"
)
clean_these_files = []


def _generate_background_images(installer_type, outpath="resources"):
    """Requires pillow"""
    if installer_type == "sh":
        # shell installers are text-based, no graphics
        return

    from PIL import Image

    logo_path = SPYREPO / "img_src" / "spyder.png"
    logo = Image.open(logo_path, "r")

    global clean_these_files

    if installer_type in ("exe", "all"):
        sidebar = Image.new("RGBA", (164, 314), (0, 0, 0, 0))
        sidebar.paste(logo.resize((101, 101)), (32, 180))
        output = Path(outpath, "spyder_164x314.png")
        sidebar.save(output, format="png")
        clean_these_files.append(output)

        banner = Image.new("RGBA", (150, 57), (0, 0, 0, 0))
        banner.paste(logo.resize((44, 44)), (8, 6))
        output = Path(outpath, "spyder_150x57.png")
        banner.save(output, format="png")
        clean_these_files.append(output)

    if installer_type in ("pkg", "all"):
        _logo = Image.new("RGBA", logo.size, "WHITE")
        _logo.paste(logo, mask=logo)
        background = Image.new("RGBA", (1227, 600), (0, 0, 0, 0))
        background.paste(_logo.resize((148, 148)), (95, 418))
        output = Path(outpath, "spyder_1227x600.png")
        background.save(output, format="png")
        clean_these_files.append(output)


def _get_condarc():
    # we need defaults for tensorflow and others on windows only
    defaults = "- defaults" if WINDOWS else ""
    prompt = "[spyder]({default_env}) "
    contents = dedent(
        f"""
        channels:  #!final
          - spyder-ide
          - conda-forge
          {defaults}
        repodata_fns:  #!final
          - repodata.json
        auto_update_conda: false  #!final
        notify_outdated_conda: false  #!final
        channel_priority: strict  #!final
        env_prompt: '{prompt}'  #! final
        """
    )
    # the undocumented #!final comment is explained here
    # https://www.anaconda.com/blog/conda-configuration-engine-power-users
    with NamedTemporaryFile(delete=False, mode="w+") as f:
        f.write(contents)
    return f.name


def _base_env(python_version=PY_VER):
    return {
        "name": "base",
        "channels": [
            "napari/label/bundle_tools",
            "spyder-ide",
            "conda-forge",
        ],
        "specs": [
            "python",
            "conda",
            "mamba",
            "pip",
        ],
    }


def _spyder_env(
    python_version=PY_VER,
    spyder_version=_version(),
    extra_specs=None,
):
    return {
        "name": f"spyder-{spyder_version}",
        # "channels": same as _base_env(), omit to inherit :)
        "specs": [
            f"spyder={spyder_version}",
            f"spyder-menu={spyder_version}",
            # "conda",
            # "mamba",
            # "pip",
        ]
        + (extra_specs or []),
        # "exclude": exclude, # TODO: not supported yet in constructor
    }


def _definitions(version=_version(), extra_specs=None, spy_repo=SPYREPO):
    resources = spy_repo / "installers-exp" / "resources"
    base_env = _base_env()
    spyder_env = _spyder_env(spyder_version=version, extra_specs=extra_specs)
    condarc = _get_condarc()
    definitions = {
        "name": APP,
        "company": "Spyder-IDE",
        "reverse_domain_identifier": "org.spyder-ide.Spyder",
        "version": version.replace("+", "_"),
        "channels": base_env["channels"],
        "conda_default_channels": ["conda-forge"],
        "installer_filename": OUTPUT_FILENAME,
        "initialize_by_default": False,
        "license_file": str(resources / "bundle_license.rtf"),
        "specs": base_env["specs"],
        "extra_envs": {
            spyder_env["name"]: {
                "specs": spyder_env["specs"],
            },
        },
        "menu_packages": [
            "spyder-menu",
        ],
        "extra_files": {
            str(resources / "bundle_readme.md"): "README.txt",
            condarc: ".condarc",
        },
    }
    if _use_local():
        definitions["channels"].insert(0, "local")
    if LINUX:
        definitions["default_prefix"] = os.path.join(
            "$HOME", ".local", INSTALLER_DEFAULT_PATH_STEM
        )
        definitions["license_file"] = str(resources / "bundle_license.txt")
        definitions["installer_type"] = "sh"

    if MACOS:
        # These two options control the default install location:
        # ~/<default_location_pkg>/<pkg_name>
        definitions["pkg_name"] = INSTALLER_DEFAULT_PATH_STEM
        definitions["default_location_pkg"] = "Library"
        definitions["installer_type"] = "pkg"
        definitions["welcome_image"] = str(resources / "spyder_1227x600.png")
        welcome_text_tmpl = (resources / "osx_pkg_welcome.rtf.tmpl").read_text()
        welcome_file = resources / "osx_pkg_welcome.rtf"
        clean_these_files.append(welcome_file)
        welcome_file.write_text(welcome_text_tmpl.replace("__VERSION__", version))
        definitions["welcome_file"] = str(welcome_file)
        definitions["conclusion_text"] = ""
        definitions["readme_text"] = ""
        definitions["post_install"] = str(spy_repo / "installers-exp" / "post-install.sh")
        signing_identity = os.environ.get("CONSTRUCTOR_SIGNING_IDENTITY")
        if signing_identity:
            definitions["signing_identity_name"] = signing_identity
        notarization_identity = os.environ.get("CONSTRUCTOR_NOTARIZATION_IDENTITY")
        if notarization_identity:
            definitions["notarization_identity_name"] = notarization_identity

    if WINDOWS:
        definitions["conda_default_channels"].append("defaults")
        definitions.update(
            {
                "welcome_image": str(resources / "spyder_164x314.png"),
                "header_image": str(resources / "spyder_150x57.png"),
                "icon_image": str(resources / "icon.ico"),
                "register_python_default": False,
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
                "installer_type": "exe",
            }
        )
        signing_certificate = os.environ.get("CONSTRUCTOR_SIGNING_CERTIFICATE")
        if signing_certificate:
            definitions["signing_certificate"] = signing_certificate

    if definitions.get("welcome_image") or definitions.get("header_image"):
        _generate_background_images(
            definitions.get("installer_type", "all"),
            outpath=resources,
        )

    clean_these_files.append("construct.yaml")
    clean_these_files.append(condarc)

    return definitions


def _constructor(version=_version(), extra_specs=None, spy_repo=SPYREPO):
    """
    Create a temporary `construct.yaml` input file and
    run `constructor`.

    Parameters
    ----------
    version: str
        Version of `spyder` to be built. Defaults to the
        one detected by `importlib` from the source code.
    extra_specs: list of str
        Additional packages to be included in the installer.
        A list of conda spec strings (`numpy`, `python=3`, etc)
        is expected.
    spy_repo: str
        location where the spyder-ide/spyder repository was cloned
    """
    constructor = find_executable("constructor")
    if not constructor:
        raise RuntimeError("Constructor must be installed and in PATH.")

    # TODO: temporarily patching password - remove block when the secret has been fixed
    # (I think it contains an ending newline or something like that, copypaste artifact?)
    pfx_password = os.environ.get("CONSTRUCTOR_PFX_CERTIFICATE_PASSWORD")
    if pfx_password:
        os.environ["CONSTRUCTOR_PFX_CERTIFICATE_PASSWORD"] = pfx_password.strip()

    definitions = _definitions(
        version=version, extra_specs=extra_specs, spy_repo=spy_repo
    )

    args = [constructor, "-v", "--debug", "."]
    conda_exe = os.environ.get("CONSTRUCTOR_CONDA_EXE")
    if TARGET_PLATFORM and conda_exe:
        args += ["--platform", TARGET_PLATFORM, "--conda-exe", conda_exe]
    env = os.environ.copy()
    env["CONDA_CHANNEL_PRIORITY"] = "strict"

    print("+++++++++++++++++")
    print("Command:", " ".join(args))
    print("Configuration:")
    yaml.dump(definitions, sys.stdout, transform=indent4)
    print("\nConda config:\n")
    print(
        indent4(check_output(["conda", "config", "--show-sources"], text=True, env=env))
    )
    print("Conda info:")
    print(indent4(check_output(["conda", "info"], text=True, env=env)))
    print("+++++++++++++++++")

    with open("construct.yaml", "w") as fin:
        yaml.dump(definitions, fin)

    check_call(args, env=env)

    return OUTPUT_FILENAME


def licenses():
    info_path = Path("dist") / "info.json"
    try:
        with open(info_path) as f:
            info = json.load(f)
    except FileNotFoundError:
        print(
            "!! Use `constructor --debug` to write info.json and get licenses",
            file=sys.stderr,
        )
        raise

    zipname = Path("dist") / f"licenses.{OS}-{ARCH}.zip"
    output_zip = zipfile.ZipFile(zipname, mode="w", compression=zipfile.ZIP_DEFLATED)
    output_zip.write(info_path)
    for package_id, license_info in info["_licenses"].items():
        package_name = package_id.split("::", 1)[1]
        for license_type, license_files in license_info.items():
            for i, license_file in enumerate(license_files, 1):
                arcname = f"{package_name}.{license_type.replace(' ', '_')}.{i}.txt"
                output_zip.write(license_file, arcname=arcname)
    output_zip.close()
    return zipname.resolve()


def main(extra_specs=None, spy_repo=SPYREPO):
    try:
        cwd = os.getcwd()
        workdir = spy_repo / "installers-exp" / "dist"
        workdir.mkdir(exist_ok=True)
        os.chdir(workdir)
        _constructor(extra_specs=extra_specs, spy_repo=spy_repo)
        assert Path(OUTPUT_FILENAME).exists(), f"{OUTPUT_FILENAME} was not created!"
    finally:
        for path in clean_these_files:
            try:
                os.unlink(path)
            except OSError:
                print("!! Could not remove", path, file=sys.stderr)
        os.chdir(cwd)
    return workdir / OUTPUT_FILENAME


def cli(argv=None):
    p = ArgumentParser(argv)
    p.add_argument(
        "--version",
        action="store_true",
        help="Print local Spyder version and exit.",
    )
    p.add_argument(
        "--installer-version",
        action="store_true",
        help="Print installer version and exit.",
    )
    p.add_argument(
        "--arch",
        action="store_true",
        help="Print machine architecture tag and exit.",
    )
    p.add_argument(
        "--ext",
        action="store_true",
        help="Print installer extension for this platform and exit.",
    )
    p.add_argument(
        "--artifact-name",
        action="store_true",
        help="Print computed artifact name and exit.",
    )
    p.add_argument(
        "--extra-specs",
        nargs="+",
        help="One or more extra conda specs to add to the installer",
    )
    p.add_argument(
        "--licenses",
        action="store_true",
        help="Post-process licenses AFTER having built the installer. "
        "This must be run as a separate step.",
    )
    p.add_argument(
        "--images",
        action="store_true",
        help="Generate background images from the logo (test only)",
    )
    p.add_argument(
        "--location",
        default=SPYREPO,
        help="Path to spyder source repository",
        type=os.path.abspath,
    )
    return p.parse_args()


if __name__ == "__main__":
    args = cli()
    if args.version:
        print(_version())
        sys.exit()
    if args.installer_version:
        print(INSTALLER_VERSION)
        sys.exit()
    if args.arch:
        print(ARCH)
        sys.exit()
    if args.ext:
        print(EXT)
        sys.exit()
    if args.artifact_name:
        print(OUTPUT_FILENAME)
        sys.exit()
    if args.licenses:
        print(licenses())
        sys.exit()
    if args.images:
        _generate_background_images(spy_repo=args.location)
        sys.exit()

    print("Created", main(extra_specs=args.extra_specs, spy_repo=args.location))
