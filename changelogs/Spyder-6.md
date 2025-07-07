# History of changes for Spyder 6

## Version 6.1.0 (Unreleased)

### New features

* Add support to work with multiple cursors in the Editor. Options to configure them are available in `Preferences > Editor > Advanced settings`.
* Add a graphical interface to the update process of our standalone installers.
* Plot histograms from the dataframe viewer.
* Add support for `frozenset`, Numpy string arrays and `pathlib.Path` objects to the Variable Explorer.
* Show the remote file system in the Files pane when a remote console has focus.
* Add support to use Pixi environments in the IPython console.
* Paths can be added to the front of `sys.path` in the Pythonpath manager.
* Copy/cut the current line if nothing is selected in the Editor with `Ctrl+C`/`Ctrl+X`, respectively.
* Add option to show/hide the Editor's file name toolbar to `Preferences > Editor > Interface`.
* Select full floating point numbers by double-clicking them on the Editor and the IPython console.

### Important fixes

* Much better support for PyQt6 and PySide6.
* Make shortcuts to move to different panes work when they are undocked.
* Disable magics and commands to call Python package managers in the IPython console because they don't work reliably there.
* Drop support for Python 3.8

### UX/UI improvements

* Add option to hide all messages displayed in panes that are empty to `Preferences > Application > Interface`.

### API changes

#### Editor

* **Breaking** - The `NewFile`, `OpenFile`, `OpenLastClosed`, `MaxRecentFiles`, `ClearRecentFiles`, `SaveFile`, `SaveAll`, `SaveAs`, `SaveCopyAs`, `RevertFile`, `CloseFile` and `CloseAll` actions were moved to the `ApplicationActions` class in the `Application` plugin.
* **Breaking** - The shortcuts "new file", "open file", "open last closed", "save file", "save all", "save as", "close file 1", "close file 2" and "close all" were moved to the "main" section.
* Add `open_last_closed`, `current_file_is_temporary`, `save_all`, `save_as`, `save_copy_as` and `revert_file` methods.

#### IPython console

* **Breaking** - The `sig_current_directory_changed` signal now emits two strings instead of a single one.
* **Breaking** - Remove `set_working_directory` method. You can use `set_current_client_working_directory` instead, which does the same.
* **Breaking** - The `save_working_directory` method was made private because it's only used internally.
* Add `sender_plugin` kwarg to the `set_current_client_working_directory` method.
* Add `server_id` kwarg to the `set_current_client_working_directory` method.

#### Working Directory

* **Breaking** - The `sig_current_directory_changed` signal now emits three strings instead of a single one.
* **Breaking** - The `sender_plugin` kwarg of the `chdir` method now expects a string instead of a `SpyderPluginV2` object.
* Add `server_id` kwarg to the `chdir` method.


#### Remote Client

* **Breaking** - The `create_ipyclient_for_server` and `get_kernels` methods were removed.
* Add `sig_server_changed` signal to report when a server was added or removed.
* Add `get_server_name` method to get a server name given its id.
* Add `register_api` and `get_api` methods in order to get and register new rest API modules for the remote client.
* Add `get_jupyter_api` method to get the Jupyter API to interact with a remote Jupyter server.
* Add `get_file_api` method to get the rest API module to manage remote file systems.
* Add `get_environ_api` method to get the rest API module to work with environment variables in the remote machine.

#### Pythonpath manager

* **Breaking** - The `sig_pythonpath_changed` signal now emits a list of strings and a bool, instead of two dictionaries.

#### Application plugin

* Add `create_new_file`, `open_file_using_dialog`, `open_file_in_plugin`, `open_last_closed_file`, `add_recent_file`, `save_file`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file`, `close_all` and `enable_file_action` methods to perform file operations in the appropriate plugin.
* Add `focused_plugin` attribute.

#### File Explorer

* **Breaking** - `ExplorerTreeWidgetActions` renamed to `ExplorerWidgetActions`.
* **Breaking** - The `sig_dir_opened` signal now emits two strings instead of a single one.
* Add `server_id` kwarg to the `chdir` method.

### Main menu

* **Breaking** - From `SourceMenuSections`, move the `Formatting` section to `EditMenuSections` and `Cursor` to `SearchMenuSections`, remove the `CodeAnalysis` section and add the `Autofix` section.
* **Breaking** - Replace the `Tools`, `External` and `Extras` sections in `ToolsMenuSections` with `Managers` and `Preferences`.

#### SpyderPluginV2

* Add `CAN_HANDLE_FILE_ACTIONS` and `FILE_EXTENSIONS` attributes and `create_new_file`, `open_file`, `get_current_filename`, `current_file_is_temporary`, `open_last_closed_file`, `save_file`, `save_all`, `save_file_as`, `save_copy_as`, `revert_file`, `close_file` and `close all` methods to allow other plugins to hook into file actions.
* Add `sig_focused_plugin_changed` signal to signal that the plugin with focus has changed.

#### PluginMainWidget

* Add `SHOW_MESSAGE_WHEN_EMPTY`, `MESSAGE_WHEN_EMPTY`, `IMAGE_WHEN_EMPTY`, `DESCRIPTION_WHEN_EMPTY` and `SET_LAYOUT_WHEN_EMPTY` class attributes,
  and `set_content_widget`, `show_content_widget` and `show_empty_message` methods to display a message when it's empty (like the one shown in
  the Variable Explorer).

#### Shellconnect

* **Breaking** - Rename `is_current_widget_empty` to `is_current_widget_error_message` in `ShellConnectMainWidget`.
* Add `switch_empty_message` to `ShellConnectMainWidget` to switch between the empty message widget and the one with content.
* Add `ShellConnectWidgetForStackMixin` class for widgets that will be added to the stacked widget part of `ShellConnectMainWidget`.

#### AsyncDispatcher

* **Breaking** - Remove `dispatch` method to use it directly as decorator.
* Add class `DispatcherFuture` to `spyder.api.asyncdispatcher` and `QtSlot` method to `AsyncDispatcher` so that connected methods can be run inside the main Qt event loop.
* Add `early_return` and `return_awaitable` kwargs its constructor.

----

## Version 6.1.0a3 (2025/06/05)

### Issues Closed

* [Issue 24504](https://github.com/spyder-ide/spyder/issues/24504) - Error when starting the debugger ([PR 24508](https://github.com/spyder-ide/spyder/pull/24508) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24442](https://github.com/spyder-ide/spyder/issues/24442) - Annotations are not limited to comments ([PR 24491](https://github.com/spyder-ide/spyder/pull/24491) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24423](https://github.com/spyder-ide/spyder/issues/24423) - Add shortcut for `Replace all` action ([PR 24444](https://github.com/spyder-ide/spyder/pull/24444) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24370](https://github.com/spyder-ide/spyder/issues/24370) - Error with Open file dialog on macOS ([PR 24416](https://github.com/spyder-ide/spyder/pull/24416) by [@mrclary](https://github.com/mrclary))
* [Issue 24306](https://github.com/spyder-ide/spyder/issues/24306) - Add support for `frozenset` to Variable Explorer ([PR 24307](https://github.com/spyder-ide/spyder/pull/24307) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 24280](https://github.com/spyder-ide/spyder/issues/24280) - Error on `PaneEmptyWidget` resize event ([PR 24303](https://github.com/spyder-ide/spyder/pull/24303) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23558](https://github.com/spyder-ide/spyder/issues/23558) - Add support to activate environments with Pixi ([PR 23919](https://github.com/spyder-ide/spyder/pull/23919) by [@dalthviz](https://github.com/dalthviz))
* [Issue 23415](https://github.com/spyder-ide/spyder/issues/23415) - Spyder fails to launch on MacOS with case-sensitive root volume ([PR 24321](https://github.com/spyder-ide/spyder/pull/24321) by [@mrclary](https://github.com/mrclary))
* [Issue 22570](https://github.com/spyder-ide/spyder/issues/22570) - Array of strings not displayed in Variable Explorer pane ([PR 24150](https://github.com/spyder-ide/spyder/pull/24150) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 22351](https://github.com/spyder-ide/spyder/issues/22351) - ENH: Show repr() info on a WindowPath variable ([PR 24330](https://github.com/spyder-ide/spyder/pull/24330) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21894](https://github.com/spyder-ide/spyder/issues/21894) - `conda` gives `error: incomplete escape \U` when trying to install package in the IPython console ([PR 24344](https://github.com/spyder-ide/spyder/pull/24344) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21683](https://github.com/spyder-ide/spyder/issues/21683) - Viewing older plots drags you down to the newly made plots while the code is running ([PR 24279](https://github.com/spyder-ide/spyder/pull/24279) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21659](https://github.com/spyder-ide/spyder/issues/21659) - Files are not moved to the operating system trash can after deleting them in Files or Projects ([PR 24382](https://github.com/spyder-ide/spyder/pull/24382) by [@jsbautista](https://github.com/jsbautista))
* [Issue 21025](https://github.com/spyder-ide/spyder/issues/21025) - Feature: Support creating histograms and showing images for dataframes ([PR 24266](https://github.com/spyder-ide/spyder/pull/24266) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 6853](https://github.com/spyder-ide/spyder/issues/6853) - None displays as NoneType in Variable Explorer ([PR 24330](https://github.com/spyder-ide/spyder/pull/24330) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 4126](https://github.com/spyder-ide/spyder/issues/4126) - Cannot input unicode character with `Ctrl+Shift+U` in the Editor ([PR 24381](https://github.com/spyder-ide/spyder/pull/24381) by [@jsbautista](https://github.com/jsbautista))
* [Issue 1351](https://github.com/spyder-ide/spyder/issues/1351) - Undocked windows are not reachable by shortcut ([PR 24424](https://github.com/spyder-ide/spyder/pull/24424) by [@jsbautista](https://github.com/jsbautista))

In this release 17 issues were closed.

### Pull Requests Merged

* [PR 24536](https://github.com/spyder-ide/spyder/pull/24536) - PR: Update `spyder-kernels` to 3.1.0a2 (for Spyder 6.1.0a3), by [@dalthviz](https://github.com/dalthviz)
* [PR 24508](https://github.com/spyder-ide/spyder/pull/24508) - PR: Catch any error when creating a new Pdb history session (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([24504](https://github.com/spyder-ide/spyder/issues/24504))
* [PR 24507](https://github.com/spyder-ide/spyder/pull/24507) - PR: Fix Remote client tests by passing `ClientSession` loop when closing APIs (Jupyter and Files APIs), by [@dalthviz](https://github.com/dalthviz)
* [PR 24493](https://github.com/spyder-ide/spyder/pull/24493) - PR: Increase minimal supported Python version to 3.9, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24491](https://github.com/spyder-ide/spyder/pull/24491) - PR: Make editor annotations be limited to comments, by [@jsbautista](https://github.com/jsbautista) ([24442](https://github.com/spyder-ide/spyder/issues/24442))
* [PR 24482](https://github.com/spyder-ide/spyder/pull/24482) - PR: Move filter and refresh actions to be part of the corner widgets (Files), by [@dalthviz](https://github.com/dalthviz)
* [PR 24480](https://github.com/spyder-ide/spyder/pull/24480) - PR: Remove unnecessary margins around `RemoteExplorer` widget (Files), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24445](https://github.com/spyder-ide/spyder/pull/24445) - PR: Change shortcut to transform text to lowercase (Editor), by [@jsbautista](https://github.com/jsbautista)
* [PR 24444](https://github.com/spyder-ide/spyder/pull/24444) - PR: Add shortcut to find/replace widget to replace all found instances, by [@jsbautista](https://github.com/jsbautista) ([24423](https://github.com/spyder-ide/spyder/issues/24423))
* [PR 24427](https://github.com/spyder-ide/spyder/pull/24427) - PR: Fix executable used for restarts on macOS, by [@mrclary](https://github.com/mrclary)
* [PR 24424](https://github.com/spyder-ide/spyder/pull/24424) - PR: Make shortcuts to move to plugins work when they are undocked, by [@jsbautista](https://github.com/jsbautista) ([1351](https://github.com/spyder-ide/spyder/issues/1351))
* [PR 24416](https://github.com/spyder-ide/spyder/pull/24416) - PR: Fix UnboundLocalError when cancelling the open file dialog, by [@mrclary](https://github.com/mrclary) ([24370](https://github.com/spyder-ide/spyder/issues/24370))
* [PR 24382](https://github.com/spyder-ide/spyder/pull/24382) - PR : Move files to the OS trash can when deleting them in Files or Projects, by [@jsbautista](https://github.com/jsbautista) ([21659](https://github.com/spyder-ide/spyder/issues/21659))
* [PR 24381](https://github.com/spyder-ide/spyder/pull/24381) - PR : Change shortcut to transform text to uppercase (Editor), by [@jsbautista](https://github.com/jsbautista) ([4126](https://github.com/spyder-ide/spyder/issues/4126))
* [PR 24344](https://github.com/spyder-ide/spyder/pull/24344) - PR: Disable magics and commands to call Python package managers in the IPython console, by [@ccordoba12](https://github.com/ccordoba12) ([21894](https://github.com/spyder-ide/spyder/issues/21894))
* [PR 24331](https://github.com/spyder-ide/spyder/pull/24331) - PR: Rename `PaneEmptyWidget` to `EmptyMessageWidget` (Widgets), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24330](https://github.com/spyder-ide/spyder/pull/24330) - PR: Display `pathlib.Path` variables and `None` in Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([6853](https://github.com/spyder-ide/spyder/issues/6853), [22351](https://github.com/spyder-ide/spyder/issues/22351))
* [PR 24327](https://github.com/spyder-ide/spyder/pull/24327) - PR: Add ability to filter elements in `ElementsTable`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24321](https://github.com/spyder-ide/spyder/pull/24321) - PR: Rename resources to Resources in our runtime environment for macOS case-sensitive file systems (Installers), by [@mrclary](https://github.com/mrclary) ([23415](https://github.com/spyder-ide/spyder/issues/23415))
* [PR 24314](https://github.com/spyder-ide/spyder/pull/24314) - PR: Updater implementation improvements (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 24311](https://github.com/spyder-ide/spyder/pull/24311) - PR: Remove 6.x branch from weekly scheduled installer build, by [@mrclary](https://github.com/mrclary)
* [PR 24307](https://github.com/spyder-ide/spyder/pull/24307) - PR: Treat `frozenset` as `set` in Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([24306](https://github.com/spyder-ide/spyder/issues/24306))
* [PR 24303](https://github.com/spyder-ide/spyder/pull/24303) - PR: Fix error when resizing not visible `PaneEmptyWidget`'s, by [@ccordoba12](https://github.com/ccordoba12) ([24280](https://github.com/spyder-ide/spyder/issues/24280))
* [PR 24279](https://github.com/spyder-ide/spyder/pull/24279) - PR: Do not scroll to the bottom if last plot is not selected (Plots), by [@jitseniesen](https://github.com/jitseniesen) ([21683](https://github.com/spyder-ide/spyder/issues/21683))
* [PR 24268](https://github.com/spyder-ide/spyder/pull/24268) - PR: Add support to connect to JupyterHub instances (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 24266](https://github.com/spyder-ide/spyder/pull/24266) - PR: Plot histogram from dataframe editor (Variable Explorer), by [@jitseniesen](https://github.com/jitseniesen) ([21025](https://github.com/spyder-ide/spyder/issues/21025))
* [PR 24249](https://github.com/spyder-ide/spyder/pull/24249) - PR: Improve UI of dialog to create new projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24150](https://github.com/spyder-ide/spyder/pull/24150) - PR: Show contents of Numpy string arrays in the Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([22570](https://github.com/spyder-ide/spyder/issues/22570))
* [PR 23986](https://github.com/spyder-ide/spyder/pull/23986) - PR: Add support for displaying remote files (File Explorer, Working Directory), by [@dalthviz](https://github.com/dalthviz)
* [PR 23919](https://github.com/spyder-ide/spyder/pull/23919) - PR: Support activation of Pixi environments, by [@dalthviz](https://github.com/dalthviz) ([23558](https://github.com/spyder-ide/spyder/issues/23558))

In this release 30 pull requests were closed.

----

## Version 6.1.0a2 (2025/04/22)

### Issues Closed

* [Issue 23951](https://github.com/spyder-ide/spyder/issues/23951) - Multi-Cursor editing uses non-standard mouse shortcuts which cannot be configured ([PR 23463](https://github.com/spyder-ide/spyder/pull/23463) by [@athompson673](https://github.com/athompson673))
* [Issue 23691](https://github.com/spyder-ide/spyder/issues/23691) - Multi-Cursor paste does not paste entire clipboard, or pastes nothing for some cursors ([PR 24223](https://github.com/spyder-ide/spyder/pull/24223) by [@athompson673](https://github.com/athompson673))
* [Issue 23607](https://github.com/spyder-ide/spyder/issues/23607) - Remove Editor top bar showing file path ([PR 24194](https://github.com/spyder-ide/spyder/pull/24194) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22354](https://github.com/spyder-ide/spyder/issues/22354) - Provide custom editor widget for given file extension via plugin ([PR 22564](https://github.com/spyder-ide/spyder/pull/22564) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21197](https://github.com/spyder-ide/spyder/issues/21197) - Minimum size of empty pane is fairly big ([PR 24181](https://github.com/spyder-ide/spyder/pull/24181) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 7794](https://github.com/spyder-ide/spyder/issues/7794) - Allow plugins to hook into File > Open ([PR 22564](https://github.com/spyder-ide/spyder/pull/22564) by [@jitseniesen](https://github.com/jitseniesen))

In this release 6 issues were closed.

### Pull Requests Merged

* [PR 24276](https://github.com/spyder-ide/spyder/pull/24276) - PR: Add new features and improvements for 6.1.0 to our Changelog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24257](https://github.com/spyder-ide/spyder/pull/24257) - PR: Follow-up to removing `CONF` from `mouse_shortcuts` (Editor), by [@athompson673](https://github.com/athompson673)
* [PR 24250](https://github.com/spyder-ide/spyder/pull/24250) - PR: Remove `CONF` usage in `MouseShortcutEditor` (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24223](https://github.com/spyder-ide/spyder/pull/24223) - PR: Add multicursor paste behavior configuration to Preferences (Editor), by [@athompson673](https://github.com/athompson673) ([23691](https://github.com/spyder-ide/spyder/issues/23691))
* [PR 24213](https://github.com/spyder-ide/spyder/pull/24213) - PR: Update `python-lsp-server` and `qtconsole` subrepos, by [@mrclary](https://github.com/mrclary)
* [PR 24204](https://github.com/spyder-ide/spyder/pull/24204) - PR: Fix several issues in the Layout plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24194](https://github.com/spyder-ide/spyder/pull/24194) - PR: Add option to show/hide file name toolbar (Editor), by [@jsbautista](https://github.com/jsbautista) ([23607](https://github.com/spyder-ide/spyder/issues/23607))
* [PR 24181](https://github.com/spyder-ide/spyder/pull/24181) - PR: Add API to display an empty message in any dockable plugin (API), by [@ccordoba12](https://github.com/ccordoba12) ([21197](https://github.com/spyder-ide/spyder/issues/21197))
* [PR 24144](https://github.com/spyder-ide/spyder/pull/24144) - PR: Use `spyder-updater` to handle updates (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 24131](https://github.com/spyder-ide/spyder/pull/24131) - PR: Use checksum to verify downloaded asset for updating Spyder (Update manager), by [@mrclary](https://github.com/mrclary)
* [PR 24014](https://github.com/spyder-ide/spyder/pull/24014) - PR: Return an iterable from `ls` method of `SpyderRemoteFileServicesAPI` (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 23732](https://github.com/spyder-ide/spyder/pull/23732) - PR: Fixes to make the app work with PySide6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23720](https://github.com/spyder-ide/spyder/pull/23720) - PR: Refactor Remote Client kernel management, by [@hlouzada](https://github.com/hlouzada)
* [PR 23463](https://github.com/spyder-ide/spyder/pull/23463) - PR: Make `CodeEditor` mouse shortcuts configurable (Editor), by [@athompson673](https://github.com/athompson673) ([23951](https://github.com/spyder-ide/spyder/issues/23951))
* [PR 23287](https://github.com/spyder-ide/spyder/pull/23287) - PR: Refactor how the installers are built, by [@mrclary](https://github.com/mrclary)
* [PR 22564](https://github.com/spyder-ide/spyder/pull/22564) - PR: Allow plugins to hook into file actions (API), by [@jitseniesen](https://github.com/jitseniesen) ([7794](https://github.com/spyder-ide/spyder/issues/7794), [22354](https://github.com/spyder-ide/spyder/issues/22354))

In this release 16 pull requests were closed.

----

## Version 6.1.0a1 (2025/03/13)

### Issues Closed

* [Issue 22830](https://github.com/spyder-ide/spyder/issues/22830) - A couple of errors with PyQt6 ([PR 22846](https://github.com/spyder-ide/spyder/pull/22846) by [@fxjaeckel](https://github.com/fxjaeckel))
* [Issue 22207](https://github.com/spyder-ide/spyder/issues/22207) - Feature: Select full floating point numbers by double-clicking on them ([PR 22728](https://github.com/spyder-ide/spyder/pull/22728) by [@athompson673](https://github.com/athompson673))
* [Issue 21264](https://github.com/spyder-ide/spyder/issues/21264) - Request: copy entire line with CTRL+C and no selection ([PR 22480](https://github.com/spyder-ide/spyder/pull/22480) by [@The-Ludwig](https://github.com/The-Ludwig))
* [Issue 17066](https://github.com/spyder-ide/spyder/issues/17066) - Suggestion: insert paths from PYTHONPATH manager before system's PYTHONPATH ([PR 21769](https://github.com/spyder-ide/spyder/pull/21769) by [@mrclary](https://github.com/mrclary))
* [Issue 8574](https://github.com/spyder-ide/spyder/issues/8574) - Feature Suggestion: Cut current line ([PR 22480](https://github.com/spyder-ide/spyder/pull/22480) by [@The-Ludwig](https://github.com/The-Ludwig))
* [Issue 2112](https://github.com/spyder-ide/spyder/issues/2112) - Add multiline editing to the Editor ([PR 22996](https://github.com/spyder-ide/spyder/pull/22996) by [@athompson673](https://github.com/athompson673))

In this release 6 issues were closed.

### Pull Requests Merged

* [PR 23946](https://github.com/spyder-ide/spyder/pull/23946) - PR: Update `spyder-kernels` to 3.1.0a1 (for Spyder 6.1.0a1), by [@dalthviz](https://github.com/dalthviz)
* [PR 23944](https://github.com/spyder-ide/spyder/pull/23944) - PR: Check async changes to debugger completions (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23932](https://github.com/spyder-ide/spyder/pull/23932) - PR: Fix `sig_current_directory_changed` signal of the Working directory plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23754](https://github.com/spyder-ide/spyder/pull/23754) - PR: Fix workflow to run tests with PyQt6 (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23721](https://github.com/spyder-ide/spyder/pull/23721) - PR: Use `AsyncDispatcher` as class decorator (API), by [@hlouzada](https://github.com/hlouzada)
* [PR 23481](https://github.com/spyder-ide/spyder/pull/23481) - PR: Add `ipython_pygments_lexers` as a new dependency, by [@takluyver](https://github.com/takluyver)
* [PR 23447](https://github.com/spyder-ide/spyder/pull/23447) - PR: Fix code style for some multicursor tests (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23381](https://github.com/spyder-ide/spyder/pull/23381) - PR: Add remote filesystem API to the Remote client plugin, by [@hlouzada](https://github.com/hlouzada)
* [PR 23320](https://github.com/spyder-ide/spyder/pull/23320) - PR: Make `TextEditBaseWidget.__move_line_or_selection` public, by [@athompson673](https://github.com/athompson673)
* [PR 23118](https://github.com/spyder-ide/spyder/pull/23118) - PR: Add workflow to run tests with PyQt6 (CI), by [@rear1019](https://github.com/rear1019)
* [PR 23100](https://github.com/spyder-ide/spyder/pull/23100) - PR: Use style functions from `spyder-kernels` (IPython Console), by [@dalthviz](https://github.com/dalthviz)
* [PR 23079](https://github.com/spyder-ide/spyder/pull/23079) - PR: Update Remote client plugin to the new `spyder-remote-services` API, by [@hlouzada](https://github.com/hlouzada)
* [PR 22996](https://github.com/spyder-ide/spyder/pull/22996) - PR: Add multi-cursor support to the Editor, by [@athompson673](https://github.com/athompson673) ([2112](https://github.com/spyder-ide/spyder/issues/2112))
* [PR 22846](https://github.com/spyder-ide/spyder/pull/22846) - PR: Fix error with PyQt6 when pasting code with middle-click on Linux, by [@fxjaeckel](https://github.com/fxjaeckel) ([22830](https://github.com/spyder-ide/spyder/issues/22830))
* [PR 22728](https://github.com/spyder-ide/spyder/pull/22728) - PR: Select full floating point numbers by double-clicking them, by [@athompson673](https://github.com/athompson673) ([22207](https://github.com/spyder-ide/spyder/issues/22207))
* [PR 22670](https://github.com/spyder-ide/spyder/pull/22670) - PR: Fix issue where cache keys with spaces are not removed (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22663](https://github.com/spyder-ide/spyder/pull/22663) - PR: Purge workflow cache weekly, by [@mrclary](https://github.com/mrclary)
* [PR 22662](https://github.com/spyder-ide/spyder/pull/22662) - PR: Replace `is_anaconda` with `is_conda_env`, by [@mrclary](https://github.com/mrclary)
* [PR 22642](https://github.com/spyder-ide/spyder/pull/22642) - PR: Simplify min/max required versions of spyder-kernels in the master branch (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22620](https://github.com/spyder-ide/spyder/pull/22620) - PR: Various additional fixes for Qt 6 compatibility, by [@rear1019](https://github.com/rear1019)
* [PR 22576](https://github.com/spyder-ide/spyder/pull/22576) - PR: Remove `dock_toolbar` attribute from the Editor main widget, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22480](https://github.com/spyder-ide/spyder/pull/22480) - PR: Copy/cut entire line if nothing is selected (Editor), by [@The-Ludwig](https://github.com/The-Ludwig) ([8574](https://github.com/spyder-ide/spyder/issues/8574), [21264](https://github.com/spyder-ide/spyder/issues/21264))
* [PR 22465](https://github.com/spyder-ide/spyder/pull/22465) - PR: Update dev version to correctly reflect what `master` is pointing at, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21891](https://github.com/spyder-ide/spyder/pull/21891) - PR: Pass paths from the Pythonpath manager to the Pylint plugin, by [@znapy](https://github.com/znapy)
* [PR 21769](https://github.com/spyder-ide/spyder/pull/21769) - PR: Add option to prepend or append Pythonpath Manager paths to `sys.path`, by [@mrclary](https://github.com/mrclary) ([17066](https://github.com/spyder-ide/spyder/issues/17066))

In this release 25 pull requests were closed.

----

## Version 6.0.7 (2025/05/22)

### Important fixes

* Fix crash at startup on Windows when Conda is not available.
* Fix failure to show plots in the Plots pane due to faulty `traitlets` versions.

### Issues Closed

* [Issue 24421](https://github.com/spyder-ide/spyder/issues/24421) - Spyder 6.0.6 crashes at startup ([PR 24448](https://github.com/spyder-ide/spyder/pull/24448) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24390](https://github.com/spyder-ide/spyder/issues/24390) - Inline plots are not working due to faulty `traitlets` versions ([PR 24450](https://github.com/spyder-ide/spyder/pull/24450) by [@ccordoba12](https://github.com/ccordoba12))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 24458](https://github.com/spyder-ide/spyder/pull/24458) - PR: Update `spyder-kernels` to 3.0.5 (for Spyder 6.0.7), by [@dalthviz](https://github.com/dalthviz)
* [PR 24450](https://github.com/spyder-ide/spyder/pull/24450) - PR: Require a minimal version of the `traitlets` package (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([24390](https://github.com/spyder-ide/spyder/issues/24390))
* [PR 24448](https://github.com/spyder-ide/spyder/pull/24448) - PR: Fix hard crash when checking conda for cached kernels (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([24421](https://github.com/spyder-ide/spyder/issues/24421))
* [PR 24425](https://github.com/spyder-ide/spyder/pull/24425) - PR: Fix cached kernels on Windows for CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24399](https://github.com/spyder-ide/spyder/pull/24399) - PR: Try to decrease `test_dedicated_consoles` flakyness (CI/Tests), by [@dalthviz](https://github.com/dalthviz)

In this release 5 pull requests were closed.

----

## Version 6.0.6 (2025/05/14)

### New features

* Make Editor annotations (like `FIXME` or `HINT`) work in lowercase.
* Retore `Quit` action to the the IPython console context menu.
* Don't advance line when running code if there's selected text in the Editor.

### Important fixes

* Prevent breakpoints from disappearing when formatting code.
* Fix remote connections error when using the `Key file` authentication method.
* Respect case sensitivity of working directory when running code.
* Disable fullscreen mode when running on the Windows Subsystem for Linux.
* Several fixes to prevent the Editor and Find panes from taking too much horizontal space.
* Show a better error message when failing to open objects in the Variable Explorer due to a mismatch of Python versions.
* Fix opening Files pane context menu when clicking on its blank area.
* Remove `QtWebEngine` requirement to show the `Help Spyder` action.
* Prevent `Matplotlib` cache font message from being displayed.
* Ensure color scheme changes are applied to all the open files.

### Issues Closed

* [Issue 24318](https://github.com/spyder-ide/spyder/issues/24318) - Typo in updating script ([PR 24322](https://github.com/spyder-ide/spyder/pull/24322) by [@mrclary](https://github.com/mrclary))
* [Issue 24281](https://github.com/spyder-ide/spyder/issues/24281) - `FileNotFoundError` when removing autosave file ([PR 24329](https://github.com/spyder-ide/spyder/pull/24329) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24205](https://github.com/spyder-ide/spyder/issues/24205) - Cannot open context menu when right-clicking the blank area of Files pane ([PR 24299](https://github.com/spyder-ide/spyder/pull/24299) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24188](https://github.com/spyder-ide/spyder/issues/24188) - Find pane is too wide after searching for a long string ([PR 24239](https://github.com/spyder-ide/spyder/pull/24239) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24153](https://github.com/spyder-ide/spyder/issues/24153) - Error in console with message `Matplotlib is building the font cache; this may take a moment.` ([PR 24176](https://github.com/spyder-ide/spyder/pull/24176) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24132](https://github.com/spyder-ide/spyder/issues/24132) - `The process cannot access the file because it is being used by another process` error when starting a console ([PR 24389](https://github.com/spyder-ide/spyder/pull/24389) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24125](https://github.com/spyder-ide/spyder/issues/24125) - Can't open user defined class in Variable explorer ([PR 24349](https://github.com/spyder-ide/spyder/pull/24349) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24096](https://github.com/spyder-ide/spyder/issues/24096) - Restore Quit action in IPython console context menu ([PR 24145](https://github.com/spyder-ide/spyder/pull/24145) by [@jsbautista](https://github.com/jsbautista))
* [Issue 24094](https://github.com/spyder-ide/spyder/issues/24094) - ValueError when trying to open a dataframe ([PR 24106](https://github.com/spyder-ide/spyder/pull/24106) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24091](https://github.com/spyder-ide/spyder/issues/24091) - Selecting a single line and running it advances the cursor to the next one ([PR 24112](https://github.com/spyder-ide/spyder/pull/24112) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 24058](https://github.com/spyder-ide/spyder/issues/24058) - Error when updating to 6.0.5: 'libmambapy' has no attribute 'QueryFormat' ([PR 24072](https://github.com/spyder-ide/spyder/pull/24072) by [@mrclary](https://github.com/mrclary))
* [Issue 23835](https://github.com/spyder-ide/spyder/issues/23835) - Initial runfile changes cwd to lowercase version which fails all code needing case sensitive paths ([PR 24105](https://github.com/spyder-ide/spyder/pull/24105) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23378](https://github.com/spyder-ide/spyder/issues/23378) - Variable Explorer error when class has attribute that references a generator ([PR 24074](https://github.com/spyder-ide/spyder/pull/24074) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23375](https://github.com/spyder-ide/spyder/issues/23375) - Remote connections error with `Key file` authentication method ([PR 24086](https://github.com/spyder-ide/spyder/pull/24086) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22736](https://github.com/spyder-ide/spyder/issues/22736) - In Fullscreen Mode child windows are hidden and have no mouse control in WSL ([PR 24009](https://github.com/spyder-ide/spyder/pull/24009) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22693](https://github.com/spyder-ide/spyder/issues/22693) - Changing the color schema only affects new opened files when using a custom one ([PR 24195](https://github.com/spyder-ide/spyder/pull/24195) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22341](https://github.com/spyder-ide/spyder/issues/22341) - Make Editor annotations work in lower case ([PR 24338](https://github.com/spyder-ide/spyder/pull/24338) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22098](https://github.com/spyder-ide/spyder/issues/22098) - Long folder name breaks window layout ([PR 24315](https://github.com/spyder-ide/spyder/pull/24315) by [@jsbautista](https://github.com/jsbautista))
* [Issue 21751](https://github.com/spyder-ide/spyder/issues/21751) - Reading large integer error ([PR 24078](https://github.com/spyder-ide/spyder/pull/24078) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 16549](https://github.com/spyder-ide/spyder/issues/16549) - Breakpoints disappear when I save a file with the autoformat option toggled on ([PR 24178](https://github.com/spyder-ide/spyder/pull/24178) by [@jsbautista](https://github.com/jsbautista))

In this release 20 issues were closed.

### Pull Requests Merged

* [PR 24407](https://github.com/spyder-ide/spyder/pull/24407) - PR: Update `spyder-kernels` to 3.0.4 (for Spyder 6.0.6), by [@dalthviz](https://github.com/dalthviz)
* [PR 24397](https://github.com/spyder-ide/spyder/pull/24397) - PR: Sanity check in `setup.py` will mistakenly let Python 2 pass, by [@a-detiste](https://github.com/a-detiste)
* [PR 24389](https://github.com/spyder-ide/spyder/pull/24389) - PR: Don't use cached kernels on Windows with Conda 25.3.0+ (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([24132](https://github.com/spyder-ide/spyder/issues/24132))
* [PR 24373](https://github.com/spyder-ide/spyder/pull/24373) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 24372](https://github.com/spyder-ide/spyder/pull/24372) - PR: Update translations for 6.0.6, by [@dalthviz](https://github.com/dalthviz)
* [PR 24368](https://github.com/spyder-ide/spyder/pull/24368) - PR: Don't display errors when calling `get_value` (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24349](https://github.com/spyder-ide/spyder/pull/24349) - PR: Show message when a mismatch of Python versions prevents to deserialize objects (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([24125](https://github.com/spyder-ide/spyder/issues/24125))
* [PR 24338](https://github.com/spyder-ide/spyder/pull/24338) - PR: Make Editor annotations work in lower case, by [@jsbautista](https://github.com/jsbautista) ([22341](https://github.com/spyder-ide/spyder/issues/22341))
* [PR 24329](https://github.com/spyder-ide/spyder/pull/24329) - PR: Use modern and more fine-grained error types in autosave module (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([24281](https://github.com/spyder-ide/spyder/issues/24281))
* [PR 24322](https://github.com/spyder-ide/spyder/pull/24322) - PR: Fix grammatical error in updater script (Installers), by [@mrclary](https://github.com/mrclary) ([24318](https://github.com/spyder-ide/spyder/issues/24318))
* [PR 24315](https://github.com/spyder-ide/spyder/pull/24315) - PR: Improve UI for long file names (Editor), by [@jsbautista](https://github.com/jsbautista) ([22098](https://github.com/spyder-ide/spyder/issues/22098))
* [PR 24299](https://github.com/spyder-ide/spyder/pull/24299) - PR: Fix opening context menu when clicking the blank area of Files pane, by [@jsbautista](https://github.com/jsbautista) ([24205](https://github.com/spyder-ide/spyder/issues/24205))
* [PR 24294](https://github.com/spyder-ide/spyder/pull/24294) - PR: Skip some tests about warnings on Mac because they became flaky, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24273](https://github.com/spyder-ide/spyder/pull/24273) - PR: Remove qtwebengine patch from feedstock for 6.0.5+ (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 24255](https://github.com/spyder-ide/spyder/pull/24255) - PR: Catch error when `xdg-open` is missing and show message instead (Files), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24245](https://github.com/spyder-ide/spyder/pull/24245) - PR: Remove unnecessary workflow triggers (CI), by [@mrclary](https://github.com/mrclary)
* [PR 24244](https://github.com/spyder-ide/spyder/pull/24244) - PR: Update workflow actions to address some warnings (CI), by [@mrclary](https://github.com/mrclary)
* [PR 24239](https://github.com/spyder-ide/spyder/pull/24239) - PR: Fix width of the Find pane when searching for long strings, by [@jsbautista](https://github.com/jsbautista) ([24188](https://github.com/spyder-ide/spyder/issues/24188))
* [PR 24234](https://github.com/spyder-ide/spyder/pull/24234) - PR: Fix failing tests on macOS (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24227](https://github.com/spyder-ide/spyder/pull/24227) - PR: Kill persistent `python.exe` tasks on Windows test workflows (CI), by [@mrclary](https://github.com/mrclary)
* [PR 24215](https://github.com/spyder-ide/spyder/pull/24215) - PR: Avoid rounding scaling for figure browser to zero (Plots), by [@oscargus](https://github.com/oscargus)
* [PR 24195](https://github.com/spyder-ide/spyder/pull/24195) - PR: Fix applying changes to custom color schemes to open files (Editor), by [@jsbautista](https://github.com/jsbautista) ([22693](https://github.com/spyder-ide/spyder/issues/22693))
* [PR 24178](https://github.com/spyder-ide/spyder/pull/24178) - PR: Restore breakpoints after auto-formatting a file (Editor), by [@jsbautista](https://github.com/jsbautista) ([16549](https://github.com/spyder-ide/spyder/issues/16549))
* [PR 24176](https://github.com/spyder-ide/spyder/pull/24176) - PR: Add Matplotlib font cache message to benign errors (IPython console), by [@jsbautista](https://github.com/jsbautista) ([24153](https://github.com/spyder-ide/spyder/issues/24153))
* [PR 24156](https://github.com/spyder-ide/spyder/pull/24156) - PR: Use link to our webpage for donations when no web widgets are available (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24145](https://github.com/spyder-ide/spyder/pull/24145) - PR: Restore `Quit` action in IPython console context menu, by [@jsbautista](https://github.com/jsbautista) ([24096](https://github.com/spyder-ide/spyder/issues/24096))
* [PR 24114](https://github.com/spyder-ide/spyder/pull/24114) - PR: Drop unnecessary runtime dependency on `setuptools`, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 24112](https://github.com/spyder-ide/spyder/pull/24112) - PR: Don't advance line when running code if there's selected text (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([24091](https://github.com/spyder-ide/spyder/issues/24091))
* [PR 24106](https://github.com/spyder-ide/spyder/pull/24106) - PR: Catch error when computing max of columms in dataframe editor (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([24094](https://github.com/spyder-ide/spyder/issues/24094))
* [PR 24105](https://github.com/spyder-ide/spyder/pull/24105) - PR: Respect case sensitivity of working directory when running code (IPython console), by [@jsbautista](https://github.com/jsbautista) ([23835](https://github.com/spyder-ide/spyder/issues/23835))
* [PR 24095](https://github.com/spyder-ide/spyder/pull/24095) - PR: Make the `Help Spyder` action not depend on QtWebEngine (Application), by [@hmaarrfk](https://github.com/hmaarrfk)
* [PR 24086](https://github.com/spyder-ide/spyder/pull/24086) - PR: Fix connecting to remote host with key file and passphrase (Remote client), by [@ccordoba12](https://github.com/ccordoba12) ([23375](https://github.com/spyder-ide/spyder/issues/23375))
* [PR 24078](https://github.com/spyder-ide/spyder/pull/24078) - PR: Fix editing of large ints in the Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([21751](https://github.com/spyder-ide/spyder/issues/21751))
* [PR 24074](https://github.com/spyder-ide/spyder/pull/24074) - PR: Improve message when trying to view object with an attribute that references a generator, by [@jsbautista](https://github.com/jsbautista) ([23378](https://github.com/spyder-ide/spyder/issues/23378))
* [PR 24072](https://github.com/spyder-ide/spyder/pull/24072) - PR: Revert removing mamba from base environment specification, by [@mrclary](https://github.com/mrclary) ([24058](https://github.com/spyder-ide/spyder/issues/24058))
* [PR 24042](https://github.com/spyder-ide/spyder/pull/24042) - PR: Skip some tests to make the suite more reliable (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24009](https://github.com/spyder-ide/spyder/pull/24009) - PR: Disable fullscreen mode when running on WSL (Layout), by [@jsbautista](https://github.com/jsbautista) ([22736](https://github.com/spyder-ide/spyder/issues/22736))

In this release 37 pull requests were closed.

----

## Version 6.0.5 (2025/03/26)

### New features

* Add option to the Projects options menu to disable file searches in the Switcher.
* Support displaying environments with the same name in the IPython Console `New console in environment` menu.

### Important fixes

* Fix `Check for updates at startup` option when an update is declined.
* Remove `mamba` from Spyder installers.
* Several improvements to the Variable Explorer messages shown when a variable can't be displayed.
* Prevent error in `Connect to an existing kernel` dialog when the connection file doesn't exist.
* Several fixes related to the Run plugin and working directory options used to run and debug files.
* Fix conda executable validation when creating kernels and improve feedback in case it's not found.
* Add message related to support for Pixi environments when starting kernels.
* Improve message related to loading the Spyder icon theme not being possible.
* Prevent Spyder softlock when lossing focus while the tour is being shown.
* Fixes to better handle errors when trying to load `.spydata` files in the Variable Explorer.
* Fix Editor code folding and indent guides for cloned editors.

### Issues Closed

* [Issue 23953](https://github.com/spyder-ide/spyder/issues/23953) - `Check for updates at startup` checkbox is ignored ([PR 24008](https://github.com/spyder-ide/spyder/pull/24008) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23940](https://github.com/spyder-ide/spyder/issues/23940) - Malwarebytes dislikes file: mamba.exe ([PR 24000](https://github.com/spyder-ide/spyder/pull/24000) by [@mrclary](https://github.com/mrclary))
* [Issue 23866](https://github.com/spyder-ide/spyder/issues/23866) - Difficulty using Project directory as working directory ([PR 23905](https://github.com/spyder-ide/spyder/pull/23905) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23729](https://github.com/spyder-ide/spyder/issues/23729) - `TypeError: 'in <string>' requires string as left operand, not NoneType` when connecting to an existing kernel ([PR 23898](https://github.com/spyder-ide/spyder/pull/23898) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23726](https://github.com/spyder-ide/spyder/issues/23726) - Can not start a console when CWD is a UNC path ([PR 23727](https://github.com/spyder-ide/spyder/pull/23727) by [@impact27](https://github.com/impact27))
* [Issue 23716](https://github.com/spyder-ide/spyder/issues/23716) - Run file (F5) button in Run Toolbar greyed out after using `Save As...` to save a file ([PR 23955](https://github.com/spyder-ide/spyder/pull/23955) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23694](https://github.com/spyder-ide/spyder/issues/23694) - ModuleNotFoundError while debugging: `debugfile` uses current working directory instead of parent directory of the file being executed ([PR 23892](https://github.com/spyder-ide/spyder/pull/23892) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23677](https://github.com/spyder-ide/spyder/issues/23677) - `ValueError: math domain error` in the Plots pane ([PR 23920](https://github.com/spyder-ide/spyder/pull/23920) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23665](https://github.com/spyder-ide/spyder/issues/23665) - Don't show `Move`/`Undock` actions in new editor windows options menu ([PR 23724](https://github.com/spyder-ide/spyder/pull/23724) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23622](https://github.com/spyder-ide/spyder/issues/23622) - No code folding in a new editor window ([PR 23722](https://github.com/spyder-ide/spyder/pull/23722) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23597](https://github.com/spyder-ide/spyder/issues/23597) - Search and replace case sensitivity and history in editor ([PR 23978](https://github.com/spyder-ide/spyder/pull/23978) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23595](https://github.com/spyder-ide/spyder/issues/23595) - Kernel fails to start in Spyder 6 when conda distribution installation is in a custom path ([PR 23869](https://github.com/spyder-ide/spyder/pull/23869) by [@dalthviz](https://github.com/dalthviz))
* [Issue 23529](https://github.com/spyder-ide/spyder/issues/23529) - RuntimeError when opening remote console ([PR 23845](https://github.com/spyder-ide/spyder/pull/23845) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23516](https://github.com/spyder-ide/spyder/issues/23516) - Spyder app gets softlocked when lose focus during "Show tour" ([PR 23846](https://github.com/spyder-ide/spyder/pull/23846) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23395](https://github.com/spyder-ide/spyder/issues/23395) - `Consoles > New console in environment` menu not listing all environments ([PR 23632](https://github.com/spyder-ide/spyder/pull/23632) by [@jsbautista](https://github.com/jsbautista))
* [Issue 23297](https://github.com/spyder-ide/spyder/issues/23297) - Indent guides not shown when its corresponding option is enabled ([PR 23801](https://github.com/spyder-ide/spyder/pull/23801) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23074](https://github.com/spyder-ide/spyder/issues/23074) - `test_pylint.py` throws `Exception: Invalid font prefix "mdi"` when run alone ([PR 23687](https://github.com/spyder-ide/spyder/pull/23687) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22972](https://github.com/spyder-ide/spyder/issues/22972) - Impossible to load .spydata file ([PR 23812](https://github.com/spyder-ide/spyder/pull/23812) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22913](https://github.com/spyder-ide/spyder/issues/22913) - DataFrame viewer resizes the index column wrongly under certain conditions ([PR 23833](https://github.com/spyder-ide/spyder/pull/23833) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22843](https://github.com/spyder-ide/spyder/issues/22843) - Remote services installation script failed with syntax error ([PR 23968](https://github.com/spyder-ide/spyder/pull/23968) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22629](https://github.com/spyder-ide/spyder/issues/22629) - Format (d) is incorrect in Numpy array viewer ([PR 23782](https://github.com/spyder-ide/spyder/pull/23782) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22554](https://github.com/spyder-ide/spyder/issues/22554) - Can not use Spyder 6 with old conda (4.8.3) ([PR 23869](https://github.com/spyder-ide/spyder/pull/23869) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22499](https://github.com/spyder-ide/spyder/issues/22499) - Spyder 6 on Windows cannot load Spyder's icon theme --> no start ([PR 23848](https://github.com/spyder-ide/spyder/pull/23848) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22461](https://github.com/spyder-ide/spyder/issues/22461) - Option to disable Project files search in switcher ([PR 23965](https://github.com/spyder-ide/spyder/pull/23965) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22358](https://github.com/spyder-ide/spyder/issues/22358) - IsADirectoryError when uncompressing spydata file ([PR 23814](https://github.com/spyder-ide/spyder/pull/23814) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22222](https://github.com/spyder-ide/spyder/issues/22222) - `site-packages` directories in `AppData\Roaming` are not excluded from the Pythonpath manager ([PR 23668](https://github.com/spyder-ide/spyder/pull/23668) by [@jsbautista](https://github.com/jsbautista))
* [Issue 21995](https://github.com/spyder-ide/spyder/issues/21995) - RuntimeError when restarting a kernel ([PR 23845](https://github.com/spyder-ide/spyder/pull/23845) by [@jsbautista](https://github.com/jsbautista))
* [Issue 21978](https://github.com/spyder-ide/spyder/issues/21978) - Inconsistency between menu options and button names for `Run Cell` operations ([PR 23781](https://github.com/spyder-ide/spyder/pull/23781) by [@jsbautista](https://github.com/jsbautista))

In this release 28 issues were closed.

### Pull Requests Merged

* [PR 24047](https://github.com/spyder-ide/spyder/pull/24047) - PR: Change donations links from Open Collective to our own page, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24034](https://github.com/spyder-ide/spyder/pull/24034) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 24033](https://github.com/spyder-ide/spyder/pull/24033) - PR: Update translations for 6.0.5 (part 2), by [@dalthviz](https://github.com/dalthviz)
* [PR 24026](https://github.com/spyder-ide/spyder/pull/24026) - PR: Improve text of option to search files in the switcher (Projects), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24008](https://github.com/spyder-ide/spyder/pull/24008) - PR: Fix `Check for updates at startup` checkbox being ignored when an update is declined (Update manager), by [@jsbautista](https://github.com/jsbautista) ([23953](https://github.com/spyder-ide/spyder/issues/23953))
* [PR 24006](https://github.com/spyder-ide/spyder/pull/24006) - PR: Update translations for 6.0.5, by [@dalthviz](https://github.com/dalthviz)
* [PR 24004](https://github.com/spyder-ide/spyder/pull/24004) - PR: More improvements to the message shown when a variable can't be displayed (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 24000](https://github.com/spyder-ide/spyder/pull/24000) - PR: Remove mamba from Spyder's installer build and base environment (Installers), by [@mrclary](https://github.com/mrclary) ([23940](https://github.com/spyder-ide/spyder/issues/23940))
* [PR 23991](https://github.com/spyder-ide/spyder/pull/23991) - PR: Improve message we show when getting a variable fails (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23978](https://github.com/spyder-ide/spyder/pull/23978) - PR: Fix case sensitivity and history when searching and replacing text in the Editor, by [@jsbautista](https://github.com/jsbautista) ([23597](https://github.com/spyder-ide/spyder/issues/23597))
* [PR 23968](https://github.com/spyder-ide/spyder/pull/23968) - PR: Use Bash to run the `spyder-remote-services` installation script (Remote client), by [@ccordoba12](https://github.com/ccordoba12) ([22843](https://github.com/spyder-ide/spyder/issues/22843))
* [PR 23965](https://github.com/spyder-ide/spyder/pull/23965) - PR: Add option to disable searching files in the switcher (Projects), by [@ccordoba12](https://github.com/ccordoba12) ([22461](https://github.com/spyder-ide/spyder/issues/22461))
* [PR 23955](https://github.com/spyder-ide/spyder/pull/23955) - PR: Update focused file for Run plugin after a `Save as` operation (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([23716](https://github.com/spyder-ide/spyder/issues/23716))
* [PR 23954](https://github.com/spyder-ide/spyder/pull/23954) - PR: Allow to set keyboard shortcut for `Run in external terminal` action, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23920](https://github.com/spyder-ide/spyder/pull/23920) - PR: Prevent collapsing splitter widgets in the Plots plugin, by [@jsbautista](https://github.com/jsbautista) ([23677](https://github.com/spyder-ide/spyder/issues/23677))
* [PR 23918](https://github.com/spyder-ide/spyder/pull/23918) - PR: Add message for Pixi created envs when conda executable is not found (IPython Console), by [@dalthviz](https://github.com/dalthviz)
* [PR 23905](https://github.com/spyder-ide/spyder/pull/23905) - PR: Set the current working directory used by the Run plugin directly in the Working directory plugin, by [@ccordoba12](https://github.com/ccordoba12) ([23866](https://github.com/spyder-ide/spyder/issues/23866))
* [PR 23903](https://github.com/spyder-ide/spyder/pull/23903) - PR: Fix text being cropped in some config pages (Preferences), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23902](https://github.com/spyder-ide/spyder/pull/23902) - PR: Various minor fixes, by [@rear1019](https://github.com/rear1019)
* [PR 23898](https://github.com/spyder-ide/spyder/pull/23898) - PR: Catch error when trying to connect to a non-existing connection file (IPython console), by [@jsbautista](https://github.com/jsbautista) ([23729](https://github.com/spyder-ide/spyder/issues/23729))
* [PR 23892](https://github.com/spyder-ide/spyder/pull/23892) - PR: Declare `File` as super context when Run plugin is created, by [@ccordoba12](https://github.com/ccordoba12) ([23694](https://github.com/spyder-ide/spyder/issues/23694))
* [PR 23876](https://github.com/spyder-ide/spyder/pull/23876) - PR: Update Ubuntu to 22.04 because the 20.04 image will be removed (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23869](https://github.com/spyder-ide/spyder/pull/23869) - PR: Add validation for conda version, raise error if using version <4.9 and if conda executable can't be detected (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([23595](https://github.com/spyder-ide/spyder/issues/23595), [22554](https://github.com/spyder-ide/spyder/issues/22554))
* [PR 23848](https://github.com/spyder-ide/spyder/pull/23848) - PR: Give a more informative error message if font load fails while launching Spyder (Main window), by [@dalthviz](https://github.com/dalthviz) ([22499](https://github.com/spyder-ide/spyder/issues/22499))
* [PR 23846](https://github.com/spyder-ide/spyder/pull/23846) - PR: Close tour when it loses focus, by [@jsbautista](https://github.com/jsbautista) ([23516](https://github.com/spyder-ide/spyder/issues/23516))
* [PR 23845](https://github.com/spyder-ide/spyder/pull/23845) - PR: Make `infowidget` a `property` to prevent errors when it's garbage collected (IPython console), by [@jsbautista](https://github.com/jsbautista) ([23529](https://github.com/spyder-ide/spyder/issues/23529), [21995](https://github.com/spyder-ide/spyder/issues/21995))
* [PR 23841](https://github.com/spyder-ide/spyder/pull/23841) - PR: Fix running `test_update_outline` on CI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23833](https://github.com/spyder-ide/spyder/pull/23833) - PR: Adjust index column to contents when clicking the button for that in dataframe editor (Variable Explorer), by [@jsbautista](https://github.com/jsbautista) ([22913](https://github.com/spyder-ide/spyder/issues/22913))
* [PR 23814](https://github.com/spyder-ide/spyder/pull/23814) - PR: Ignore `OSError`  when trying to load data (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([22358](https://github.com/spyder-ide/spyder/issues/22358))
* [PR 23812](https://github.com/spyder-ide/spyder/pull/23812) - PR: Handle `TypeError` when loading a `.spydata` file (Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([22972](https://github.com/spyder-ide/spyder/issues/22972))
* [PR 23801](https://github.com/spyder-ide/spyder/pull/23801) - PR: Fix indent guides at startup and for cloned editors (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([23297](https://github.com/spyder-ide/spyder/issues/23297))
* [PR 23788](https://github.com/spyder-ide/spyder/pull/23788) - PR: Fix some issues in our test suite (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23782](https://github.com/spyder-ide/spyder/pull/23782) - PR: Fix format specifier for integers in array and dataframe editors (Variable explorer), by [@jsbautista](https://github.com/jsbautista) ([22629](https://github.com/spyder-ide/spyder/issues/22629))
* [PR 23781](https://github.com/spyder-ide/spyder/pull/23781) - PR: Fix inconsistency between menu entries and button tooltips for Run cell buttons (Editor), by [@jsbautista](https://github.com/jsbautista) ([21978](https://github.com/spyder-ide/spyder/issues/21978))
* [PR 23748](https://github.com/spyder-ide/spyder/pull/23748) - PR: Try to recover files from autosave before the main window is visible (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23727](https://github.com/spyder-ide/spyder/pull/23727) - PR: Add string that contains `UNC` to benign errors (IPython console), by [@impact27](https://github.com/impact27) ([23726](https://github.com/spyder-ide/spyder/issues/23726))
* [PR 23724](https://github.com/spyder-ide/spyder/pull/23724) - PR: Don't show move, undock and close actions in the Options menu of new editor windows, by [@jsbautista](https://github.com/jsbautista) ([23665](https://github.com/spyder-ide/spyder/issues/23665))
* [PR 23722](https://github.com/spyder-ide/spyder/pull/23722) - PR: Fix code folding in cloned editors (Editor), by [@jsbautista](https://github.com/jsbautista) ([23622](https://github.com/spyder-ide/spyder/issues/23622))
* [PR 23687](https://github.com/spyder-ide/spyder/pull/23687) - PR: Set icon in constructor for `ConfigDialog` (Widgets), by [@ccordoba12](https://github.com/ccordoba12) ([23074](https://github.com/spyder-ide/spyder/issues/23074))
* [PR 23668](https://github.com/spyder-ide/spyder/pull/23668) - PR: Prevent to add `site-packages` directories placed inside `AppData` ones to the Pythonpath manager, by [@jsbautista](https://github.com/jsbautista) ([22222](https://github.com/spyder-ide/spyder/issues/22222))
* [PR 23632](https://github.com/spyder-ide/spyder/pull/23632) - PR: Show environments with the same name in different paths in the `New console in environment` menu, by [@jsbautista](https://github.com/jsbautista) ([23395](https://github.com/spyder-ide/spyder/issues/23395))
* [PR 23278](https://github.com/spyder-ide/spyder/pull/23278) - PR: Reduce calls to get environment variables in `SpyderKernelSpec` and raise timeout threshold to do that, by [@mrclary](https://github.com/mrclary)
* [PR 23239](https://github.com/spyder-ide/spyder/pull/23239) - PR: Update Spyder conda builds for PRs to accommodate split packaging (Installers), by [@mrclary](https://github.com/mrclary)

In this release 43 pull requests were closed.

----

## Version 6.0.4 (2025/02/06)

### New features

* Add command line option to connect to an existing kernel at startup.
* Display a button to select an entire row when hovering it in the Variable Explorer.

### Important fixes

* Fix error in debugger with Python 3.12.5+ (`_pdbcmd_print_frame_status is not defined` message).
* Improve messages shown when a variable can't be viewed due to a missing module.
* Add validations when doing color theme changes.
* Fix error when executing in a dedicated console with an interpreter without a valid version of `spyder-kernels` installed.
* Fix setting run configurations per file for multiple runners (e.g. the IPython console and Debugger).
* Fix errors related to the update logic of our standalone installers.
* Make shortcuts that control the Debugger global again.
* Show debugger buttons in the main toolbar while executing code in debugging mode.
* Restore functionality to select a custom interpreter from the statusbar.
* Fix thumbnails keyboard navigation in the Plots pane when their order changes.
* Handle keyring backend not being available.

### API changes

* Add `give_focus` kwarg to the `create_client_for_kernel` method of the
  IPython console plugin.

### Issues Closed

* [Issue 23650](https://github.com/spyder-ide/spyder/issues/23650) - Spyder 6 standalone installer - automatic update only works with bash not zsh ([PR 23660](https://github.com/spyder-ide/spyder/pull/23660) by [@mrclary](https://github.com/mrclary))
* [Issue 23497](https://github.com/spyder-ide/spyder/issues/23497) - Open project command line option conflicts with the new connect to kernel one ([PR 23498](https://github.com/spyder-ide/spyder/pull/23498) by [@Social-Mean](https://github.com/Social-Mean))
* [Issue 23484](https://github.com/spyder-ide/spyder/issues/23484) - Spyder 6.0.3 can't display tracebacks in the IPython console when using Python 3.8 ([PR 23477](https://github.com/spyder-ide/spyder/pull/23477) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23361](https://github.com/spyder-ide/spyder/issues/23361) - RuntimeError when setting Python interpreter ([PR 23410](https://github.com/spyder-ide/spyder/pull/23410) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23313](https://github.com/spyder-ide/spyder/issues/23313) - The Chinese input method blocks the input content. ([PR 23316](https://github.com/spyder-ide/spyder/pull/23316) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23237](https://github.com/spyder-ide/spyder/issues/23237) - UnboundLocalError when checking for updates on non-recognized platforms ([PR 23263](https://github.com/spyder-ide/spyder/pull/23263) by [@mrclary](https://github.com/mrclary))
* [Issue 23232](https://github.com/spyder-ide/spyder/issues/23232) - Purge cache workflow has been failing since #22791 ([PR 23255](https://github.com/spyder-ide/spyder/pull/23255) by [@mrclary](https://github.com/mrclary))
* [Issue 23208](https://github.com/spyder-ide/spyder/issues/23208) - The control debugger buttons are hidden from the main toolbar when code is executed ([PR 23273](https://github.com/spyder-ide/spyder/pull/23273) by [@athompson673](https://github.com/athompson673))
* [Issue 23130](https://github.com/spyder-ide/spyder/issues/23130) - Add command line option to connect to an existing kernel ([PR 23444](https://github.com/spyder-ide/spyder/pull/23444) by [@Social-Mean](https://github.com/Social-Mean))
* [Issue 23124](https://github.com/spyder-ide/spyder/issues/23124) - PermissionError when writing kernel connection file ([PR 23230](https://github.com/spyder-ide/spyder/pull/23230) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23076](https://github.com/spyder-ide/spyder/issues/23076) - Alt + Return runs the cell in the currently opened file instead of the last cell ([PR 23505](https://github.com/spyder-ide/spyder/pull/23505) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22970](https://github.com/spyder-ide/spyder/issues/22970) - Custom syntax highlighting theme has been removed / Spyder crashes when a custom syntax highlighting theme has as color an invalid hex value ([PR 23524](https://github.com/spyder-ide/spyder/pull/23524) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22844](https://github.com/spyder-ide/spyder/issues/22844) - Spyder can't open files with spaces from the Windows Explorer
* [Issue 22834](https://github.com/spyder-ide/spyder/issues/22834) - Error when checking for updates ([PR 23420](https://github.com/spyder-ide/spyder/pull/23420) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22722](https://github.com/spyder-ide/spyder/issues/22722) - Debugger keyboard shortcuts should also work when console has focus ([PR 23452](https://github.com/spyder-ide/spyder/pull/23452) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22697](https://github.com/spyder-ide/spyder/issues/22697) - Not possible to change default environment from the status bar in Spyder 6 ([PR 23578](https://github.com/spyder-ide/spyder/pull/23578) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22673](https://github.com/spyder-ide/spyder/issues/22673) - Ctrl+Shift+F12 doesn't stop debugging in Spyder 6 ([PR 23369](https://github.com/spyder-ide/spyder/pull/23369) by [@jsbautista](https://github.com/jsbautista))
* [Issue 22623](https://github.com/spyder-ide/spyder/issues/22623) - Crash when it's not possible to save an option securely ([PR 23598](https://github.com/spyder-ide/spyder/pull/23598) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22524](https://github.com/spyder-ide/spyder/issues/22524) - Not possible to select rows in the Variable Explorer when using Spyder 6 ([PR 23376](https://github.com/spyder-ide/spyder/pull/23376) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22500](https://github.com/spyder-ide/spyder/issues/22500) - `name '_pdbcmd_print_frame_status' is not defined` message when debugging ([PR 23648](https://github.com/spyder-ide/spyder/pull/23648) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22496](https://github.com/spyder-ide/spyder/issues/22496) - Debug File (Ctrl+F5) does not respect working directory in Run configuration ([PR 23580](https://github.com/spyder-ide/spyder/pull/23580) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22458](https://github.com/spyder-ide/spyder/issues/22458) - Arrow keys agnostic to reordering Plots pane (Spyder 6) ([PR 23417](https://github.com/spyder-ide/spyder/pull/23417) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21884](https://github.com/spyder-ide/spyder/issues/21884) - AttributeError when executing in a dedicated console and the interpreter was set to an environment without spyder-kernels installed/correct version installed ([PR 23511](https://github.com/spyder-ide/spyder/pull/23511) by [@jsbautista](https://github.com/jsbautista))
* [Issue 12913](https://github.com/spyder-ide/spyder/issues/12913) - ValueError when trying to copy a variable in the Variable Explorer ([PR 23460](https://github.com/spyder-ide/spyder/pull/23460) by [@ccordoba12](https://github.com/ccordoba12))

In this release 24 issues were closed.

### Pull Requests Merged

* [PR 23662](https://github.com/spyder-ide/spyder/pull/23662) - PR: Update `spyder-kernels` to 3.0.3, by [@dalthviz](https://github.com/dalthviz)
* [PR 23660](https://github.com/spyder-ide/spyder/pull/23660) - PR: Disable shell history for both zsh and bash when installing update for macOS (Installers), by [@mrclary](https://github.com/mrclary) ([23650](https://github.com/spyder-ide/spyder/issues/23650))
* [PR 23648](https://github.com/spyder-ide/spyder/pull/23648) - PR: Fix error in debugger with Python 3.12.5+ , by [@ccordoba12](https://github.com/ccordoba12) ([22500](https://github.com/spyder-ide/spyder/issues/22500))
* [PR 23647](https://github.com/spyder-ide/spyder/pull/23647) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 23646](https://github.com/spyder-ide/spyder/pull/23646) - PR: Update translations for 6.0.4 (part 2), by [@dalthviz](https://github.com/dalthviz)
* [PR 23633](https://github.com/spyder-ide/spyder/pull/23633) - PR: Improve functionality for color scheme Cancel button (Preferences), by [@jsbautista](https://github.com/jsbautista)
* [PR 23613](https://github.com/spyder-ide/spyder/pull/23613) - PR: Update translations for 6.0.4, by [@dalthviz](https://github.com/dalthviz)
* [PR 23598](https://github.com/spyder-ide/spyder/pull/23598) - PR: Catch error when there's no keyring backend available (Config), by [@ccordoba12](https://github.com/ccordoba12) ([22623](https://github.com/spyder-ide/spyder/issues/22623))
* [PR 23580](https://github.com/spyder-ide/spyder/pull/23580) - PR: Fix setting custom run configurations for multiple executors (Run), by [@ccordoba12](https://github.com/ccordoba12) ([22496](https://github.com/spyder-ide/spyder/issues/22496))
* [PR 23578](https://github.com/spyder-ide/spyder/pull/23578) - PR: Restore functionality to open Main interpreter preferences from Python env statusbar widget, by [@jsbautista](https://github.com/jsbautista) ([22697](https://github.com/spyder-ide/spyder/issues/22697))
* [PR 23562](https://github.com/spyder-ide/spyder/pull/23562) - PR: Give more descriptive names to the shortcuts that control the Debugger, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23524](https://github.com/spyder-ide/spyder/pull/23524) - PR : Add validation for theme color changes (Preferences), by [@jsbautista](https://github.com/jsbautista) ([22970](https://github.com/spyder-ide/spyder/issues/22970))
* [PR 23513](https://github.com/spyder-ide/spyder/pull/23513) - PR: Improve reliability of some tests and fix teardown error for another one, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23511](https://github.com/spyder-ide/spyder/pull/23511) - PR: Fix error when executing in a dedicated console and the interpreter doesn't have spyder-kernels installed or its right version, by [@jsbautista](https://github.com/jsbautista) ([21884](https://github.com/spyder-ide/spyder/issues/21884))
* [PR 23505](https://github.com/spyder-ide/spyder/pull/23505) - PR: Fix Re-run cell when the last executed cell is not in the current file (Run), by [@ccordoba12](https://github.com/ccordoba12) ([23076](https://github.com/spyder-ide/spyder/issues/23076))
* [PR 23498](https://github.com/spyder-ide/spyder/pull/23498) - PR: Fix `--connect-to-kernel` cli option when a project is loaded at startup, by [@Social-Mean](https://github.com/Social-Mean) ([23497](https://github.com/spyder-ide/spyder/issues/23497))
* [PR 23477](https://github.com/spyder-ide/spyder/pull/23477) - PR: Filter frames that come from Spyder-kernels in tracebacks and fix tracebacks in Python 3.8 (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([23484](https://github.com/spyder-ide/spyder/issues/23484))
* [PR 23460](https://github.com/spyder-ide/spyder/pull/23460) - PR: Avoid error when getting an object's value to copy it (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([12913](https://github.com/spyder-ide/spyder/issues/12913))
* [PR 23452](https://github.com/spyder-ide/spyder/pull/23452) - PR: Make shortcuts for actions that control the debugger global again, by [@jsbautista](https://github.com/jsbautista) ([22722](https://github.com/spyder-ide/spyder/issues/22722))
* [PR 23444](https://github.com/spyder-ide/spyder/pull/23444) - PR: Add command line option to connect to an existing kernel at startup (IPython console), by [@Social-Mean](https://github.com/Social-Mean) ([23130](https://github.com/spyder-ide/spyder/issues/23130))
* [PR 23420](https://github.com/spyder-ide/spyder/pull/23420) - PR: Catch error when checking for updates (Update Manager), by [@jsbautista](https://github.com/jsbautista) ([22834](https://github.com/spyder-ide/spyder/issues/22834))
* [PR 23417](https://github.com/spyder-ide/spyder/pull/23417) - PR: Recreate thumbnails list after dropping one in a new position (Plots), by [@ccordoba12](https://github.com/ccordoba12) ([22458](https://github.com/spyder-ide/spyder/issues/22458))
* [PR 23410](https://github.com/spyder-ide/spyder/pull/23410) - PR: Avoid error in `PathComboBox` (Widgets), by [@ccordoba12](https://github.com/ccordoba12) ([23361](https://github.com/spyder-ide/spyder/issues/23361))
* [PR 23390](https://github.com/spyder-ide/spyder/pull/23390) - PR: Add missing `__init__()` calls in a couple of places, by [@rear1019](https://github.com/rear1019)
* [PR 23384](https://github.com/spyder-ide/spyder/pull/23384) - PR: Don't install `spyder-boilerplate` testing plugin in editable mode (CI), by [@juliangilbey](https://github.com/juliangilbey)
* [PR 23377](https://github.com/spyder-ide/spyder/pull/23377) - PR: Improve message when a variable can't be viewed due to a missing module (Variable Explorer), by [@jsbautista](https://github.com/jsbautista)
* [PR 23376](https://github.com/spyder-ide/spyder/pull/23376) - PR: Display a button to select the entire row when hovering it in `CollectionsEditor` (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12) ([22524](https://github.com/spyder-ide/spyder/issues/22524))
* [PR 23369](https://github.com/spyder-ide/spyder/pull/23369) - PR: Fix shortcut to stop the debugger, by [@jsbautista](https://github.com/jsbautista) ([22673](https://github.com/spyder-ide/spyder/issues/22673))
* [PR 23360](https://github.com/spyder-ide/spyder/pull/23360) - PR: Fix detecting Micromamba on Windows for kernel activation (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23327](https://github.com/spyder-ide/spyder/pull/23327) - PR: Replace set with list when searching for installed program, by [@mrclary](https://github.com/mrclary)
* [PR 23316](https://github.com/spyder-ide/spyder/pull/23316) - PR: Prevent Chinese input method to block edit input area, by [@ccordoba12](https://github.com/ccordoba12) ([23313](https://github.com/spyder-ide/spyder/issues/23313))
* [PR 23273](https://github.com/spyder-ide/spyder/pull/23273) - PR: Don't hide control debugger buttons from main toolbar while executing, by [@athompson673](https://github.com/athompson673) ([23208](https://github.com/spyder-ide/spyder/issues/23208))
* [PR 23263](https://github.com/spyder-ide/spyder/pull/23263) - PR: Skip checking for updates on unsupported platforms, by [@mrclary](https://github.com/mrclary) ([23237](https://github.com/spyder-ide/spyder/issues/23237))
* [PR 23255](https://github.com/spyder-ide/spyder/pull/23255) - PR: Fix invalid workflow issue with `purge_cache.yml`, by [@mrclary](https://github.com/mrclary) ([23232](https://github.com/spyder-ide/spyder/issues/23232))
* [PR 23254](https://github.com/spyder-ide/spyder/pull/23254) - PR: Set python_min environment variable for subrepo conda package builds, by [@mrclary](https://github.com/mrclary)
* [PR 23231](https://github.com/spyder-ide/spyder/pull/23231) - PR: Improve reporting status and logger messages (Remote client), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23230](https://github.com/spyder-ide/spyder/pull/23230) - PR: Improve displaying several kernel error messages (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([23124](https://github.com/spyder-ide/spyder/issues/23124))
* [PR 23141](https://github.com/spyder-ide/spyder/pull/23141) - PR: Update `setup.py` to accommodate the Conda-forge package split (Installation), by [@mrclary](https://github.com/mrclary)

In this release 38 pull requests were closed.

----

## Version 6.0.3 (2024/12/10)

### Important fixes

* Restore widget shortcuts to Preferences and allow to change them on the fly.
* Add support for IPython enhanced tracebacks and use the selected color scheme in the editor when showing them.
* Improve the way users can select the interface font in Preferences.
* Activate `Open last closed` shortcut and restore some missing context menu actions in the Editor.
* Fix several issues when getting selections to run them.
* Use the `INSTALLER_UNATTENDED` environment variable to not launch Spyder automatically if installing it in batch/silent mode from the standalone installers.

### API changes

* Add `plugin_name` kwarg to the `register_shortcut_for_widget` method of
  `SpyderShortcutsMixin`.
* The `add_configuration_observer` method was added to `SpyderConfigurationObserver`.
* Add `items_elide_mode` kwarg to the constructors of `SpyderComboBox` and
  `SpyderComboBoxWithIcons`.
* The `sig_item_in_popup_changed` and `sig_popup_is_hidden` signals were added
  to `SpyderComboBox`, `SpyderComboBoxWithIcons` and `SpyderFontComboBox`.

### Issues Closed

* [Issue 23203](https://github.com/spyder-ide/spyder/issues/23203) - Menuinst error related with the reset shortcut
* [Issue 23196](https://github.com/spyder-ide/spyder/issues/23196) - Internal console completions are very difficult to read in dark mode ([PR 23217](https://github.com/spyder-ide/spyder/pull/23217) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23151](https://github.com/spyder-ide/spyder/issues/23151) - Shortcuts don't work for new files in the Editor ([PR 23161](https://github.com/spyder-ide/spyder/pull/23161) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23072](https://github.com/spyder-ide/spyder/issues/23072) - Custom shortcut `Alt+Shift+Return` doesn't work ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 23062](https://github.com/spyder-ide/spyder/issues/23062) - `REQUIRED.app` is installed by Spyder macOS installer
* [Issue 23042](https://github.com/spyder-ide/spyder/issues/23042) - Delete folded block erases text on following line ([PR 23044](https://github.com/spyder-ide/spyder/pull/23044) by [@athompson673](https://github.com/athompson673))
* [Issue 22929](https://github.com/spyder-ide/spyder/issues/22929) - RuntimeError when trying to compute the console banner ([PR 22958](https://github.com/spyder-ide/spyder/pull/22958) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22912](https://github.com/spyder-ide/spyder/issues/22912) - Open last closed shortcut (Ctrl+Shift+T) does not work ([PR 22914](https://github.com/spyder-ide/spyder/pull/22914) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 22827](https://github.com/spyder-ide/spyder/issues/22827) - Attempt to add path in `Anaconda3/pkgs` to Pythonpath manager leads to an error ([PR 22850](https://github.com/spyder-ide/spyder/pull/22850) by [@mrclary](https://github.com/mrclary))
* [Issue 22794](https://github.com/spyder-ide/spyder/issues/22794) - Move from using `jupyter-desktop-server` to `jupyter-remote-desktop-proxy` for binder setup ([PR 22881](https://github.com/spyder-ide/spyder/pull/22881) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22741](https://github.com/spyder-ide/spyder/issues/22741) - Spyder restart required after changing some shortcuts in Preferences ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22730](https://github.com/spyder-ide/spyder/issues/22730) - Silent install automatically starts the application in Spyder 6 ([PR 22876](https://github.com/spyder-ide/spyder/pull/22876) by [@mrclary](https://github.com/mrclary))
* [Issue 22683](https://github.com/spyder-ide/spyder/issues/22683) - Restore content of font selection pull-down menu in preferences back to version 5 quality ([PR 22927](https://github.com/spyder-ide/spyder/pull/22927) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22661](https://github.com/spyder-ide/spyder/issues/22661) - Spyder 6 stuck when computing `xHeight` of monospace font ([PR 22826](https://github.com/spyder-ide/spyder/pull/22826) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22649](https://github.com/spyder-ide/spyder/issues/22649) - Global Run preset default values reappear after restart
* [Issue 22637](https://github.com/spyder-ide/spyder/issues/22637) - Run selection is missing from the Editor's context menu in Sypder 6.0 ([PR 22796](https://github.com/spyder-ide/spyder/pull/22796) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22635](https://github.com/spyder-ide/spyder/issues/22635) - AttributeError in tour when Help plugin is not available ([PR 23177](https://github.com/spyder-ide/spyder/pull/23177) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22630](https://github.com/spyder-ide/spyder/issues/22630) - F9 (run selection) fails from .md file ([PR 22820](https://github.com/spyder-ide/spyder/pull/22820) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22607](https://github.com/spyder-ide/spyder/issues/22607) - KeyError problem when running files ([PR 22819](https://github.com/spyder-ide/spyder/pull/22819) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22516](https://github.com/spyder-ide/spyder/issues/22516) - Many shortcuts not showing in Preferences ([PR 23024](https://github.com/spyder-ide/spyder/pull/23024) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22492](https://github.com/spyder-ide/spyder/issues/22492) - Color Scheme Error: `configparser.NoOptionError: No option 'custom-0/normal' in section: 'appearance'` ([PR 23022](https://github.com/spyder-ide/spyder/pull/23022) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22453](https://github.com/spyder-ide/spyder/issues/22453) - Search -> Find text only works for Editor ([PR 23145](https://github.com/spyder-ide/spyder/pull/23145) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22412](https://github.com/spyder-ide/spyder/issues/22412) - Traceback color handling and definition need improvements ([PR 22965](https://github.com/spyder-ide/spyder/pull/22965) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22060](https://github.com/spyder-ide/spyder/issues/22060) - Code highlight removed after run selected or current line ([PR 22940](https://github.com/spyder-ide/spyder/pull/22940) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 1052](https://github.com/spyder-ide/spyder/issues/1052) - Add support for IPython enhanced tracebacks ([PR 22965](https://github.com/spyder-ide/spyder/pull/22965) by [@dalthviz](https://github.com/dalthviz))

In this release 25 issues were closed.

### Pull Requests Merged

* [PR 23235](https://github.com/spyder-ide/spyder/pull/23235) - PR: Minor improvements to `RELEASE.md` release candidate section, by [@dalthviz](https://github.com/dalthviz)
* [PR 23233](https://github.com/spyder-ide/spyder/pull/23233) - PR: Fix error when inserting items in DataFrameEditor (Variable Explorer), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23217](https://github.com/spyder-ide/spyder/pull/23217) - PR: A couple of fixes for the Internal console, by [@ccordoba12](https://github.com/ccordoba12) ([23196](https://github.com/spyder-ide/spyder/issues/23196))
* [PR 23213](https://github.com/spyder-ide/spyder/pull/23213) - PR: Add constraint for `pyqt5-sip` on Python 3.8 (Dependencies), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23211](https://github.com/spyder-ide/spyder/pull/23211) - PR: Enable/disable the `Configuration per file` action according to the current file run configuration (Run), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23201](https://github.com/spyder-ide/spyder/pull/23201) - PR: Update `spyder-kernels` to 3.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 23178](https://github.com/spyder-ide/spyder/pull/23178) - PR: Add release instructions on how to update the Conda-forge `rc` feedstock channel (Installers), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23177](https://github.com/spyder-ide/spyder/pull/23177) - PR: Remove from intro tour steps for unavailable plugins (Tours), by [@ccordoba12](https://github.com/ccordoba12) ([22635](https://github.com/spyder-ide/spyder/issues/22635))
* [PR 23165](https://github.com/spyder-ide/spyder/pull/23165) - PR: UI fixes for the Appearance config page and find/replace widget on Mac , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23161](https://github.com/spyder-ide/spyder/pull/23161) - PR: Register shortcuts for widgets directly (API), by [@ccordoba12](https://github.com/ccordoba12) ([23151](https://github.com/spyder-ide/spyder/issues/23151))
* [PR 23145](https://github.com/spyder-ide/spyder/pull/23145) - PR: Don't register shortcuts for find/replace related actions that go in the Search menu (Editor), by [@dalthviz](https://github.com/dalthviz) ([22453](https://github.com/spyder-ide/spyder/issues/22453))
* [PR 23144](https://github.com/spyder-ide/spyder/pull/23144) - PR: Fix `DeprecationWarning: module 'sre_constants' is deprecated`, by [@athompson673](https://github.com/athompson673)
* [PR 23121](https://github.com/spyder-ide/spyder/pull/23121) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 23120](https://github.com/spyder-ide/spyder/pull/23120) - PR: Update translations for 6.0.3, by [@dalthviz](https://github.com/dalthviz)
* [PR 23069](https://github.com/spyder-ide/spyder/pull/23069) - PR: Fix small error in `get_spyder_conda_channel` (Utils), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23055](https://github.com/spyder-ide/spyder/pull/23055) - PR: Choose Qt binding to install from `SPYDER_QT_BINDING` environment variable, by [@dpizetta](https://github.com/dpizetta)
* [PR 23044](https://github.com/spyder-ide/spyder/pull/23044) - PR: Fix `FoldingPanel._expand_selection` to not select text an extra line below a folded region (Editor), by [@athompson673](https://github.com/athompson673) ([23042](https://github.com/spyder-ide/spyder/issues/23042))
* [PR 23029](https://github.com/spyder-ide/spyder/pull/23029) - PR: Pin Jedi to 0.19.1 for now on Linux (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 23024](https://github.com/spyder-ide/spyder/pull/23024) - PR: Restore widget shortcuts to Preferences and allow to change them on the fly (Shortcuts), by [@ccordoba12](https://github.com/ccordoba12) ([23072](https://github.com/spyder-ide/spyder/issues/23072), [22741](https://github.com/spyder-ide/spyder/issues/22741), [22516](https://github.com/spyder-ide/spyder/issues/22516))
* [PR 23022](https://github.com/spyder-ide/spyder/pull/23022) - PR: Handle error when trying to get invalid/unavailable custom syntax highlighting themes (Appearance), by [@dalthviz](https://github.com/dalthviz) ([22492](https://github.com/spyder-ide/spyder/issues/22492))
* [PR 22965](https://github.com/spyder-ide/spyder/pull/22965) - PR: Initial traceback setup to use selected syntax style (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([22412](https://github.com/spyder-ide/spyder/issues/22412), [1052](https://github.com/spyder-ide/spyder/issues/1052))
* [PR 22958](https://github.com/spyder-ide/spyder/pull/22958) - PR: Catch error when trying to compute the console banner (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22929](https://github.com/spyder-ide/spyder/issues/22929))
* [PR 22940](https://github.com/spyder-ide/spyder/pull/22940) - PR: Fix several issues when getting selections to run them (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22060](https://github.com/spyder-ide/spyder/issues/22060))
* [PR 22927](https://github.com/spyder-ide/spyder/pull/22927) - PR: Improve the way users can select the interface font in Preferences (Appearance), by [@ccordoba12](https://github.com/ccordoba12) ([22683](https://github.com/spyder-ide/spyder/issues/22683))
* [PR 22914](https://github.com/spyder-ide/spyder/pull/22914) - PR: Activate `Open last closed` shortcut in `EditorStack` (Editor), by [@jitseniesen](https://github.com/jitseniesen) ([22912](https://github.com/spyder-ide/spyder/issues/22912))
* [PR 22881](https://github.com/spyder-ide/spyder/pull/22881) - PR: Use `jupyter-remote-desktop-proxy` for binder setup (Binder), by [@dalthviz](https://github.com/dalthviz) ([22794](https://github.com/spyder-ide/spyder/issues/22794))
* [PR 22876](https://github.com/spyder-ide/spyder/pull/22876) - PR: Do not launch Spyder if installing in CI or batch/silent mode (Installers), by [@mrclary](https://github.com/mrclary) ([22730](https://github.com/spyder-ide/spyder/issues/22730))
* [PR 22861](https://github.com/spyder-ide/spyder/pull/22861) - PR: Add `overflow: hidden` to body and container in in-app appeal page (Application), by [@conradolandia](https://github.com/conradolandia)
* [PR 22860](https://github.com/spyder-ide/spyder/pull/22860) - PR: Check `spyder-remote-services` version compatibility (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22850](https://github.com/spyder-ide/spyder/pull/22850) - PR: Fix `UnboundLocalError` when removing and adding paths to Pythonpath Manager, by [@mrclary](https://github.com/mrclary) ([22827](https://github.com/spyder-ide/spyder/issues/22827))
* [PR 22826](https://github.com/spyder-ide/spyder/pull/22826) - PR: Try to set the monospace font size up to six times in `SpyderApplication` (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22661](https://github.com/spyder-ide/spyder/issues/22661))
* [PR 22820](https://github.com/spyder-ide/spyder/pull/22820) - PR: Register run metadata on renames for supported file extensions (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22630](https://github.com/spyder-ide/spyder/issues/22630))
* [PR 22819](https://github.com/spyder-ide/spyder/pull/22819) - PR: Fix enabled state of Run plugin actions when a file type doesn't have an associated configuration, by [@ccordoba12](https://github.com/ccordoba12) ([22607](https://github.com/spyder-ide/spyder/issues/22607))
* [PR 22796](https://github.com/spyder-ide/spyder/pull/22796) - PR: Restore run actions to the context menu of `CodeEditor` (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22637](https://github.com/spyder-ide/spyder/issues/22637))
* [PR 22791](https://github.com/spyder-ide/spyder/pull/22791) - PR: Run installer build workflow on both master and 6.x weekly (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22696](https://github.com/spyder-ide/spyder/pull/22696) - PR: Update workflows to accommodate GitHub deprecation of macos-12 runners (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22541](https://github.com/spyder-ide/spyder/pull/22541) - PR: Update Python versions used for testing on Windows and Mac (CI), by [@ccordoba12](https://github.com/ccordoba12)

In this release 37 pull requests were closed.

----

## Version 6.0.2 (2024/10/31)

### Important fixes

* Fix plots not being generated with the Matplotlib inline backend.
* Restore missing debugger buttons to the main toolbar.
* Several fixes and improvements to the update detection mechanism.
* Fix SSH tunneling info handling for remote kernels connection and add remote client tests.
* Handle kernel fault file not being available.
* Update QtConsole constraint to 5.6.1 to support ANSI codes that move the cursor.

### API changes

* The `sig_is_rendered` signal was added to `SpyderToolbar`.
* The `add_toolbar` kwarg of the `create_run_button` and `create_run_in_executor_button`
  methods of the Run plugin can now accept a dictionary.

### Issues Closed

* [Issue 22732](https://github.com/spyder-ide/spyder/issues/22732) - return in finally swallows exceptions ([PR 22745](https://github.com/spyder-ide/spyder/pull/22745) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22685](https://github.com/spyder-ide/spyder/issues/22685) - Check update process for 6.0.2 with a rc (6.0.2rc1)
* [Issue 22593](https://github.com/spyder-ide/spyder/issues/22593) - Banner not shown when there are many files open in the Editor at startup ([PR 22594](https://github.com/spyder-ide/spyder/pull/22594) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22584](https://github.com/spyder-ide/spyder/issues/22584) - RuntimeError when setting a layout and the IPython console is undocked ([PR 22595](https://github.com/spyder-ide/spyder/pull/22595) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22574](https://github.com/spyder-ide/spyder/issues/22574) - `SpyderCodeRunner._debugger_exec` error when starting the debugger from Spyder 6.0.1 ([PR 22633](https://github.com/spyder-ide/spyder/pull/22633) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22572](https://github.com/spyder-ide/spyder/issues/22572) - Spyder  encounters an internal problem after declining update to 6.0.1 ([PR 22598](https://github.com/spyder-ide/spyder/pull/22598) by [@mrclary](https://github.com/mrclary))
* [Issue 22566](https://github.com/spyder-ide/spyder/issues/22566) - Standalone installer shows 404 error on spyder-conda-lock.zip ([PR 22598](https://github.com/spyder-ide/spyder/pull/22598) by [@mrclary](https://github.com/mrclary))
* [Issue 22555](https://github.com/spyder-ide/spyder/issues/22555) - Remote spyder kernel not connecting  ([PR 22691](https://github.com/spyder-ide/spyder/pull/22691) by [@hlouzada](https://github.com/hlouzada))
* [Issue 22551](https://github.com/spyder-ide/spyder/issues/22551) - Error message "the system cannot find the path specified" upon trying to start the kernel ([PR 22575](https://github.com/spyder-ide/spyder/pull/22575) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22546](https://github.com/spyder-ide/spyder/issues/22546) - UnicodeDecodeError when changing files with an open project ([PR 22656](https://github.com/spyder-ide/spyder/pull/22656) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22448](https://github.com/spyder-ide/spyder/issues/22448) - TypeError on connecting to spyder-notebook kernel ([PR 22628](https://github.com/spyder-ide/spyder/pull/22628) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22434](https://github.com/spyder-ide/spyder/issues/22434) - Spyder 6: Debugging buttons missing from the main toolbar ([PR 22702](https://github.com/spyder-ide/spyder/pull/22702) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22420](https://github.com/spyder-ide/spyder/issues/22420) - Plots not showing in Spyder 6 using external Python interpreter  ([PR 22664](https://github.com/spyder-ide/spyder/pull/22664) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22407](https://github.com/spyder-ide/spyder/issues/22407) - Update mechanism not working for Spyder 6.0 installed from Fedora distro package ([PR 22631](https://github.com/spyder-ide/spyder/pull/22631) by [@mrclary](https://github.com/mrclary))
* [Issue 6172](https://github.com/spyder-ide/spyder/issues/6172) - TQDM progress bar is not displayed correctly in the console ([PR 22718](https://github.com/spyder-ide/spyder/pull/22718) by [@dalthviz](https://github.com/dalthviz))

In this release 15 issues were closed.

### Pull Requests Merged

* [PR 22785](https://github.com/spyder-ide/spyder/pull/22785) - PR: Improve version update instructions on `RELEASE.md`, by [@dalthviz](https://github.com/dalthviz)
* [PR 22771](https://github.com/spyder-ide/spyder/pull/22771) - PR: Update dev version from alpha to rc, by [@dalthviz](https://github.com/dalthviz)
* [PR 22760](https://github.com/spyder-ide/spyder/pull/22760) - PR: Update core dependencies for 6.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22759](https://github.com/spyder-ide/spyder/pull/22759) - PR: Update `spyder-kernels` to 3.0.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 22757](https://github.com/spyder-ide/spyder/pull/22757) - PR: Mention that we need to publish release candidates for bugfix versions in release instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22753](https://github.com/spyder-ide/spyder/pull/22753) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 22752](https://github.com/spyder-ide/spyder/pull/22752) - PR: Update translations for 6.0.2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22745](https://github.com/spyder-ide/spyder/pull/22745) - PR: Remove unnecessary `return` in a `try/finally` statement (Files), by [@ccordoba12](https://github.com/ccordoba12) ([22732](https://github.com/spyder-ide/spyder/issues/22732))
* [PR 22718](https://github.com/spyder-ide/spyder/pull/22718) - PR: Update QtConsole subrepo to take into account changes to support cursor move actions, by [@dalthviz](https://github.com/dalthviz) ([6172](https://github.com/spyder-ide/spyder/issues/6172))
* [PR 22709](https://github.com/spyder-ide/spyder/pull/22709) - PR: Update installing developer repos to accommodate dist-info, by [@mrclary](https://github.com/mrclary)
* [PR 22702](https://github.com/spyder-ide/spyder/pull/22702) - PR: Restore buttons that control the debugger to the main toolbar, by [@ccordoba12](https://github.com/ccordoba12) ([22434](https://github.com/spyder-ide/spyder/issues/22434))
* [PR 22699](https://github.com/spyder-ide/spyder/pull/22699) - PR: Add `Help Spyder` entry to the Help menu (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22692](https://github.com/spyder-ide/spyder/pull/22692) - PR: Configure `spyder-remote-services` as an external dependency for the remote client tests, by [@hlouzada](https://github.com/hlouzada)
* [PR 22691](https://github.com/spyder-ide/spyder/pull/22691) - PR: Provide username, host and port from hostname info in ssh tunnels, by [@hlouzada](https://github.com/hlouzada) ([22555](https://github.com/spyder-ide/spyder/issues/22555))
* [PR 22668](https://github.com/spyder-ide/spyder/pull/22668) - PR: Don't use hard-coded path to Python in script shebang used to launch Spyder, by [@Flamefire](https://github.com/Flamefire)
* [PR 22664](https://github.com/spyder-ide/spyder/pull/22664) - PR: Manually register the Matplotlib inline backend in case it hasn't, by [@ccordoba12](https://github.com/ccordoba12) ([22420](https://github.com/spyder-ide/spyder/issues/22420))
* [PR 22656](https://github.com/spyder-ide/spyder/pull/22656) - PR: Always use `utf-8` when handling QByteArray data in `ProcessWorker` (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22546](https://github.com/spyder-ide/spyder/issues/22546))
* [PR 22654](https://github.com/spyder-ide/spyder/pull/22654) - PR: Some small fixes to the Maintenance instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22636](https://github.com/spyder-ide/spyder/pull/22636) - PR: Simplify min/max required versions of spyder-kernels in the stable branch (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22633](https://github.com/spyder-ide/spyder/pull/22633) - PR: Fix debug file and cell buttons in Debugger toolbar, by [@ccordoba12](https://github.com/ccordoba12) ([22574](https://github.com/spyder-ide/spyder/issues/22574))
* [PR 22631](https://github.com/spyder-ide/spyder/pull/22631) - PR: Do not check for updates if Spyder is in a system or managed environment, by [@mrclary](https://github.com/mrclary) ([22407](https://github.com/spyder-ide/spyder/issues/22407))
* [PR 22628](https://github.com/spyder-ide/spyder/pull/22628) - PR: Handle case when kernel fault file doesn't exist and show error with info explaining that no connection was possible (IPython Console), by [@dalthviz](https://github.com/dalthviz) ([22448](https://github.com/spyder-ide/spyder/issues/22448))
* [PR 22621](https://github.com/spyder-ide/spyder/pull/22621) - PR: Fix setting of working directory in Profiler plugin, by [@rear1019](https://github.com/rear1019)
* [PR 22618](https://github.com/spyder-ide/spyder/pull/22618) - PR: Fix `test_copy_paste_autoindent` forcing text over the clipboard to work (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 22598](https://github.com/spyder-ide/spyder/pull/22598) - PR: Check for asset availability when checking for updates, by [@mrclary](https://github.com/mrclary) ([22572](https://github.com/spyder-ide/spyder/issues/22572), [22566](https://github.com/spyder-ide/spyder/issues/22566))
* [PR 22597](https://github.com/spyder-ide/spyder/pull/22597) - PR: Minor updates to the installer, by [@mrclary](https://github.com/mrclary)
* [PR 22595](https://github.com/spyder-ide/spyder/pull/22595) - PR: Dock all undocked plugins before applying a layout, by [@ccordoba12](https://github.com/ccordoba12) ([22584](https://github.com/spyder-ide/spyder/issues/22584))
* [PR 22594](https://github.com/spyder-ide/spyder/pull/22594) - PR: Set shell banner attribute to be the one computed by us (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22593](https://github.com/spyder-ide/spyder/issues/22593))
* [PR 22577](https://github.com/spyder-ide/spyder/pull/22577) - PR: Pin micromamba to the last version before 2.0 to prevent hangs (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22575](https://github.com/spyder-ide/spyder/pull/22575) - PR: Add harmless OpenCL warning to bening errors (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22551](https://github.com/spyder-ide/spyder/issues/22551))
* [PR 22527](https://github.com/spyder-ide/spyder/pull/22527) - PR: Add initial tests for the Remote client plugin, by [@hlouzada](https://github.com/hlouzada)

In this release 31 pull requests were closed.

----

## Version 6.0.1 (2024/09/23)

### Important fixes

* Fix Spyder hanging at startup on Linux when started in a terminal in background mode.
* Fix appeal/sponsor Spyder message being shown at every startup.
* Fix error that prevented mouse clicks in Spyder to work on the Windows Subsystem for Linux.
* Avoid crashes at startup from faulty/outdated external plugins.
* Fix Spyder installer not being able to finish installation due to Start Menu entry error in some Conda installations.
* Fix Spyder installer not installing the right Spyder version (`6.0.0` vs `6.0.0rc2`)
* Fix Binder instance with example workshop project from being non-responsive.
* Fix errors related to unmaximazing panes and layout changes.

### Issues Closed

* [Issue 22514](https://github.com/spyder-ide/spyder/issues/22514) - AttributeError when unmaximizing plugin ([PR 22534](https://github.com/spyder-ide/spyder/pull/22534) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22494](https://github.com/spyder-ide/spyder/issues/22494) - Error while changing the layout and a plugin was closed while undocked ([PR 22502](https://github.com/spyder-ide/spyder/pull/22502) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22466](https://github.com/spyder-ide/spyder/issues/22466) - ndarray of text does not display correctly in variable explorer ([PR 22484](https://github.com/spyder-ide/spyder/pull/22484) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 22457](https://github.com/spyder-ide/spyder/issues/22457) - Help Spyder dialog is shown at every startup ([PR 22476](https://github.com/spyder-ide/spyder/pull/22476) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22454](https://github.com/spyder-ide/spyder/issues/22454) - Support Spyder dialog does not get focus on startup ([PR 22476](https://github.com/spyder-ide/spyder/pull/22476) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22440](https://github.com/spyder-ide/spyder/issues/22440) - IPython console not showing initial banner in Spyder 6 ([PR 22501](https://github.com/spyder-ide/spyder/pull/22501) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22433](https://github.com/spyder-ide/spyder/issues/22433) - Spyder 6 - `%autoreload` magic not loaded by default on Windows ([PR 22438](https://github.com/spyder-ide/spyder/pull/22438) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22432](https://github.com/spyder-ide/spyder/issues/22432) - AttributeError message at start up ([PR 22437](https://github.com/spyder-ide/spyder/pull/22437) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22428](https://github.com/spyder-ide/spyder/issues/22428) - Spyder 6.0 fails to install when creating Start Menu entry
* [Issue 22416](https://github.com/spyder-ide/spyder/issues/22416) - Installers for 6.0.0 release come with 6.0.0rc2 ([PR 22424](https://github.com/spyder-ide/spyder/pull/22424) by [@mrclary](https://github.com/mrclary))
* [Issue 22415](https://github.com/spyder-ide/spyder/issues/22415) - Spyder 6.0 hangs at startup on Linux (proc.communicate never times out) ([PR 22504](https://github.com/spyder-ide/spyder/pull/22504) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22124](https://github.com/spyder-ide/spyder/issues/22124) - Spyder on Binder is non-responsive ([PR 22509](https://github.com/spyder-ide/spyder/pull/22509) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21563](https://github.com/spyder-ide/spyder/issues/21563) - Error while closing project just after Spyder starts ([PR 22490](https://github.com/spyder-ide/spyder/pull/22490) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20851](https://github.com/spyder-ide/spyder/issues/20851) - Spyder under WSL2 loss of mouse click ability (corruption of transient.ini file??) ([PR 22549](https://github.com/spyder-ide/spyder/pull/22549) by [@ccordoba12](https://github.com/ccordoba12))

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 22550](https://github.com/spyder-ide/spyder/pull/22550) - PR: Avoid crashes at startup due to faulty/outdated external plugins, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22549](https://github.com/spyder-ide/spyder/pull/22549) - PR: Prevent storing a negative position when saving the main window settings (Layout), by [@ccordoba12](https://github.com/ccordoba12) ([20851](https://github.com/spyder-ide/spyder/issues/20851))
* [PR 22539](https://github.com/spyder-ide/spyder/pull/22539) - PR: Add step to `RELEASE.md` to update metadata files (`org.spyder_ide.spyder.appdata.xml`), by [@dalthviz](https://github.com/dalthviz)
* [PR 22538](https://github.com/spyder-ide/spyder/pull/22538) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)
* [PR 22534](https://github.com/spyder-ide/spyder/pull/22534) - PR: Prevent error when unmaximizing plugins (Main window), by [@ccordoba12](https://github.com/ccordoba12) ([22514](https://github.com/spyder-ide/spyder/issues/22514))
* [PR 22530](https://github.com/spyder-ide/spyder/pull/22530) - PR: Update translations for 6.0.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 22509](https://github.com/spyder-ide/spyder/pull/22509) - PR: Don't kill kernel process tree when running in Binder (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22124](https://github.com/spyder-ide/spyder/issues/22124))
* [PR 22504](https://github.com/spyder-ide/spyder/pull/22504) - PR: Don't use script to get env vars if Spyder is launched from a terminal (Utils), by [@ccordoba12](https://github.com/ccordoba12) ([22415](https://github.com/spyder-ide/spyder/issues/22415))
* [PR 22502](https://github.com/spyder-ide/spyder/pull/22502) - PR: Reset `undocked before hiding` state of all plugins before applying layout, by [@ccordoba12](https://github.com/ccordoba12) ([22494](https://github.com/spyder-ide/spyder/issues/22494))
* [PR 22501](https://github.com/spyder-ide/spyder/pull/22501) - PR: Show banner when the kernel is ready (IPython console) , by [@ccordoba12](https://github.com/ccordoba12) ([22440](https://github.com/spyder-ide/spyder/issues/22440))
* [PR 22490](https://github.com/spyder-ide/spyder/pull/22490) - PR: Prevent error when updating `sys.path` in consoles (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([21563](https://github.com/spyder-ide/spyder/issues/21563))
* [PR 22484](https://github.com/spyder-ide/spyder/pull/22484) - PR: Change default format in array editor to `''`, by [@jitseniesen](https://github.com/jitseniesen) ([22466](https://github.com/spyder-ide/spyder/issues/22466))
* [PR 22476](https://github.com/spyder-ide/spyder/pull/22476) - PR: Fix issues showing the in-app appeal message, by [@ccordoba12](https://github.com/ccordoba12) ([22457](https://github.com/spyder-ide/spyder/issues/22457), [22454](https://github.com/spyder-ide/spyder/issues/22454))
* [PR 22474](https://github.com/spyder-ide/spyder/pull/22474) - PR: Update org.spyder_ide.spyder.appdata.xml, by [@kevinsmia1939](https://github.com/kevinsmia1939)
* [PR 22468](https://github.com/spyder-ide/spyder/pull/22468) - PR: Fix development version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22459](https://github.com/spyder-ide/spyder/pull/22459) - PR: Update workflows to run in the `6.x` branch (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22442](https://github.com/spyder-ide/spyder/pull/22442) - PR: Update contributing, release and maintenance instructions for backporting, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22438](https://github.com/spyder-ide/spyder/pull/22438) - PR: Enable `autoreload` magic on all operating systems (Config), by [@ccordoba12](https://github.com/ccordoba12) ([22433](https://github.com/spyder-ide/spyder/issues/22433))
* [PR 22437](https://github.com/spyder-ide/spyder/pull/22437) - PR: Fix bug when calling `update_edit_menu` at startup (Editor), by [@ccordoba12](https://github.com/ccordoba12) ([22432](https://github.com/spyder-ide/spyder/issues/22432))
* [PR 22424](https://github.com/spyder-ide/spyder/pull/22424) - PR: Prioritize conda-forge channel so that stable releases are pulled above unstable ones (Installers), by [@mrclary](https://github.com/mrclary) ([22416](https://github.com/spyder-ide/spyder/issues/22416))

In this release 20 pull requests were closed.

----

## Version 6.0.0 (2024-09-03)

### New features

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

### Important fixes

* Environment variables declared in `~/.bashrc` or `~/.zhrc` are detected and
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

### UX/UI improvements

* Make Spyder accept Chinese, Korean or Japanese input on Linux by adding
  `fcitx-qt5` as a new dependency (in conda environments only).
* The file switcher can browse and open files present in the current project
  (in conda environments or if the `fzf` package is installed).
* Improve how options are displayed and handled in several Variable Explorer
  viewers.
* The interface font used by the entire application can be configured in
  `Preferences > Appearance`.
* Files can be opened in the editor by pasting their path in the Working
  Directory toolbar.
* Add a new button to the Variable Explorer to indicate when variables are being
  filtered.
* Show intro message for panes that don't display content at startup.

### New, updated and removed plugins

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

### New API features

* `SpyderPluginV2.get_description` must be a static method and
  `SpyderPluginV2.get_icon` a class or static method. This is necessary to
  display the list of available plugins in Preferences in a more user-friendly
  way (see PR [PR 21101](https://github.com/spyder-ide/spyder/pull/21101) for
  the details).
* `SpyderPlugin` and `SpyderPluginWidget` are no longer exposed in the public
  API. They will be removed in Spyder 6.1.
* All comboboxes must inherit from `SpyderComboBox` or related subclasses in
  `spyder.api.widgets.comboboxes`. Comboboxes that inherit directly from
  `QComboBox` won't follow Spyder's graphical style.
* All menus must inherit from `SpyderMenu` in `spyder.api.widgets.menus`.
* All dialog button boxes must inherit from `SpyderDialogButtonBox` in
  `spyder.api.widgets.dialogs`.
* Helper classes were added to `spyder.api.fonts` to get and set the fonts used
  in Spyder in different widgets.
* Helper classes were added to `spyder.api.shortcuts` to get and set keyboard
  shortcuts.
* `AsyncDispatcher` was added to `spyder.api.asyncdispatcher` to run asyncio
  code in Spyder. Only Qt signals can be attached to asyncio
  `future.add_done_callback` calls to avoid segfaults.
* `ShellConnectStatusBarWidget` was added to `spyder.api.shellconnect.status`
  to create status bar widgets connected to the current console.

### Issues Closed

* [Issue 22378](https://github.com/spyder-ide/spyder/issues/22378) - Spyder 6.0.0 release ([PR 22401](https://github.com/spyder-ide/spyder/pull/22401) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22374](https://github.com/spyder-ide/spyder/issues/22374) - Check reason why Sphinx upper constraint is needed to make the splash screen work on Windows ([PR 22404](https://github.com/spyder-ide/spyder/pull/22404) by [@mrclary](https://github.com/mrclary))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 22404](https://github.com/spyder-ide/spyder/pull/22404) - PR: Resolve issue where splash screen was incorrectly rendered if conda environment is not activated (Installers), by [@mrclary](https://github.com/mrclary) ([22374](https://github.com/spyder-ide/spyder/issues/22374))
* [PR 22403](https://github.com/spyder-ide/spyder/pull/22403) - PR: Minor fixes to Spyder 6 Changelog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22401](https://github.com/spyder-ide/spyder/pull/22401) - PR: Update core dependencies for 6.0.0, by [@dalthviz](https://github.com/dalthviz) ([22378](https://github.com/spyder-ide/spyder/issues/22378))
* [PR 22399](https://github.com/spyder-ide/spyder/pull/22399) - PR: Fix issue where single-instance mode was not enforced (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22397](https://github.com/spyder-ide/spyder/pull/22397) - PR: Update user-facing Changelog for Spyder 6.0, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22395](https://github.com/spyder-ide/spyder/pull/22395) - PR: Some last minute fixes before releasing Spyder 6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22394](https://github.com/spyder-ide/spyder/pull/22394) - PR: Restore `TMPDIR` in the kernel if it's available in the system, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22387](https://github.com/spyder-ide/spyder/pull/22387) - PR: Add in-app appeal message for donations (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22382](https://github.com/spyder-ide/spyder/pull/22382) - PR: Pass `TMPDIR` env var to kernels (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22380](https://github.com/spyder-ide/spyder/pull/22380) - PR: Fix listing envs in the Consoles' environment menu (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22379](https://github.com/spyder-ide/spyder/pull/22379) - PR: Update Qtconsole subrepo, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22377](https://github.com/spyder-ide/spyder/pull/22377) - PR: Don't expose `SpyderPlugin` and `SpyderPluginWidget` as part of the public API, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22334](https://github.com/spyder-ide/spyder/pull/22334) - PR: Update translations from Crowdin, by [@spyder-bot](https://github.com/spyder-bot)

In this release 13 pull requests were closed.

----

## Version 6.0rc2 (2024-08-22)

### Issues Closed

* [Issue 22363](https://github.com/spyder-ide/spyder/issues/22363) - Unable to connect via new remote development feature: poetry: command not found ([PR 22368](https://github.com/spyder-ide/spyder/pull/22368) by [@hlouzada](https://github.com/hlouzada))
* [Issue 22353](https://github.com/spyder-ide/spyder/issues/22353) - Splash screen when running from installer shows partially (at least on Windows) ([PR 22370](https://github.com/spyder-ide/spyder/pull/22370) by [@mrclary](https://github.com/mrclary))
* [Issue 22352](https://github.com/spyder-ide/spyder/issues/22352) - Spyder 6.0 rc2 release
* [Issue 22309](https://github.com/spyder-ide/spyder/issues/22309) - Status bar does not show Python version ([PR 22350](https://github.com/spyder-ide/spyder/pull/22350) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22266](https://github.com/spyder-ide/spyder/issues/22266) - Panes options menus not rendering correctly on first trigger  ([PR 22355](https://github.com/spyder-ide/spyder/pull/22355) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22240](https://github.com/spyder-ide/spyder/issues/22240) - Spyder 6.0.0b2 consoles fail to start with micromamba ([PR 22360](https://github.com/spyder-ide/spyder/pull/22360) by [@mrclary](https://github.com/mrclary))
* [Issue 21652](https://github.com/spyder-ide/spyder/issues/21652) - Warnings in the console with the Brain2 library ([PR 22350](https://github.com/spyder-ide/spyder/pull/22350) by [@ccordoba12](https://github.com/ccordoba12))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 22371](https://github.com/spyder-ide/spyder/pull/22371) - PR: Fix starting kernels for old Conda versions (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22370](https://github.com/spyder-ide/spyder/pull/22370) - PR: Limit sphinx version to `<7.4.0` to prevent bug with splash screen on Windows, by [@mrclary](https://github.com/mrclary) ([22353](https://github.com/spyder-ide/spyder/issues/22353))
* [PR 22368](https://github.com/spyder-ide/spyder/pull/22368) - PR: Update `spyder-remote-services` installation script (Remote client), by [@hlouzada](https://github.com/hlouzada) ([22363](https://github.com/spyder-ide/spyder/issues/22363))
* [PR 22367](https://github.com/spyder-ide/spyder/pull/22367) - PR: Update core dependencies for 6.0.0rc2, by [@dalthviz](https://github.com/dalthviz)
* [PR 22364](https://github.com/spyder-ide/spyder/pull/22364) - PR: Sync the IPython console current env with the one used in the Editor for completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22362](https://github.com/spyder-ide/spyder/pull/22362) - PR: Update menuinst version for file-type association (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22361](https://github.com/spyder-ide/spyder/pull/22361) - PR: Fix buttons style of the start tour dialog (Tours), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22360](https://github.com/spyder-ide/spyder/pull/22360) - PR: Fix redirection flag for micromamba (IPython console), by [@mrclary](https://github.com/mrclary) ([22240](https://github.com/spyder-ide/spyder/issues/22240))
* [PR 22355](https://github.com/spyder-ide/spyder/pull/22355) - PR: Prevent first time render glitch by calling position logic via a timer in `showEvent` (Menus), by [@dalthviz](https://github.com/dalthviz) ([22266](https://github.com/spyder-ide/spyder/issues/22266))
* [PR 22350](https://github.com/spyder-ide/spyder/pull/22350) - PR: Add statusbar widget to display the env info associated to the current console (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22309](https://github.com/spyder-ide/spyder/issues/22309), [21652](https://github.com/spyder-ide/spyder/issues/21652))
* [PR 22339](https://github.com/spyder-ide/spyder/pull/22339) - PR: Recreate Spyder runtime environment on minor updates (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22338](https://github.com/spyder-ide/spyder/pull/22338) - PR: Ensure "Update Assets" job runs when "Build Subrepos" is skipped, by [@mrclary](https://github.com/mrclary)
* [PR 22303](https://github.com/spyder-ide/spyder/pull/22303) - PR: Update connections dialog size constants, title and icon (Remote Client), by [@dalthviz](https://github.com/dalthviz)

In this release 13 pull requests were closed.

----

## Version 6.0rc1 (2024-08-08)

### Issues Closed

* [Issue 22317](https://github.com/spyder-ide/spyder/issues/22317) - Spyder 6.0 rc1 release ([PR 22336](https://github.com/spyder-ide/spyder/pull/22336) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22181](https://github.com/spyder-ide/spyder/issues/22181) - Warning message on the first console that is open ([PR 22302](https://github.com/spyder-ide/spyder/pull/22302) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22180](https://github.com/spyder-ide/spyder/issues/22180) - Text being cut in the `About` dialog ([PR 22286](https://github.com/spyder-ide/spyder/pull/22286) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22112](https://github.com/spyder-ide/spyder/issues/22112) - `ModuleNotFoundError: No module named 'win32gui'` on the Windows installer
* [Issue 22033](https://github.com/spyder-ide/spyder/issues/22033) - Closing last unfocused document tab causes IndexError ([PR 22292](https://github.com/spyder-ide/spyder/pull/22292) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21959](https://github.com/spyder-ide/spyder/issues/21959) - Do not translate `Commit` in context menu of Files/Projects ([PR 22320](https://github.com/spyder-ide/spyder/pull/22320) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21824](https://github.com/spyder-ide/spyder/issues/21824) - It's not clear what some actions in the new Options menus of Variable Explorer editors do ([PR 22061](https://github.com/spyder-ide/spyder/pull/22061) by [@jitseniesen](https://github.com/jitseniesen))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 22336](https://github.com/spyder-ide/spyder/pull/22336) - PR: Update core dependencies for 6.0.0 rc1, by [@dalthviz](https://github.com/dalthviz) ([22317](https://github.com/spyder-ide/spyder/issues/22317))
* [PR 22333](https://github.com/spyder-ide/spyder/pull/22333) - PR: Update translations for 6.0.0 (extra strings), by [@dalthviz](https://github.com/dalthviz)
* [PR 22328](https://github.com/spyder-ide/spyder/pull/22328) - PR: Add a widget to show connection logs to `ConnectionDialog` (Remote client), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22327](https://github.com/spyder-ide/spyder/pull/22327) - PR: Fix typo in shebang line in `user-env.sh`, by [@mrclary](https://github.com/mrclary)
* [PR 22320](https://github.com/spyder-ide/spyder/pull/22320) - PR: Improve text of several strings for translation (Files/Projects), by [@ccordoba12](https://github.com/ccordoba12) ([21959](https://github.com/spyder-ide/spyder/issues/21959))
* [PR 22308](https://github.com/spyder-ide/spyder/pull/22308) - PR: Enable showing calltip widget even with signatures without parameters (Editor/Completion), by [@dalthviz](https://github.com/dalthviz)
* [PR 22304](https://github.com/spyder-ide/spyder/pull/22304) - PR: Disable shortcuts for actions in the `View > Panes` menu when not visible (Layout), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22302](https://github.com/spyder-ide/spyder/pull/22302) - PR: Filter unnecessary stream messages in the kernel (IPython console), by [@dalthviz](https://github.com/dalthviz) ([22181](https://github.com/spyder-ide/spyder/issues/22181))
* [PR 22300](https://github.com/spyder-ide/spyder/pull/22300) - PR: Update Spyder installer base environment with conda-lock file, by [@mrclary](https://github.com/mrclary)
* [PR 22293](https://github.com/spyder-ide/spyder/pull/22293) - PR: Fix resetting layout options (Layout), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22292](https://github.com/spyder-ide/spyder/pull/22292) - PR: Update custom button tab index when removing intermediate tabs without changing current selected tab (Widgets), by [@dalthviz](https://github.com/dalthviz) ([22033](https://github.com/spyder-ide/spyder/issues/22033))
* [PR 22291](https://github.com/spyder-ide/spyder/pull/22291) - PR: Revert PR 22269 (Disable signing Mac app), by [@mrclary](https://github.com/mrclary)
* [PR 22290](https://github.com/spyder-ide/spyder/pull/22290) - PR: Always create the local conda channel on CI, even for releases, by [@mrclary](https://github.com/mrclary)
* [PR 22286](https://github.com/spyder-ide/spyder/pull/22286) - PR: Increase about dialog width to prevent cutting text on Windows (Application), by [@dalthviz](https://github.com/dalthviz) ([22180](https://github.com/spyder-ide/spyder/issues/22180))
* [PR 22285](https://github.com/spyder-ide/spyder/pull/22285) - PR: Handle remote connection lost (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22276](https://github.com/spyder-ide/spyder/pull/22276) - PR: Improve UI of status bar widgets (API/Completions), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22061](https://github.com/spyder-ide/spyder/pull/22061) - PR: New menu item for view options in array and dataframe editors, by [@jitseniesen](https://github.com/jitseniesen) ([21824](https://github.com/spyder-ide/spyder/issues/21824))

In this release 17 pull requests were closed.

----

## Version 6.0beta3 (2024-07-18)

### Issues Closed

* [Issue 22262](https://github.com/spyder-ide/spyder/issues/22262) - Spyder 6.0 beta3 release
* [Issue 22201](https://github.com/spyder-ide/spyder/issues/22201) - Build string in conda package url for Spyder in the conda-lock file release asset does not match conda-forge ([PR 22204](https://github.com/spyder-ide/spyder/pull/22204) by [@mrclary](https://github.com/mrclary))
* [Issue 22194](https://github.com/spyder-ide/spyder/issues/22194) - CommError upon opening existing console ([PR 22231](https://github.com/spyder-ide/spyder/pull/22231) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22179](https://github.com/spyder-ide/spyder/issues/22179) - Kernel is dead message when starting Spyder ([PR 22231](https://github.com/spyder-ide/spyder/pull/22231) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22178](https://github.com/spyder-ide/spyder/issues/22178) - Traceback related to run parameters over CI ([PR 22232](https://github.com/spyder-ide/spyder/pull/22232) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21596](https://github.com/spyder-ide/spyder/issues/21596) - Left pane size changes when starting Spyder ([PR 22232](https://github.com/spyder-ide/spyder/pull/22232) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21590](https://github.com/spyder-ide/spyder/issues/21590) - Profiler pane not showing results ([PR 21713](https://github.com/spyder-ide/spyder/pull/21713) by [@rear1019](https://github.com/rear1019))
* [Issue 21129](https://github.com/spyder-ide/spyder/issues/21129) - Spyder 6.0.0a1 - New line (ctrl-enter) in console runs cell instead ([PR 22230](https://github.com/spyder-ide/spyder/pull/22230) by [@ccordoba12](https://github.com/ccordoba12))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 22269](https://github.com/spyder-ide/spyder/pull/22269) - PR: Temporarily suspend notarizing the macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 22253](https://github.com/spyder-ide/spyder/pull/22253) - PR: Update conda-lock for change in release workflow, by [@mrclary](https://github.com/mrclary)
* [PR 22243](https://github.com/spyder-ide/spyder/pull/22243) - PR: Add missing space over masked label text (Variable Explorer - `ArrayEditor`), by [@dalthviz](https://github.com/dalthviz)
* [PR 22234](https://github.com/spyder-ide/spyder/pull/22234) - PR: Improve Switcher UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22232](https://github.com/spyder-ide/spyder/pull/22232) - PR: Tabify Outline next to Projects in default layout and other layout improvements and fixes, by [@ccordoba12](https://github.com/ccordoba12) ([22178](https://github.com/spyder-ide/spyder/issues/22178), [21596](https://github.com/spyder-ide/spyder/issues/21596))
* [PR 22231](https://github.com/spyder-ide/spyder/pull/22231) - PR: Fix errors when getting Matplotlib backend in the kernel (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22194](https://github.com/spyder-ide/spyder/issues/22194), [22179](https://github.com/spyder-ide/spyder/issues/22179))
* [PR 22230](https://github.com/spyder-ide/spyder/pull/22230) - PR: Fix shortcuts for several Run and Debugger actions, by [@ccordoba12](https://github.com/ccordoba12) ([21129](https://github.com/spyder-ide/spyder/issues/21129))
* [PR 22228](https://github.com/spyder-ide/spyder/pull/22228) - PR: Minor UI improvements to the Run entry in Preferences, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22223](https://github.com/spyder-ide/spyder/pull/22223) - PR: Fix Windows tunneling error when connecting to kernels (Remote client), by [@hlouzada](https://github.com/hlouzada)
* [PR 22204](https://github.com/spyder-ide/spyder/pull/22204) - PR: Fix issues with installers discovered after 6.0.0b2 was released, by [@mrclary](https://github.com/mrclary) ([22201](https://github.com/spyder-ide/spyder/issues/22201))
* [PR 22202](https://github.com/spyder-ide/spyder/pull/22202) - PR: Fix issue where macOS installer update fails to launch Spyder, by [@mrclary](https://github.com/mrclary)
* [PR 22200](https://github.com/spyder-ide/spyder/pull/22200) - PR: Improve implementation and UI of console envs menu (IPython console/Main interpreter) , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22197](https://github.com/spyder-ide/spyder/pull/22197) - PR: Address small PySide2 compatibility issues, by [@hmaarrfk](https://github.com/hmaarrfk)
* [PR 22196](https://github.com/spyder-ide/spyder/pull/22196) - PR: Make QtWebEngine optional, by [@hmaarrfk](https://github.com/hmaarrfk)
* [PR 22185](https://github.com/spyder-ide/spyder/pull/22185) - PR: Update translations for 6.0.0 , by [@dalthviz](https://github.com/dalthviz)
* [PR 22183](https://github.com/spyder-ide/spyder/pull/22183) - PR: Update `README`, `RELEASE` and `Announcements` files, by [@dalthviz](https://github.com/dalthviz)
* [PR 21713](https://github.com/spyder-ide/spyder/pull/21713) - PR: Fix profiling results being hidden (Profiler), by [@rear1019](https://github.com/rear1019) ([21590](https://github.com/spyder-ide/spyder/issues/21590))

In this release 17 pull requests were closed.

----

## Version 6.0beta2 (2024-06-19)

### Issues Closed

* [Issue 22176](https://github.com/spyder-ide/spyder/issues/22176) - Spyder 6.0 beta2 release  ([PR 22177](https://github.com/spyder-ide/spyder/pull/22177) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22070](https://github.com/spyder-ide/spyder/issues/22070) - Snapping Spyder 6 while `Show breakpoints` is active is broken ([PR 22163](https://github.com/spyder-ide/spyder/pull/22163) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22034](https://github.com/spyder-ide/spyder/issues/22034) - IPython console Matplotlib rc parameters are inconsistent when switching backends ([PR 22088](https://github.com/spyder-ide/spyder/pull/22088) by [@mrclary](https://github.com/mrclary))
* [Issue 22030](https://github.com/spyder-ide/spyder/issues/22030) - Issue reporter submit to Github results in 403 error ([PR 22108](https://github.com/spyder-ide/spyder/pull/22108) by [@mrclary](https://github.com/mrclary))
* [Issue 21878](https://github.com/spyder-ide/spyder/issues/21878) - KeyError when changing run options in 6.0.0a4 ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21771](https://github.com/spyder-ide/spyder/issues/21771) - Adding "User environment variables in Windows registry" ([PR 22075](https://github.com/spyder-ide/spyder/pull/22075) by [@mrclary](https://github.com/mrclary))
* [Issue 20700](https://github.com/spyder-ide/spyder/issues/20700) - Run settings can not be changed in master ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20569](https://github.com/spyder-ide/spyder/issues/20569) - Run after closing  all files ([PR 22141](https://github.com/spyder-ide/spyder/pull/22141) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 16265](https://github.com/spyder-ide/spyder/issues/16265) - Outline pane is automatically shown when editor is maximized ([PR 19784](https://github.com/spyder-ide/spyder/pull/19784) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 10932](https://github.com/spyder-ide/spyder/issues/10932) - Spyder is ignoring matplotlib user settings ([PR 22088](https://github.com/spyder-ide/spyder/pull/22088) by [@mrclary](https://github.com/mrclary))

In this release 10 issues were closed.

### Pull Requests Merged

* [PR 22177](https://github.com/spyder-ide/spyder/pull/22177) - PR: Update core dependencies for 6.0.0 beta2, by [@dalthviz](https://github.com/dalthviz) ([22176](https://github.com/spyder-ide/spyder/issues/22176))
* [PR 22163](https://github.com/spyder-ide/spyder/pull/22163) - PR: Improve UI/UX of the Debugger pane, by [@ccordoba12](https://github.com/ccordoba12) ([22070](https://github.com/spyder-ide/spyder/issues/22070))
* [PR 22155](https://github.com/spyder-ide/spyder/pull/22155) - PR: Use `jupyter_server` instead of `jupyterhub` for remote client plugin, by [@hlouzada](https://github.com/hlouzada)
* [PR 22143](https://github.com/spyder-ide/spyder/pull/22143) - PR: Add new icons to be used in the Debugger toolbar, by [@conradolandia](https://github.com/conradolandia)
* [PR 22141](https://github.com/spyder-ide/spyder/pull/22141) - PR: Improve UI/UX of the Run plugin configuration widgets, by [@ccordoba12](https://github.com/ccordoba12) ([21878](https://github.com/spyder-ide/spyder/issues/21878), [20700](https://github.com/spyder-ide/spyder/issues/20700), [20569](https://github.com/spyder-ide/spyder/issues/20569))
* [PR 22137](https://github.com/spyder-ide/spyder/pull/22137) - PR: Fix conflict between AsyncDispatcher and `run_sync` function of `jupyter_core`, by [@hlouzada](https://github.com/hlouzada)
* [PR 22120](https://github.com/spyder-ide/spyder/pull/22120) - PR: Enable comms to work across different Python versions (IPython console), by [@impact27](https://github.com/impact27)
* [PR 22118](https://github.com/spyder-ide/spyder/pull/22118) - PR: Use `GITHUB_TOKEN` to make authorized user requests against GitHub (CI), by [@mrclary](https://github.com/mrclary)
* [PR 22110](https://github.com/spyder-ide/spyder/pull/22110) - PR: Adjust emblems for Projects menu icons, by [@conradolandia](https://github.com/conradolandia)
* [PR 22108](https://github.com/spyder-ide/spyder/pull/22108) - PR: Replace `github.py` with `pygithub` package, by [@mrclary](https://github.com/mrclary) ([22030](https://github.com/spyder-ide/spyder/issues/22030))
* [PR 22103](https://github.com/spyder-ide/spyder/pull/22103) - PR: Update macOS from 11 to 12 in installer workflow, by [@mrclary](https://github.com/mrclary)
* [PR 22089](https://github.com/spyder-ide/spyder/pull/22089) - PR: Fix workflow glob (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 22088](https://github.com/spyder-ide/spyder/pull/22088) - PR: Fix issue where Spyder's inline graphics preferences were not applied, by [@mrclary](https://github.com/mrclary) ([22034](https://github.com/spyder-ide/spyder/issues/22034), [10932](https://github.com/spyder-ide/spyder/issues/10932))
* [PR 22077](https://github.com/spyder-ide/spyder/pull/22077) - PR: Try to decrease timeouts when running tests and check general tests robustness and speed (CI/Testing), by [@dalthviz](https://github.com/dalthviz)
* [PR 22075](https://github.com/spyder-ide/spyder/pull/22075) - PR: Fix setting user environment variables on Windows, by [@mrclary](https://github.com/mrclary) ([21771](https://github.com/spyder-ide/spyder/issues/21771))
* [PR 19784](https://github.com/spyder-ide/spyder/pull/19784) - PR: Remember undocked state of plugins when closed and allow to close Outline when the Editor is maximized or in an Editor window, by [@ccordoba12](https://github.com/ccordoba12) ([16265](https://github.com/spyder-ide/spyder/issues/16265))

In this release 16 pull requests were closed.

----

## Version 6.0beta1 (2024-05-16)

### Issues Closed

* [Issue 22084](https://github.com/spyder-ide/spyder/issues/22084) - Error when restarting kernel ([PR 22085](https://github.com/spyder-ide/spyder/pull/22085) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 22076](https://github.com/spyder-ide/spyder/issues/22076) - Spyder 6.0 beta1 release ([PR 22083](https://github.com/spyder-ide/spyder/pull/22083) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22068](https://github.com/spyder-ide/spyder/issues/22068) - Use Python 3.11 in the Spyder 6 installers ([PR 22072](https://github.com/spyder-ide/spyder/pull/22072) by [@mrclary](https://github.com/mrclary))
* [Issue 22049](https://github.com/spyder-ide/spyder/issues/22049) - Editor tab no longer called "Editor" ([PR 22050](https://github.com/spyder-ide/spyder/pull/22050) by [@dalthviz](https://github.com/dalthviz))
* [Issue 22012](https://github.com/spyder-ide/spyder/issues/22012) - QThread destroyed when still running error in tests with main_window fixture ([PR 22053](https://github.com/spyder-ide/spyder/pull/22053) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21899](https://github.com/spyder-ide/spyder/issues/21899) - Feature Request: Be able to double click plots so they blow up into a larger screen ([PR 22029](https://github.com/spyder-ide/spyder/pull/22029) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21743](https://github.com/spyder-ide/spyder/issues/21743) - Enhancement proposal: create a plot button in variable explorer to visualize numerical data ([PR 21969](https://github.com/spyder-ide/spyder/pull/21969) by [@dpturibio](https://github.com/dpturibio))
* [Issue 17468](https://github.com/spyder-ide/spyder/issues/17468) - Editor migration tracker ([PR 22005](https://github.com/spyder-ide/spyder/pull/22005) by [@dalthviz](https://github.com/dalthviz))
* [Issue 12158](https://github.com/spyder-ide/spyder/issues/12158) - Move plots in Plots pane ([PR 22029](https://github.com/spyder-ide/spyder/pull/22029) by [@ccordoba12](https://github.com/ccordoba12))

In this release 9 issues were closed.

### Pull Requests Merged

* [PR 22085](https://github.com/spyder-ide/spyder/pull/22085) - PR: Fix callable associated to `restart_action` (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([22084](https://github.com/spyder-ide/spyder/issues/22084))
* [PR 22083](https://github.com/spyder-ide/spyder/pull/22083) - PR: Update core dependencies for 6.0.0 beta1, by [@dalthviz](https://github.com/dalthviz) ([22076](https://github.com/spyder-ide/spyder/issues/22076))
* [PR 22079](https://github.com/spyder-ide/spyder/pull/22079) - PR: Add UI for the `Remote client` plugin, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22072](https://github.com/spyder-ide/spyder/pull/22072) - PR: Use Python 3.11 for our installers, by [@mrclary](https://github.com/mrclary) ([22068](https://github.com/spyder-ide/spyder/issues/22068))
* [PR 22059](https://github.com/spyder-ide/spyder/pull/22059) - PR: Use conda-lock files to incrementally update conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 22057](https://github.com/spyder-ide/spyder/pull/22057) - PR: Make Matplotlib status bar widget show the right backend and fix some errors related to kernel restarts for options that require them, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 22053](https://github.com/spyder-ide/spyder/pull/22053) - PR: Fix introspection testing (CI), by [@dalthviz](https://github.com/dalthviz) ([22012](https://github.com/spyder-ide/spyder/issues/22012))
* [PR 22050](https://github.com/spyder-ide/spyder/pull/22050) - PR: Show `Editor` as title when the Editor is tabbed (Editor), by [@dalthviz](https://github.com/dalthviz) ([22049](https://github.com/spyder-ide/spyder/issues/22049))
* [PR 22029](https://github.com/spyder-ide/spyder/pull/22029) - PR: Improve UX of the Plots plugin, by [@ccordoba12](https://github.com/ccordoba12) ([21899](https://github.com/spyder-ide/spyder/issues/21899), [12158](https://github.com/spyder-ide/spyder/issues/12158))
* [PR 22025](https://github.com/spyder-ide/spyder/pull/22025) - PR: Improve drag & drop out of file explorer plugin, by [@rear1019](https://github.com/rear1019)
* [PR 22005](https://github.com/spyder-ide/spyder/pull/22005) - PR: Editor migration missing TODOs (Editor), by [@dalthviz](https://github.com/dalthviz) ([17468](https://github.com/spyder-ide/spyder/issues/17468))
* [PR 21969](https://github.com/spyder-ide/spyder/pull/21969) - PR: Add ability to show plots for dataframes (Variable Explorer), by [@dpturibio](https://github.com/dpturibio) ([21743](https://github.com/spyder-ide/spyder/issues/21743))
* [PR 21757](https://github.com/spyder-ide/spyder/pull/21757) - PR: Add backend for a new `Remote client` plugin, by [@hlouzada](https://github.com/hlouzada)

In this release 13 pull requests were closed.

----

## Version 6.0alpha5 (2024-04-23)

### Issues Closed

* [Issue 22008](https://github.com/spyder-ide/spyder/issues/22008) - Spyder 6.0 alpha5 release ([PR 22017](https://github.com/spyder-ide/spyder/pull/22017) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21900](https://github.com/spyder-ide/spyder/issues/21900) - IPython Console does not start if `debugpy` is not available (6.0 alpha4) ([PR 21926](https://github.com/spyder-ide/spyder/pull/21926) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21882](https://github.com/spyder-ide/spyder/issues/21882) - Connect errors without specific handling triggered while doing a check for updates to our error report dialog ([PR 21836](https://github.com/spyder-ide/spyder/pull/21836) by [@mrclary](https://github.com/mrclary))
* [Issue 21876](https://github.com/spyder-ide/spyder/issues/21876) - `%runcell` can not edit locals ([PR 21875](https://github.com/spyder-ide/spyder/pull/21875) by [@impact27](https://github.com/impact27))
* [Issue 21855](https://github.com/spyder-ide/spyder/issues/21855) - `menuinst` `Exception: Nothing to do:` traceback when installing Spyder 6.0.0a4 in a new conda env
* [Issue 21849](https://github.com/spyder-ide/spyder/issues/21849) - Message without translation in the tour ([PR 21880](https://github.com/spyder-ide/spyder/pull/21880) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21776](https://github.com/spyder-ide/spyder/issues/21776) - Standalone installers for 6.0 alpha4 are incorrectly named and Mac installer failed to build ([PR 21782](https://github.com/spyder-ide/spyder/pull/21782) by [@mrclary](https://github.com/mrclary))
* [Issue 21627](https://github.com/spyder-ide/spyder/issues/21627) - Larger dataframes with columns on the far right doesnt display max values when clicking on their column names twice + Other bugs ([PR 21913](https://github.com/spyder-ide/spyder/pull/21913) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21556](https://github.com/spyder-ide/spyder/issues/21556) - Follow up to work that added refresh buttons to editors from the Variable Explorer ([PR 21666](https://github.com/spyder-ide/spyder/pull/21666) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21468](https://github.com/spyder-ide/spyder/issues/21468) - Editor error while closing a project ([PR 21918](https://github.com/spyder-ide/spyder/pull/21918) by [@dalthviz](https://github.com/dalthviz))
* [Issue 17807](https://github.com/spyder-ide/spyder/issues/17807) - Spyder not conform PEP3120 ([PR 21804](https://github.com/spyder-ide/spyder/pull/21804) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 12193](https://github.com/spyder-ide/spyder/issues/12193) - Move Editor plugin to use new API ([PR 21353](https://github.com/spyder-ide/spyder/pull/21353) by [@dalthviz](https://github.com/dalthviz))
* [Issue 9148](https://github.com/spyder-ide/spyder/issues/9148) - Low quality matplotlib inline plots on hidpi display ([PR 21812](https://github.com/spyder-ide/spyder/pull/21812) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 7609](https://github.com/spyder-ide/spyder/issues/7609) - Add a shortcut to create a new cell

In this release 14 issues were closed.

### Pull Requests Merged

* [PR 22017](https://github.com/spyder-ide/spyder/pull/22017) - PR: Update core dependencies for 6.0.0 alpha5, by [@dalthviz](https://github.com/dalthviz) ([22008](https://github.com/spyder-ide/spyder/issues/22008))
* [PR 22006](https://github.com/spyder-ide/spyder/pull/22006) - PR: Fix adding corner widgets in dockable plugins (API), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21948](https://github.com/spyder-ide/spyder/pull/21948) - PR: Fix getting IPython version for external conda environments (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21945](https://github.com/spyder-ide/spyder/pull/21945) - PR: Remove icons from standard buttons in dialogs (UI/UX), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21934](https://github.com/spyder-ide/spyder/pull/21934) - PR: Correct icon colors for remote connection dialog following WCAG 2 guidelines, by [@conradolandia](https://github.com/conradolandia)
* [PR 21926](https://github.com/spyder-ide/spyder/pull/21926) - PR: Add benign error when `debugpy` is not available (IPython console), by [@ccordoba12](https://github.com/ccordoba12) ([21900](https://github.com/spyder-ide/spyder/issues/21900))
* [PR 21918](https://github.com/spyder-ide/spyder/pull/21918) - PR: Add validation for `editor.sideareas_color` over debugger panel, by [@dalthviz](https://github.com/dalthviz) ([21468](https://github.com/spyder-ide/spyder/issues/21468))
* [PR 21913](https://github.com/spyder-ide/spyder/pull/21913) - PR: Fix issues with scrolling in dataframe editor (Variable Explorer), by [@jitseniesen](https://github.com/jitseniesen) ([21627](https://github.com/spyder-ide/spyder/issues/21627))
* [PR 21883](https://github.com/spyder-ide/spyder/pull/21883) - PR: Add icon to represent clearing the console (IPython console), by [@conradolandia](https://github.com/conradolandia)
* [PR 21880](https://github.com/spyder-ide/spyder/pull/21880) - PR: Add missing string for translation (Tours), by [@ccordoba12](https://github.com/ccordoba12) ([21849](https://github.com/spyder-ide/spyder/issues/21849))
* [PR 21875](https://github.com/spyder-ide/spyder/pull/21875) - PR: Allow magic to edit locals while debugging, by [@impact27](https://github.com/impact27) ([21876](https://github.com/spyder-ide/spyder/issues/21876))
* [PR 21871](https://github.com/spyder-ide/spyder/pull/21871) - PR: Fix issue where Spyder started automatically before conda-based installer exited, by [@mrclary](https://github.com/mrclary)
* [PR 21857](https://github.com/spyder-ide/spyder/pull/21857) - PR: UI improvements to configuration pages and other widgets, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21852](https://github.com/spyder-ide/spyder/pull/21852) - PR: Update to `codecov/action@v4` (CI), by [@mrclary](https://github.com/mrclary)
* [PR 21848](https://github.com/spyder-ide/spyder/pull/21848) - PR: Add icons for the remote connection dialog, by [@conradolandia](https://github.com/conradolandia)
* [PR 21844](https://github.com/spyder-ide/spyder/pull/21844) - PR: Make `SpyderPalette` inherit from QDarkStyle palettes and remove `QStylePalette`, by [@conradolandia](https://github.com/conradolandia)
* [PR 21836](https://github.com/spyder-ide/spyder/pull/21836) - PR: Only show UpdateManager statusbar widget while updating and when updates are available, by [@mrclary](https://github.com/mrclary) ([21882](https://github.com/spyder-ide/spyder/issues/21882))
* [PR 21813](https://github.com/spyder-ide/spyder/pull/21813) - PR: Additional UI/UX improvements for Files and Projects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21812](https://github.com/spyder-ide/spyder/pull/21812) - PR: Change default resolution of plots to 144 dpi, by [@jitseniesen](https://github.com/jitseniesen) ([9148](https://github.com/spyder-ide/spyder/issues/9148))
* [PR 21804](https://github.com/spyder-ide/spyder/pull/21804) - PR: Use UTF-8 by default for Python files per PEP3120, by [@jitseniesen](https://github.com/jitseniesen) ([17807](https://github.com/spyder-ide/spyder/issues/17807))
* [PR 21788](https://github.com/spyder-ide/spyder/pull/21788) - PR: Avoid `conda run` capturing output in env activation (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21785](https://github.com/spyder-ide/spyder/pull/21785) - PR: Do not use version in artifact name (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21782](https://github.com/spyder-ide/spyder/pull/21782) - PR: Fix release build issues, by [@mrclary](https://github.com/mrclary) ([21776](https://github.com/spyder-ide/spyder/issues/21776))
* [PR 21666](https://github.com/spyder-ide/spyder/pull/21666) - PR: Unify UI of editors in Variable Explorer and simplify code, by [@jitseniesen](https://github.com/jitseniesen) ([21556](https://github.com/spyder-ide/spyder/issues/21556))
* [PR 21392](https://github.com/spyder-ide/spyder/pull/21392) - PR: Add macOS-arm64 target platform using M1 runner (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21353](https://github.com/spyder-ide/spyder/pull/21353) - PR: Initial Editor migration to the new API, by [@dalthviz](https://github.com/dalthviz) ([12193](https://github.com/spyder-ide/spyder/issues/12193))

In this release 26 pull requests were closed.

----

## Version 6.0alpha4 (2024-02-08)

### Issues Closed

* [Issue 21675](https://github.com/spyder-ide/spyder/issues/21675) - Icons for "Remove plots" and "Remove all plots" inconsistent ([PR 21715](https://github.com/spyder-ide/spyder/pull/21715) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21640](https://github.com/spyder-ide/spyder/issues/21640) - Minor update to standalone, conda-based installation via conda breaks the application ([PR 21647](https://github.com/spyder-ide/spyder/pull/21647) by [@mrclary](https://github.com/mrclary))
* [Issue 21538](https://github.com/spyder-ide/spyder/issues/21538) - TypeError after clicking "Find in files" action ([PR 21622](https://github.com/spyder-ide/spyder/pull/21622) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21482](https://github.com/spyder-ide/spyder/issues/21482) - When closing a modified file, the text on the popup's buttons could be clarified ([PR 21631](https://github.com/spyder-ide/spyder/pull/21631) by [@mrclary](https://github.com/mrclary))
* [Issue 21046](https://github.com/spyder-ide/spyder/issues/21046) - Improve highlighting of current plot ([PR 21598](https://github.com/spyder-ide/spyder/pull/21598) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 20114](https://github.com/spyder-ide/spyder/issues/20114) - Runfile raising syntax error when a dictionary is passed as an argument
* [Issue 19672](https://github.com/spyder-ide/spyder/issues/19672) - Missing options to control inline plots look ([PR 21566](https://github.com/spyder-ide/spyder/pull/21566) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 15264](https://github.com/spyder-ide/spyder/issues/15264) - Move calltip to not crop code written in the console ([PR 21710](https://github.com/spyder-ide/spyder/pull/21710) by [@ccordoba12](https://github.com/ccordoba12))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 21774](https://github.com/spyder-ide/spyder/pull/21774) - PR: Update core dependencies for 6.0.0 alpha4, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21762](https://github.com/spyder-ide/spyder/pull/21762) - PR: Improve performance of workspace watcher (Projects), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21740](https://github.com/spyder-ide/spyder/pull/21740) - PR: Remove old `python-lsp-black` related code, by [@remisalmon](https://github.com/remisalmon)
* [PR 21734](https://github.com/spyder-ide/spyder/pull/21734) - PR: Create a base class for sidebar dialogs (Widgets), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21715](https://github.com/spyder-ide/spyder/pull/21715) - PR: Change icon for "Remove all plots", by [@jitseniesen](https://github.com/jitseniesen) ([21675](https://github.com/spyder-ide/spyder/issues/21675))
* [PR 21710](https://github.com/spyder-ide/spyder/pull/21710) - PR: Improve hovers, completion hints and calltips, by [@ccordoba12](https://github.com/ccordoba12) ([15264](https://github.com/spyder-ide/spyder/issues/15264))
* [PR 21707](https://github.com/spyder-ide/spyder/pull/21707) - PR: Fix several UI regressions and errors, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21685](https://github.com/spyder-ide/spyder/pull/21685) - PR: More fixes for Qt 6 compatibility and a PySide2 fix, by [@rear1019](https://github.com/rear1019)
* [PR 21669](https://github.com/spyder-ide/spyder/pull/21669) - PR: Fix folding and make some performance improvements (Editor), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21667](https://github.com/spyder-ide/spyder/pull/21667) - PR: Fix errors when displaying the Symbols switcher, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21657](https://github.com/spyder-ide/spyder/pull/21657) - PR: Add icons for project actions, by [@conradolandia](https://github.com/conradolandia)
* [PR 21647](https://github.com/spyder-ide/spyder/pull/21647) - PR: Update for new menuinst and friends and new Spyder feedstock (Installers), by [@mrclary](https://github.com/mrclary) ([21640](https://github.com/spyder-ide/spyder/issues/21640))
* [PR 21641](https://github.com/spyder-ide/spyder/pull/21641) - PR: Additional UI improvements to the `About Spyder` dialog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21631](https://github.com/spyder-ide/spyder/pull/21631) - PR: Update button text for editor changed files message box, by [@mrclary](https://github.com/mrclary) ([21482](https://github.com/spyder-ide/spyder/issues/21482))
* [PR 21622](https://github.com/spyder-ide/spyder/pull/21622) - PR: Make some UI/UX improvements to the Find pane, by [@ccordoba12](https://github.com/ccordoba12) ([21538](https://github.com/spyder-ide/spyder/issues/21538))
* [PR 21598](https://github.com/spyder-ide/spyder/pull/21598) - PR: Change style of border around thumbnail of current plot, by [@jitseniesen](https://github.com/jitseniesen) ([21046](https://github.com/spyder-ide/spyder/issues/21046))
* [PR 21566](https://github.com/spyder-ide/spyder/pull/21566) - PR: Add new options for font size and bottom edge for inline plot, by [@jitseniesen](https://github.com/jitseniesen) ([19672](https://github.com/spyder-ide/spyder/issues/19672))

In this release 17 pull requests were closed.

----

## Version 6.0alpha3 (2023-12-19)

### Issues Closed

* [Issue 21591](https://github.com/spyder-ide/spyder/issues/21591) - Spyder 6.0 alpha3 release ([PR 21628](https://github.com/spyder-ide/spyder/pull/21628) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21527](https://github.com/spyder-ide/spyder/issues/21527) - Generate docstring not working if there are comments on the function definition lines ([PR 21536](https://github.com/spyder-ide/spyder/pull/21536) by [@rhkarls](https://github.com/rhkarls))
* [Issue 21520](https://github.com/spyder-ide/spyder/issues/21520) - Error when opening Preferences ([PR 21530](https://github.com/spyder-ide/spyder/pull/21530) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21499](https://github.com/spyder-ide/spyder/issues/21499) - Wrong Sphinx version detection for jsmath ([PR 21518](https://github.com/spyder-ide/spyder/pull/21518) by [@Mte90](https://github.com/Mte90))
* [Issue 21404](https://github.com/spyder-ide/spyder/issues/21404) - Spyder 6.0.0a2 splash screen text says version 5 ([PR 21535](https://github.com/spyder-ide/spyder/pull/21535) by [@conradolandia](https://github.com/conradolandia))
* [Issue 21326](https://github.com/spyder-ide/spyder/issues/21326) - Menu bar entries are too close to each other ([PR 21511](https://github.com/spyder-ide/spyder/pull/21511) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21322](https://github.com/spyder-ide/spyder/issues/21322) - Tests seems to be passing but fail ([PR 21102](https://github.com/spyder-ide/spyder/pull/21102) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21315](https://github.com/spyder-ide/spyder/issues/21315) - Array editor should have a toolbar ([PR 21317](https://github.com/spyder-ide/spyder/pull/21317) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21302](https://github.com/spyder-ide/spyder/issues/21302) - Codesign hangs on macOS installer ([PR 21334](https://github.com/spyder-ide/spyder/pull/21334) by [@mrclary](https://github.com/mrclary))
* [Issue 20831](https://github.com/spyder-ide/spyder/issues/20831) - Migrate existing update mechanism to new conda-based installers ([PR 21483](https://github.com/spyder-ide/spyder/pull/21483) by [@mrclary](https://github.com/mrclary))
* [Issue 20791](https://github.com/spyder-ide/spyder/issues/20791) - Two Spyder icons on Windows taskbar
* [Issue 20129](https://github.com/spyder-ide/spyder/issues/20129) - Check that paths are added in the expected order and to expected position in `sys.path` by the Pythonpath manager ([PR 21574](https://github.com/spyder-ide/spyder/pull/21574) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 19182](https://github.com/spyder-ide/spyder/issues/19182) - Folders will disappear from the Pythonpath manager when they are deleted, but remain in `sys.path` ([PR 21574](https://github.com/spyder-ide/spyder/pull/21574) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15659](https://github.com/spyder-ide/spyder/issues/15659) - Shortcuts and icons not appearing in context menus of plugins on macOS ([PR 21511](https://github.com/spyder-ide/spyder/pull/21511) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15073](https://github.com/spyder-ide/spyder/issues/15073) - Switch order of entries in preferences ([PR 21233](https://github.com/spyder-ide/spyder/pull/21233) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 14326](https://github.com/spyder-ide/spyder/issues/14326) - Uncommenting adds an extra whitespace in some cases ([PR 14768](https://github.com/spyder-ide/spyder/pull/14768) by [@remisalmon](https://github.com/remisalmon))
* [Issue 6325](https://github.com/spyder-ide/spyder/issues/6325) - Add ability to refresh/update existing Variable Explorer windows to reflect current variable state ([PR 21312](https://github.com/spyder-ide/spyder/pull/21312) by [@jitseniesen](https://github.com/jitseniesen))

In this release 17 issues were closed.

### Pull Requests Merged

* [PR 21628](https://github.com/spyder-ide/spyder/pull/21628) - PR: Update core dependencies for 6.0.0.alpha3, by [@dalthviz](https://github.com/dalthviz) ([21591](https://github.com/spyder-ide/spyder/issues/21591))
* [PR 21616](https://github.com/spyder-ide/spyder/pull/21616) - PR: Start spinner in dependencies dialog only when it's visible and make some improvements to the dialog's UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21574](https://github.com/spyder-ide/spyder/pull/21574) - PR: Some improvements to the Pythonpath plugin, by [@ccordoba12](https://github.com/ccordoba12) ([20129](https://github.com/spyder-ide/spyder/issues/20129), [19182](https://github.com/spyder-ide/spyder/issues/19182))
* [PR 21573](https://github.com/spyder-ide/spyder/pull/21573) - PR: Increase minimal required version of PyQt to 5.15, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21572](https://github.com/spyder-ide/spyder/pull/21572) - PR: Initial fixes to make Spyder work with Qt 6, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21555](https://github.com/spyder-ide/spyder/pull/21555) - PR: Add new combobox widgets (API), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21540](https://github.com/spyder-ide/spyder/pull/21540) - PR: Remove double message on restart after kernel dies (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21536](https://github.com/spyder-ide/spyder/pull/21536) - PR: Remove comments from the function definition lines before generating docstrings, by [@rhkarls](https://github.com/rhkarls) ([21527](https://github.com/spyder-ide/spyder/issues/21527))
* [PR 21535](https://github.com/spyder-ide/spyder/pull/21535) - PR: Update Spyder splash screen text to read 'version 6', by [@conradolandia](https://github.com/conradolandia) ([21404](https://github.com/spyder-ide/spyder/issues/21404))
* [PR 21530](https://github.com/spyder-ide/spyder/pull/21530) - PR: Cast to `int` parameters used inside `ItemDelegate.sizeHint` return value (Widgets), by [@dalthviz](https://github.com/dalthviz) ([21520](https://github.com/spyder-ide/spyder/issues/21520))
* [PR 21524](https://github.com/spyder-ide/spyder/pull/21524) - PR: Fix syntax error over the completion plugin API (`SpyderCompletionProvider` class) (Completion), by [@dalthviz](https://github.com/dalthviz)
* [PR 21518](https://github.com/spyder-ide/spyder/pull/21518) - PR: Fix not displaying math equations in the Help pane, by [@Mte90](https://github.com/Mte90) ([21499](https://github.com/spyder-ide/spyder/issues/21499))
* [PR 21517](https://github.com/spyder-ide/spyder/pull/21517) - PR: Install QDarkstyle 3.2.0 on Linux pip slots (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21511](https://github.com/spyder-ide/spyder/pull/21511) - PR: Improve how menus are rendered and fix graphical errors related to them (UI), by [@ccordoba12](https://github.com/ccordoba12) ([21326](https://github.com/spyder-ide/spyder/issues/21326), [15659](https://github.com/spyder-ide/spyder/issues/15659))
* [PR 21510](https://github.com/spyder-ide/spyder/pull/21510) - PR: Fix deprecated top-level `developer_name` in AppData XML (Linux), by [@musicinmybrain](https://github.com/musicinmybrain)
* [PR 21483](https://github.com/spyder-ide/spyder/pull/21483) - PR: Create `UpdateManager` plugin to handle updates for the conda-based installers, by [@mrclary](https://github.com/mrclary) ([20831](https://github.com/spyder-ide/spyder/issues/20831))
* [PR 21451](https://github.com/spyder-ide/spyder/pull/21451) - PR: Fix interface language auto-configuration, by [@sthibaul](https://github.com/sthibaul)
* [PR 21391](https://github.com/spyder-ide/spyder/pull/21391) - PR: Temporarily use Apple Developer ID Application Certificate for signing Windows installer, by [@mrclary](https://github.com/mrclary)
* [PR 21352](https://github.com/spyder-ide/spyder/pull/21352) - PR: Add an empty message to the Debugger pane, by [@conradolandia](https://github.com/conradolandia)
* [PR 21343](https://github.com/spyder-ide/spyder/pull/21343) - PR: Fix Installer workflow on schedule and add badge to Readme, by [@mrclary](https://github.com/mrclary)
* [PR 21334](https://github.com/spyder-ide/spyder/pull/21334) - PR: Fix Codesigning for the Installers and Run Workflow on Schedule, by [@mrclary](https://github.com/mrclary) ([21302](https://github.com/spyder-ide/spyder/issues/21302))
* [PR 21333](https://github.com/spyder-ide/spyder/pull/21333) - PR: Fix syntax in `test_namespacebrowser.py` for Python 3.8 and 3.9, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 21323](https://github.com/spyder-ide/spyder/pull/21323) - PR: Fix some failing tests, by [@impact27](https://github.com/impact27)
* [PR 21320](https://github.com/spyder-ide/spyder/pull/21320) - PR: Group kernel config calls (IPython console), by [@impact27](https://github.com/impact27)
* [PR 21317](https://github.com/spyder-ide/spyder/pull/21317) - PR: Add toolbar to array editor (Variable Explorer), by [@jitseniesen](https://github.com/jitseniesen) ([21315](https://github.com/spyder-ide/spyder/issues/21315))
* [PR 21312](https://github.com/spyder-ide/spyder/pull/21312) - PR: Add Refresh button to editors from Variable Explorer, by [@jitseniesen](https://github.com/jitseniesen) ([6325](https://github.com/spyder-ide/spyder/issues/6325))
* [PR 21294](https://github.com/spyder-ide/spyder/pull/21294) - PR: Rename `External Console` plugin to `External Terminal`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21276](https://github.com/spyder-ide/spyder/pull/21276) - PR: More UI fixes in several places, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21271](https://github.com/spyder-ide/spyder/pull/21271) - PR: Create loading screen for the Dependencies widget, and added new icons for dependencies, debug, console-off and console-remote-off, by [@conradolandia](https://github.com/conradolandia)
* [PR 21249](https://github.com/spyder-ide/spyder/pull/21249) - PR: Remove Kite completion provider code, by [@jsbautista](https://github.com/jsbautista)
* [PR 21233](https://github.com/spyder-ide/spyder/pull/21233) - PR: Improve style of the Preferences dialog (UI), by [@ccordoba12](https://github.com/ccordoba12) ([15073](https://github.com/spyder-ide/spyder/issues/15073))
* [PR 21102](https://github.com/spyder-ide/spyder/pull/21102) - PR: Fix error when running main window tests and failing tests, by [@ccordoba12](https://github.com/ccordoba12) ([21322](https://github.com/spyder-ide/spyder/issues/21322))
* [PR 20546](https://github.com/spyder-ide/spyder/pull/20546) - PR: Add edition menu and toolbar to dataframe viewer, by [@dpturibio](https://github.com/dpturibio) ([76](https://github.com/spyder-ide/ux-improvements/issues/76))
* [PR 14768](https://github.com/spyder-ide/spyder/pull/14768) - PR: Fix commenting/uncommenting to not change leading whitespaces, by [@remisalmon](https://github.com/remisalmon) ([14326](https://github.com/spyder-ide/spyder/issues/14326))

In this release 34 pull requests were closed.

----

## Version 6.0alpha2 (2023-09-05)

### Issues Closed

* [Issue 21257](https://github.com/spyder-ide/spyder/issues/21257) - Spyder 6.0 alpha2 release ([PR 21298](https://github.com/spyder-ide/spyder/pull/21298) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21222](https://github.com/spyder-ide/spyder/issues/21222) - DataFrame Editor background coloring does not support `pandas.Int*Dtype` dtypes ([PR 21295](https://github.com/spyder-ide/spyder/pull/21295) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 21206](https://github.com/spyder-ide/spyder/issues/21206) - Config page for Shortcuts always shows shortcuts in black regardless of interface theme ([PR 21215](https://github.com/spyder-ide/spyder/pull/21215) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 21191](https://github.com/spyder-ide/spyder/issues/21191) - TypeError when hovering over value in dictionary editor ([PR 21193](https://github.com/spyder-ide/spyder/pull/21193) by [@dalthviz](https://github.com/dalthviz))
* [Issue 21173](https://github.com/spyder-ide/spyder/issues/21173) - Error with the Rich library in the Mac app
* [Issue 21157](https://github.com/spyder-ide/spyder/issues/21157) - Use caching for conda builds of subrepos in the installers-conda workflow ([PR 21182](https://github.com/spyder-ide/spyder/pull/21182) by [@mrclary](https://github.com/mrclary))
* [Issue 21149](https://github.com/spyder-ide/spyder/issues/21149) - Spyder 6.0a1 - Pandas error crashes console ([PR 21184](https://github.com/spyder-ide/spyder/pull/21184) by [@impact27](https://github.com/impact27))
* [Issue 21145](https://github.com/spyder-ide/spyder/issues/21145) - Plots from collection editor don't appear in Plots pane ([PR 21235](https://github.com/spyder-ide/spyder/pull/21235) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 20960](https://github.com/spyder-ide/spyder/issues/20960) - My font size in the variable explore is weird ([PR 20933](https://github.com/spyder-ide/spyder/pull/20933) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20940](https://github.com/spyder-ide/spyder/issues/20940) - Enhancements to Projects file switcher ([PR 21275](https://github.com/spyder-ide/spyder/pull/21275) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20715](https://github.com/spyder-ide/spyder/issues/20715) - Can not run IPython files in master ([PR 20762](https://github.com/spyder-ide/spyder/pull/20762) by [@impact27](https://github.com/impact27))
* [Issue 20701](https://github.com/spyder-ide/spyder/issues/20701) - Can not run renamed file in master ([PR 20762](https://github.com/spyder-ide/spyder/pull/20762) by [@impact27](https://github.com/impact27))
* [Issue 20571](https://github.com/spyder-ide/spyder/issues/20571) - Everything runs slowly after debugger is called ([PR 21107](https://github.com/spyder-ide/spyder/pull/21107) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 17464](https://github.com/spyder-ide/spyder/issues/17464) - It is not possible to disable external plugins ([PR 21101](https://github.com/spyder-ide/spyder/pull/21101) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 15254](https://github.com/spyder-ide/spyder/issues/15254) - Feature request: Pasting a file in the working directory doesn't work. ([PR 14092](https://github.com/spyder-ide/spyder/pull/14092) by [@impact27](https://github.com/impact27))
* [Issue 12851](https://github.com/spyder-ide/spyder/issues/12851) - Filenames are lowercased in debug mode ([PR 20493](https://github.com/spyder-ide/spyder/pull/20493) by [@impact27](https://github.com/impact27))
* [Issue 10968](https://github.com/spyder-ide/spyder/issues/10968) - Feature request: scroll line up/down using keyboard shortcut ([PR 10990](https://github.com/spyder-ide/spyder/pull/10990) by [@jnsebgosselin](https://github.com/jnsebgosselin))
* [Issue 10815](https://github.com/spyder-ide/spyder/issues/10815) - Add "Copy absolute/relative path" actions to the editor ([PR 21205](https://github.com/spyder-ide/spyder/pull/21205) by [@dalthviz](https://github.com/dalthviz))
* [Issue 5942](https://github.com/spyder-ide/spyder/issues/5942) - Is there any way to change the font for the entire application? ([PR 20933](https://github.com/spyder-ide/spyder/pull/20933) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 4120](https://github.com/spyder-ide/spyder/issues/4120) - Spyder cannot accept Chinese input ([PR 21260](https://github.com/spyder-ide/spyder/pull/21260) by [@dalthviz](https://github.com/dalthviz))
* [Issue 3860](https://github.com/spyder-ide/spyder/issues/3860) - File Switcher should search all project files and not only the open ones ([PR 20895](https://github.com/spyder-ide/spyder/pull/20895) by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez))

In this release 21 issues were closed.

### Pull Requests Merged

* [PR 21306](https://github.com/spyder-ide/spyder/pull/21306) - PR: Update `RELEASE.md` instructions and bump `spyder-kernels` version used in the IPython Console validations, by [@dalthviz](https://github.com/dalthviz)
* [PR 21305](https://github.com/spyder-ide/spyder/pull/21305) - PR: Do not sign or notarize macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 21300](https://github.com/spyder-ide/spyder/pull/21300) - PR: Remove installers workflow step validation for spyder conda package build to be done only on PRs (CI), by [@dalthviz](https://github.com/dalthviz)
* [PR 21298](https://github.com/spyder-ide/spyder/pull/21298) - PR: Update core dependencies for 6.0.0.alpha2, by [@dalthviz](https://github.com/dalthviz) ([21257](https://github.com/spyder-ide/spyder/issues/21257))
* [PR 21295](https://github.com/spyder-ide/spyder/pull/21295) - PR: Support all real number dtypes in dataframe editor, by [@jitseniesen](https://github.com/jitseniesen) ([21222](https://github.com/spyder-ide/spyder/issues/21222))
* [PR 21275](https://github.com/spyder-ide/spyder/pull/21275) - PR: Compute Projects switcher results in a worker to avoid freezes, by [@ccordoba12](https://github.com/ccordoba12) ([20940](https://github.com/spyder-ide/spyder/issues/20940))
* [PR 21262](https://github.com/spyder-ide/spyder/pull/21262) - PR: Handle decode errors in threads used for standard streams (IPython console), by [@impact27](https://github.com/impact27)
* [PR 21260](https://github.com/spyder-ide/spyder/pull/21260) - PR: Add `fzf` and `fcitx-qt5` as conda requirements, by [@dalthviz](https://github.com/dalthviz) ([4120](https://github.com/spyder-ide/spyder/issues/4120))
* [PR 21236](https://github.com/spyder-ide/spyder/pull/21236) - PR: Fix error after changes to Plugins page (Preferences), by [@rear1019](https://github.com/rear1019)
* [PR 21235](https://github.com/spyder-ide/spyder/pull/21235) - PR: Display plots from collections editor in the Plots pane, by [@jitseniesen](https://github.com/jitseniesen) ([21145](https://github.com/spyder-ide/spyder/issues/21145))
* [PR 21226](https://github.com/spyder-ide/spyder/pull/21226) - PR: Fixes to improve compatibility with PySide2, by [@rear1019](https://github.com/rear1019)
* [PR 21224](https://github.com/spyder-ide/spyder/pull/21224) - PR: Fix `TypeError` in breakpoints table (Debugger), by [@rear1019](https://github.com/rear1019)
* [PR 21215](https://github.com/spyder-ide/spyder/pull/21215) - PR: Fix showing text in the dark theme for keyboard sequences in the Shortcurts page (Preferences), by [@ccordoba12](https://github.com/ccordoba12) ([21206](https://github.com/spyder-ide/spyder/issues/21206))
* [PR 21213](https://github.com/spyder-ide/spyder/pull/21213) - PR: Update installer workflow to only restore cache of subrepo builds (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21212](https://github.com/spyder-ide/spyder/pull/21212) - PR: Build subrepo caches on master (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21210](https://github.com/spyder-ide/spyder/pull/21210) - PR: Move Editor API inside the plugin (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 21205](https://github.com/spyder-ide/spyder/pull/21205) - PR: Add copy absolute and relative paths to file context menu (Editor), by [@dalthviz](https://github.com/dalthviz) ([10815](https://github.com/spyder-ide/spyder/issues/10815))
* [PR 21194](https://github.com/spyder-ide/spyder/pull/21194) - PR: Move classes in `editor.py` to their own modules (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 21193](https://github.com/spyder-ide/spyder/pull/21193) - PR: Fix `ReadOnlyCollectionsModel` tooltip logic (Widgets/Variable Explorer), by [@dalthviz](https://github.com/dalthviz) ([21191](https://github.com/spyder-ide/spyder/issues/21191))
* [PR 21185](https://github.com/spyder-ide/spyder/pull/21185) - PR: Fix config page radiobutton reference (Main interpreter), by [@dalthviz](https://github.com/dalthviz)
* [PR 21184](https://github.com/spyder-ide/spyder/pull/21184) - PR: Remove locals inspection from the kernel (IPython console), by [@impact27](https://github.com/impact27) ([21149](https://github.com/spyder-ide/spyder/issues/21149))
* [PR 21182](https://github.com/spyder-ide/spyder/pull/21182) - PR: Cache subrepo conda builds for installers, by [@mrclary](https://github.com/mrclary) ([21157](https://github.com/spyder-ide/spyder/issues/21157))
* [PR 21156](https://github.com/spyder-ide/spyder/pull/21156) - PR: Some fixes for the report error dialog (UI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21134](https://github.com/spyder-ide/spyder/pull/21134) - PR: Improve UI of `PaneEmptyWidget`, show message on panes connected to dead consoles and improve About dialog UI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21133](https://github.com/spyder-ide/spyder/pull/21133) - PR: Improve style of dockwidget tabbars (UI), by [@ccordoba12](https://github.com/ccordoba12) ([4](https://github.com/spyder-ide/ux-improvements/issues/4))
* [PR 21132](https://github.com/spyder-ide/spyder/pull/21132) - PR: Don't write to shell history file when getting user environment variables, by [@mrclary](https://github.com/mrclary)
* [PR 21131](https://github.com/spyder-ide/spyder/pull/21131) - PR: Reinstate notarization of conda-based macOS installer, by [@mrclary](https://github.com/mrclary)
* [PR 21125](https://github.com/spyder-ide/spyder/pull/21125) - PR: Update to `napari/label/bundle_tools_3` (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21107](https://github.com/spyder-ide/spyder/pull/21107) - PR: Add `exitdb` command and some speed optimizations to the debugger, by [@ccordoba12](https://github.com/ccordoba12) ([20571](https://github.com/spyder-ide/spyder/issues/20571))
* [PR 21101](https://github.com/spyder-ide/spyder/pull/21101) - PR: Improve UI of Plugins page in Preferences, by [@ccordoba12](https://github.com/ccordoba12) ([17464](https://github.com/spyder-ide/spyder/issues/17464))
* [PR 21092](https://github.com/spyder-ide/spyder/pull/21092) - PR: Remove setting font for update status bar widget (Application), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21084](https://github.com/spyder-ide/spyder/pull/21084) - PR: Automatically launch Spyder after installation (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21083](https://github.com/spyder-ide/spyder/pull/21083) - PR: Fix issue where bootstrap incorrectly determines git branch, by [@mrclary](https://github.com/mrclary)
* [PR 21075](https://github.com/spyder-ide/spyder/pull/21075) - PR: Update installers to use Python 3.10, by [@mrclary](https://github.com/mrclary)
* [PR 21065](https://github.com/spyder-ide/spyder/pull/21065) - PR: Fix issue getting user environment variables on Posix systems and pass them to the IPython console, by [@mrclary](https://github.com/mrclary)
* [PR 21062](https://github.com/spyder-ide/spyder/pull/21062) - PR: Fix issue where cmd.exe window flashes on Spyder startup on Windows (installer), by [@mrclary](https://github.com/mrclary)
* [PR 21057](https://github.com/spyder-ide/spyder/pull/21057) - PR: Remove Spyder 5 changelog from tarball, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21053](https://github.com/spyder-ide/spyder/pull/21053) - PR: Fix issues for all-user install in post-install script (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21050](https://github.com/spyder-ide/spyder/pull/21050) - PR: Small fixes to release files after 6.0a1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20997](https://github.com/spyder-ide/spyder/pull/20997) - PR: Remove Spyder 2 icon set because it's incomplete, by [@jsbautista](https://github.com/jsbautista) ([43](https://github.com/spyder-ide/ux-improvements/issues/43))
* [PR 20933](https://github.com/spyder-ide/spyder/pull/20933) - PR: Make the font used by the application configurable and other UI fixes, by [@ccordoba12](https://github.com/ccordoba12) ([5942](https://github.com/spyder-ide/spyder/issues/5942), [20960](https://github.com/spyder-ide/spyder/issues/20960))
* [PR 20926](https://github.com/spyder-ide/spyder/pull/20926) - PR: Add help info widget to show tooltips in Preferences (UX/UI), by [@jsbautista](https://github.com/jsbautista)
* [PR 20895](https://github.com/spyder-ide/spyder/pull/20895) - PR: Add switcher integration to projects, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez) ([3860](https://github.com/spyder-ide/spyder/issues/3860))
* [PR 20868](https://github.com/spyder-ide/spyder/pull/20868) - PR: Improve Variable Explorer UX, by [@jsbautista](https://github.com/jsbautista) ([17](https://github.com/spyder-ide/ux-improvements/issues/17))
* [PR 20767](https://github.com/spyder-ide/spyder/pull/20767) - PR: Add clarifying message to several empty panes, by [@jsbautista](https://github.com/jsbautista) ([11](https://github.com/spyder-ide/ux-improvements/issues/11))
* [PR 20762](https://github.com/spyder-ide/spyder/pull/20762) - PR: Enable running renamed and IPython files again, by [@impact27](https://github.com/impact27) ([20715](https://github.com/spyder-ide/spyder/issues/20715), [20701](https://github.com/spyder-ide/spyder/issues/20701))
* [PR 20493](https://github.com/spyder-ide/spyder/pull/20493) - PR: Fix capitalization on Windows when opening a file in debug mode, by [@impact27](https://github.com/impact27) ([12851](https://github.com/spyder-ide/spyder/issues/12851))
* [PR 19492](https://github.com/spyder-ide/spyder/pull/19492) - PR: Merge Breakpoints and Debugger plugins, by [@impact27](https://github.com/impact27)
* [PR 19350](https://github.com/spyder-ide/spyder/pull/19350) - PR: Improve debugging for IPython kernels, by [@impact27](https://github.com/impact27)
* [PR 14092](https://github.com/spyder-ide/spyder/pull/14092) - PR: Open file pasted into working directory toolbar, by [@impact27](https://github.com/impact27) ([15254](https://github.com/spyder-ide/spyder/issues/15254))
* [PR 10990](https://github.com/spyder-ide/spyder/pull/10990) - PR: Add scroll line up/down keyboard shortcuts (Editor), by [@jnsebgosselin](https://github.com/jnsebgosselin) ([10968](https://github.com/spyder-ide/spyder/issues/10968))

In this release 51 pull requests were closed.

----

## Version 6.0alpha1 (2023-06-19)

### Issues Closed

* [Issue 20885](https://github.com/spyder-ide/spyder/issues/20885) - Error when opening files due to a corrupted config file ([PR 20886](https://github.com/spyder-ide/spyder/pull/20886) by [@dalthviz](https://github.com/dalthviz))
* [Issue 20776](https://github.com/spyder-ide/spyder/issues/20776) - Loading of old third-party plugins in Spyder 6 ([PR 20789](https://github.com/spyder-ide/spyder/pull/20789) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 20630](https://github.com/spyder-ide/spyder/issues/20630) - Proposition: Turn runfile / runcell to IPython magics ([PR 20633](https://github.com/spyder-ide/spyder/pull/20633) by [@impact27](https://github.com/impact27))
* [Issue 20572](https://github.com/spyder-ide/spyder/issues/20572) - Graphical way to pause at current point and drop to debugger ([PR 18514](https://github.com/spyder-ide/spyder/pull/18514) by [@impact27](https://github.com/impact27))
* [Issue 20561](https://github.com/spyder-ide/spyder/issues/20561) - Spyder crashes at shutdown ([PR 20562](https://github.com/spyder-ide/spyder/pull/20562) by [@impact27](https://github.com/impact27))
* [Issue 20536](https://github.com/spyder-ide/spyder/issues/20536) - Attach sha256sum for installers ([PR 20587](https://github.com/spyder-ide/spyder/pull/20587) by [@mrclary](https://github.com/mrclary))
* [Issue 20474](https://github.com/spyder-ide/spyder/issues/20474) - Generating new plots always overrides currently selected plot ([PR 20475](https://github.com/spyder-ide/spyder/pull/20475) by [@impact27](https://github.com/impact27))
* [Issue 20403](https://github.com/spyder-ide/spyder/issues/20403) - Find and replace "Replace all occurences" ignores "Only search for whole words" ([PR 20497](https://github.com/spyder-ide/spyder/pull/20497) by [@mrclary](https://github.com/mrclary))
* [Issue 19920](https://github.com/spyder-ide/spyder/issues/19920) - Debug toolbar is enabled for non-Python files (e.g.:  .trp)
* [Issue 19502](https://github.com/spyder-ide/spyder/issues/19502) - Update Python version on Windows installer to 3.10 to not flag `match` as an error
* [Issue 18855](https://github.com/spyder-ide/spyder/issues/18855) - `test_leaks` is failing on master ([PR 18857](https://github.com/spyder-ide/spyder/pull/18857) by [@impact27](https://github.com/impact27))
* [Issue 17888](https://github.com/spyder-ide/spyder/issues/17888) - Add Debug line functionality to Debug menu and toolbar ([PR 19306](https://github.com/spyder-ide/spyder/pull/19306) by [@impact27](https://github.com/impact27))
* [Issue 16662](https://github.com/spyder-ide/spyder/issues/16662) - Add a way to test the Windows installer ([PR 20601](https://github.com/spyder-ide/spyder/pull/20601) by [@mrclary](https://github.com/mrclary))
* [Issue 16013](https://github.com/spyder-ide/spyder/issues/16013) - Feature request: Expose pdb "u" and "d" commands to user ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 14894](https://github.com/spyder-ide/spyder/issues/14894) - Variable explorer doesn't show variables on remote kernel when using localhost forwarded ports ([PR 16890](https://github.com/spyder-ide/spyder/pull/16890) by [@impact27](https://github.com/impact27))
* [Issue 14518](https://github.com/spyder-ide/spyder/issues/14518) - How to view numbers in a dataframe with thousands separator in spyder variable explorer? ([PR 20473](https://github.com/spyder-ide/spyder/pull/20473) by [@jitseniesen](https://github.com/jitseniesen))
* [Issue 13336](https://github.com/spyder-ide/spyder/issues/13336) - Kernel not restarting sometimes ([PR 19411](https://github.com/spyder-ide/spyder/pull/19411) by [@impact27](https://github.com/impact27))
* [Issue 11177](https://github.com/spyder-ide/spyder/issues/11177) - Visualize what line of code the editor is running  ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 5205](https://github.com/spyder-ide/spyder/issues/5205) - Improvement: add a shortcut to enter the debugger after an error occurs ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))
* [Issue 1613](https://github.com/spyder-ide/spyder/issues/1613) - Visual debug call stack window - enhacement request ([PR 11186](https://github.com/spyder-ide/spyder/pull/11186) by [@impact27](https://github.com/impact27))

In this release 20 issues were closed.

### Pull Requests Merged

* [PR 21041](https://github.com/spyder-ide/spyder/pull/21041) - PR: Skip notarization of our Mac app (Installers), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 21036](https://github.com/spyder-ide/spyder/pull/21036) - PR: Add `spyder_kernels_rc` conda-forge label (Installers), by [@mrclary](https://github.com/mrclary)
* [PR 21030](https://github.com/spyder-ide/spyder/pull/21030) - PR: Update core dependencies for 6.0 alpha1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20972](https://github.com/spyder-ide/spyder/pull/20972) - PR: Add new icons for replace next, all and selection buttons, by [@conradolandia](https://github.com/conradolandia)
* [PR 20965](https://github.com/spyder-ide/spyder/pull/20965) - PR: Fix typo in Announcements.md, by [@habibmy](https://github.com/habibmy)
* [PR 20952](https://github.com/spyder-ide/spyder/pull/20952) - PR: Add support for the future `python-lsp-black` 2.0 version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20905](https://github.com/spyder-ide/spyder/pull/20905) - PR: Fix typo in kernel error message (IPython console), by [@jitseniesen](https://github.com/jitseniesen)
* [PR 20893](https://github.com/spyder-ide/spyder/pull/20893) - PR: Move LSP related code from the `CodeEditor` class definition to a new mixin and `CodeEditor` related elements to a `codeeditor` module (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20886](https://github.com/spyder-ide/spyder/pull/20886) - PR: Prevent saving `None` value as Editor bookmarks, by [@dalthviz](https://github.com/dalthviz) ([20885](https://github.com/spyder-ide/spyder/issues/20885))
* [PR 20884](https://github.com/spyder-ide/spyder/pull/20884) - PR: Cleanup Environments for Conda-based Installers, by [@mrclary](https://github.com/mrclary)
* [PR 20874](https://github.com/spyder-ide/spyder/pull/20874) - PR: Improve versions of debug icons, add new cell icon and optimize svg icons, by [@conradolandia](https://github.com/conradolandia)
* [PR 20837](https://github.com/spyder-ide/spyder/pull/20837) - PR: Define Switcher Plugin public API + fix switcher position bug, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez)
* [PR 20833](https://github.com/spyder-ide/spyder/pull/20833) - PR: Skip a test that started to fail on Linux and Mac, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20827](https://github.com/spyder-ide/spyder/pull/20827) - PR: Change logic to detect conda-based installers and micromamba on them, by [@mrclary](https://github.com/mrclary)
* [PR 20825](https://github.com/spyder-ide/spyder/pull/20825) - PR: Move CONF usage for bookmarks logic and use `SpyderConfiguratorAccessor` class in Editor widgets (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20824](https://github.com/spyder-ide/spyder/pull/20824) - PR: Declare a clear API for Projects and move implementation code to its main widget, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20810](https://github.com/spyder-ide/spyder/pull/20810) - PR: Remove some unused methods from MainWindow and fix Code Analysis and Profiler actions in menus position, by [@dalthviz](https://github.com/dalthviz)
* [PR 20789](https://github.com/spyder-ide/spyder/pull/20789) - PR: Remove code that tried to load old third-party plugins and move IO plugins to Spyder-kernels, by [@ccordoba12](https://github.com/ccordoba12) ([20776](https://github.com/spyder-ide/spyder/issues/20776))
* [PR 20773](https://github.com/spyder-ide/spyder/pull/20773) - PR: Fix `test_collectionseditor` after merge (Widgets), by [@dalthviz](https://github.com/dalthviz)
* [PR 20733](https://github.com/spyder-ide/spyder/pull/20733) - PR: Fix `test_clickable_ipython_tracebacks`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20726](https://github.com/spyder-ide/spyder/pull/20726) - PR: Improve and refactor the way we run and debug code in the IPython console, by [@impact27](https://github.com/impact27)
* [PR 20714](https://github.com/spyder-ide/spyder/pull/20714) - PR: Make the switcher a plugin, by [@angelasofiaremolinagutierrez](https://github.com/angelasofiaremolinagutierrez)
* [PR 20689](https://github.com/spyder-ide/spyder/pull/20689) - PR: Fix `Source` menu order (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20653](https://github.com/spyder-ide/spyder/pull/20653) - PR: Fix debugger tests with the latest version of IPykernel, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20633](https://github.com/spyder-ide/spyder/pull/20633) - PR: Create magics for run|debug file|cell (IPython console), by [@impact27](https://github.com/impact27) ([20630](https://github.com/spyder-ide/spyder/issues/20630))
* [PR 20620](https://github.com/spyder-ide/spyder/pull/20620) - PR: Initial code changes for old menu actions to use the `Mainmenu` plugin (Editor), by [@dalthviz](https://github.com/dalthviz)
* [PR 20601](https://github.com/spyder-ide/spyder/pull/20601) - PR: Add installer tests for Linux and Windows, by [@mrclary](https://github.com/mrclary) ([16662](https://github.com/spyder-ide/spyder/issues/16662))
* [PR 20587](https://github.com/spyder-ide/spyder/pull/20587) - PR: Add sha256sum to release assets, by [@mrclary](https://github.com/mrclary) ([20536](https://github.com/spyder-ide/spyder/issues/20536))
* [PR 20575](https://github.com/spyder-ide/spyder/pull/20575) - PR: Fix conda script selection for custom interpreter env activation on Windows, by [@dalthviz](https://github.com/dalthviz)
* [PR 20574](https://github.com/spyder-ide/spyder/pull/20574) - PR: Remove API method that's no longer necessary (Run), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20568](https://github.com/spyder-ide/spyder/pull/20568) - PR: Add public API method to set custom interpreter (Main interpreter), by [@dalthviz](https://github.com/dalthviz)
* [PR 20562](https://github.com/spyder-ide/spyder/pull/20562) - PR: Wait on all shutdown threads (IPython console), by [@impact27](https://github.com/impact27) ([20561](https://github.com/spyder-ide/spyder/issues/20561))
* [PR 20557](https://github.com/spyder-ide/spyder/pull/20557) - PR: Transition Debugger plugin actions to the new Run architecture and cleanup Editor plugin, by [@impact27](https://github.com/impact27)
* [PR 20548](https://github.com/spyder-ide/spyder/pull/20548) - PR: Fix test_shell_execution for macOS, by [@mrclary](https://github.com/mrclary)
* [PR 20509](https://github.com/spyder-ide/spyder/pull/20509) - PR: Improve cells support in the Editor, by [@jsbautista](https://github.com/jsbautista)
* [PR 20497](https://github.com/spyder-ide/spyder/pull/20497) - PR: Fix issue where replace all did not respect whole words filter, by [@mrclary](https://github.com/mrclary) ([20403](https://github.com/spyder-ide/spyder/issues/20403))
* [PR 20475](https://github.com/spyder-ide/spyder/pull/20475) - PR: Stop automatic scrolling when a plot is selected (Plots), by [@impact27](https://github.com/impact27) ([20474](https://github.com/spyder-ide/spyder/issues/20474))
* [PR 20473](https://github.com/spyder-ide/spyder/pull/20473) - PR: Use .format() to format floats in array and dataframe editors, by [@jitseniesen](https://github.com/jitseniesen) ([14518](https://github.com/spyder-ide/spyder/issues/14518))
* [PR 20471](https://github.com/spyder-ide/spyder/pull/20471) - PR: Update conda-based installers, by [@mrclary](https://github.com/mrclary)
* [PR 20460](https://github.com/spyder-ide/spyder/pull/20460) - PR: Fix failure installing Spyder-kernels from master on Windows and other minor fixes on CIS, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20449](https://github.com/spyder-ide/spyder/pull/20449) - PR: Replace mamba command with micromamba in CI install script (Testing), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20421](https://github.com/spyder-ide/spyder/pull/20421) - PR: Add menu to use specific environment interpreter for a new console instance, by [@jsbautista](https://github.com/jsbautista)
* [PR 20411](https://github.com/spyder-ide/spyder/pull/20411) - PR: Pin PyZMQ to version 24 to prevent hangs in our CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20368](https://github.com/spyder-ide/spyder/pull/20368) - PR: Remove original installers in favor of conda-based ones, by [@mrclary](https://github.com/mrclary)
* [PR 20306](https://github.com/spyder-ide/spyder/pull/20306) - PR: Skip a test that started to fail on Windows, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 20238](https://github.com/spyder-ide/spyder/pull/20238) - PR: Fix a small kernel restart issue (IPython console), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19842](https://github.com/spyder-ide/spyder/pull/19842) - PR: Update Variable Explorer from the kernel, by [@impact27](https://github.com/impact27)
* [PR 19411](https://github.com/spyder-ide/spyder/pull/19411) - PR: Use pipes for stdout and stderr and improve comm connection (IPython console), by [@impact27](https://github.com/impact27) ([13336](https://github.com/spyder-ide/spyder/issues/13336))
* [PR 19343](https://github.com/spyder-ide/spyder/pull/19343) - PR: Use new API to handle creation and removal of debug toolbar and menu, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 19306](https://github.com/spyder-ide/spyder/pull/19306) - PR: Add a debug current line or selection button, by [@impact27](https://github.com/impact27) ([17888](https://github.com/spyder-ide/spyder/issues/17888))
* [PR 19305](https://github.com/spyder-ide/spyder/pull/19305) - PR: Add button to debugger plugin to go to editor, by [@impact27](https://github.com/impact27)
* [PR 19265](https://github.com/spyder-ide/spyder/pull/19265) - PR: Move debug functions from IPython plugin to debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19208](https://github.com/spyder-ide/spyder/pull/19208) - PR: Move breakpoints logic from editor plugin to debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19181](https://github.com/spyder-ide/spyder/pull/19181) - PR: Move debug cell / file / config to Debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 19092](https://github.com/spyder-ide/spyder/pull/19092) - PR: Use cached kernel for faster kernel restart (IPython console), by [@impact27](https://github.com/impact27)
* [PR 19074](https://github.com/spyder-ide/spyder/pull/19074) - PR: Improve validation for the right Spyder-kernels version, by [@impact27](https://github.com/impact27)
* [PR 19062](https://github.com/spyder-ide/spyder/pull/19062) - PR: Refactor the way clients are created (IPython console), by [@impact27](https://github.com/impact27)
* [PR 19005](https://github.com/spyder-ide/spyder/pull/19005) - PR: Unmaximize debugger plugin when clicking on debug toolbar buttons, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 18877](https://github.com/spyder-ide/spyder/pull/18877) - PR: Add debug cell icon to the debug toolbar, by [@stevetracvc](https://github.com/stevetracvc)
* [PR 18864](https://github.com/spyder-ide/spyder/pull/18864) - PR: Fix `test_leaks` on master, by [@impact27](https://github.com/impact27)
* [PR 18857](https://github.com/spyder-ide/spyder/pull/18857) - PR: Close memory leak in master, by [@impact27](https://github.com/impact27) ([18855](https://github.com/spyder-ide/spyder/issues/18855))
* [PR 18853](https://github.com/spyder-ide/spyder/pull/18853) - PR: Move debug buttons to the Debugger plugin, by [@impact27](https://github.com/impact27)
* [PR 18852](https://github.com/spyder-ide/spyder/pull/18852) - PR: Rename FramesExplorer plugin to Debugger, by [@impact27](https://github.com/impact27)
* [PR 18837](https://github.com/spyder-ide/spyder/pull/18837) - PR: Make the debugger work faster, by [@impact27](https://github.com/impact27)
* [PR 18514](https://github.com/spyder-ide/spyder/pull/18514) - PR: Add ability to interrupt the current execution and enter the debugger after that, by [@impact27](https://github.com/impact27) ([20572](https://github.com/spyder-ide/spyder/issues/20572))
* [PR 18476](https://github.com/spyder-ide/spyder/pull/18476) - PR: Do not reset the frames explorer while debugging, by [@impact27](https://github.com/impact27)
* [PR 18463](https://github.com/spyder-ide/spyder/pull/18463) - PR: Refactor to separate ShellWidget from VariableExplorerWidget and FigureBrowser, by [@impact27](https://github.com/impact27)
* [PR 17656](https://github.com/spyder-ide/spyder/pull/17656) - PR: Ignore `REVIEW.md` from `check-manifest` and fix `setup.py` patch for Windows installers on PRs, by [@dalthviz](https://github.com/dalthviz)
* [PR 17467](https://github.com/spyder-ide/spyder/pull/17467) - PR: Generalize Run plugin to support generic inputs and executors, by [@andfoy](https://github.com/andfoy)
* [PR 17335](https://github.com/spyder-ide/spyder/pull/17335) - PR: Skip Spyder-kernels check for now (Dependencies), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 16890](https://github.com/spyder-ide/spyder/pull/16890) - PR: Use control channel for comms, by [@impact27](https://github.com/impact27) ([14894](https://github.com/spyder-ide/spyder/issues/14894))
* [PR 16789](https://github.com/spyder-ide/spyder/pull/16789) - PR: Create Reviewer Guidelines, by [@isabela-pf](https://github.com/isabela-pf)
* [PR 16661](https://github.com/spyder-ide/spyder/pull/16661) - PR: Add a finder widget to reuse a similar widget used in the Variable Explorer, by [@impact27](https://github.com/impact27)
* [PR 14199](https://github.com/spyder-ide/spyder/pull/14199) - PR: Show Matplotlib backend state in status bar, by [@impact27](https://github.com/impact27)
* [PR 11186](https://github.com/spyder-ide/spyder/pull/11186) - PR: Add a new plugin to explore frames while debugging, by [@impact27](https://github.com/impact27) ([5205](https://github.com/spyder-ide/spyder/issues/5205), [1613](https://github.com/spyder-ide/spyder/issues/1613), [16013](https://github.com/spyder-ide/spyder/issues/16013), [11177](https://github.com/spyder-ide/spyder/issues/11177))

In this release 75 pull requests were closed.
