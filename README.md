![Spyder — The Scientific Python Development Environment](https://raw.githubusercontent.com/spyder-ide/spyder/master/branding/logo/spyder_readme_banner.png)

*Copyright © 2009–2022 [Spyder Project Contributors](
https://github.com/spyder-ide/spyder/graphs/contributors)*

*Some source files and icons may be under other authorship/licenses; see
[NOTICE.txt](https://github.com/spyder-ide/spyder/blob/master/NOTICE.txt).*

## Project status

[![license](https://img.shields.io/pypi/l/spyder.svg)](./LICENSE.txt)
[![pypi version](https://img.shields.io/pypi/v/spyder.svg)](https://pypi.org/project/spyder/)
[![conda version](https://img.shields.io/conda/vn/conda-forge/spyder.svg)](https://www.anaconda.com/download/)
[![download count](https://img.shields.io/conda/dn/conda-forge/spyder.svg)](https://www.anaconda.com/download/)
[![OpenCollective Backers](https://opencollective.com/spyder/backers/badge.svg?color=blue)](#backers)
[![OpenCollective Sponsors](https://opencollective.com/spyder/sponsors/badge.svg?color=blue)](#sponsors)
[![Join the chat at https://gitter.im/spyder-ide/public](https://badges.gitter.im/spyder-ide/spyder.svg)](https://gitter.im/spyder-ide/public)<br>
[![PyPI status](https://img.shields.io/pypi/status/spyder.svg)](https://github.com/spyder-ide/spyder)

## Build status
[![Win](https://github.com/spyder-ide/spyder/workflows/Win%20tests/badge.svg)](https://github.com/spyder-ide/spyder/actions?query=workflow%3A%22Win+tests%22)
[![Mac](https://github.com/spyder-ide/spyder/workflows/Mac%20tests/badge.svg)](https://github.com/spyder-ide/spyder/actions?query=workflow%3A%22Mac+tests%22)
[![Linux](https://github.com/spyder-ide/spyder/workflows/Linux%20tests/badge.svg)](https://github.com/spyder-ide/spyder/actions?query=workflow%3A%Linux+tests%22)
[![Coverage Status](https://coveralls.io/repos/github/spyder-ide/spyder/badge.svg?branch=master)](https://coveralls.io/github/spyder-ide/spyder?branch=master)
[![codecov](https://codecov.io/gh/spyder-ide/spyder/branch/master/graph/badge.svg)](https://codecov.io/gh/spyder-ide/spyder)
[![Crowdin](https://badges.crowdin.net/spyder/localized.svg)](https://crowdin.com/project/spyder)

## Try Spyder online

[![Binder Spyder latest release](https://img.shields.io/badge/launch-latest%20release-579ACA.svg?logo=data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAFkAAABZCAMAAABi1XidAAAB8lBMVEX///9XmsrmZYH1olJXmsr1olJXmsrmZYH1olJXmsr1olJXmsrmZYH1olL1olJXmsr1olJXmsrmZYH1olL1olJXmsrmZYH1olJXmsr1olL1olJXmsrmZYH1olL1olJXmsrmZYH1olL1olL0nFf1olJXmsrmZYH1olJXmsq8dZb1olJXmsrmZYH1olJXmspXmspXmsr1olL1olJXmsrmZYH1olJXmsr1olL1olJXmsrmZYH1olL1olLeaIVXmsrmZYH1olL1olL1olJXmsrmZYH1olLna31Xmsr1olJXmsr1olJXmsrmZYH1olLqoVr1olJXmsr1olJXmsrmZYH1olL1olKkfaPobXvviGabgadXmsqThKuofKHmZ4Dobnr1olJXmsr1olJXmspXmsr1olJXmsrfZ4TuhWn1olL1olJXmsqBi7X1olJXmspZmslbmMhbmsdemsVfl8ZgmsNim8Jpk8F0m7R4m7F5nLB6jbh7jbiDirOEibOGnKaMhq+PnaCVg6qWg6qegKaff6WhnpKofKGtnomxeZy3noG6dZi+n3vCcpPDcpPGn3bLb4/Mb47UbIrVa4rYoGjdaIbeaIXhoWHmZYHobXvpcHjqdHXreHLroVrsfG/uhGnuh2bwj2Hxk17yl1vzmljzm1j0nlX1olL3AJXWAAAAbXRSTlMAEBAQHx8gICAuLjAwMDw9PUBAQEpQUFBXV1hgYGBkcHBwcXl8gICAgoiIkJCQlJicnJ2goKCmqK+wsLC4usDAwMjP0NDQ1NbW3Nzg4ODi5+3v8PDw8/T09PX29vb39/f5+fr7+/z8/Pz9/v7+zczCxgAABC5JREFUeAHN1ul3k0UUBvCb1CTVpmpaitAGSLSpSuKCLWpbTKNJFGlcSMAFF63iUmRccNG6gLbuxkXU66JAUef/9LSpmXnyLr3T5AO/rzl5zj137p136BISy44fKJXuGN/d19PUfYeO67Znqtf2KH33Id1psXoFdW30sPZ1sMvs2D060AHqws4FHeJojLZqnw53cmfvg+XR8mC0OEjuxrXEkX5ydeVJLVIlV0e10PXk5k7dYeHu7Cj1j+49uKg7uLU61tGLw1lq27ugQYlclHC4bgv7VQ+TAyj5Zc/UjsPvs1sd5cWryWObtvWT2EPa4rtnWW3JkpjggEpbOsPr7F7EyNewtpBIslA7p43HCsnwooXTEc3UmPmCNn5lrqTJxy6nRmcavGZVt/3Da2pD5NHvsOHJCrdc1G2r3DITpU7yic7w/7Rxnjc0kt5GC4djiv2Sz3Fb2iEZg41/ddsFDoyuYrIkmFehz0HR2thPgQqMyQYb2OtB0WxsZ3BeG3+wpRb1vzl2UYBog8FfGhttFKjtAclnZYrRo9ryG9uG/FZQU4AEg8ZE9LjGMzTmqKXPLnlWVnIlQQTvxJf8ip7VgjZjyVPrjw1te5otM7RmP7xm+sK2Gv9I8Gi++BRbEkR9EBw8zRUcKxwp73xkaLiqQb+kGduJTNHG72zcW9LoJgqQxpP3/Tj//c3yB0tqzaml05/+orHLksVO+95kX7/7qgJvnjlrfr2Ggsyx0eoy9uPzN5SPd86aXggOsEKW2Prz7du3VID3/tzs/sSRs2w7ovVHKtjrX2pd7ZMlTxAYfBAL9jiDwfLkq55Tm7ifhMlTGPyCAs7RFRhn47JnlcB9RM5T97ASuZXIcVNuUDIndpDbdsfrqsOppeXl5Y+XVKdjFCTh+zGaVuj0d9zy05PPK3QzBamxdwtTCrzyg/2Rvf2EstUjordGwa/kx9mSJLr8mLLtCW8HHGJc2R5hS219IiF6PnTusOqcMl57gm0Z8kanKMAQg0qSyuZfn7zItsbGyO9QlnxY0eCuD1XL2ys/MsrQhltE7Ug0uFOzufJFE2PxBo/YAx8XPPdDwWN0MrDRYIZF0mSMKCNHgaIVFoBbNoLJ7tEQDKxGF0kcLQimojCZopv0OkNOyWCCg9XMVAi7ARJzQdM2QUh0gmBozjc3Skg6dSBRqDGYSUOu66Zg+I2fNZs/M3/f/Grl/XnyF1Gw3VKCez0PN5IUfFLqvgUN4C0qNqYs5YhPL+aVZYDE4IpUk57oSFnJm4FyCqqOE0jhY2SMyLFoo56zyo6becOS5UVDdj7Vih0zp+tcMhwRpBeLyqtIjlJKAIZSbI8SGSF3k0pA3mR5tHuwPFoa7N7reoq2bqCsAk1HqCu5uvI1n6JuRXI+S1Mco54YmYTwcn6Aeic+kssXi8XpXC4V3t7/ADuTNKaQJdScAAAAAElFTkSuQmCC)](https://mybinder.org/v2/gh/spyder-ide/binder-environments/spyder-stable?urlpath=git-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252Fspyder-ide%252FSpyder-Workshop%26urlpath%3Ddesktop%252F%26branch%3Dmaster) :point_left: By clicking on this link you'll be able to test the [latest Spyder version](https://github.com/spyder-ide/spyder/releases/latest) in your browser.

[![Binder Spyder from 5.x](https://img.shields.io/badge/launch-5.x-E66581.svg?logo=data:image/png;base64,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)](https://mybinder.org/v2/gh/spyder-ide/binder-environments/5.x?urlpath=git-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252Fspyder-ide%252Fspyder%26urlpath%3Ddesktop%252F%26branch%3D5.x%26depth%3D500) :point_left: By clicking on this link you'll be able to test the latest Spyder 5.x development version.

[![Binder Spyder from master](https://img.shields.io/badge/launch-master-E66581.svg?logo=data:image/png;base64,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)](https://mybinder.org/v2/gh/spyder-ide/binder-environments/master?urlpath=git-pull%3Frepo%3Dhttps%253A%252F%252Fgithub.com%252Fspyder-ide%252Fspyder%26urlpath%3Ddesktop%252F%26branch%3Dmaster%26depth%3D500) :point_left: By clicking on this link you'll be able to test the latest Spyder 6.x development version.

----

## How Spyder looks


![Screenshot of Spyder's main window](https://raw.githubusercontent.com/spyder-ide/spyder/5.x/img_src/screenshot.png)

----

## Help support Spyder, the community-developed scientific IDE!

Spyder development is made possible by contributions from our global user
community, along with organizations like [NumFOCUS](https://www.numfocus.org)
and [Quansight](https://www.quansight.com).
There are numerous [ways you can help](
https://github.com/spyder-ide/spyder/wiki/Contributing-to-Spyder), many of
which don't require any programming. If you'd like to make a [donation](
https://opencollective.com/spyder/donate) to help fund further improvements,
we're on [OpenCollective](https://opencollective.com/spyder).

Thanks for all you do to make the Spyder project thrive! [More details](
https://github.com/spyder-ide/spyder/wiki/Current-Funding-and-Development-Status)



----

## Overview

Spyder is a powerful scientific environment written in Python, for Python,
and designed by and for scientists, engineers and data analysts. It offers a
unique combination of the advanced editing, analysis, debugging, and profiling
functionality of a comprehensive development tool with the data exploration,
interactive execution, deep inspection, and beautiful visualization
capabilities of a scientific package.

Beyond its many built-in features, its abilities can be extended even further
via its plugin system and API. Furthermore, Spyder can also be used as a PyQt5
extension library, allowing you to build upon its functionality and embed
its components, such as the interactive console, in your own software.

For more general information about Spyder and to stay up to date on the
latest Spyder news and information, please check out [our new website](
https://www.spyder-ide.org/).


## Core components

* **Editor**

    Work efficiently in a multi-language editor with a function/class browser,
    real-time code analysis tools (`pyflakes`, `pylint`, and `pycodestyle`),
    automatic code completion (`jedi` and `rope`),
    horizontal/vertical splitting, and go-to-definition.

* **Interactive console**

    Harness the power of as many IPython consoles as you like with full
    workspace and debugging support, all within the flexibility of a full
    GUI interface. Instantly run your code by line, cell, or file,
    and render plots right inline with the output or in interactive windows.

* **Documentation viewer**

    Render documentation in real-time with Sphinx for any class or function,
    whether external or user-created, from either the Editor or a Console.

* **Variable explorer**

    Inspect any variables, functions or objects created during your session.
    Editing and interaction is supported with many common types, including
    numeric/strings/bools, Python lists/tuples/dictionaries, dates/timedeltas,
    Numpy arrays, Pandas index/series/dataframes, PIL/Pillow images, and more.

* **Development tools**

    Examine your code with the static analyzer, trace its execution with the
    interactive debugger, and unleash its performance with the profiler.
    Keep things organized with project support and a built-in file explorer, and
    use find in files to search across entire projects with full regex support.


## Documentation

You can read the Spyder documentation online on [the Spyder Docs website](
https://docs.spyder-ide.org/).


## Installation

For a detailed guide to installing Spyder, please refer to our
[installation instructions](https://docs.spyder-ide.org/installation.html).

The easiest way to install Spyder on any of our supported platforms
is to download it as part of the [Anaconda](https://www.anaconda.com/download/)
distribution, and use the `conda` package and environment manager to keep it
and your other packages installed and up to date.

If in doubt, you should always install Spyder via this method to avoid
unexpected issues we are unable to help you with; it generally has the
least likelihood of potential pitfalls for non-experts, and we may be
able to provide limited assistance if you do run into trouble.

Other installation options exist, including:

* The [WinPython](https://winpython.github.io/) distribution for Windows
* The [MacPorts](https://www.macports.org/) project for macOS
* Your distribution's package manager (i.e. `apt-get`, `yum`, etc) on Linux
* The `pip` package manager, included with most Python installations

**However**, we lack the resources to provide individual support for users who
install via these methods, and they may be out of date or contain bugs outside
our control, so we recommend the Anaconda version instead if you run into issues.


## Troubleshooting

Before posting a report, *please* carefully read our **[Troubleshooting Guide](
https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ)**
and search the [issue tracker](https://github.com/spyder-ide/spyder/issues)
for your error message and problem description, as the great majority of bugs
are either duplicates, or can be fixed on the user side with a few easy steps.
Thanks!


## Contributing and Credits

Spyder was originally created by [Pierre Raybaut](
https://github.com/PierreRaybaut), and is currently maintained by
[Carlos Córdoba](https://github.com/ccordoba12) and an international
community of volunteers.

You can join us—everyone is welcome to help with Spyder!
Please read our [contributing instructions](
https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md)
to get started!

Certain source files are distributed under other compatible permissive licenses
and/or originally by other authors.
The icons for the Spyder 3 theme are derived from [Font Awesome](
https://fontawesome.com/) 4.7 (© 2016 David Gandy; SIL OFL 1.1).
Most Spyder 2 theme icons are sourced from the [Crystal Project icon set](
https://www.everaldo.com) (© 2006-2007 Everaldo Coelho; LGPL 2.1+).
Other Spyder 2 icons are from [Yusuke Kamiyamane](
http://p.yusukekamiyamane.com/) (© 2013 Yusuke Kamiyamane; CC-BY 3.0),
the [FamFamFam Silk icon set](http://www.famfamfam.com/lab/icons/silk/)
(© 2006 Mark James; CC-BY 2.5), and the [KDE Oxygen icons](
https://www.kde.org/) (© 2007 KDE Artists; LGPL 3.0+).

See [NOTICE.txt](https://github.com/spyder-ide/spyder/blob/master/NOTICE.txt)
for full legal information.


## Running from a git clone

Please see the instructions in our
[Contributing guide](https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md#setting-up-a-development-environment)
to learn how to do run Spyder after cloning its repo from Github.

## Dependencies

**Important Note**: Most or all of the dependencies listed below come
with *Anaconda* and other scientific Python distributions, so you don't need
to install them separately in those cases.

### Build dependencies

When installing Spyder from its source package, the only requirement is to have
a Python version equal or greater than 3.7.

### Runtime dependencies

The basic dependencies to run Spyder are:

* **Python** 3.7+: The core language Spyder is written in and for.
* **PyQt5** 5.9+: Python bindings for Qt, used for Spyder's GUI.

The rest our dependencies (both required and optional) are declared in
[this file](https://github.com/spyder-ide/spyder/blob/master/spyder/dependencies.py).


## Sponsors

Spyder is funded thanks to the generous support of


[![Quansight](https://user-images.githubusercontent.com/16781833/142477716-53152d43-99a0-470c-a70b-c04bbfa97dd4.png)](https://www.quansight.com/)[![Numfocus](https://i2.wp.com/numfocus.org/wp-content/uploads/2017/07/NumFocus_LRG.png?fit=320%2C148&ssl=1)](https://numfocus.org/)


and the donations we have received from our users around the world through [Open Collective](https://opencollective.com/spyder/):

[![Sponsors](https://opencollective.com/spyder/sponsors.svg)](https://opencollective.com/spyder#support)


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
