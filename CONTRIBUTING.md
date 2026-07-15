# Contributing to Spyder

:+1::tada: First off, thanks for taking the time to contribute to Spyder! :tada::+1:


## General Guidelines

This page documents at a very high level how to contribute to Spyder. Please check the [Spyder IDE Contributor Documentation](https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder) for a more detailed guide on how to do so.
Also, make sure you're familiar with our [Github workflow](https://github.com/spyder-ide/spyder/wiki/Dev:-Github-Workflow).


## Troubleshooting

Before posting a report, *please* carefully read our **[Troubleshooting Guide](https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)** and search the [issue tracker](https://github.com/spyder-ide/spyder/issues) for your error message and problem description, as the great majority of bugs are either duplicates, or can be fixed on the user side with a few easy steps. Thanks!


## Submitting a Helpful Issue

Submitting useful, effective and to-the-point issue reports can go a long way toward improving Spyder for everyone. Accordingly, please read the [relevant section](https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ#calling-for-help-still-have-a-problem) of the Spyder Troubleshooting Guide, which describes in detail how to do just that.

Most importantly, aside from the error message/traceback and the requested environment/dependency information, *please* be sure you include a detailed, step by step description of exactly what triggered the problem. Otherwise, we likely won't be able to find and fix it, and your issue will have to be closed after a week (7 days). Thanks!


## Setting Up a Development Environment

### Forking and cloning the repo

First, navigate to the [Spyder repo](https://github.com/spyder-ide/spyder) in your web browser and press the ``Fork`` button to make a personal copy of the repository on your own Github account.
Then, click the ``Clone or Download`` button on your repository, copy the link and run the following on the command line to clone the repo:

```bash
$ git clone <LINK-TO-YOUR-REPO>
```

Finally, set the upstream remote to the official Spyder repo with:

```bash
$ git remote add upstream https://github.com/spyder-ide/spyder.git
```


### Creating an environment and installing dependencies

If you use Anaconda or Conda-forge, you can create an environment and install the necessary dependencies as follows:

```bash
$ conda create -n spyder-dev -c conda-forge python=3.9
$ conda activate spyder-dev
$ conda env update --file requirements/main.yml
```

After doing that, you need to install Spyder's specific dependencies per operating system. For instance, if you're working on macOS you need to run

```bash
$ conda env update --file requirements/macos.yml
```

You can also use `virtualenv` on Linux, but `conda` is **strongly** recommended:

```bash
$ mkvirtualenv spyder-dev
$ workon spyder-dev
(spyder-dev) $ pip install -e .
```


### Running Spyder

To run Spyder from your clone in its development mode, with extra checks and options (pass `--help` to see them), launch it via the `bootstrap.py` script in the repo root directory:

```bash
$ python bootstrap.py
```

Note that if you are running on macOS 10.15 or earlier, you will need to call `pythonw` instead of `python`.

To start Spyder in debug mode, useful for tracking down an issue, you can run:

```bash
$ python bootstrap.py --debug
```

**Important Note**: To test any changes you've made to the Spyder source code, you need to restart Spyder or start a fresh instance (you can run multiple copies simultaneously by unchecking the Preferences option <kbd>Use a single instance</kbd> under <kbd>General</kbd> > <kbd>Advanced Settings</kbd> .

To start Spyder with different Qt bindings (e.g. PySide2 or PyQt6), you can run:

```bash
$ python bootstrap.py --gui pyqt6
```

To access Spyder command line options from `bootstrap.py`, you need to run:

```bash
$ python bootstrap.py -- --help
```

Note that `bootstrap.py` has its own command line options, which can be listed by running:

```bash
$ python bootstrap.py --help
```


###  Running tests

To install our test dependencies under Anaconda:

```bash
$ conda env update --file requirements/tests.yml
```

If using `pip` (for experts only), run the following from the directory where your git clone is stored:

```bash
$ pip install -e .[test]
```

To run the Spyder test suite, please use (from the `spyder` root directory):

```bash
$ python runtests.py
```


## Spyder Branches

To start working on a new pull request you need to execute these commands, filling in the branch name where appropriate:

```bash
$ git checkout master
$ git pull upstream master
$ git checkout -b <NAME-NEW-BRANCH>
```


## Making contributions that depend on pull requests in spyder-kernels

Spyder and spyder-kernels are developed jointly because a lot of communication happens between them in order to run code written in the editor in the IPython console.

For this reason, a clone of spyder-kernels is placed in the `external-deps` subfolder of the Spyder repository. The instructions on this section will help you in case you need to make changes that touch both repositories at the same time.

The first thing you need to do is cloning the [git-subrepo](https://github.com/ingydotnet/git-subrepo) project and follow these instructions to install it (on Windows you need to use Git Bash in order to run them):

```
git clone https://github.com/ingydotnet/git-subrepo /path/to/git-subrepo
echo 'source /path/to/git-subrepo/.rc' >> ~/.bashrc
source ~/.bashrc
```

As an example, let's assume that (i) your Github user name is `myuser`; (ii) you have two git clones placed at `~/spyder` and `~/spyder-kernels` that link to `https://github.com/myuser/spyder` and `https://github.com/myuser/spyder-kernels` respectively; and (iii) you have two branches named `fix_in_spyder` and `fix_in_kernel` in each of these git repos respectively. If you want to open a joint PR in `spyder` and `spyder-kernels` that link these branches, here is how to do it:

* Go to the `~/spyder` folder, checkout your `fix_in_spyder` branch and replace the spyder-kernels clone in the `external-deps` subfolder by a clone of your `fix_in_kernel` branch:

    ```
    $ cd ~/spyder
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/spyder-kernels -r https://github.com/myuser/spyder-kernels.git -b fix_in_kernel -u -f
    ```

* You can now open a PR on `https://github.com/spyder-ide/spyder` and on `https://github.com/spyder-ide/spyder-kernels` for each of your branches.

* If you make additional changes to the `fix_in_kernel` branch in `spyder-kernels` (e.g. adding a new file, as in the example below), you need to sync them in your Spyder's `fix_in_spyder` branch like this:

    ```
    $ cd ~/spyder-kernels
    $ git checkout fix_in_kernel
    $ touch foo.py
    $ git add -A
    $ git commit -m "Adding foo.py to the repo"
    $ git push origin fix_in_kernel

    $ cd ~/spyder
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/spyder-kernels -r https://github.com/myuser/spyder-kernels.git -b fix_in_kernel -u -f
    $ git push origin fix_in_spyder
    ```

* When your `fix_in_kernel` PR is merged, you need to update Spyder's `fix_in_spyder` branch because the clone in Spyder's repo must point out again to the spyder-kernel's repo and not to your own clone. For that, please run:

    ```
    $ git subrepo pull external-deps/spyder-kernels -r https://github.com/spyder-ide/spyder-kernels.git -b master -u -f
    ```


## Making contributions that depend on pull requests in python-lsp-server or qtconsole

As with spyder-kernels, Spyder is tightly integrated with the [python-lsp-server](https://github.com/python-lsp/python-lsp-server) to provide code completion, linting and folding on its editor; and [qtconsole](https://github.com/jupyter/qtconsole) for its IPython console.

Due to that, a clone of those projects is placed in the `external-deps` directory, which is managed with the `git subrepo` project. If you want to make a pull request in python-lsp-server or qtconsole that affects functionality in Spyder, please read carefully the instructions in the previous section because they are very similar for those cases. A summary of those instructions applied to these projects is the following:

* First you need to create a pull request in python-lsp-server or qtconsole with the changes you want to make there. Let's assume the branch from which that pull request is created is called `fix_in_external_dep`.

* Then you need to create a branch in Spyder (let's call it `fix_in_spyder`) with the fixes that require that pull request and update the python-lsp-server subrepo. For that you need to execute the following commands:

    ```
    $ git checkout -b fix_in_spyder
    $ git subrepo pull external-deps/python-lsp-server -r https://github.com/myuser/python-lsp-server.git -b fix_in_external_dep -u -f
    ```

    in case the fix is in python-lsp-server, or

    ```
    $ git checkout -b fix_in_spyder
    $ git subrepo pull external-deps/qtconsole -r https://github.com/myuser/qtconsole.git -b fix_in_external_dep -u -f
    ```

    if the fix is in qtconsole. And then commit the changes you need to make in Spyder.

* If you need to add more commits to `fix_in_external_dep`, you need to update `fix_in_spyder` with these commands:

    ```
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/python-lsp-server -r https://github.com/myuser/python-lsp-server.git -b fix_in_external_dep -u -f
    $ git push origin fix_in_spyder
    ```

    or

    ```
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/qtconsole -r https://github.com/myuser/qtconsole.git -b fix_in_external_dep -u -f
    $ git push origin fix_in_spyder
    ```

* After `fix_in_external_dep` is merged, you need to update the python-lsp-server or qtconsole subrepos in your `fix_in_spyder` branch with

    ```
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/python-lsp-server -r https://github.com/python-lsp/python-lsp-server.git -b develop -u -f
    ```

    or

    ```
    $ git checkout fix_in_spyder
    $ git subrepo pull external-deps/qtconsole -r https://github.com/jupyter/qtconsole.git -b main -u -f
    ```


## Guidelines for Spyder API changes

If your work makes changes to public classes, methods or Qt signals in `spyder.api`, or to the public interface of any plugin (e.g. `plugins/editor/plugin.py`), you must add a note about it in the current Changelog (e.g. `changelogs/Spyder-6.md`).
If an entry for the version where your PR will be included doesn't exist yet, create one (with `Unreleased` as its date) and a subsection called `API changes`.

Please note that the Spyder API must be changed according to the following guidelines:

* For bugfix versions (e.g. `6.0.3`), you can only add new Qt signals or methods, or kwargs to current methods.
* For minor versions (e.g. `6.1.0`), you should try to do the same as for bugfix versions, unless it's **strictly** necessary to break the API by removing or changing certain Qt signals, classes or methods in a backwards incompatible way.
* For major versions (e.g. `7.0.0`), there are no restrictions on API changes.


## Mixing Qt and plain Python classes (multiple inheritance)

Spyder runs on PyQt5/PyQt6 (SIP) and PySide2/PySide6 (Shiboken), and the two
binding families have different — partly contradictory — rules for classes
that inherit from both a Qt class and plain Python classes (mixins):

* **SIP** requires the Qt class' `__init__` to run before anything else
  touches `self` (otherwise you get `RuntimeError: super-class __init__() of
  type ... was never called`).
* **Shiboken** auto-invokes the `__init__` of whatever class *follows* the Qt
  class in the MRO when the Qt `__init__` runs — even when you call it
  explicitly by name. If you then also call that class' `__init__` yourself,
  the process aborts with `You can't initialize an object twice`.
* **Shiboken** resolves reimplemented Qt virtual methods (e.g.
  `mouseDoubleClickEvent`) to the first hit in the MRO. So if the Qt class is
  listed before a mixin, the mixin's overrides are **silently ignored**. (SIP
  skips the C++ method wrappers while searching, so the wrong order happens
  to work there — don't rely on it.)

All of these are satisfied simultaneously by the following pattern for
widgets (i.e. when inheriting from a Qt class directly, or from a Spyder
class like `PluginMainWidget` that already composes one):

1. List mixins first and the Qt class **last** in the bases.
2. In `__init__`, call the Qt class' `__init__` **first**. (With the Qt class
   last in the MRO, Shiboken's auto-invocation only reaches `object`, so it's
   harmless.)
3. Then call each mixin's `__init__` **explicitly by name**. Don't rely on a
   cooperative `super().__init__()` chain that crosses the Qt/mixin boundary.
   (If none of the mixins define an `__init__`, e.g. for pure accessor mixins
   like `SpyderFontsMixin` or `SpyderConfigurationAccessor`, a plain
   `super().__init__(parent)` is fine — it falls through them straight to the
   Qt class.)

This is a simple example:

```python
class MyWidget(FooMixin, BarMixin, QWidget):

    def __init__(self, parent=None):
        QWidget.__init__(self, parent)
        FooMixin.__init__(self)
        BarMixin.__init__(self, some_arg)
```

**Plugins** follow a variation of this: the plugin base
(`SpyderPluginV2`/`SpyderDockablePlugin`, which is QObject-derived and
already puts `QObject` last in its own bases) stays **first** so that its
methods take precedence, with interface mixins after it. The `__init__` order
is the same: plugin base first, then each mixin explicitly:

```python
class MyPlugin(SpyderDockablePlugin, ShellConnectPluginMixin):

    def __init__(self, parent, configuration=None):
        SpyderDockablePlugin.__init__(self, parent, configuration)
        ShellConnectPluginMixin.__init__(self)
```

This is safe because these interface mixins don't override Qt virtual
methods, so the MRO position of the Qt lineage doesn't hide anything.

Canonical examples of the patterns used in the codebase:

* Widget plus mixins:
  [`ControlWidget`](spyder/plugins/ipythonconsole/widgets/control.py) and
  [`ClientWidget`](spyder/plugins/ipythonconsole/widgets/client.py).
* Plugin plus interface mixins:
  [`Plots`](spyder/plugins/plots/plugin.py) and
  [`Layout`](spyder/plugins/layout/plugin.py).
* Plugin plus a QObject-derived mixin whose state setup must not re-init the
  QObject part: [`Debugger`](spyder/plugins/debugger/plugin.py), which calls
  `RunExecutor._setup_run_executor()` — a method split out of
  `RunExecutor.__init__` (see [spyder/plugins/run/api.py](spyder/plugins/run/api.py))
  precisely so that it can be invoked without running `QObject.__init__` twice.
* Deliberate exception with the Qt class **first**:
  [`WorkspaceEventHandler`](spyder/plugins/projects/utils/watcher.py), where
  the other base is a third-party class that calls `super().__init__()`
  internally; the comment there explains why the usual order would abort
  under Shiboken.

Two related gotchas to keep in mind:

* Enum members must be accessed on the **class**, not on instances
  (`QClipboard.Clipboard`, not `clipboard_instance.Clipboard`) — instance
  access raises `AttributeError` on PySide6.
* For overloaded signals like `Signal((), (object,))`, a slot is attached to
  a *single* overload, and the bindings pick it differently: PySide uses the
  slot's signature (a slot with an optional argument lands on `(object,)`),
  while PyQt uses the first overload. Either way emits of the other overload
  never reach the slot, so connect each overload explicitly and give the
  no-arg one a slot that can't take arguments — e.g. by wrapping it in
  `functools.partial` (see how `sig_unmaximize_plugin_requested` is connected
  in [spyder/app/mainwindow.py](spyder/app/mainwindow.py)).


## Adding Third-Party Content

All files or groups of files, including source code, images, icons, and other assets, that originate from projects outside of the Spyder organization (regardless of the license), must be first approved by the Spyder team. Always check with us (on Github, Gitter, Google Group, etc) before attempting to add content from an external project, and only do so when necessary.


### Licenses

Code considered for inclusion must be under a permissive (i.e. non-copyleft) license, particularly as the following (in order of preference):

* MIT (Expat)
* Public domain (preferably, CC0)
* ISC license
* BSD 2-clause ("Simplified BSD")
* BSD 3-clause ("New" or "Modified BSD")
* Apache License 2.0

Additionally, external assets (fonts, icons, images, sounds, animations) can generally be under one of the following weak-copyleft and content licenses:

* Creative Commons Attribution 3.0 or 4.0
* SIL Open Font License 1.1
* GNU LGPL 2.1 or 3.0

Additional licenses *may* qualify for these lists from time to time, but every effort should be made to avoid it. Regardless, all such licenses must be OSI, FSF, and DSFG approved as well as GPLv3-compatible to ensure maximum free distribution and use of Spyder with minimum ambiguity or fragmentation.


### Steps to take

1. Contact the Spyder team to ensure the usage is justified and compatible.

2. Add the files, preserving any original copyright/legal/attribution header

3. If making non-trivial modifications, copy the standard Spyder copyright header from ``.ciocopyright`` to just below the original headers; if the original headers are unformatted and just consist of a copyright statement and perhaps mention of the license, incorporate them verbatim within the Spyder header where appropriate. Always ensure copyright statements are in ascending chronological order, and replace the year in the Spyder copyright statement with the current one. Modify the license location to be the current directory, or NOTICE.txt.

4. Include the following line at the end of each module's docstring, separated by blank lines:

   ```rst
   Adapted from path/to/file/in/original/repo.py of the
   `Project Name <url-to-original-github-repo>`_.
   ```

   For example,

   ```rst
   Adapted from qcrash/_dialogs/gh_login.py of the
   `QCrash Project <https://github.com/ColinDuquesnoy/QCrash>`_.
   ```

5. Convert the files to project standards where needed.

6. If the copied file(s) reside in a directory dedicated to them, place the source project's LICENSE.txt file there, and any other legal files. Also, mention the same in the __init__.py file in that directory.

7. Add an entry in NOTICE.txt with the instructions and template there.

8. If a non-code visible asset (icons, fonts, animations, etc) or otherwise under a Creative Commons license, include a mention in the appropriate section of the README, as well as Spyder's About dialog, in the same form as the others present there.


## More information

[Main Website](https://www.spyder-ide.org/)

[Download Spyder (with Anaconda)](https://www.anaconda.com/download/)

[Online Documentation](https://docs.spyder-ide.org/)

[Spyder Github](https://github.com/spyder-ide/spyder)

[Troubleshooting Guide and FAQ](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)

[Development Wiki](https://github.com/spyder-ide/spyder/wiki/Dev:-Index)

[Gitter Chatroom](https://gitter.im/spyder-ide/public)

[Google Group](https://groups.google.com/group/spyderlib)

[@Spyder_IDE on Twitter](https://twitter.com/spyder_ide)

[@SpyderIDE on Facebook](https://www.facebook.com/SpyderIDE/)

[Support Spyder on OpenCollective](https://opencollective.com/spyder/)
