Project Explorer
================

The project explorer plugin handles project management in Spyder with the 
following main features:

* import from existing Pydev (Eclipse) or Spyder projects
* add/remove project folders to/from Spyder's PYTHONPATH directly from 
  the context menu or manage these folders in a dedicated dialog box
* multiple file selection (for all available actions: open, rename, delete,
  and so on)
* file type filters

.. image:: images/projectexplorer.png

.. image:: images/projectexplorer2.png

Version Control Integration
---------------------------

Spyder has limited integration with Mercurial_ and Git_. Commit and browse
commands are available by right-clicking on relevant files that reside within
an already initialized repository. These menu picks
assume that certain commands are available on the system path.

* For Mercurial repositories, TortoiseHG_ must be installed, and either ``thg``
  or ``hgtk`` must be on the system path.
* For git repositories, the commands ``git`` and ``gitk`` must be on the 
  system path. For Windows systems, the msysgit_ package provides a convenient
  installer and the option to place common git commands on the system path without
  creating conflicts with Windows system tools.
  The second option in the dialog below is generally a safe approach.

.. image:: images/git_install_dialog.png

.. _Git: http://git-scm.com/
.. _Mercurial: http://mercurial.selenic.com/
.. _TortoiseHg: http://tortoisehg.bitbucket.org/
.. _msysgit: https://code.google.com/p/msysgit/
