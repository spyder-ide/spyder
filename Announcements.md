# Minor release to list

**Subject**: [ANN] Spyder 6.1.3 is released!


Hi all,

On behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **6.1.3** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes eight weeks after version 6.1.2 and with the following interesting new features, fixes and API changes:

- New features
    * Allow to reconnect to remote kernels after the connection is lost.
    * Add ability to explore objects that depend on custom library code to the
      Variable Explorer.

- Important fixes
    * Fix memory leak on Linux when getting user's environment variables.
    * Fix several issues with the auto-update process of the standalone installers.
    * Fix segfault on closing with PyQt6.
    * Fix errors when creating new remote connections if credentials are wrong.
    * Finish fixing and improving docstrings for modules under `spyder.api`.

- API changes
    * Add `sig_update_performed` signal to Update manager plugin.
    * All public and most private APIs in `spyder.api` now have comprehensive
      docstrings and type hints with descriptions, parameters, returns and raises,
      and are thoroughly rewritten for correctness, clarity and proper formatting.
      They are also now fully built and richly rendered on the new
      [Spyder developer docs site](https://spyder-ide.github.io/spyder-api-docs/).
    * `spyder.api.plugin_registration` modules
      * The `mixins` module, containing the mixin used internally for
        handling the `@on_plugin_available` and `@on_plugin_teardown` decorators
        in the `SpyderPluginV2` class, is now documented as pending deprecation as
        a public module, will become an alias of a private `_mixins` module
        and issue a `DeprecationWarning` in Spyder 6.2, and have the public alias
        be removed in Spyder 7.0. It is a private implementation detail that wasn't
        designed or intended to be used directly by external code; plugins
        access its functionality through the `SpyderPluginV2` class instead.
      * The `registry` module's vestigial `SpyderPluginRegistry.old_plugins`
        attribute, originally added in Spyder 5 to list legacy Spyder 4 plugins,
        has been removed. It was mistakenly left over when Spyder 6 fully dropped
        support for Spyder 4 plugins, which never actually functioned as intended
        and should be updated to support modern Spyder 5+ plugins instead.
      * In the `registry` module's `SpyderPluginRegistry` class,
        setters for the `all_internal_plugins` (`set_all_internal_plugins()`),
        `all_external_plugins` (`set_all_external_plugins()`) and
        `main` (`set_main()`) instance attributes are now documented as
        pending deprecation, will raise a `DeprecationWarning` in Spyder 6.2,
        and will be removed in Spyder 7.0. Set the attributes directly instead.
      * In the `registry.SpyderPluginRegistry` class' `register_plugin()` method,
        passing arbitrary `*args` and `**kwargs` is now documented as
        pending deprecation, will raise a DeprecationWarning in Spyder 6.2
        and will be removed in Spyder 7.0. This was only needed for backward
        compatibility before the Editor plugin was migrated in Spyder 6 to the
        new plugin API introduced in Spyder 5.
    * `spyder.api.plugins` modules
      * Importing from the `enum` and `new_api` modules is now documented as
        pending deprecation. In Spyder 6.2, they will be renamed to the private
        `_enum` and `_api` modules, respectively, with the original names becoming
        aliases raising a `DeprecationWarning` on import, that will be removed
        in Spyder 7.0. They should be imported from their canonical location,
        the top-level `spyder.api.plugins` module, instead.
      * The `SpyderPluginV2`'s `main` instance attribute is now a property,
        to reduce duplication with the identically-valued `_main` attribute.
      * `SpyderPluginV2`'s `_added_toolbars` and `_actions` private attributes
        have been removed, as they are not used at least in Spyder 6 and above.
      * Obsolete checks/warnings for `SpyderPluginV2`'s removed `register()` and
        `unregister()` methods have been removed, as they have been unsupported
        since Spyder 5.1/5.2 and any code still using them is already broken.
        The respective `on_initialize()` and `on_close()` methods should be used
        instead.
    * `spyder.api.widgets` modules
      * In the `mixins` module's `SpyderActionMixin.update_actions()` method,
        remove the spurious leftover `options` parameter that does nothing, and
        is inconsistent and incompatible with all its actual current usage.
        As this is an abstract method and none of its implementations include
        it, any plugin code that does will already raise an error at runtime.
      * In the `menus` and `toolbars` modules, the `SpyderMenuProxyStyle` and
        `ToolbarStyle` proxy style classes are now documented as pending
        deprecation. In Spyder 6.2, they will be renamed to the private
        `_SpyderMenuProxyStyle` and `_ToolbarStyle` classes, respectively,
        with the original names becoming aliases raising a `DeprecationWarning`
        on use, that will be removed in Spyder 7.0. They were never intended to
        be used directly by plugins.
      * In the `toolbars` module, `ToolbarStyle.pixelMetric()` now correctly
        raises a `SpyderAPIError` (instead of silently not working as intended
        save for a spurious `print()` call) if the `TYPE` class attribute is not
        set to one of the two valid values, `"Application"` or `"MainWindow"`.
        Additionally, using `SpyderToolbar` directly rather than its
        `ApplicationToolbar` and `MainWidgetToolbar` subclasses is now documented
        as formally discouraged so their respective styling will be applied.
      * In the `toolbars` module, the `ToolTipFilter` class is now correctly
        underscored as private, as it is only for internal use handling Qt events
        by a private attribute of the `SpyderToolbar` class.

For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md)

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

**Subject**: [ANN] Spyder 6.1.0rc1 is released!


Hi all,

On behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the first release candidate of our next minor version: Spyder **6.1**.

We've been working on this version for more than half a year now and it's working
relatively well. We encourage all people who like the bleeding edge to give it a try.

Spyder 6.1 comes with the following interesting new features and fixes:

- New features
    * Add support to work with multiple cursors in the Editor. Options to configure them are available in `Preferences > Editor > Advanced settings`.
    * Rearchitect Profiler to run through the IPython console and add `%profilefile`, `%profilecell` and `%profile` magics for that.
    * Add a graphical interface to the update process of our standalone installers and base them in Python 3.12.
    * Add support to use Ruff and Flake8 for linting in the Editor.
    * Plot histograms from the dataframe viewer.
    * Add support for Polars dataframes, frozen sets, Numpy string arrays and `pathlib.Path` objects to the Variable Explorer.
    * Show the remote file system in the Files pane when a remote console has focus.
    * Add support to connect to JupyterHub servers.
    * Add support to use Pixi environments in the IPython console.
    * Paths can be added to the front of `sys.path` in the Pythonpath manager.
    * Copy/cut the current line if nothing is selected in the Editor with `Ctrl+C`/`Ctrl+X`, respectively.
    * Add option to show/hide the Editor's file name toolbar to `Preferences > Editor > Interface`.
    * Select full floating point numbers by double-clicking them on the Editor and the IPython console.

- Important fixes
    * Much better support for PyQt6 and PySide6. PyQt 6.9.0+ and PySide >=6.8.0,<6.9.0 are required now.
    * Make shortcuts to move to different panes work when they are undocked.
    * Remove blank lines around cells when copying their contents to the console.
    * Automatically kill kernels when Spyder crashes.
    * Disable magics and commands to call Python package managers in the IPython console because they don't work reliably there.
    * Add support for IPython 9.
    * Drop support for Python 3.8

- UX/UI improvements
    * Reorganize most menus to make them easier to navigate.
    * Allow to zoom in/out with Ctrl + mouse wheel in the IPython console.
    * Add `Shift+Alt+Right/Left` shortcuts to move to the next/previous console.
    * Add shortcut `Ctrl+W` to close Variable Explorer viewers.
    * Add option to hide all messages displayed in panes that are empty to `Preferences > Application > Interface`.
    * Fix plots looking blurred when scaling is enabled in high DPI screens.

- API changes
    - Editor
        * **Breaking** - The `NewFile`, `OpenFile`, `OpenLastClosed`, `MaxRecentFiles`, `ClearRecentFiles`, `SaveFile`, `SaveAll`, `SaveAs`, `SaveCopyAs`, `RevertFile`, `CloseFile`, `CloseAll`, `Undo`, `Redo`, `Cut`, `Copy`, `Paste`, `SelectAll`, `FindText`, `FindNext`, `FindPrevious` and `ReplaceText` actions were moved to the `ApplicationActions` class in the `Application` plugin.
        * **Breaking** - The shortcuts "new file", "open file", "open last closed", "save file", "save all", "save as", "close file 1", "close file 2" and "close all" were moved to the "main" section.
        * Add "undo", "redo", "cut", "copy", "paste" and "select all" shortcuts to the "main" section.
        * Add `open_last_closed`, `current_file_is_temporary`, `save_all`, `save_as`, `save_copy_as`, `revert_file`, `undo`, `redo`, `cut`, `copy`, `paste`, `select_all`, `find`, `find_next`, `find_previous` and `replace` methods.
    - IPython console
        * **Breaking** - The `sig_current_directory_changed` signal now emits two strings instead of a single one.
        * **Breaking** - Remove `set_working_directory` method. You can use `set_current_client_working_directory` instead, which does the same.
        * **Breaking** - The `save_working_directory` method was made private because it's only used internally.
        * Add `sender_plugin` kwarg to the `set_current_client_working_directory` method.
        * Add `server_id` kwarg to the `set_current_client_working_directory` method.
        * Add `Switch` entry to `IPythonConsoleWidgetMenus`.
        * Add `NextConsole` and `PreviousConsole` to `IPythonConsoleWidgetActions`.
        * Add `undo`, `redo`, `cut`, `copy`, `paste`, `select_all`, `find`, `find_next` and `find_previous` methods.
    - Working Directory
        * **Breaking** - The `sig_current_directory_changed` signal now emits three strings instead of a single one.
        * **Breaking** - The `sender_plugin` kwarg of the `chdir` method now expects a string instead of a `SpyderPluginV2` object.
        * Add `server_id` kwarg to the `chdir` method.
    - Remote Client
        * **Breaking** - The `create_ipyclient_for_server` and `get_kernels` methods were removed.
        * Add `sig_server_changed` signal to report when a server was added or removed.
        * Add `sig_create_env_requested` and `sig_import_env_requested` to request creating or importing a remote environment (they work if the Spyder-env-manager plugin is installed).
        * Add `get_server_name` method to get a server name given its id.
        * Add `register_api` and `get_api` methods in order to get and register new rest API modules for the remote client.
        * Add `get_jupyter_api` method to get the Jupyter API to interact with a remote Jupyter server.
        * Add `get_file_api` method to get the rest API module to manage remote file systems.
        * Add `get_environ_api` method to get the rest API module to work with environment variables in the remote machine.
        * Add `set_default_kernel_spec` in order to set the kernel spec used to open default consoles.
    - Pythonpath manager
        * **Breaking** - The `sig_pythonpath_changed` signal now emits a list of strings and a bool, instead of two dictionaries.
    - Application plugin
        * Add `create_new_file`, `open_file_using_dialog`, `open_file_in_plugin`, `open_last_closed_file`, `add_recent_file`, `save_file`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file`, `close_all` and `enable_file_action` methods to perform file operations in the appropriate plugin.
        * Add `undo`, `redo`, `cut`, `copy`, `paste`, `select_all` and `enable_edit_action` methods to perform edit operations in the appropriate plugin.
        * Add `find`, `find_next`, `find_previous`, `replace` and `enable_search_action` methods to perform search operations in the appropriate plugin.
        * Add `focused_plugin` attribute.
    - File Explorer
        * **Breaking** - `ExplorerTreeWidgetActions` renamed to `ExplorerWidgetActions`.
        * **Breaking** - The `sig_dir_opened` signal now emits two strings instead of a single one.
        * Add `server_id` kwarg to the `chdir` method.
    - Profiler
        * **Breaking** - Remove `sig_started` and `sig_finished` signals, and `run_profiler`, `stop_profiler` and `run_file` methods.
        * **Breaking** - Remove `ProfilerWidgetToolbars` and `ProfilerWidgetInformationToolbarSections` enums
        * Add `ProfilerWidgetMenus`, `ProfilerContextMenuSections` and `ProfilerWidgetContextMenuActions` enums.
        * Add `profile_file`, `profile_cell` and `profile_selection` methods.
    - Main menu
        * **Breaking** - From `SourceMenuSections`, move the `Formatting` section to `EditMenuSections` and `Cursor` to `SearchMenuSections`, remove the `CodeAnalysis` section and add the `Autofix` section.
        * **Breaking** - Replace the `Tools`, `External` and `Extras` sections in `ToolsMenuSections` with `Managers` and `Preferences`.
        * **Future Breaking** - Rename the `View` menu to `Window` in `ApplicationMenus` and `ViewMenuSections` to `WindowMenuSections`; aliases are retained for backward compatibility but may be removed in Spyder 7+.
        * Add `Profile` constant to `RunMenuSections`.
    - Toolbar
        * Add `Profile` constant to `ApplicationToolbars`.
    - SpyderPluginV2
        * Add `CAN_HANDLE_FILE_ACTIONS` and `FILE_EXTENSIONS` attributes and `create_new_file`, `open_file`, `get_current_filename`, `current_file_is_temporary`, `open_last_closed_file`, `save_file`, `save_all`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file` and `close all` methods to allow other plugins to hook into file actions.
        * Add `CAN_HANDLE_EDIT_ACTIONS` attribute and `undo`, `redo`, `cut`, `copy`, `paste` and `select_all` methods to allow other plugins to hook into edit actions.
        * Add `CAN_HANDLE_SEARCH_ACTIONS` attribute and `find`, `find_next`, `find_previous` and `replace`  methods to allow other plugins to hook into search actions.
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
    - General API
        * **Breaking** - Remove `old_conf_version` method from `SpyderConfigurationAccessor`.
        * Add `OptionalPlugins` enum for plugins that Spyder can rely on to provide additional functionality.

For a more complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/master/changelogs/Spyder-6.md)

You can easily install this release candidate if you use conda by running:

    conda install -c conda-forge/label/spyder_rc -c conda-forge/label/spyder_kernels_rc -c conda-forge spyder=6.1.0rc1

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!
Daniel
