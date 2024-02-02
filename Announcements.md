# Minor release to list

**Subject**: [ANN] Spyder 5.5.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **5.5.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes ten weeks after version 5.4.5 and it contains the
following new features and important fixes:

* Drop support for Python 3.7
* Drop support for PyQt < 5.10
* Improvements to the logic that checks available updates and the update messages
* Improvements to the syntax highlighting for `match`/`case` keywords
* Improved compatibility for the standalone installer with Windows Server 2016
* Additional information about Spyder available through `spyder.appdata.xml`
* Fix Outline Explorer `Display variables and attributes` option
* Fix disabling completion and linting providers
* Fix errors when removing language servers configurations
* Fix Editor replace all occurences when using backslashes
* Fix errors when restarting external kernels
* Fix error when using the Online help with Python 3.11
* Fix debugging after errors via the `%debug` magic
* Fix compatibility with Python 2 environments/custom interpreters
* Fix application window disappearing when changing monitors
* Fix PYTHONPATH manager logic to get user environment variables and detect possible `site-packages` directories

In this release we fixed 26 issues and merged 42 pull requests that amount
to more than 151 commits. For a full list of fixes, please see our
[Changelog](https://github.com/spyder-ide/spyder/blob/5.x/CHANGELOG.md).

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development and computing environment. Join us to help
creating your favorite environment!

Enjoy!

Daniel


----


# Major release to list

**Subject**: [ANN] Spyder 5.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **5.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release represents more than one year of development since version 4.0 was
released, and it introduces major enhancements and new features. The most important ones
are:

* Improved dark theme based on QDarkstyle 3.0.
* New light theme based on QDarkstyle 3.0.
* New look and feel for toolbars.
* New icon set based on Material Design.
* New API to extend core plugins, with the exception of the Editor, IPython
  console and Projects.
* New plugins to manage menus, toolbars, layouts, shortcuts, preferences and
  status bar.
* New architecture to access and write configuration options.
* New API to declare code completion providers.
* New registries to access actions, tool buttons, toolbars and menus by their
  identifiers.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/5.x/CHANGELOG.md)

Spyder 4.0 has been a huge success and we hope 5.0 will be as successful. For that we
fixed 54 bugs, merged 142 pull requests from about 16 authors and added more than
830 commits between these two releases.

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development/computing environment. Join us to help creating
your favorite environment!

Enjoy!
-Carlos


----


# Major release to others

**Note**: Leave this free of Markdown because it could go to mailing lists that
don't support html.

**Subject**: [ANN] Spyder 4.0 is released!


Hi all,

On the behalf of the Spyder Project Contributors (https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder 3.0 has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

Spyder is a free, open-source (MIT license) interactive development environment
for the Python language with advanced editing, interactive testing, debugging
and introspection features. It was designed to provide MATLAB-like features
(integrated help, interactive console, variable explorer with GUI-based editors
for NumPy arrays and Pandas dataframes), it is strongly oriented towards
scientific computing and software development.

<The rest is the same as for the list>


----


# Alpha/beta/rc release

**Subject**: [ANN] Spyder 6.0 alpha3 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the second alpha of our next major version: Spyder **6.0**.

We've been working on this version for more than one year now and it's working
relatively well. There are still several bugs to squash but we encourage all
people who like the bleeding edge to give it a try. This alpha version includes
more than 532 commits over our latest alpha release (6.0.0a2).

Spyder 6.0 comes with the following interesting new features and fixes:

- New features
    * New installers for Windows, Linux and macOS based on Conda and Conda-forge.
    * Add a Debugger pane to explore the stack frame of the current debugging
      session.
    * Add a button to the Debugger pane to pause the current code execution and
      enter the debugger afterwards.
    * Add submenu to the `Consoles` menu to start a new console for a specific
      Conda or Pyenv environment.
    * Show Matplotlib backend state in status bar.
    * Make kernel restarts be much faster for the current interpreter.
    * Turn `runfile`, `debugfile`, `runcell` and related commands to IPython magics.

- Important fixes
    * Restore ability to load Hdf5 and Dicom files through the Variable Explorer
      (this was working in Spyder 4 and before).

- New API features
    * Generalize Run plugin to support generic inputs and executors. This allows
      plugins to declare what kind of inputs (i.e. file, cell or selection) they
      can execute and how they will display the result.
    * Add a new plugin for the files and symbols switcher.
    * Declare a proper API for the Projects plugin.

For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md)

You can easily install this alpha if you use conda by running:

    conda install -c conda-forge/label/spyder_dev -c conda-forge/label/spyder_kernels_rc -c conda-forge spyder=6.0.0a3

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Daniel
