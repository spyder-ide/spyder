# -*- coding: utf-8 -*-
#
# Copyright © 2020 Spyder Project Contributors.
# Licensed under the terms of the GPL-3.0 License
#
# Copyright © 2018 Nicholas H.Tollervey.
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Script to create a Windows installer using pynsist.

Based on the Mu's win_installer.py script
https://github.com/mu-editor/mu/blob/master/win_installer.py
"""

import argparse
import importlib.util as iutil
import os
import requests
import shutil
import subprocess
import sys
import tempfile
import zipfile

import yarg


# URL to download assets that the installer needs and that will be put on
# the assets directory when building the installer

ASSETS_URL = os.environ.get(
    'ASSETS_URL',
    'https://github.com/spyder-ide/windows-installer-assets/'
    'releases/download/0.0.1/assets.zip')

# Packages to remove from the requirements for example pip or
# external direct dependencies (python-language-server spyder-kernels)

UNWANTED_PACKAGES = os.environ.get('UNWANTED_PACKAGES', '').split()

# Packages to skip when checking for wheels and instead add them directly in
# the 'packages' section, for example bcrypt

SKIP_PACKAGES = os.environ.get('SKIP_PACKAGES', '').split()

# Packages to be added to the packages section regardless wheel checks or
# packages skipped, for example external direct dependencies
# (spyder-kernels python-language-server)

ADD_PACKAGES = os.environ.get('ADD_PACKAGES', '').split()

# Packages to be installed using the editable flag
# (python-language-server in PRs)

INSTALL_EDITABLE_PACKAGES = os.environ.get(
    'INSTALL_EDITABLE_PACKAGES', '').split()

# The pynsist requirement spec that will be used to install pynsist in
# the temporary packaging virtual environment (pynsist==2.5.1).

PYNSIST_REQ = os.environ.get('PYNSIST_REQ', 'pynsist==2.5.1')

# The pynsist configuration file template that will be used. Of note,
# with regards to pynsist dependency collection and preparation:
# - {pypi_wheels} will be downloaded by pynsist from PyPI.
# - {packages} will be copied by pynsist from the current Python env.

PYNSIST_CFG_TEMPLATE = """
[Application]
name={name}
version={version}
entry_point={entrypoint}
icon={icon_file}
publisher={publisher}
license_file={license_file}
[Python]
version={python_version}
bitness={bitness}
format=bundled
[Include]
pypi_wheels=
    {pypi_wheels}
packages=
    tkinter
    _tkinter
    turtle
    win32api
    win32security
    ntsecuritycon
    {packages}
files={package_dist_info} > $INSTDIR/pkgs
    black-20.8b1.dist-info > $INSTDIR/pkgs
    __main__.py > $INSTDIR/pkgs/jedi/inference/compiled/subprocess
    lib
    tcl86t.dll > $INSTDIR/pkgs
    tk86t.dll > $INSTDIR/pkgs
[Build]
installer_name={installer_name}
nsi_template={template}
"""


def subprocess_run(args):
    """
    Wrapper-function around subprocess.run.

    When the sub-process exits with a non-zero return code,
    prints out a message and exits with the same code.
    """
    cp = subprocess.run(args)
    try:
        cp.check_returncode()
    except subprocess.CalledProcessError as exc:
        print(exc)
        sys.exit(cp.returncode)


def create_packaging_env(
        target_directory, python_version, name="packaging-env",
        conda_path=None):
    """
    Create a Python virtual environment in the target_directory.

    Returns the path to the newly created environment's Python executable.
    """
    fullpath = os.path.join(target_directory, name)
    if conda_path:
        command = [
            conda_path, "create",
            "-p", os.path.normpath(fullpath),
            "python={}".format(python_version),
            "-y"]
        env_path = os.path.join(fullpath, "python.exe")
    else:
        command = [sys.executable, "-m", "venv", fullpath]
        env_path = os.path.join(fullpath, "Scripts", "python.exe")
    subprocess_run(command)
    return env_path


def pip_freeze(python, encoding):
    """
    Return the "pip freeze --all" output as a list of strings.
    """
    print("Getting frozen requirements.")
    output = subprocess.check_output([python, "-m", "pip", "freeze", "--all"])
    text = output.decode(encoding)
    return text.splitlines()


def about_dict(repo_root, package):
    """
    Return the package about dict.

    keys are the __variables__ in <package>/__init__.py.
    """
    package_init = os.path.join(repo_root, package, "__init__.py")
    spec = iutil.spec_from_file_location("package", package_init)
    package = iutil.module_from_spec(spec)
    spec.loader.exec_module(package)

    return package.__dict__


def pypi_wheels_in(requirements, skip_packages):
    """
    Return a list of the entries in requirements (distributed as wheels).

    Where requirements is a list of strings formatted like "name==version".
    """
    print("Checking for wheel availability at PyPI.")
    wheels = []
    for requirement in requirements:
        name, _, version = requirement.partition("==")
        # Needed to detect the package being installed from source
        # <package> @ <path to package>==<version>
        name = name.split('@')[0].strip()
        if name in skip_packages:
            print("-", requirement, "skipped")
        else:
            print("-", requirement, end=" ")
            package = yarg.get(name)
            releases = package.release(version)
            if not releases:
                raise RuntimeError(
                    "ABORTING: Did not find {!r} at PyPI. "
                    "(bad meta-data?)".format(
                        requirement
                    )
                )
            if any(r.package_type == "wheel" for r in releases):
                wheels.append(requirement)
                feedback = "ok"
            else:
                feedback = "missing"
            print(feedback)
    return wheels


def package_name(requirement):
    """
    Return the name component of a `name==version` formatted requirement.
    """
    requirement_name = requirement.partition("==")[0].split("@")[0].strip()
    return requirement_name


def packages_from(requirements, wheels, skip_packages):
    """
    Return a list of the entries in requirements that aren't found in wheels.

    Both assumed to be lists/iterables of strings formatted like
    "name==version".
    """
    packages = set(requirements) - set(wheels) - set(skip_packages)
    packages = packages | set(ADD_PACKAGES)
    return [package_name(p) for p in packages]


def create_pynsist_cfg(
        python, python_version, repo_root, entrypoint, package,
        icon_file, license_file, filename, encoding="latin1", extras=None,
        suffix=None, template=None):
    """
    Create a pynsist configuration file from the PYNSIST_CFG_TEMPLATE.

    Determines dependencies by running pip freeze,
    which are then split between those distributed as PyPI wheels and
    others. Returns the name of the resulting installer executable, as
    set into the pynsist configuration file.
    """
    repo_about_file = about_dict(repo_root, package)
    repo_package_name = repo_about_file["__title__"]
    repo_version = repo_about_file["__installer_version__"]
    repo_author = repo_about_file["__author__"]
    repo_dist_info = "{}-{}.dist-info".format(package, repo_version)

    requirements = [
        # Those from pip freeze except the package itself and packages local
        # installed (by passing a directory path or with the editable flag).
        # To add such packages the ADD_PACKAGES should include the import names
        # of the packages.
        line
        for line in pip_freeze(python, encoding=encoding)
        if package_name(line) != package and \
        package_name(line) not in UNWANTED_PACKAGES and \
        '-e git' not in line
    ]
    skip_wheels = [package] + SKIP_PACKAGES
    wheels = pypi_wheels_in(requirements, skip_wheels)
    skip_packages = [package]
    packages = packages_from(requirements, wheels, skip_packages)

    if suffix:
        installer_name = "{}_{}bit_{}.exe"
    else:
        installer_name = "{}_{}bit{}.exe"

    if not suffix:
        suffix = ""

    installer_exe = installer_name.format(repo_package_name, bitness, suffix)

    pynsist_cfg_payload = PYNSIST_CFG_TEMPLATE.format(
        name=repo_package_name,
        version=repo_version,
        entrypoint=entrypoint,
        icon_file=icon_file,
        license_file=license_file,
        python_version=python_version,
        publisher=repo_author,
        bitness=bitness,
        pypi_wheels="\n    ".join(wheels),
        packages="\n    ".join(packages),
        installer_name=installer_exe,
        template=template,
        package_dist_info=repo_dist_info
    )
    with open(filename, "wt", encoding=encoding) as f:
        f.write(pynsist_cfg_payload)
    print("Wrote pynsist configuration file", filename)
    print("Contents:")
    print(pynsist_cfg_payload)
    print("End of pynsist configuration file.")

    return installer_exe


def download_file(url, target_directory):
    """
    Download the URL to the target_directory and return the filename.
    """
    local_filename = os.path.join(target_directory, url.split("/")[-1])
    r = requests.get(url, stream=True)
    with open(local_filename, "wb") as f:
        for chunk in r.iter_content(chunk_size=1024):
            if chunk:  # filter out keep-alive new chunks
                f.write(chunk)
    return local_filename


def unzip_file(filename, target_directory):
    """
    Given a filename, unzip it into the given target_directory.
    """
    with zipfile.ZipFile(filename) as z:
        z.extractall(target_directory)


def run(python_version, bitness, repo_root, entrypoint, package, icon_path,
        license_path, extra_packages=None, conda_path=None, suffix=None,
        template=None):
    """
    Run the installer generation.

    Given a certain python version, bitness, package repository root directory,
    package name, icon path and license path a pynsist configuration file
    (locking the dependencies set in setup.py) is generated and pynsist runned.
    """
    try:
        print("Setting up assets from", ASSETS_URL)
        print("Downloading assets from ", ASSETS_URL)
        filename = download_file(ASSETS_URL, 'installers/Windows/assets')

        print("Unzipping assets to", 'installers/Windows/assets')
        unzip_file(filename, 'installers/Windows/assets')

        with tempfile.TemporaryDirectory(
                prefix="installer-pynsist-") as work_dir:
            print("Temporary working directory at", work_dir)

            # NOTE: SHOULD BE TEMPORAL (until black has wheels available).
            # See the 'files' section on the pynsist template config too.
            print("Copying dist.info for black-20.8b1")
            shutil.copytree(
                "installers/Windows/assets/black/black-20.8b1.dist-info",
                os.path.join(work_dir, "black-20.8b1.dist-info"))

            # NOTE: SHOULD BE TEMPORAL (until jedi has the fix available).
            # See the 'files' section on the pynsist template config too.
            print("Copying patched CompiledSubprocess __main__.py for jedi")
            shutil.copy(
                "installers/Windows/assets/jedi/__main__.py",
                os.path.join(work_dir, "__main__.py"))

            print("Copying required assets for Tkinter to work")
            shutil.copytree(
                "installers/Windows/assets/tcl/lib",
                os.path.join(work_dir, "lib"))
            shutil.copy(
                "installers/Windows/assets/tcl/tcl86t.dll",
                os.path.join(work_dir, "tcl86t.dll"))
            shutil.copy(
                "installers/Windows/assets/tcl/tk86t.dll",
                os.path.join(work_dir, "tk86t.dll"))

            print("Copying NSIS plugins into discoverable path")
            shutil.copy(
                "installers/Windows/assets/nsist/plugins/x86-unicode/"
                "WinShell.dll",
                "C:/Program Files (x86)/NSIS/Plugins/x86-unicode/WinShell.dll")

            if template:
                print("Copying template into discoverable path for Pynsist")
                template_basename = os.path.basename(template)
                template_new_path = os.path.normpath(
                    os.path.join(
                        work_dir,
                        "packaging-env/Lib/site-packages/nsist"))
                os.makedirs(template_new_path)
                shutil.copy(
                    template,
                    os.path.join(template_new_path, template_basename))
                template = template_basename

            print("Creating the package virtual environment.")
            env_python = create_packaging_env(
                work_dir, python_version, conda_path=conda_path)

            print("Updating pip in the virtual environment", env_python)
            subprocess_run(
                [env_python, "-m", "pip", "install", "--upgrade", "pip",
                 "--no-warn-script-location"]
            )

            print("Updating setuptools in the virtual environment", env_python)
            subprocess_run(
                [env_python, "-m", "pip", "install", "--upgrade",
                 "--force-reinstall", "setuptools",
                 "--no-warn-script-location"]
            )

            print("Updating/installing wheel in the virtual environment",
                  env_python)
            subprocess_run(
                [env_python, "-m", "pip", "install", "--upgrade", "wheel",
                 "--no-warn-script-location"]
            )

            print("Installing package with", env_python)
            subprocess_run([env_python, "-m",
                            "pip", "install", repo_root,
                            "--no-warn-script-location"])

            print("Copy package .dist-info into the pynsist future "
                  "build directory")
            package_info = about_dict(repo_root, package)
            dist_info_dir = "{}-{}.dist-info".format(
                package,
                package_info["__installer_version__"])
            shutil.copytree(
                os.path.join(
                    work_dir, "packaging-env/Lib/site-packages",
                    dist_info_dir),
                os.path.join(work_dir, dist_info_dir))

            if extra_packages:
                print("Installing extra packages.")
                subprocess_run([env_python, "-m", "pip", "install", "-r",
                                extra_packages, "--no-warn-script-location"])

            if INSTALL_EDITABLE_PACKAGES:
                print("Installing packages with the --editable flag")
                for e_package in INSTALL_EDITABLE_PACKAGES:
                    subprocess_run([env_python, "-m", "pip", "install", "-e",
                                    e_package, "--no-warn-script-location"])

            pynsist_cfg = os.path.join(work_dir, "pynsist.cfg")
            print("Creating pynsist configuration file", pynsist_cfg)
            installer_exe = create_pynsist_cfg(
                env_python, python_version, repo_root, entrypoint, package,
                icon_path, license_path, pynsist_cfg, extras=extra_packages,
                suffix=suffix, template=template)

            print("Installing pynsist.")
            subprocess_run([env_python, "-m", "pip", "install", PYNSIST_REQ,
                            "--no-warn-script-location"])

            print("Running pynsist.")
            subprocess_run([env_python, "-m", "nsist", pynsist_cfg])

            destination_dir = os.path.join(repo_root, "dist")
            print("Copying installer file to", destination_dir)
            os.makedirs(destination_dir, exist_ok=True)
            shutil.copy(
                os.path.join(work_dir, "build", "nsis", installer_exe),
                destination_dir,
            )
            print("Installer created!")
    except PermissionError:
        pass


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description='Build a Windows installer with Pynsist')
    parser.add_argument(
        'python_version', help='Python version of the installer')
    parser.add_argument('bitness', help='Bitness of the installer (32, 64)')
    parser.add_argument('setup_py_path', help='Path to the setup.py file')
    parser.add_argument('entrypoint', help='Entrypoint to execute the package')
    parser.add_argument('package', help='Name of the package')
    parser.add_argument(
        'icon_path', help='Path to icon to use for the installer')
    parser.add_argument('license_path', help='Path to license file')
    parser.add_argument(
        '-ep', '--extra_packages',
        help='''Path to a .txt file with a list of packages to be added '''
             '''to the installer besides the dependencies of '''
             '''the main package''')
    parser.add_argument(
        '-cp', '--conda_path', help='Path to conda executable')
    parser.add_argument(
        '-s', '--suffix',
        help='Suffix for the name of the generated executable')
    parser.add_argument(
        '-t', '--template',
        help='Path to .nsi template for the installer')

    args = parser.parse_args()
    from operator import attrgetter
    (python_version, bitness, setup_py_path, entrypoint, package, icon_path,
     license_path, extra_packages, conda_path, suffix, template) = attrgetter(
         'python_version', 'bitness', 'setup_py_path',
         'entrypoint', 'package', 'icon_path', 'license_path',
         'extra_packages', 'conda_path', 'suffix', 'template')(args)

    if not setup_py_path.endswith("setup.py"):
        sys.exit("Invalid path to setup.py:", setup_py_path)

    repo_root = os.path.abspath(os.path.dirname(setup_py_path))
    icon_file = os.path.abspath(icon_path)
    license_file = os.path.abspath(license_path)
    if extra_packages:
        extra_packages = os.path.abspath(extra_packages)
    if template:
        template = os.path.abspath(template)

    run(python_version, bitness, repo_root, entrypoint,
        package, icon_file, license_file, extra_packages=extra_packages,
        conda_path=conda_path, suffix=suffix, template=template)
