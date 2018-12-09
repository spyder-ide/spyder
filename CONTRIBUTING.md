# Contributing to Spyder

:+1::tada: First off, thanks for taking the time to contribute to Spyder! :tada::+1:


## General Guidelines

This page documents at a very high level how to contribute to Spyder.
Please check the
[Spyder IDE Contributor Documentation](
https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder)
for a more detailed guide on how to do so.


## Troubleshooting

Before posting a report, *please* carefully read our
**[Troubleshooting Guide](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)**
and search the [issue tracker](https://github.com/spyder-ide/spyder/issues)
for your error message and problem description, as the great majority of bugs
are either duplicates, or can be fixed on the user side with a few easy steps.
Thanks!


## Submitting a Helpful Issue

Submitting useful, effective and to-the-point issue reports can go a long
way toward improving Spyder for everyone. Accordingly, please read the
[relevant section](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ#calling-for-help-still-have-a-problem)
of the Spyder Troubleshooting Guide, which describes in detail how to do
just that.

Most importantly, aside from the error message/traceback and the requested
environment/dependency information, *please* be sure you include a detailed,
step by step description of exactly what triggered the problem. Otherwise,
we likely won't be able to find and fix it, and your issue will have to be
closed after a week (7 days). Thanks!


## Setting Up a Development Environment


### Cloning the repo

```bash
  $ git clone https://github.com/spyder-ide/spyder.git
```

### Creating a conda environment or virtualenv

If you use Anaconda you can create a conda environment with
the following commands:

```bash
  $ conda create -n spyder-dev python=3.6
  $ source activate spyder-dev
```

On Windows, you'll want to run the commands with the Anaconda Prompt,
and use just ```activate spyder-dev``` for the second command.

You can also use `virtualenv` on Linux, but `conda` is strongly
recommended:

```bash
  $ mkvirtualenv spyder-dev
  $ workon spyder-dev
```

### Installing dependencies

After you have created your development environment, you need to install
Spyder's necessary dependencies. The easiest way to do so (with Anaconda) is

```bash
  $ conda install -c spyder-ide --file requirements/conda.txt
```

This installs all of Spyder's dependencies into the environment along with
the stable/packaged version of Spyder itself, and then removes the latter.

If using `pip` and `virtualenv` (not recommended), you need to `cd` to
the directory where your git clone is stored and run:

```bash
  $ pip install -e .
```

### Using the correct version of spyder-kernels

Following the separation in v3.3 of Spyder's console code into its own package,
`spyder-kernels`, you'll need to have the corresponding version of it
available—`0.x` for Spyder 3 (`3.x` branch), and `1.x` for Spyder 4
(`master` branch). The above procedure will install the `0.x` version;
to test the `master` branch (Spyder 4), you'll need to install the
corresponding `1.x` version of `spyder-kernels`.

This can be done via two methods: installing the correct version via `conda`:

```bash
conda install -c spyder-ide spyder-kernels=1.*
```

or `pip`:

```bash
pip install spyder-kernels==1.*
```

(and using `conda install spyder-kernels=0.*` to switch back to the
Spyder 3 version), or by `clone`-ing the
[spyder-kernels git repository](https://github.com/spyder-ide/spyder-kernels)
to somewhere on your path checking out the appropriate branch
(`0.x` or `master`) corresponding to the version of Spyder (3 or 4)
you would like to run, and running the commend `pip install -e` at the root.
For any non-trivial development work, keeping two separate virtual environments
(with `conda-env` or `venv`) for Spyder 3 and 4 makes this process
much quicker and less tedious.

### Running Spyder

To start Spyder directly from your clone, i.e. without installing it into
your environment, you need to run
(from the directory you cloned it to e.g. `spyder`):

```bash
  $ python bootstrap.py
```

To start Spyder in debug mode, useful for tracking down an issue, you can run:

```bash
  $ python bootstrap.py --debug
```

**Important Note**: To test any changes you've made to the Spyder source code,
you need to restart Spyder or start a fresh instance (you can run multiple
copies simultaneously by unchecking the Preferences option
<kbd>Use a single instance</kbd> under
<kbd>General</kbd> > <kbd>Advanced Settings</kbd> .


##  Running Tests

To install our test dependencies under Anaconda:

```bash
  $ conda install -c spyder-ide --file requirements/tests.txt
```

If using `pip` (for experts only), run the following from the directory
where your git clone is stored:
```bash
  $ pip install -e .[test]
```

To run the Spyder test suite, please use (from the `spyder` root directory):
```bash
  $ python runtests.py
```


## Spyder Branches

When you start to work on a new pull request (PR), you need to be sure that your
work is done on top of the correct Spyder branch, and that you base your
PR on Github against it.

To guide you, issues on Github are marked with a milestone that indicates
the correct branch to use. If not, follow these guidelines:

* Use the `3.x` branch for bugfixes only (*e.g.* milestones `v3.2.1`, `v3.2.2`,
  or `v3.2.3`)
* Use `master` to introduce new features or break compatibility with previous
  Spyder versions (*e.g.* milestones `v4.0beta1` or `v4.0beta2`).

You should also submit bugfixes to `3.x` or `master` for errors that are
only present in those respective branches.

To start working on a new PR, you need to execute these commands, filling in
the branch names where appropriate:

```bash
  $ git checkout <SPYDER-BASE-BRANCH>
  $ git pull upstream <SPYDER-BASE-BRANC>
  $ git checkout -b NAME-NEW-BRANCH
```

### Changing the base branch

If you started your work in the wrong base branch, or want to backport it,
you can change the base branch using `git rebase --onto`, like this:

```bash
  $ git rebase --onto <NEW-BASE-BRANCH> <OLD-BASE-BRANCH> <YOUR-BRANCH>
```

For example, backporting `my_branch` from `master` to `3.x`:

```bash
  $ git rebase --onto 3.x master my_branch
```


## Adding Third-Party Content

All files or groups of files, including source code, images, icons, and other
assets, that originate from projects outside of the Spyder organization
(regardless of the license), must be first approved by the Spyder team.
Always check with us (on Github, Gitter, Google Group, etc) before attempting
to add content from an external project, and only do so when necessary.


### Licenses

Code considered for inclusion must be under a permissive (i.e. non-copyleft)
license, particularly as the following (in order of preference):
* MIT (Expat)
* Public domain (preferably, CC0)
* ISC license
* BSD 2-clause ("Simplified BSD")
* BSD 3-clause ("New" or "Modified BSD")
* Apache License 2.0

Additionally, external assets (fonts, icons, images, sounds, animations)
can generally be under one of the following weak-copyleft and content licenses:
* Creative Commons Attribution 3.0 or 4.0
* SIL Open Font License 1.1
* GNU LGPL 2.1 or 3.0

Additional licenses *may* qualify for these lists from time to time, but every
effort should be made to avoid it. Regardless, all such licenses must be
OSI, FSF, and DSFG approved as well as GPLv3-compatible to ensure maximum
free distribution and use of Spyder with minimum ambiguity or fragmentation.


### Steps to take

#. Contact the Spyder team to ensure the usage is justified and compatible.

#. Add the files, preserving any original copyright/legal/attribution header

#. If making non-trivial modifications, copy the standard Spyder copyright
   header from ``.ciocopyright`` to just below the original headers;
   if the original headers are unformatted and just consist of a copyright
   statement and perhaps mention of the license, incorporate them verbatim
   within the Spyder header where appropriate.
   Always ensure copyright statements are in ascending chronological order,
   and replace the year in the Spyder copyright statement with the current one.
   Modify the license location to be the current directory, or NOTICE.txt.

#. Include the following line at the end of each module's docstring,
   separated by blank lines:

   ```rst
   Adapted from path/to/file/in/original/repo.py of the
   `Project Name <url-to-original-github-repo>`_.
   ```

   For example,

   ```rst
   Adapted from qcrash/_dialogs/gh_login.py of the
   `QCrash Project <https://github.com/ColinDuquesnoy/QCrash>`_.
   ```

#. Convert the files to project standards where needed.

#. If the copied file(s) reside in a directory dedicated to them, place the
   source project's LICENSE.txt file there, and any other legal files.
   Also, mention the same in the __init__.py file in that directory.

#. Add an entry in NOTICE.txt with the instructions and template there.

#. If a non-code visible asset (icons, fonts, animations, etc) or otherwise
   under a Creative Commons license, include a mention in the appropriate
   section of the README, as well as Spyder's About dialog, in the same form
   as the others present there.


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
