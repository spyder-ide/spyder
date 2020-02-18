# Jupyter kernels for the Spyder console

[![CircleCI](https://circleci.com/gh/spyder-ide/spyder-kernels.svg?style=shield)](https://circleci.com/gh/spyder-ide/spyder-kernels)
[![AppVeyor](https://ci.appveyor.com/api/projects/status/pd0etf64xyiyd3qb/branch/master?svg=true)](https://ci.appveyor.com/project/spyder-ide/spyder-kernels/branch/master)
[![Travis status](https://travis-ci.org/spyder-ide/spyder-kernels.svg?branch=master)](https://travis-ci.org/spyder-ide/spyder-kernels)
[![codecov](https://codecov.io/gh/spyder-ide/spyder-kernels/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder-kernels)

Package that provides Jupyter kernels for use with the consoles of Spyder, the
Scientific Python Development Environment.

These kernels can launched either through Spyder itself or in an independent
Python session, and allow for interactive or file-based execution of Python
code inside Spyder.

To learn about creating, connecting to and using these kernels with the Spyder
console, please read our [documentation](https://docs.spyder-ide.org/ipythonconsole.html).

For advice on managing packages and environments with `spyder-kernels`, please visit
our [wiki](https://github.com/spyder-ide/spyder/wiki/Working-with-packages-and-environments-in-Spyder).


## Installation

To install this package, you can use either the ``pip`` or ``conda`` package
managers, as follows:

Using conda (the recommended way!):

```
conda install spyder-kernels
```

Using pip:

```
pip install spyder-kernels
```

## Dependencies

This project depends on:

* [ipykernel](https://github.com/ipython/ipykernel/)
* [cloudpickle](https://github.com/cloudpipe/cloudpickle)
* [wurlitzer](https://github.com/minrk/wurlitzer) (only on Linux and macOS).


## Changelog

Visit our [CHANGELOG](CHANGELOG.md) file to know more about our new features
and improvements.

## Development and contribution

To start contributing to this project you can execute

```
pip install -e .
```

in your git clone and then test your changes in Spyder. We follow PEP8 and
PEP257 style guidelines.
