### Script from Mu windows installer


Copyright (c) 2018 Nicholas H.Tollervey.

Copyright (c) 2020- Spyder Project Contributors (see AUTHORS.txt)


Author: Nicholas H.Tollervey | ntoll@ntoll.org | https://github.com/ntoll
Site/Source: https://github.com/mu-editor/mu/
License: GPL-3.0 License | http://www.gnu.org/licenses/

Script to build an installer for Windows using Pynsist.


Mu is distributed under the GPL-3.0 license.


We use here the base functions of the script to build a Windows installer of
spyder, mainly changing the code to generalize its functionality and configure
the run with more arguments (package name, conda python interpreter, extra
packages, etc.).

As a NSIS installer the generated installer counts with some command line flags:
https://nsis.sourceforge.io/Docs/Chapter3.html#installerusage

Besides those flags, the installer also counts with the command line options
available when using the `MultiUser.nsh` header file:

* `/ALLUSERS` to install for all the users
* `/CURRENTUSER` to install only for the current user (default)

See below for the full text of the GPL-3.0 license.

The current MU license can be viewed at:
https://github.com/mu-editor/mu/blob/master/LICENSE

The current version of the original files can be viewed at:
https://github.com/mu-editor/mu/blob/master/win_installer.py


Files covered:

installer.py