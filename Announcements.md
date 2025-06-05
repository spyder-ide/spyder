# Minor release to list

**Subject**: [ANN] Spyder 6.0.7 is released!


Hi all,

On behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **6.0.7** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes one week after version 6.0.6 and it contains the
following important fixes:

* Fix crash at startup on Windows when Conda is not available.
* Fix failure to show plots in the Plots pane due to faulty `traitlets` versions.

In this release we fixed 2 issues and merged 5 pull requests. For a full
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

**Subject**: [ANN] Spyder 6.1.0a3 is released!


Hi all,

On behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the third alpha of our next minor version: Spyder **6.1**.

We've been working on this version for around half a year now and it's working
relatively well. We encourage all people who like the bleeding edge to give it a try.

Spyder 6.1 comes with the following interesting new features and fixes:

- New features
    * Add support to work with multiple cursors to the Editor. Options to configure them are available in `Preferences > Editor > Advanced settings`.
    * Add a graphical interface to the update process of our standalone installers.
    * Paths can be added to the front of `sys.path` in the Pythonpath manager.
    * Copy/cut the current line if nothing is selected in the Editor with `Ctrl+C`/`Ctrl+V`, respectively.
    * Add option to show/hide the Editor's file name toolbar to `Preferences > Editor > Interface`.
    * Select full floating point numbers by double-clicking them on the Editor and the IPython console.

- Important fixes
    * Much better support for PyQt6 and PySide6.

- UX/UI improvements
    * Add option to hide all messages displayed in panes that are empty to `Preferences > Application > Interface`.

- API changes
    - Editor
        * **Breaking** - The `NewFile`, `OpenFile`, `OpenLastClosed`, `MaxRecentFiles`, `ClearRecentFiles`, `SaveFile`, `SaveAll`, `SaveAs`, `SaveCopyAs`, `RevertFile`, `CloseFile` and `CloseAll` actions were moved to the `ApplicationActions` class in the `Application` plugin.
        * **Breaking** - The shortcuts "new file", "open file", "open last closed", "save file", "save all", "save as", "close file 1", "close file 2" and "close all" were moved to the "main" section.
        * Add `open_last_closed`, `current_file_is_temporary`, `save_all`, `save_as`, `save_copy_as` and `revert_file` methods.
    - IPython console
        * **Breaking** - The `sig_current_directory_changed` signal now emits two strings instead of a single one.
        * **Breaking** - Remove `set_working_directory` method. You can use `set_current_client_working_directory` instead, which does the same.
        * **Breaking** - The `save_working_directory` method was made private because it's only used internally.
        * Add `sender_plugin` kwarg to the `set_current_client_working_directory` method.
        * Add `server_id` kwarg to the `set_current_client_working_directory` method.
    - Working Directory
        * **Breaking** - The `sig_current_directory_changed` signal now emits three strings instead of a single one.
        * **Breaking** - The `sender_plugin` kwarg of the `chdir` method now expects a string instead of a `SpyderPluginV2` object.
        * Add `server_id` kwarg to the `chdir` method.
    - Remote Client
        * **Breaking** - The `create_ipyclient_for_server` and `get_kernels` methods were removed.
        * Add `sig_server_changed` signal to report when a server was added or removed.
        * Add `get_server_name` method to get a server name given its id.
        * Add `register_api` and `get_api` methods in order to get and register new rest API modules for the remote client.
        * Add `get_jupyter_api` method to get the Jupyter API to interact with a remote Jupyter server.
        * Add `get_file_api` method to get the `SpyderRemoteFileServicesAPI` rest API module to manage remote file systems.
    - Pythonpath manager
        * **Breaking** - The `sig_pythonpath_changed` signal now emits a list of strings and a bool, instead of two dictionaries.
    - Application plugin
        * Add `create_new_file`, `open_file_using_dialog`, `open_file_in_plugin`, `open_last_closed_file`, `add_recent_file`, `save_file`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file`, `close_all` and `enable_file_action` methods to perform file operations in the appropriate plugin.
        * Add `focused_plugin` attribute.
    - File Explorer
        * **Breaking** - `ExplorerTreeWidgetActions` renamed to `ExplorerWidgetActions`.
        * **Breaking** - The `sig_dir_opened` signal now emits two strings instead of a single one.
        * Add `server_id` kwarg to the `chdir` method.
    - SpyderPluginV2
        * Add `CAN_HANDLE_FILE_ACTIONS` and `FILE_EXTENSIONS` attributes and `create_new_file`, `open_file`, `get_current_filename`, `current_file_is_temporary`, `open_last_closed_file`, `save_file`, `save_all`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file` and `close all` methods to allow other plugins to hook into file actions.
        * Add `sig_focused_plugin_changed` signal to signal that the plugin with focus has changed.
    - PluginMainWidget
        * Add `SHOW_MESSAGE_WHEN_EMPTY`, `MESSAGE_WHEN_EMPTY`, `IMAGE_WHEN_EMPTY`, `DESCRIPTION_WHEN_EMPTY` and `SET_LAYOUT_WHEN_EMPTY` class attributes, and `set_content_widget`, `show_content_widget` and `show_empty_message` methods to display a message when it's empty (like the one shown in the Variable Explorer).
    - Shellconnect
        * **Breaking** - Rename `is_current_widget_empty` to `is_current_widget_error_message` in `ShellConnectMainWidget`.
        * Add `switch_empty_message` to `ShellConnectMainWidget` to switch between the empty message widget and the one with content.
        * Add `ShellConnectWidgetForStackMixin` class for widgets that will be added to the stacked widget part of `ShellConnectMainWidget`.
    - AsyncDispatcher
        * **Breaking** - Remove `dispatch` method to use it directly as decorator.
        * Add class `DispatcherFuture` to `spyder.api.asyncdispatcher` and `QtSlot` method to `AsyncDispatcher` so that connected methods can be run inside the main Qt event loop.
        * Add `early_return` and `return_awaitable` kwargs its constructor.

For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md)

You can easily install this release candidate if you use conda by running:

    conda install -c conda-forge/label/spyder_dev -c conda-forge/label/spyder_kernels_rc -c conda-forge spyder=6.1.0a3

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Daniel
