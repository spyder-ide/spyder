# Minor release to list

**Subject**: [ANN] Spyder 6.0.3 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **6.0.3** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes six weeks after version 6.0.2 and it contains the
following important fixes and API changes:

* Restore widget shortcuts to Preferences and allow to change them on the fly.
* Add support for IPython enhanced tracebacks and use the selected color scheme in the editor when showing them.
* Improve the way users can select the interface font in Preferences.
* Activate `Open last closed` shortcut and restore some missing context menu actions in the Editor.
* Fix several issues when getting selections to run them.
* Use the `INSTALLER_UNATTENDED` environment variable to not launch Spyder automatically if installing it in batch/silent mode from the standalone installers.
* Add `plugin_name` kwarg to the `register_shortcut_for_widget` method of
  `SpyderShortcutsMixin`.
* The `add_configuration_observer` method was added to `SpyderConfigurationObserver`.
* Add `items_elide_mode` kwarg to the constructors of `SpyderComboBox` and
  `SpyderComboBoxWithIcons`.
* The `sig_item_in_popup_changed` and `sig_popup_is_hidden` signals were added
  to `SpyderComboBox`, `SpyderComboBoxWithIcons` and `SpyderFontComboBox`.

In this release we fixed 25 issues and merged 37 pull requests. For a full
list of fixes, please see our
[Changelog](https://github.com/spyder-ide/spyder/blob/6.x/CHANGELOG.md).

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development and computing environment. Join us to help
creating your favorite environment!

Enjoy!

Daniel


----


# Major release to list

**Subject**: [ANN] Spyder 6.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **6.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release represents more than three years of development since version 5.0 was
released, and it introduces major enhancements and new features. The most important ones
are:

* New installers for Windows, Linux and macOS based on Conda and Conda-forge.
  They come up with a more robust update process and are based on Python 3.11.
* Add a Debugger pane to explore the stack frame of the current debugging
  session.
* Add a button to the Debugger pane to pause the current code execution and
  enter the debugger afterwards.
* Add submenu to the `Consoles` menu to start a new console for a specific
  Conda or Pyenv environment.
* Add ability to refresh the open Variable Explorer viewers to reflect the current
  variable value.
* Add initial support to automatically connect to remote servers through SSH
  and run code in them. This functionality can be found in the menu
  `Consoles > New console in remote server`.
* Show plots generated in the Variable Explorer or its viewers in the Plots pane.
* Show Matplotlib backend and Python environment information in the status bar.
* Make kernel restarts be much faster for the current interpreter.
* Add experimental support for Qt 6 and increase minimal required version to
  Qt 5.15.
* Turn `runfile`, `debugfile`, `runcell` and related commands into IPython magics.
 Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
  passed to the IPython console.
* Support all real number dtypes in the dataframe viewer.
* Respect Matplotlib user settings configured outside Spyder.
* Increase DPI of Matplotlib plots so they look better in high resolution screens.
* Allow to copy the absolute and relative paths of the current file to the tabs'
  context menu of the Editor.
* Restore ability to load Hdf5 and Dicom files through the Variable Explorer
  (this was working in Spyder 4 and before).
* Add ability to disable external plugins in `Preferences > Plugins`.
* Use a simpler filesystem watcher in Projects to improve performance.
* Make Spyder accept Chinese, Korean or Japanese input on Linux by adding
  `fcitx-qt5` as a new dependency (in conda environments only).
* The file switcher can browse and open files present in the current project (
  in conda environments or if the `fzf` package is installed).
* Improve how options are displayed and handled in several Variable Explorer
  viewers.
* The interface font used by the entire application can be configured in
  `Preferences > Appearance`.
* Files can be opened in the editor by pasting their path in the Working
  Directory toolbar.
* Add a new button to the Variable Explorer to indicate when variables are being
  filtered.
* Show intro message for panes that don't display content at startup.
* Add a Switcher plugin for the files and symbols switcher.
* Add a Debugger plugin to centralize all functionality related to debugging.
* Add an External Terminal plugin to execute Python and Bash/Batch/PS1 files on
  a system terminal.
* Generalize the Run plugin to support generic inputs and executors. This allows
  plugins to declare what kind of inputs (i.e. file, cell or selection) they
  can execute and how they will display the result.
* Declare a proper API for the Projects plugin.
* The Editor now uses the API introduced in Spyder 5. That was the last built-in
  plugin that needed to be migrated to it.
* The Breakpoints plugin was removed and its functionality moved to the Debugger
  one.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/6.x/CHANGELOG.md)

Spyder 5.0 has been a huge success and we hope 6.0 will be as successful. For that we
fixed 123 bugs and merged 292 pull requests from about 22 authors.

Don't forget to follow Spyder updates/news on the project's
[website](https://www.spyder-ide.org).

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development/computing environment. Join us to help creating
your favorite environment!

Enjoy!
-Daniel


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

**Subject**: [ANN] Spyder 6.0 rc2 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the second beta of our next major version: Spyder **6.0**.

We've been working on this version for more than one year now and it's working
relatively well. We encourage all people who like the bleeding edge to give it a try.

Spyder 6.0 comes with the following interesting new features and fixes:

- New features
    * New installers for Windows, Linux and macOS based on Conda and Conda-forge.
    * Add a Debugger pane to explore the stack frame of the current debugging
      session.
    * Add a button to the Debugger pane to pause the current code execution and
      enter the debugger afterwards.
    * Add submenu to the `Consoles` menu to start a new console for a specific
      Conda or Pyenv environment.
    * Add ability to refresh the open Variable Explorer viewers to reflect the current
      variable state.
    * Show plots generated in the Variable Explorer or its viewers in the Plots pane.
    * Show Matplotlib backend state in status bar.
    * Make kernel restarts be much faster for the current interpreter.
    * Turn `runfile`, `debugfile`, `runcell` and related commands into IPython magics.
    * Add a new way to manage and establish connections with remote servers/kernels

- Important fixes
    * Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
      passed to the IPython console.
    * Support all real number dtypes in the dataframe viewer.
    * Restore ability to load Hdf5 and Dicom files through the Variable Explorer
      (this was working in Spyder 4 and before).

- New API features
    * `SpyderPluginV2.get_description` must be a static method now and
      `SpyderPluginV2.get_icon` a class or static method. This is necessary to
      display the list of available plugins in Preferences in a more user-friendly
      way (see PR spyder-ide/spyder#21101).
    * Generalize the Run plugin to support generic inputs and executors. This allows
      plugins to declare what kind of inputs (i.e. file, cell or selection) they
      can execute and how they will display the result.
    * Add a new plugin called Switcher for the files and symbols switcher.
    * Declare a proper API for the Projects plugin.
    * Remove the Breakpoints plugin and add its functionality to the Debugger one.

For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md)

You can easily install this release candidate if you use conda by running:

    conda install -c conda-forge/label/spyder_dev -c conda-forge/label/spyder_kernels_rc -c conda-forge spyder=6.0.0rc2

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Daniel
