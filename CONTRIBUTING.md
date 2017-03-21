# Contributing to Spyder-IDE

:+1::tada: First off, thanks for taking the time to contribute! :tada::+1:

## General Guidelines

This page documents at a very high level how to contribute to Spyder.
Please Check the [Spyder-IDE Contributor Documentation](https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder) for a more to developing and contributing to the Spyder.


## Setting Up a Development Environment


### Cloning the repo

```bash
  $ git clone https://github.com/spyder-ide/spyder.git
```

### Creating a conda environment (or virtualenv)

```bash
  $ conda create -n spyder spyder
  $ source activate spyder
```
This will also install spyder latest version and dependencies into the environment, if you want only to create the environment and install them manually, run:

```bash
  $ conda create -n spyder
  $ source activate spyder
```

You could also use `virtualenv`, but `conda` is prefered:

```bash
  $ mkvirtualenv spyder -a spyder
  $ workon spyder
```

### Installing spyder

This will also install required dependencies:

```bash
  $ python setup.py install
```

You can also run spyder from source code without installing it, (but you will need to [install dependencies](#installing-dependencies)):

```bash
  $ ./bootstrap.py
```

### Installing dependencies

```bash
  $ conda install --file requirements/requirements.txt
```
or using pip:

```bash
  $ pip install -r requirements/requirements.txt
```

> If you are using pip you also need to install a Qt binding (pyqt4, pyqt5)

```bash
  $ apt-get install python3-pyqt5
```

## Spyder Branches

When start working in a new pull request, be sure your branch is child of the correct branch and your PR is against it.

Normally issues are marked with a milestone, that indicate the correct branch:

* Use `3.1.x` branch for Bugfixes (Milestones `v3.1.1`, `v3.1.2`, `v3.1.3`...)

* Use `3.x` branch for introducing new features (Milestones `v3.1`, `v3.2`, `v3.3`...)

* Use `master` for break compatibility changes (Milestone `v4.0beta1`)

You can also submit bugfixes to `3.x` and `master` for errors that are only present in that branches.

You could start working in a new PR in this way:

```bash
  $ git checkout <branch>
  $ git pull upstream <branch>
  $ git checkout -b name-new-branch
```

##  Running Tests

Install test dependencies:
```bash
  $ conda install --file requirements/requirements.txt && pip install flaky
```

```bash
  $ pip install -r requirements/requirements.txt && pip install flaky
```

or using pip:
```bash
  $ pip install -e .[test]
```

To run the Python tests, use:
```bash
  $ python runtests.py
```
