### Script from Mu windows installer


Copyright (c) 2018 Nicholas H.Tollervey.

Copyright (c) 2020- Spyder Project Contributors (see AUTHORS.txt)


Author: Nicholas H.Tollervey | ntoll@ntoll.org | https://github.com/ntoll
Site/Source: https://github.com/mu-editor/mu/
License: GPL-3.0 License | http://www.gnu.org/licenses/

Script to build an installer for Windows using Pynsist.


Mu is distributed under the GPL-3.0 license.


We use here the base functions of the script to build a Windows installer for
Spyder, mainly changing the code to generalize its functionality and configuring
the run with more arguments (package name, conda python interpreter, extra
packages, etc.).

As an NSIS installer, the generated Spyder executable has the following command line flags:
https://nsis.sourceforge.io/Docs/Chapter3.html#installerusage

Besides those flags, the installer also has the following command line options
available because it uses the `MultiUser.nsh` header file:

* `/ALLUSERS` to install for all the users
* `/CURRENTUSER` to install only for the current user (default)

See below for the full text of the GPL-3.0 license.

The current MU license can be viewed at:
https://github.com/mu-editor/mu/blob/master/LICENSE

The current version of the original files can be viewed at:
https://github.com/mu-editor/mu/blob/master/win_installer.py


Files covered:

installer.py

## Step by Step: Creating a Spyder Windows Installer

To create a Spyder Windows Installer you must follow the next steps.

### Creating a Conda Environment 

- Download and install Anaconda. You can find the latest version [here](https://www.anaconda.com/products/distribution). 
- Open the Anaconda prompt and make sure that you have admin permissions.
- Create a new environment with the following commands:

```
$ conda create -n installer python=3.8.10
$ conda activate installer
```

The first command creates an enviroment called `installer` with Python version 3.8.10 and the second one, changes the current enviroment to the new one, `installer`.

After changing to the new enviroment, install yarg with pip:

```
pip install yarg
```

### Creating Enviroment Variables

Before running the `installer.py` script, you must set first some environment variables. The list below shows all the variables that must be created:
- URL to download assets that the installer needs and that will be put on the assets directory when building the installer.
	 - `ASSETS_URL=https://github.com/spyder-ide/windows-installer-assets/releases/latest/download/assets.zip`

    Note: *This link points to the repository where the assets/extra files used by the installer construction process can be found and are being managed.*
- Packages to remove from the requirements for example pip or external direct dependencies (e.g. python-lsp-server or spyder-kernels).
  - `UNWANTED_PACKAGES=pip spyder-kernels python-slugify Rtree QDarkStyle PyNaCl`
 - Packages to skip when checking for wheels and instead add them directly in the 'packages' section, for example `bcrypt`.
   - `SKIP_PACKAGES=bcrypt slugify`
- Packages to be added to the packages section regardless wheel checks or packages skipped, for example external direct dependencies (spyder-kernels, python-lsp-server).
  - `ADD_PACKAGES=spyder_kernels blib2to3 _black_version blackd rtree qdarkstyle nacl`
- The pynsist requirement spec that will be used to install pynsist in the temporary packaging virtual environment (pynsist==2.5.1).
  - `PYNSIST_REQ=pynsist==2.7`
- Name of the installer.
  - `EXE_NAME=Spyder_64bit_full.exe`

For each variable on the list, type `set <variable=value>` in the Anaconda prompt. Another way to handle these environment variables is by using the conda `conda env config vars` command. For more information about that you can check the [conda documentation](https://docs.conda.io/projects/conda/en/latest/user-guide/tasks/manage-environments.html#setting-environment-variables).

### Running the Installer Script

Type the following line into the Anaconda prompt:

Note: *To make this line work the current working directory must be the repository root directory.*

```
python installers/Windows/installer.py 3.8.10 64 setup.py spyder.app.start:main spyder img_src/spyder.ico LICENSE.txt -ep installers/Windows/req-extras-pull-request.txt -s full -t installers/Windows/assets/nsist/spyder.nsi
```

where:

- `installers/Windows/installer.py` is the path to the installer script
- `3.8.10` is the Python version 
- `64` is the bitness of the installer
- `setup.py` is the path to the setup script
- `spyder.app.start:main` is the entrypoint to execute the package
- `spyder` is the name of the package
- `img_src/spyder.ico` is the path to the Spyder installer icon.
- `LICENSE.txt` is the path to the license file
- `installers/Windows/req-extras-pull-request.txt` is the path to the file with the requirements needed besides the dependencies of the main package.
-  `installers/Windows/assets/nsist/spyder.nsi` is the path to the .nsi template for the installer

Additionaly,
- `-ep` means path to a `.txt` file with extra packages definition
- `-s` means suffix for the name of the generated executable (it can be full or lite)
- `-t` means path to a `.nsi` file template
- The command `--help`  is also available for the `installer.py` script. This command will give you the description of all arguments needed to run it. An example for this command is shown below.
```
python installers/Windows/installer.py --help
```
