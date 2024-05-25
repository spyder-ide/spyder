# Jupyter kernels for the Spyder console

[![Windows status](https://github.com/spyder-ide/spyder-kernels/workflows/Windows%20tests/badge.svg)](https://github.com/spyder-ide/spyder-kernels/actions?query=workflow%3A%22Windows+tests%22)
[![Linux status](https://github.com/spyder-ide/spyder-kernels/workflows/Linux%20tests/badge.svg)](https://github.com/spyder-ide/spyder-kernels/actions?query=workflow%3A%22Linux+tests%22)
[![Macos status](https://github.com/spyder-ide/spyder-kernels/workflows/Macos%20tests/badge.svg)](https://github.com/spyder-ide/spyder-kernels/actions?query=workflow%3A%22Macos+tests%22)
[![codecov](https://codecov.io/gh/spyder-ide/spyder-kernels/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder-kernels/branch/master)

Package that provides Jupyter kernels for use with the consoles of Spyder, the
Scientific Python Development Environment.

These kernels can be launched either through Spyder itself or in an independent
Python session, and allow for interactive or file-based execution of Python
code inside Spyder.

To learn about creating, connecting to and using these kernels with the Spyder
console, please read our [documentation](https://docs.spyder-ide.org/current/panes/ipythonconsole.html).

For advice on managing packages and environments with `spyder-kernels`, please read this
[FAQ](http://docs.spyder-ide.org/current/faq.html#using-existing-environment) in our docs.


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

## Sponsors

Spyder and its subprojects are funded thanks to the generous support of

[![Quansight](https://user-images.githubusercontent.com/16781833/142477716-53152d43-99a0-470c-a70b-c04bbfa97dd4.png)](https://www.quansight.com/)[![Numfocus](https://i2.wp.com/numfocus.org/wp-content/uploads/2017/07/NumFocus_LRG.png?fit=320%2C148&ssl=1)](https://numfocus.org/)

and the donations we have received from our users around the world through [Open Collective](https://opencollective.com/spyder/):

[![Sponsors](https://opencollective.com/spyder/sponsors.svg)](https://opencollective.com/spyder#support)
