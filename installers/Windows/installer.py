# -*- coding: utf-8 -*-
#
# Copyright © 2020 Spyder Project Contributors.
# Licensed under the terms of the GPL-3.0 License
# (see spyder/__init__.py for details)
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
Script to create a windows installer using pynsist.

Based on the Mu's win_installer.py script
https://github.com/mu-editor/mu/blob/master/win_installer.py
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile

import yarg


# Packages to remove from the requirements for example pip. Needed also for
# packages with a different import name than the package name, e.g.
# 'python-slugify' vs 'slugify' (in such case change too the
# SKIP_PACKAGES constant)
UNWANTED_PACKAGES = ['pip', 'python-slugify']

# Packages to skip checking for wheels and instead add them directly in the
# 'packages' section. Needed for example if a package has different import name
# than the package name, e.g. 'python-slugify' vs 'slugify'

SKIP_PACKAGES = ['bcrypt', 'slugify']

# The pynsist requirement spec that will be used to install pynsist in
# the temporary packaging virtual environment.

PYNSIST_REQ = "pynsist==2.5.1"

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
[Build]
installer_name={installer_name}
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
    DUNDER_ASSIGN_RE = re.compile(r"""^__\w+__\s*=\s*['"].+['"]$""")
    about = {}
    with open(os.path.join(repo_root, package, "__init__.py")) as f:
        for line in f:
            if DUNDER_ASSIGN_RE.search(line):
                exec(line, about)
    return about


def pypi_wheels_in(requirements, skip):
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
        if name in skip:
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
    Return the name component of a `name==version` formated requirement.
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
    return [package_name(p) for p in packages]


def create_pynsist_cfg(
        python, python_version, repo_root, entrypoint, package,
        icon_file, license_file, filename, encoding="latin1"):
    """
    Create a pynsist configuration file from the PYNSIST_CFG_TEMPLATE.

    Determines dependencies by running pip freeze,
    which are then split between those distributed as PyPI wheels and
    others. Returns the name of the resulting installer executable, as
    set into the pynsist configuration file.
    """
    repo_about = about_dict(repo_root, package)
    repo_package_name = repo_about["__title__"]
    repo_version = repo_about["__installer_version__"]
    repo_author = repo_about["__author__"]

    requirements = [
        # Those from pip freeze except the package itself.
        line
        for line in pip_freeze(python, encoding=encoding)
        if package_name(line) != package and \
        package_name(line) not in UNWANTED_PACKAGES
    ]
    skip_wheels = [package] + SKIP_PACKAGES
    wheels = pypi_wheels_in(requirements, skip_wheels)
    skip_packages = [package]
    packages = packages_from(requirements, wheels, skip_packages)

    installer_exe = "{}_{}bit.exe".format(repo_package_name, bitness)

    pynsist_cfg_payload = PYNSIST_CFG_TEMPLATE.format(
        name=package,
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
    )
    with open(filename, "wt", encoding=encoding) as f:
        f.write(pynsist_cfg_payload)
    print("Wrote pynsist configuration file", filename)
    print("Contents:")
    print(pynsist_cfg_payload)
    print("End of pynsist configuration file.")

    return installer_exe


def run(python_version, bitness, repo_root, entrypoint, package, icon_path,
        license_path, extra_packages=None, conda_path=None):
    """
    Run the installer generation.

    Given a certain python version, bitness, package repository root directory,
    package name, icon path and license path a pynsist configuration file
    (locking the dependencies set in setup.py) is generated and pynsist runned.
    """
    try:
        with tempfile.TemporaryDirectory(
                prefix="installer-pynsist-") as work_dir:
            print("Temporary working directory at", work_dir)

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

            print("Installing package with", env_python)
            subprocess_run([env_python, "-m",
                            "pip", "install", repo_root,
                            "--no-warn-script-location"])

            if extra_packages:
                print("Installing extra packages.")
                subprocess_run([env_python, "-m", "pip", "install", "-r",
                                extra_packages, "--no-warn-script-location"])

            pynsist_cfg = os.path.join(work_dir, "pynsist.cfg")
            print("Creating pynsist configuration file", pynsist_cfg)
            installer_exe = create_pynsist_cfg(
                env_python, python_version, repo_root, entrypoint, package,
                icon_path, license_path, pynsist_cfg)

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

    args = parser.parse_args()
    from operator import attrgetter
    (python_version, bitness, setup_py_path, entrypoint, package, icon_path,
     license_path, extra_packages, conda_path) = attrgetter(
         'python_version', 'bitness', 'setup_py_path',
         'entrypoint', 'package', 'icon_path', 'license_path',
         'extra_packages', 'conda_path')(args)

    if not setup_py_path.endswith("setup.py"):
        sys.exit("Invalid path to setup.py:", setup_py_path)

    repo_root = os.path.abspath(os.path.dirname(setup_py_path))
    icon_file = os.path.abspath(icon_path)
    license_file = os.path.abspath(license_path)
    if extra_packages:
        extra_packages = os.path.abspath(extra_packages)

    run(python_version, bitness, repo_root, entrypoint,
        package, icon_file, license_file, extra_packages=extra_packages,
        conda_path=conda_path)
