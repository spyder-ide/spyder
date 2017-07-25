# Minor release to list

**Subject**: [ANN] Spyder 3.2.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **3.2.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release comes three months after version 3.1.4 and comes with major
enhancements and new features. The most important ones are:

* **Main Window**
    * Add a dialog to quickly view all keyboard shortcuts defined in Spyder.
      It can be accessed in the `Help > Shortcuts Summary` menu or using
      the `Meta+F1` shortcut.
    * Add an option to set a custom screen resolution scale factor. This option
      is available in `Preferences > Appearance > Screen resolution`.

* **Editor**
    * Add the ability to reorganize tabs by drag and drop.
    * Add option to only replace in a selection.
    * Add `Ctrl+Up` and `Ctrl+Down` shortcuts to move to the next/previous
      cell, respectively.
    * Add `Alt+Enter` shortcut to re-run the last cell.
    * Add support to run Cython files from the Editor (i.e. by simply
      pressing `F5`).
    * Add syntax highlighting support for Markdown files.
    * Add a tab switcher dialog to navigate files in most recently used
      order. This dialog is activated with `Ctrl+Tab` and
      `Ctrl+Shift+Tab` to go in forward or backward order, respectively.
    * Make `Shift+Enter` search text backwards in the find/replace
      widget.
    * Add `Shift+Del` shortcut to delete lines.
    * Add `Ctrl+]` and `Ctrl+[` shortcuts to indent/unindent text,
      respectively.
    * Add a *Save copy as* action.
    * Add a context menu entry to show the selected file in the operating
      system file explorer.

* **IPython Console**
    * Several improvements to its debugger:
        - Restore the ability to inspect variables using the Variable
          Explorer.
        - Make plotting work with a new `%plot` magic, but only using
          the `inline` backend (e.g. `%plot plt.plot(range(10))`).
        - Add history browsing with the Up and Down arrow keys.
        - Make the *Clear console* and *Reset* keyboard shortcuts to work.
        - Show plots from the Variable Explorer.
        - Change the current working directory using the Working Directory toolbar.
        - Use `Ctrl+Shift+C` to copy text.
    * Add the possibility to run a file in the same (dedicated) console all the
      time.
    * Allow to rename consoles by doing a double-click on their tabs and setting
      a new name.
    * Make drag and drop of its tabs to work.
    * Add menu entries to show environment variables and `sys.path` contents for
      each console.

* **Find in Files**
    * Add options to search on the current file, project or working directory.
    * Allow to order results alphabetically.
    * Remove previous search results when a new search takes place.
    * Remove unused search options.

* **Working Directory toolbar**
    * Rename it to *Current working directory* (it was Global working
      directory).
    * Simplify its options to make them more understandable.
    * Make it show the working directory of the active IPython console and
      the current directory in the File Explorer.

In this release we also fixed 98 issues and merged 111 pull requests that amount
to more than 750 commits. For a full list of fixes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/3.x/CHANGELOG.md)

Don't forget to follow Spyder updates/news on the project
[Github website](https://github.com/spyder-ide/spyder)

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development and computing environment. Join us to help
creating your favorite environment!

Enjoy!<br>
- Carlos


----


# Major release to list

**Subject**: [ANN] Spyder 3.0 is released!


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce that Spyder **3.0** has been released and is available for
Windows, GNU/Linux and MacOS X: https://github.com/spyder-ide/spyder/releases

This release represents more than two years of development since version 2.3.0 was
released, and it introduces major enhancements and new features. The most important ones
are:

* Third-party plugins: External developers can now create plugins that extend Spyder in
  novel and interesting ways. For example, we already have plugins for the line-profiler
  and memory-profiler projects, and also a graphical frontend for the conda package
  manager. These plugins can be distributed as pip and/or conda packages for authors
  convenience.
* Improved projects support: Projects have been revamped and improved significantly in
  Spyder 3.0. With our new projects support, people will have the possibility of easily
  working on different coding efforts at the same time. That's because projects save the
  state of open files in the Editor and allow Python packages created as part of the
  project to be imported in our consoles.
* Support for much more programming languages: Spyder relies now on the excellent Pygments
  library to provide syntax highlight and suggest code completions in the Editor, for all
  programming languages supported by it.
* A new file switcher: Spyder 3.0 comes with a fancy file switcher, very similar in
  spirit to the one present in Sublime Text. This is a dialog to select among the open
  files in the Editor, by doing a fuzzy search through their names. It also lets users to
  view the list of classes, methods and functions defined in the current file, and select
  one of them. This dialog is activated with `Ctrl+P`.
* A Numpy array graphical builder: Users who need to create NumPy arrays in Spyder for
  matrices and vectors can do it now in a graphical way by pressing `Ctrl+M` in the Editor
  or the Consoles. This will open an empty 2D table widget to be filled with the data
  required by the user.
* A new icon theme based on FontAwesome.
* A new set of default pane layouts for those coming from Rstudio or Matlab (under
  `View > Window layouts`).
* A simpler and more intuitive way to introduce keyboard shortcuts.
* Support for PyQt5, which fixes problems in MacOS X and in high definition screens.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/blob/3.x/CHANGELOG.md)

Spyder 2.3 has been a huge success (being downloaded almost 550,000 times!) and
we hope 3.0 will be as successful as it. For that we fixed 203 important bugs,
merged 218 pull requests from about 40 authors and added almost 2850 commits
between these two releases.

Don't forget to follow Spyder updates/news on the project Github website:
https://github.com/spyder-ide/spyder

Last, but not least, we welcome any contribution that helps making Spyder an
efficient scientific development/computing environment. Join us to help creating
your favorite environment!

Enjoy!<br>
-Carlos


----


# Major release to others

**Note**: Leave this free of Markdown because it could go to mailing lists that
don't support hmtl.

**Subject**: [ANN] Spyder 3.0 is released!


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


# Beta release

**Subject**: [ANN] Spyder 3.0 seventh public beta release


Hi all,

On the behalf of the [Spyder Project Contributors](https://github.com/spyder-ide/spyder/graphs/contributors),
I'm pleased to announce the seventh beta of our next major version: Spyder **3.0**.

We've been working on this version for more than two years now and as far as we know
it's working very well. There are still several bugs to squash but we encourage all
people who like the bleeding edge to give it a try. This beta version is released
two weeks after our sixth one and it includes more than 200 commits.

Spyder 3.0 comes with several interesting and exciting new features. The most
important ones are:

* Third-party plugins: External developers can now create plugins that extend Spyder in
  novel and interesting ways. For example, we already have plugins for the line-profiler
  and memory-profiler projects, and also a graphical frontend for the conda package
  manager. These plugins can be distributed as pip and/or conda packages for authors
  convenience.
* Improved projects support: Projects have been revamped and improved significantly in
  Spyder 3.0. With our new projects support, people will have the possibility of easily
  working on different coding efforts at the same time. That's because projects save the
  state of open files in the Editor and allow Python packages created as part of the
  project to be imported in our consoles.
* Support for much more programming languages: Spyder relies now on the excellent Pygments
  library to provide syntax highlight and suggest code completions in the Editor, for all
  programming languages supported by it.
* A new file switcher: Spyder 3.0 comes with a fancy file switcher, very similar in
  spirit to the one present in Sublime Text. This is a dialog to select among the open
  files in the Editor, by doing a fuzzy search through their names. It also lets users to
  view the list of classes, methods and functions defined in the current file, and select
  one of them. This dialog is activated with `Ctrl+P`.
* A Numpy array graphical builder: Users who need to create NumPy arrays in Spyder for
  matrices and vectors can do it now in a graphical way by pressing `Ctrl+M` in the Editor
  or the Consoles. This will open an empty 2D table widget to be filled with the data
  required by the user.
* A new icon theme based on FontAwesome.
* A new set of default pane layouts for those coming from Rstudio or Matlab (under
  `View > Window layouts`).
* A simpler and more intuitive way to introduce keyboard shortcuts.
* Support for PyQt5, which fixes problems in MacOS X and in high definition screens.

For a complete list of changes, please see our
[changelog](https://github.com/spyder-ide/spyder/wiki/Beta-version-changelog)

You can easily install this beta if you use Anaconda by running:

    conda update qt pyqt
    conda install -c qttesting qt pyqt
    conda install -c spyder-ide spyder==3.0.0b7

Or you can use pip with this command:

    pip install --pre -U spyder


Enjoy!<br>
-Carlos
