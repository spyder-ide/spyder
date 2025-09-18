# History of changes

## Version 3.1.0b1 (2025/09/10)

### Issues Closed

* [Issue 555](https://github.com/spyder-ide/spyder-kernels/issues/555) - Replace `setup.py` with `pyproject.toml` ([PR 557](https://github.com/spyder-ide/spyder-kernels/pull/557) by [@dalthviz](https://github.com/dalthviz))
* [Issue 543](https://github.com/spyder-ide/spyder-kernels/issues/543) - Support IPython 9.x ([PR 559](https://github.com/spyder-ide/spyder-kernels/pull/559) by [@dalthviz](https://github.com/dalthviz))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 559](https://github.com/spyder-ide/spyder-kernels/pull/559) - PR: Add support for IPython 9, by [@dalthviz](https://github.com/dalthviz) ([543](https://github.com/spyder-ide/spyder-kernels/issues/543))
* [PR 558](https://github.com/spyder-ide/spyder-kernels/pull/558) - PR: Add `profile`, `profilefile` and `profilecell` magics, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 557](https://github.com/spyder-ide/spyder-kernels/pull/557) - PR: Replace `setup.py` with `pyproject.toml`, by [@dalthviz](https://github.com/dalthviz) ([555](https://github.com/spyder-ide/spyder-kernels/issues/555))
* [PR 556](https://github.com/spyder-ide/spyder-kernels/pull/556) - PR: Replace `@flaky` decorator with pytest marker, by [@mgorny](https://github.com/mgorny)

In this release 4 pull requests were closed.

----

## Version 3.1.0a3 (2025/07/21)

### Pull Requests Merged

* [PR 553](https://github.com/spyder-ide/spyder-kernels/pull/553) - PR: Fix bug when converting JSON to StackSummary, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 552](https://github.com/spyder-ide/spyder-kernels/pull/552) - PR: Drop support for Python 3.8, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 551](https://github.com/spyder-ide/spyder-kernels/pull/551) - PR: Use our own poller to check if the kernel parent is alive, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 550](https://github.com/spyder-ide/spyder-kernels/pull/550) - PR: Add new security policy, by [@CAM-Gerlach](https://github.com/CAM-Gerlach)
* [PR 549](https://github.com/spyder-ide/spyder-kernels/pull/549) - PR: Support Polars dataframes, by [@jitseniesen](https://github.com/jitseniesen)

In this release 5 pull requests were closed.

----

## Version 3.1.0a2 (2025/06/05)

### Pull Requests Merged

* [PR 542](https://github.com/spyder-ide/spyder-kernels/pull/542) - PR: Disable magics and commands to call Python package managers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 541](https://github.com/spyder-ide/spyder-kernels/pull/541) - PR: Support pathlib and None in namespace view, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 540](https://github.com/spyder-ide/spyder-kernels/pull/540) - PR: Support `frozenset` in namespace view, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 535](https://github.com/spyder-ide/spyder-kernels/pull/535) - PR: Display contents of string arrays, by [@jitseniesen](https://github.com/jitseniesen)
* [PR 533](https://github.com/spyder-ide/spyder-kernels/pull/533) - PR: Add pixi related utility functions and env info, by [@dalthviz](https://github.com/dalthviz)

In this release 5 pull requests were closed.

----

## Version 3.1.0a1 (2025/03/13)

### Pull Requests Merged

* [PR 534](https://github.com/spyder-ide/spyder-kernels/pull/534) - PR: Fix some async do completes, by [@Carreau](https://github.com/Carreau)
* [PR 532](https://github.com/spyder-ide/spyder-kernels/pull/532) - PR: Split `test_interrupt` into two tests, by [@Carreau](https://github.com/Carreau)
* [PR 520](https://github.com/spyder-ide/spyder-kernels/pull/520) - Handle async do_complete in the debugger, by [@Carreau](https://github.com/Carreau)
* [PR 519](https://github.com/spyder-ide/spyder-kernels/pull/519) - PR: Clarify test error message, by [@Carreau](https://github.com/Carreau)
* [PR 515](https://github.com/spyder-ide/spyder-kernels/pull/515) - PR: Fix version that will be released from master, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 478](https://github.com/spyder-ide/spyder-kernels/pull/478) - PR: Add feature to prepend/append PYTHONPATH to sys.path, by [@mrclary](https://github.com/mrclary)

In this release 6 pull requests were closed.

----

## Version 3.0.5 (2025/05/21)

### Pull Requests Merged

* [PR 544](https://github.com/spyder-ide/spyder-kernels/pull/544) - PR: Add minimal required version of `traitlets`, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 3.0.4 (2025-05-13)

### Pull Requests Merged

* [PR 538](https://github.com/spyder-ide/spyder-kernels/pull/538) - PR: Use Ubuntu 22.04 for testing on CIs because the 20.04 image was removed, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 536](https://github.com/spyder-ide/spyder-kernels/pull/536) - PR: Preserve case sensitivity of working directory when running files, by [@jsbautista](https://github.com/jsbautista)

In this release 2 pull requests were closed.

----

## Version 3.0.3 (2025-02-05)

### Pull Requests Merged

* [PR 530](https://github.com/spyder-ide/spyder-kernels/pull/530) - PR: Correctly process Pdb commands available in `cmdqueue`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 527](https://github.com/spyder-ide/spyder-kernels/pull/527) - PR: Use an older Ubuntu version on CIs, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 526](https://github.com/spyder-ide/spyder-kernels/pull/526) - PR: Filter frames that come from Spyder-kernels in tracebacks and fix tracebacks in Python 3.8, by [@ccordoba12](https://github.com/ccordoba12)

In this release 3 pull requests were closed.

----

## Version 3.0.2 (2024-12-04)

### Pull Requests Merged

* [PR 524](https://github.com/spyder-ide/spyder-kernels/pull/524) - PR: Improve release instructions for the new backporting workflow, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 521](https://github.com/spyder-ide/spyder-kernels/pull/521) - PR: Add logic to handle traceback color configuration, by [@dalthviz](https://github.com/dalthviz)

In this release 2 pull requests were closed.

----

## Version 3.0.1 (2024-10-29)

### Pull Requests Merged

* [PR 517](https://github.com/spyder-ide/spyder-kernels/pull/517) - PR: Manually register the Matplotlib inline backend in case it hasn't, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 514](https://github.com/spyder-ide/spyder-kernels/pull/514) - PR: Fix development version for the stable branch, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 510](https://github.com/spyder-ide/spyder-kernels/pull/510) - PR: Replace Quansight logo by CZI one in Readme, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 508](https://github.com/spyder-ide/spyder-kernels/pull/508) - PR: Update workflows to run in the `3.x` branch (CI), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 506](https://github.com/spyder-ide/spyder-kernels/pull/506) - PR: Make `glob` and `loc` kwargs of `debug_exec`, by [@impact27](https://github.com/impact27)
* [PR 504](https://github.com/spyder-ide/spyder-kernels/pull/504) - PR: Update workflow actions (CI), by [@mrclary](https://github.com/mrclary)
* [PR 503](https://github.com/spyder-ide/spyder-kernels/pull/503) - PR: Update `load_dicom` to accommodate Pydicom 3.0, by [@mrclary](https://github.com/mrclary)

In this release 7 pull requests were closed.

----

## Version 3.0.0 (2024-08-29)

### New features

* Speed up debugger execution.
* Notify Spyder when Matplotlib backend changes.
* Use control channel for comms instead of a special one.
* Update variable explorer from the kernel.
* Simplify kernel configuration from Spyder.
* Add a `comm_handler` decorator.
* Transform `runfile`, `debugfile` and `runcell` commands to IPython magics.
* Add comm handlers to interrupt executions and enter the debugger after that.
* Publish Pdb stack frames to Spyder.
* Drop support for Python 2 and support Python 3.8+

### Pull Requests Merged

* [PR 500](https://github.com/spyder-ide/spyder-kernels/pull/500) - PR: Restore `TMPDIR` env var if it was available on the Spyder side, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 498](https://github.com/spyder-ide/spyder-kernels/pull/498) - PR: Remove `TMPDIR` env var after initialization, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.

----

## Version 3.0.0b9 (2024-08-21)

### Pull Requests Merged

* [PR 495](https://github.com/spyder-ide/spyder-kernels/pull/495) - PR: Add comm handler to get information about the Python environment associated to the kernel, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 3.0.0b8 (2024-08-08)

### Pull Requests Merged

* [PR 496](https://github.com/spyder-ide/spyder-kernels/pull/496) - PR: Add filtering logic for stream data and constraint `setuptools` version, by [@dalthviz](https://github.com/dalthviz)

In this release 1 pull request was closed.

----

## Version 3.0.0b7 (2024-06-18)

### Issues Closed

* [Issue 491](https://github.com/spyder-ide/spyder-kernels/issues/491) - Debugger misses breakpoint when a file can have several canonic paths ([PR 490](https://github.com/spyder-ide/spyder-kernels/pull/490) by [@impact27](https://github.com/impact27))
* [Issue 468](https://github.com/spyder-ide/spyder-kernels/issues/468) - Debugger not working for environments with different Python versions ([PR 492](https://github.com/spyder-ide/spyder-kernels/pull/492) by [@impact27](https://github.com/impact27))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 492](https://github.com/spyder-ide/spyder-kernels/pull/492) - PR: Enable comms to work across different Python versions, by [@impact27](https://github.com/impact27) ([468](https://github.com/spyder-ide/spyder-kernels/issues/468))
* [PR 490](https://github.com/spyder-ide/spyder-kernels/pull/490) - PR: Use inodes for single canonic file path (Debugger), by [@impact27](https://github.com/impact27) ([491](https://github.com/spyder-ide/spyder-kernels/issues/491))
* [PR 487](https://github.com/spyder-ide/spyder-kernels/pull/487) - PR: Fix issue where Spyder's inline graphics preferences were not applied, by [@mrclary](https://github.com/mrclary)

In this release 3 pull requests were closed.

----

## Version 3.0.0b6 (2024-05-15)

### Issues Closed

* [Issue 457](https://github.com/spyder-ide/spyder-kernels/issues/457) - Detecting the interactive backend started to fail on Mac in master ([PR 486](https://github.com/spyder-ide/spyder-kernels/pull/486) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 486](https://github.com/spyder-ide/spyder-kernels/pull/486) - PR: Run `test_get_interactive_backend` again on Mac, by [@ccordoba12](https://github.com/ccordoba12) ([457](https://github.com/spyder-ide/spyder-kernels/issues/457))
* [PR 485](https://github.com/spyder-ide/spyder-kernels/pull/485) - PR: Fix Matplotlib interactive backend detection, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.

----

## Version 3.0.0b5 (2024-04-23)

### Pull Requests Merged

* [PR 481](https://github.com/spyder-ide/spyder-kernels/pull/481) - PR: Allow magic to edit locals while debugging, by [@impact27](https://github.com/impact27)
* [PR 480](https://github.com/spyder-ide/spyder-kernels/pull/480) - PR: Save faulthandler files under `xdg_data_home/spyder` on Linux, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.

----

## Version 3.0.0b4 (2024-02-08)

### Pull Requests Merged

* [PR 477](https://github.com/spyder-ide/spyder-kernels/pull/477) - PR: Handle new Inline backend options `fontsize` and `bottom`, by [@jitseniesen](https://github.com/jitseniesen)

In this release 1 pull request was closed.

----

## Version 3.0.0b3 (2023-12-18)

### Pull Requests Merged

* [PR 476](https://github.com/spyder-ide/spyder-kernels/pull/476) - PR: Send back pickling error correctly, by [@impact27](https://github.com/impact27)
* [PR 467](https://github.com/spyder-ide/spyder-kernels/pull/467) - PR: Fix index when skipping hidden frames (Debugger), by [@impact27](https://github.com/impact27)
* [PR 466](https://github.com/spyder-ide/spyder-kernels/pull/466) - PR: Simplify kernel configuration, by [@impact27](https://github.com/impact27)

In this release 3 pull requests were closed.

----

## Version 3.0.0b2 (2023-08-22)

### Pull Requests Merged

* [PR 465](https://github.com/spyder-ide/spyder-kernels/pull/465) - Save temporary file in test to temporary location, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 464](https://github.com/spyder-ide/spyder-kernels/pull/464) - Remove locals inspection, by [@impact27](https://github.com/impact27)
* [PR 460](https://github.com/spyder-ide/spyder-kernels/pull/460) - PR: Add a global filter flag to settings, by [@jsbautista](https://github.com/jsbautista)
* [PR 445](https://github.com/spyder-ide/spyder-kernels/pull/445) - PR: Add `exitdb` command and some speed optimizations to the debugger, by [@impact27](https://github.com/impact27)
* [PR 429](https://github.com/spyder-ide/spyder-kernels/pull/429) - PR: Add a comm handler decorator, by [@impact27](https://github.com/impact27)
* [PR 411](https://github.com/spyder-ide/spyder-kernels/pull/411) - PR: Remove `set_debug_state` and `do_where` calls, by [@impact27](https://github.com/impact27)

In this release 6 pull requests were closed.

----

## Version 3.0.0b1 (2023-06-14)

### Issues Closed

* [Issue 425](https://github.com/spyder-ide/spyder-kernels/issues/425) - Possible minor issues related to post mortem debugging ([PR 444](https://github.com/spyder-ide/spyder-kernels/pull/444) by [@impact27](https://github.com/impact27))
* [Issue 340](https://github.com/spyder-ide/spyder-kernels/issues/340) - Drop support for Python 2 ([PR 341](https://github.com/spyder-ide/spyder-kernels/pull/341) by [@impact27](https://github.com/impact27))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 456](https://github.com/spyder-ide/spyder-kernels/pull/456) - PR: Remove unnecessary code for old IPykernel versions in our tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 453](https://github.com/spyder-ide/spyder-kernels/pull/453) - PR: Move code that loads and saves HDF5 and DICOM files from Spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 447](https://github.com/spyder-ide/spyder-kernels/pull/447) - PR: Create magics for run|debug file|cell, by [@impact27](https://github.com/impact27)
* [PR 446](https://github.com/spyder-ide/spyder-kernels/pull/446) - PR: Make call to interrupt children processes work for IPykernel greater than 6.21.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 444](https://github.com/spyder-ide/spyder-kernels/pull/444) - PR: Fix post mortem for debugging, by [@impact27](https://github.com/impact27) ([425](https://github.com/spyder-ide/spyder-kernels/issues/425))
* [PR 443](https://github.com/spyder-ide/spyder-kernels/pull/443) - PR: Fix small typo in Readme, by [@davidbrochart](https://github.com/davidbrochart)
* [PR 437](https://github.com/spyder-ide/spyder-kernels/pull/437) - PR: Remove imports from __future__, by [@oscargus](https://github.com/oscargus)
* [PR 421](https://github.com/spyder-ide/spyder-kernels/pull/421) - PR: Update variable explorer from the kernel, by [@impact27](https://github.com/impact27)
* [PR 417](https://github.com/spyder-ide/spyder-kernels/pull/417) - PR: Fix error in `globalsfilter`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 412](https://github.com/spyder-ide/spyder-kernels/pull/412) - PR: Use temporary file for faulthandler and make sure iopub is open for comms, by [@impact27](https://github.com/impact27)
* [PR 409](https://github.com/spyder-ide/spyder-kernels/pull/409) - PR: Add Python executable as part of kernel info, by [@impact27](https://github.com/impact27)
* [PR 408](https://github.com/spyder-ide/spyder-kernels/pull/408) - PR: Expose package version in SpyderShell, by [@impact27](https://github.com/impact27)
* [PR 403](https://github.com/spyder-ide/spyder-kernels/pull/403) - PR: Make debugger faster by avoiding unnecessary comm messages, by [@impact27](https://github.com/impact27)
* [PR 401](https://github.com/spyder-ide/spyder-kernels/pull/401) - PR: Wait for connection file to be written, by [@impact27](https://github.com/impact27)
* [PR 400](https://github.com/spyder-ide/spyder-kernels/pull/400) - PR: Use `execute_interactive` to print errors during tests, by [@impact27](https://github.com/impact27)
* [PR 397](https://github.com/spyder-ide/spyder-kernels/pull/397) - PR: Remove Python 2 code introduced when merging PR #395, by [@impact27](https://github.com/impact27)
* [PR 396](https://github.com/spyder-ide/spyder-kernels/pull/396) - PR: Add handlers to interrupt executions and enter the debugger after that, by [@impact27](https://github.com/impact27)
* [PR 390](https://github.com/spyder-ide/spyder-kernels/pull/390) - PR: Filter comm socket thread, by [@impact27](https://github.com/impact27)
* [PR 387](https://github.com/spyder-ide/spyder-kernels/pull/387) - PR: Minor changes to finish the migration to Python 3, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 366](https://github.com/spyder-ide/spyder-kernels/pull/366) - PR: Print warning when using `global` in an empty namespace, by [@impact27](https://github.com/impact27)
* [PR 341](https://github.com/spyder-ide/spyder-kernels/pull/341) - PR: Drop support for Python 2, by [@impact27](https://github.com/impact27) ([340](https://github.com/spyder-ide/spyder-kernels/issues/340))
* [PR 339](https://github.com/spyder-ide/spyder-kernels/pull/339) - PR: Use control channel for comms, by [@impact27](https://github.com/impact27)
* [PR 286](https://github.com/spyder-ide/spyder-kernels/pull/286) - PR: Improve and refactor the way we run and debug code, by [@impact27](https://github.com/impact27)
* [PR 257](https://github.com/spyder-ide/spyder-kernels/pull/257) - PR: Notify frontend of Matplotlib backend change, by [@impact27](https://github.com/impact27)
* [PR 171](https://github.com/spyder-ide/spyder-kernels/pull/171) - PR: Publish Pdb stack frames to Spyder, by [@impact27](https://github.com/impact27)

In this release 25 pull requests were closed.

----

## Version 2.5.2 (2024-06-11)

### Pull Requests Merged

* [PR 489](https://github.com/spyder-ide/spyder-kernels/pull/489) - PR: Fix detecting Matplotlib backend for its 3.9.0 version, by [@mrclary](https://github.com/mrclary)

In this release 1 pull request was closed.

----

## Version 2.5.1 (2024-02-28)

### Pull Requests Merged

* [PR 479](https://github.com/spyder-ide/spyder-kernels/pull/479) - PR: Fix hangs with Maplotlib interactive backends, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 2.5.0 (2023-11-06)

### New features

* Add support for chained exceptions to the debugger.
* Improve getting signatures from docstrings.
* Restore compatibility with Python 2.

### Pull Requests Merged

* [PR 475](https://github.com/spyder-ide/spyder-kernels/pull/475) - PR: Skip IPython 8.17.1 in our dependencies for Python 3.9+, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 474](https://github.com/spyder-ide/spyder-kernels/pull/474) - PR: More improvements to getting signatures from text, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 473](https://github.com/spyder-ide/spyder-kernels/pull/473) - PR: Improve getting signatures from docstrings and catch error when trying to get the signature of some objects, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 472](https://github.com/spyder-ide/spyder-kernels/pull/472) - PR: Add support for chained exceptions to the debugger, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 471](https://github.com/spyder-ide/spyder-kernels/pull/471) - PR: Improve the way we depend on IPython and IPykernel per Python version, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 469](https://github.com/spyder-ide/spyder-kernels/pull/469) - PR: Restore compatibility with Python 2, by [@ccordoba12](https://github.com/ccordoba12)

In this release 6 pull requests were closed.

----

## Version 2.4.4 (2023-06-29)

### Issues Closed

* [Issue 454](https://github.com/spyder-ide/spyder-kernels/issues/454) - Codecov Package was Yanked ([PR 455](https://github.com/spyder-ide/spyder-kernels/pull/455) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 461](https://github.com/spyder-ide/spyder-kernels/pull/461) - PR: Increase minimal required version of IPykernel to 6.23.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 459](https://github.com/spyder-ide/spyder-kernels/pull/459) - PR: Skip more buggy IPython versions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 458](https://github.com/spyder-ide/spyder-kernels/pull/458) - PR: Disable IPython's debugger skip functionality by default, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 455](https://github.com/spyder-ide/spyder-kernels/pull/455) - PR: Remove `codecov` package and use Github action to upload coverage instead, by [@ccordoba12](https://github.com/ccordoba12) ([454](https://github.com/spyder-ide/spyder-kernels/issues/454))

In this release 4 pull requests were closed.

----

## Version 2.4.3 (2023-04-02)

### Issues Closed

* [Issue 440](https://github.com/spyder-ide/spyder-kernels/issues/440) - distutils and LooseVersion deprecation ([PR 450](https://github.com/spyder-ide/spyder-kernels/pull/450) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 452](https://github.com/spyder-ide/spyder-kernels/pull/452) - PR: Fix error when executing empty Python script, by [@rear1019](https://github.com/rear1019)
* [PR 450](https://github.com/spyder-ide/spyder-kernels/pull/450) - PR: Remove usage of `distutils.LooseVersion`, by [@ccordoba12](https://github.com/ccordoba12) ([440](https://github.com/spyder-ide/spyder-kernels/issues/440))
* [PR 449](https://github.com/spyder-ide/spyder-kernels/pull/449) - PR: Add support for Jupyter-client 8, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 448](https://github.com/spyder-ide/spyder-kernels/pull/448) - PR: Skip IPython versions that give buggy code completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 442](https://github.com/spyder-ide/spyder-kernels/pull/442) - PR: Add FreeBSD to `test_user_sitepackages_in_pathlist`, by [@rhurlin](https://github.com/rhurlin)
* [PR 434](https://github.com/spyder-ide/spyder-kernels/pull/434) - PR: Use `allow_pickle=True` when loading Numpy arrays, by [@nkleinbaer](https://github.com/nkleinbaer)
* [PR 430](https://github.com/spyder-ide/spyder-kernels/pull/430) - PR: Inform GUI about position of exception in post mortem debugging, by [@rear1019](https://github.com/rear1019)

In this release 7 pull requests were closed.

----

## Version 2.4.2 (2023-01-17)

### Issues Closed

* [Issue 307](https://github.com/spyder-ide/spyder-kernels/issues/307) - formatargspec is deprecated since Python 3.5 ([PR 435](https://github.com/spyder-ide/spyder-kernels/pull/435) by [@juliangilbey](https://github.com/juliangilbey))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 438](https://github.com/spyder-ide/spyder-kernels/pull/438) - PR: Increase minimal required Jupyter-client version to 7.4.9, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 435](https://github.com/spyder-ide/spyder-kernels/pull/435) - PR: Replace deprecated `inspect.formatargspec` call, by [@juliangilbey](https://github.com/juliangilbey) ([307](https://github.com/spyder-ide/spyder-kernels/issues/307))

In this release 2 pull requests were closed.

----

## Version 2.4.1 (2022-12-29)

### Issues Closed

* [Issue 427](https://github.com/spyder-ide/spyder-kernels/issues/427) - Make spyder-kernels compatible with IPython 8 ([PR 419](https://github.com/spyder-ide/spyder-kernels/pull/419) by [@eendebakpt](https://github.com/eendebakpt))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 419](https://github.com/spyder-ide/spyder-kernels/pull/419) - PR: Update IPython requirement to support version 8, by [@eendebakpt](https://github.com/eendebakpt) ([427](https://github.com/spyder-ide/spyder-kernels/issues/427))

In this release 1 pull request was closed.

----

## Version 2.4.0 (2022-11-02)

### New features

* Add support for Python 3.11
* Flush standard streams after execution.

### Pull Requests Merged

* [PR 428](https://github.com/spyder-ide/spyder-kernels/pull/428) - PR: Patch for CVE-2007-4559 Tar directory traversal, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 426](https://github.com/spyder-ide/spyder-kernels/pull/426) - PR: Update ipykernel constraint to >=6.16.1, by [@dalthviz](https://github.com/dalthviz)
* [PR 423](https://github.com/spyder-ide/spyder-kernels/pull/423) - PR: Fix lineno range, by [@impact27](https://github.com/impact27) ([19862](https://github.com/spyder-ide/spyder/issues/19862))
* [PR 422](https://github.com/spyder-ide/spyder-kernels/pull/422) - PR: Make comm lock reentrant, by [@impact27](https://github.com/impact27)
* [PR 420](https://github.com/spyder-ide/spyder-kernels/pull/420) - PR: Only access sys.stdout and sys.stderr once, by [@impact27](https://github.com/impact27)
* [PR 416](https://github.com/spyder-ide/spyder-kernels/pull/416) - PR: Fix some errors when computing the namespace view, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 415](https://github.com/spyder-ide/spyder-kernels/pull/415) - PR: Fix tk eventloop handling when debugging on Windows, by [@dalthviz](https://github.com/dalthviz)
* [PR 413](https://github.com/spyder-ide/spyder-kernels/pull/413) - PR: Flush standard streams after execution, by [@impact27](https://github.com/impact27)

In this release 8 pull requests were closed.

----

## Version 2.3.3 (2022-08-28)

### Issues Closed

* [Issue 405](https://github.com/spyder-ide/spyder-kernels/issues/405) - Python 2 tests are broken in Conda slots ([PR 404](https://github.com/spyder-ide/spyder-kernels/pull/404) by [@impact27](https://github.com/impact27))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 407](https://github.com/spyder-ide/spyder-kernels/pull/407) - PR: Use `get_size` to get variable length for `get_var_properties` to prevent triggering Dask tasks, by [@dalthviz](https://github.com/dalthviz)
* [PR 404](https://github.com/spyder-ide/spyder-kernels/pull/404) - PR: Use debugging namespace when curframe is active, by [@impact27](https://github.com/impact27) ([405](https://github.com/spyder-ide/spyder-kernels/issues/405))

In this release 2 pull requests were closed.

----

## Version 2.3.2 (2022-07-06)

### Issues Closed

* [Issue 394](https://github.com/spyder-ide/spyder-kernels/issues/394) - The variable explorer is broken while debugging ([PR 395](https://github.com/spyder-ide/spyder-kernels/pull/395) by [@impact27](https://github.com/impact27))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 399](https://github.com/spyder-ide/spyder-kernels/pull/399) - PR: Increase minimal required version of jupyter_client to 7.3.4, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 398](https://github.com/spyder-ide/spyder-kernels/pull/398) - PR: Fix module namespace, by [@impact27](https://github.com/impact27)
* [PR 395](https://github.com/spyder-ide/spyder-kernels/pull/395) - PR: Fix running namespace and improve eventloop integration while debugging, by [@impact27](https://github.com/impact27) ([394](https://github.com/spyder-ide/spyder-kernels/issues/394))
* [PR 389](https://github.com/spyder-ide/spyder-kernels/pull/389) - PR: Fix debug filename path for remote debugging, by [@impact27](https://github.com/impact27) ([18330](https://github.com/spyder-ide/spyder/issues/18330))
* [PR 388](https://github.com/spyder-ide/spyder-kernels/pull/388) - PR: Fix getting args from functions or methods, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 386](https://github.com/spyder-ide/spyder-kernels/pull/386) - PR: Fix flaky test, by [@impact27](https://github.com/impact27)
* [PR 381](https://github.com/spyder-ide/spyder-kernels/pull/381) - PR: Eliminate unnecessary updates of the Variable Explorer while debugging, by [@rear1019](https://github.com/rear1019)
* [PR 378](https://github.com/spyder-ide/spyder-kernels/pull/378) - PR: Append paths that come from Spyder's Python path manager to the end of `sys.path`, by [@mrclary](https://github.com/mrclary)

In this release 8 pull requests were closed.

----

## Version 2.3.1 (2022-05-21)

### Pull Requests Merged

* [PR 385](https://github.com/spyder-ide/spyder-kernels/pull/385) - PR: Add an upper constraint to our most important dependencies, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 384](https://github.com/spyder-ide/spyder-kernels/pull/384) - PR: Prevent an error in Python 2 with our tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 382](https://github.com/spyder-ide/spyder-kernels/pull/382) - PR: Increase minimal required version of jupyter_client to 7.3.1, by [@ccordoba12](https://github.com/ccordoba12)

In this release 3 pull requests were closed.

---

## Version 2.3.0 (2022-03-30)

### New features

* Add new handler to detect the current Matplotlib interactive backend.
* Print last line of cells and Pdb code.

### Issues Closed

* [Issue 371](https://github.com/spyder-ide/spyder-kernels/issues/371) - Can't debug comprehensions ([PR 370](https://github.com/spyder-ide/spyder-kernels/pull/370) by [@impact27](https://github.com/impact27))
* [Issue 344](https://github.com/spyder-ide/spyder-kernels/issues/344) - Drop support for Python 3.6 by requiring a more recent IPython version ([PR 373](https://github.com/spyder-ide/spyder-kernels/pull/373) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 330](https://github.com/spyder-ide/spyder-kernels/issues/330) - spydercustomize in debug stack ([PR 355](https://github.com/spyder-ide/spyder-kernels/pull/355) by [@impact27](https://github.com/impact27))
* [Issue 320](https://github.com/spyder-ide/spyder-kernels/issues/320) - The length of the "excluded_names" list increases. ([PR 372](https://github.com/spyder-ide/spyder-kernels/pull/372) by [@impact27](https://github.com/impact27))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 379](https://github.com/spyder-ide/spyder-kernels/pull/379) - PR: Increase minimal required version of ipykernel to 6.9.2, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 377](https://github.com/spyder-ide/spyder-kernels/pull/377) - PR: Handle getting dasks objects size, by [@dalthviz](https://github.com/dalthviz)
* [PR 376](https://github.com/spyder-ide/spyder-kernels/pull/376) - PR: Add new handler to detect the current Matplotlib interactive backend, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 375](https://github.com/spyder-ide/spyder-kernels/pull/375) - PR: Remove support for outdated and unused Matplotlib backends, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 374](https://github.com/spyder-ide/spyder-kernels/pull/374) - PR: Catch FileNotFoundError when trying to get file code from the frontend, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 373](https://github.com/spyder-ide/spyder-kernels/pull/373) - PR: Increase minimal required IPython version to 7.31.1, by [@ccordoba12](https://github.com/ccordoba12) ([344](https://github.com/spyder-ide/spyder-kernels/issues/344))
* [PR 372](https://github.com/spyder-ide/spyder-kernels/pull/372) - PR: Avoid modifying the namespace view settings by reference, by [@impact27](https://github.com/impact27) ([320](https://github.com/spyder-ide/spyder-kernels/issues/320))
* [PR 370](https://github.com/spyder-ide/spyder-kernels/pull/370) - PR: Fix issues when debugging comprehensions, by [@impact27](https://github.com/impact27) ([371](https://github.com/spyder-ide/spyder-kernels/issues/371))
* [PR 369](https://github.com/spyder-ide/spyder-kernels/pull/369) - PR: Leave unsaved files in linecache, by [@impact27](https://github.com/impact27)
* [PR 355](https://github.com/spyder-ide/spyder-kernels/pull/355) - PR: Print last line of Pdb code and some debugger fixes, by [@impact27](https://github.com/impact27) ([330](https://github.com/spyder-ide/spyder-kernels/issues/330))

In this release 10 pull requests were closed.

----

## Version 2.2.1 (2022-01-13)

### Issues Closed

* [Issue 365](https://github.com/spyder-ide/spyder-kernels/issues/365) - `IOStream.flush timed out` message shown after every evaluation ([PR 367](https://github.com/spyder-ide/spyder-kernels/pull/367) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 347](https://github.com/spyder-ide/spyder-kernels/issues/347) - Issues handling Matplotlib backend settings ([PR 368](https://github.com/spyder-ide/spyder-kernels/pull/368) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 345](https://github.com/spyder-ide/spyder-kernels/issues/345) - Namespace issues ([PR 346](https://github.com/spyder-ide/spyder-kernels/pull/346) by [@impact27](https://github.com/impact27))
* [Issue 343](https://github.com/spyder-ide/spyder-kernels/issues/343) - Shapely 1.8 and get_namespace_view spyder call raising deprecation warning ([PR 350](https://github.com/spyder-ide/spyder-kernels/pull/350) by [@ccordoba12](https://github.com/ccordoba12))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 368](https://github.com/spyder-ide/spyder-kernels/pull/368) - PR: Improve error message when setting a Matplotlib backend whose module is not present, by [@ccordoba12](https://github.com/ccordoba12) ([347](https://github.com/spyder-ide/spyder-kernels/issues/347))
* [PR 367](https://github.com/spyder-ide/spyder-kernels/pull/367) - PR: Filter another benign message coming from comm handlers, by [@ccordoba12](https://github.com/ccordoba12) ([365](https://github.com/spyder-ide/spyder-kernels/issues/365))
* [PR 364](https://github.com/spyder-ide/spyder-kernels/pull/364) - PR: Catch error when validating if an object is defined in the namespace, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 363](https://github.com/spyder-ide/spyder-kernels/pull/363) - PR: Fix error when running multiprocessing code that contains classes, by [@impact27](https://github.com/impact27)
* [PR 362](https://github.com/spyder-ide/spyder-kernels/pull/362) - PR: Catch KeyError when closing comm, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 361](https://github.com/spyder-ide/spyder-kernels/pull/361) - PR: Increase minimal required version of pyzmq for Python 3, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 360](https://github.com/spyder-ide/spyder-kernels/pull/360) - PR: Increase minimal required version of ipykernel to 6.6.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 357](https://github.com/spyder-ide/spyder-kernels/pull/357) - PR: Require jupyter-client 7.1.0 to fix issues on Windows, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 356](https://github.com/spyder-ide/spyder-kernels/pull/356) - PR: Increase minimal required version of jupyter-client to 7.0+ for Python 3, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 354](https://github.com/spyder-ide/spyder-kernels/pull/354) - PR: Constraint IPython version to avoid issues when its next major version is released, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 353](https://github.com/spyder-ide/spyder-kernels/pull/353) - PR: Implement a less hacky solution to fix namespace issues, by [@impact27](https://github.com/impact27)
* [PR 351](https://github.com/spyder-ide/spyder-kernels/pull/351) - PR: More namespace fixes, by [@impact27](https://github.com/impact27)
* [PR 350](https://github.com/spyder-ide/spyder-kernels/pull/350) - PR: Don't print DeprecationWarning's that come from comm handlers, by [@ccordoba12](https://github.com/ccordoba12) ([343](https://github.com/spyder-ide/spyder-kernels/issues/343))
* [PR 349](https://github.com/spyder-ide/spyder-kernels/pull/349) - PR: Update Quansight logo in Readme, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 346](https://github.com/spyder-ide/spyder-kernels/pull/346) - PR: Fix some namespace issues, by [@impact27](https://github.com/impact27) ([345](https://github.com/spyder-ide/spyder-kernels/issues/345))
* [PR 338](https://github.com/spyder-ide/spyder-kernels/pull/338) - PR: Fix misplaced section in changelog, by [@ccordoba12](https://github.com/ccordoba12)

In this release 16 pull requests were closed.

----

## Version 2.2.0 (2021-11-22)

### New features

* Add the ability to capture segfaults and flush standard streams from
  Spyder.
* Add support for jupyter_client 7.

### Issues Closed

* [Issue 326](https://github.com/spyder-ide/spyder-kernels/issues/326) - Setting variables in recursive debugging namespaces is broken ([PR 327](https://github.com/spyder-ide/spyder-kernels/pull/327) by [@impact27](https://github.com/impact27))
* [Issue 325](https://github.com/spyder-ide/spyder-kernels/issues/325) - %timeit has issues with the namespace ([PR 327](https://github.com/spyder-ide/spyder-kernels/pull/327) by [@impact27](https://github.com/impact27))
* [Issue 316](https://github.com/spyder-ide/spyder-kernels/issues/316) - Disable capture_fd_output in IPykernel 6+ in favor of Wurlitzer ([PR 337](https://github.com/spyder-ide/spyder-kernels/pull/337) by [@ccordoba12](https://github.com/ccordoba12))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 337](https://github.com/spyder-ide/spyder-kernels/pull/337) - PR: Disable the new mechanism to forward low-level output in IPykernel 6, by [@ccordoba12](https://github.com/ccordoba12) ([316](https://github.com/spyder-ide/spyder-kernels/issues/316))
* [PR 336](https://github.com/spyder-ide/spyder-kernels/pull/336) - PR: Don't show traceback when exiting debugger after breakpoint call, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 335](https://github.com/spyder-ide/spyder-kernels/pull/335) - PR: Remove locals from exec in comprehensions (debugger), by [@impact27](https://github.com/impact27)
* [PR 334](https://github.com/spyder-ide/spyder-kernels/pull/334) - PR: Fix missing stderr when the kernel crashes, by [@impact27](https://github.com/impact27)
* [PR 333](https://github.com/spyder-ide/spyder-kernels/pull/333) - PR: Add cast for shape tuple subclass instances when getting values size, by [@dalthviz](https://github.com/dalthviz)
* [PR 332](https://github.com/spyder-ide/spyder-kernels/pull/332) - PR: Remove usage of f_locals.get, by [@impact27](https://github.com/impact27)
* [PR 328](https://github.com/spyder-ide/spyder-kernels/pull/328) - PR: Remove upper constraint on jupyter_client, by [@bnavigator](https://github.com/bnavigator)
* [PR 327](https://github.com/spyder-ide/spyder-kernels/pull/327) - PR: Fix timeit in Pdb and other namespace issues, by [@impact27](https://github.com/impact27) ([326](https://github.com/spyder-ide/spyder-kernels/issues/326), [325](https://github.com/spyder-ide/spyder-kernels/issues/325))
* [PR 317](https://github.com/spyder-ide/spyder-kernels/pull/317) - PR: Run asyncio and normal handlers, by [@impact27](https://github.com/impact27) ([16183](https://github.com/spyder-ide/spyder/issues/16183))
* [PR 254](https://github.com/spyder-ide/spyder-kernels/pull/254) - PR: Enable faulthandler from the frontend, by [@impact27](https://github.com/impact27)

In this release 10 pull requests were closed.

----

## Version 2.1.3 (2021-10-02)

### Pull Requests Merged

* [PR 319](https://github.com/spyder-ide/spyder-kernels/pull/319) - PR: Fix errors when setting or getting the Matplotlib backend, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 2.1.2 (2021-09-28)

### Pull Requests Merged

* [PR 323](https://github.com/spyder-ide/spyder-kernels/pull/323) - PR: Add `ipython_genutils` dependency for testing, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 322](https://github.com/spyder-ide/spyder-kernels/pull/322) - PR: Prevent other libraries to change the breakpoint builtin, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.

----

## Version 2.1.1 (2021-09-01)

### Pull Requests Merged

* [PR 318](https://github.com/spyder-ide/spyder-kernels/pull/318) - PR: Avoid runfile to be shadowed by other packages, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 314](https://github.com/spyder-ide/spyder-kernels/pull/314) - PR: Remove dependency on ipython_genutils, by [@Carreau](https://github.com/Carreau)
* [PR 313](https://github.com/spyder-ide/spyder-kernels/pull/313) - PR: Memoize results of is_module_installed, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 309](https://github.com/spyder-ide/spyder-kernels/pull/309) - PR: Restrict jupyter-client to be less than version 7, by [@ccordoba12](https://github.com/ccordoba12)

In this release 4 pull requests were closed.

----

## Version 2.1.0 (2021-07-31)

### New features

* Add support for the Rich and Colorama libraries.
* Load big modules (e.g. Numpy, Pandas and Scipy) only until it's really
  necessary.

### Issues Closed

* [Issue 302](https://github.com/spyder-ide/spyder-kernels/issues/302) - Add option to use custom Outstream in kernel app ([PR 305](https://github.com/spyder-ide/spyder-kernels/pull/305) by [@eendebakpt](https://github.com/eendebakpt))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 306](https://github.com/spyder-ide/spyder-kernels/pull/306) - PR: Patch os.get_terminal_size to return a terminal size, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 305](https://github.com/spyder-ide/spyder-kernels/pull/305) - PR: Use an outstream with isatty() equal to True, by [@eendebakpt](https://github.com/eendebakpt) ([302](https://github.com/spyder-ide/spyder-kernels/issues/302))
* [PR 303](https://github.com/spyder-ide/spyder-kernels/pull/303) - PR: Remove an unnecessary check when getting values in Pdb, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 300](https://github.com/spyder-ide/spyder-kernels/pull/300) - PR: Fix %debug magic, by [@impact27](https://github.com/impact27)
* [PR 259](https://github.com/spyder-ide/spyder-kernels/pull/259) - PR: Don't import big modules (Numpy, Pandas) until it's really necessary, by [@ccordoba12](https://github.com/ccordoba12)

In this release 5 pull requests were closed.

----

## Version 2.0.5 (2021-07-03)

### Pull Requests Merged

* [PR 292](https://github.com/spyder-ide/spyder-kernels/pull/292) - PR: Add support for ipykernel 6, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 2.0.4 (2021-06-10)

### Issues Closed

* [Issue 288](https://github.com/spyder-ide/spyder-kernels/issues/288) - Support decorator >= 5 ([PR 301](https://github.com/spyder-ide/spyder-kernels/pull/301) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 301](https://github.com/spyder-ide/spyder-kernels/pull/301) - PR: Remove pin on decorator because the Cython magic is working fine again, by [@ccordoba12](https://github.com/ccordoba12) ([288](https://github.com/spyder-ide/spyder-kernels/issues/288))
* [PR 299](https://github.com/spyder-ide/spyder-kernels/pull/299) - PR: Clear argv before adding the exec lines that come from Spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 298](https://github.com/spyder-ide/spyder-kernels/pull/298) - PR: Use backslash instead of slash for UMR path regex detection, by [@dalthviz](https://github.com/dalthviz)
* [PR 297](https://github.com/spyder-ide/spyder-kernels/pull/297) - PR: Don't report skipped frames for IPython 7.24+ (Debugger), by [@ccordoba12](https://github.com/ccordoba12)
* [PR 296](https://github.com/spyder-ide/spyder-kernels/pull/296) - PR: Redefine comm_manager method to avoid showing warning, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 295](https://github.com/spyder-ide/spyder-kernels/pull/295) - PR: Fix recursive debugger, by [@impact27](https://github.com/impact27)
* [PR 293](https://github.com/spyder-ide/spyder-kernels/pull/293) - PR: Install click 7 to run our tests in Python 2, by [@ccordoba12](https://github.com/ccordoba12)

In this release 7 pull requests were closed.

----

## Version 2.0.3 (2021-05-15)

### Pull Requests Merged

* [PR 291](https://github.com/spyder-ide/spyder-kernels/pull/291) - PR: Pass adding breakpoint on ValueError, by [@impact27](https://github.com/impact27)

In this release 1 pull request was closed.

----

## Version 2.0.2 (2021-05-02)

### Pull Requests Merged

* [PR 289](https://github.com/spyder-ide/spyder-kernels/pull/289) - PR: Fix setting tight layout in inline figures, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 287](https://github.com/spyder-ide/spyder-kernels/pull/287) - PR: Close comm on shutdown, by [@impact27](https://github.com/impact27)
* [PR 282](https://github.com/spyder-ide/spyder-kernels/pull/282) - PR: Fix numpy.complex deprecation warning in tests, by [@ArchangeGabriel](https://github.com/ArchangeGabriel)

In this release 3 pull requests were closed.

----

## Version 2.0.1 (2021-04-02)

* This release also contains all fixes present in version 1.10.3

----

## Version 2.0.0 (2021-04-01)

### New features

* Color handling in namespace view was moved to Spyder.

### Pull Requests Merged

* [PR 284](https://github.com/spyder-ide/spyder-kernels/pull/284) - PR: Remove handling of colors for object types, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 279](https://github.com/spyder-ide/spyder-kernels/pull/279) - PR: Add Python types to namespace view, by [@ccordoba12](https://github.com/ccordoba12)

In this release 2 pull requests were closed.

----

## Version 1.10.3 (2021-04-02)

### Pull Requests Merged

* [PR 285](https://github.com/spyder-ide/spyder-kernels/pull/285) - PR: Add a new dependency on decorator to fix the Cython magic, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 1.10.2 (2021-02-21)

### Pull Requests Merged

* [PR 278](https://github.com/spyder-ide/spyder-kernels/pull/278) - PR: Warn when comm call creates text output, by [@impact27](https://github.com/impact27)
* [PR 277](https://github.com/spyder-ide/spyder-kernels/pull/277) - PR: Increase minimal required version of ipykernel, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 275](https://github.com/spyder-ide/spyder-kernels/pull/275) - PR: Better test for non-interactive context, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 272](https://github.com/spyder-ide/spyder-kernels/pull/272) - PR: Fix assignment detection in exclamation mark mode (Pdb), by [@impact27](https://github.com/impact27)
* [PR 271](https://github.com/spyder-ide/spyder-kernels/pull/271) - PR: Fix recursive debugger, by [@impact27](https://github.com/impact27)

In this release 5 pull requests were closed.

----

## Version 1.10.1 (2020-12-18)

### Issues Closed

* [Issue 269](https://github.com/spyder-ide/spyder-kernels/issues/269) - Mark Windows intaller pkgs path as a library to prevent reloading modules  ([PR 270](https://github.com/spyder-ide/spyder-kernels/pull/270) by [@dalthviz](https://github.com/dalthviz))
* [Issue 256](https://github.com/spyder-ide/spyder-kernels/issues/256) - ImportError: cannot import name 'leading_empty_lines' ([PR 264](https://github.com/spyder-ide/spyder-kernels/pull/264) by [@ccordoba12](https://github.com/ccordoba12))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 270](https://github.com/spyder-ide/spyder-kernels/pull/270) - PR: Treat 'pkgs' path as a library, by [@dalthviz](https://github.com/dalthviz) ([269](https://github.com/spyder-ide/spyder-kernels/issues/269))
* [PR 267](https://github.com/spyder-ide/spyder-kernels/pull/267) - PR: Remove handlers that require direct code execution, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 266](https://github.com/spyder-ide/spyder-kernels/pull/266) - PR: Add exception for quit and exit in SpyderPdb, by [@impact27](https://github.com/impact27)
* [PR 265](https://github.com/spyder-ide/spyder-kernels/pull/265) - PR: Add space after dot in a message, by [@impact27](https://github.com/impact27)
* [PR 264](https://github.com/spyder-ide/spyder-kernels/pull/264) - PR: Add explicit requirement on IPython and require version 7.6.0+, by [@ccordoba12](https://github.com/ccordoba12) ([256](https://github.com/spyder-ide/spyder-kernels/issues/256))
* [PR 263](https://github.com/spyder-ide/spyder-kernels/pull/263) - PR: Add extra validation to is_module_installed, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 262](https://github.com/spyder-ide/spyder-kernels/pull/262) - PR: Avoid infinite hang when quitting external kernels, by [@impact27](https://github.com/impact27)
* [PR 261](https://github.com/spyder-ide/spyder-kernels/pull/261) - PR: Fix get_cwd permission errors, by [@steff456](https://github.com/steff456)
* [PR 260](https://github.com/spyder-ide/spyder-kernels/pull/260) - PR: Fix Github actions, by [@ccordoba12](https://github.com/ccordoba12)

In this release 9 pull requests were closed.

----

## Version 1.10.0 (2020-11-08)

### New features

* Use '!' to prefix Pdb commands.
* Show length of all iterables.

### Issues Closed

* [Issue 247](https://github.com/spyder-ide/spyder-kernels/issues/247) - Remove from warning that future versions of Spyder will give an error when using non-Python syntax ([PR 243](https://github.com/spyder-ide/spyder-kernels/pull/243) by [@impact27](https://github.com/impact27))
* [Issue 245](https://github.com/spyder-ide/spyder-kernels/issues/245) - Display size of string in variable editor

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 255](https://github.com/spyder-ide/spyder-kernels/pull/255) - PR: Fix warning for '!' Pdb option, by [@impact27](https://github.com/impact27)
* [PR 253](https://github.com/spyder-ide/spyder-kernels/pull/253) - PR: Extend sys.path with paths that come from Spyder, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 252](https://github.com/spyder-ide/spyder-kernels/pull/252) - PR: Use frame locals when evaluating code in Pdb, by [@impact27](https://github.com/impact27)
* [PR 251](https://github.com/spyder-ide/spyder-kernels/pull/251) - PR: Catch errors when trying to get the len of an object, by [@impact27](https://github.com/impact27)
* [PR 250](https://github.com/spyder-ide/spyder-kernels/pull/250) - PR: Show size of objects correctly, if they implement len(), by [@skjerns](https://github.com/skjerns)
* [PR 246](https://github.com/spyder-ide/spyder-kernels/pull/246) - PR: Allow sorting with custom sorting key, by [@skjerns](https://github.com/skjerns)
* [PR 244](https://github.com/spyder-ide/spyder-kernels/pull/244) - PR: Set multiprocessing ORIGINAL_DIR at startup, by [@impact27](https://github.com/impact27) ([13632](https://github.com/spyder-ide/spyder/issues/13632))
* [PR 243](https://github.com/spyder-ide/spyder-kernels/pull/243) - PR: Allow leading indents in cells, by [@impact27](https://github.com/impact27) ([247](https://github.com/spyder-ide/spyder-kernels/issues/247))
* [PR 242](https://github.com/spyder-ide/spyder-kernels/pull/242) - PR: Display error if required, by [@impact27](https://github.com/impact27)
* [PR 240](https://github.com/spyder-ide/spyder-kernels/pull/240) - PR: Hide runcell and runfile frames using a new IPython feature, by [@impact27](https://github.com/impact27)
* [PR 239](https://github.com/spyder-ide/spyder-kernels/pull/239) - PR: Improve Pdb input handling, by [@impact27](https://github.com/impact27)
* [PR 232](https://github.com/spyder-ide/spyder-kernels/pull/232) - PR: Make do_where go to the current file, by [@impact27](https://github.com/impact27)
* [PR 223](https://github.com/spyder-ide/spyder-kernels/pull/223) - PR: Add methods to handle IPython console config on the fly, by [@dalthviz](https://github.com/dalthviz)
* [PR 214](https://github.com/spyder-ide/spyder-kernels/pull/214) - PR: Use '!' for Pdb commands, by [@impact27](https://github.com/impact27)

In this release 14 pull requests were closed.

----

## Version 1.9.4 (2020-09-01)

### Pull Requests Merged

* [PR 238](https://github.com/spyder-ide/spyder-kernels/pull/238) - PR: Set get_local_scope correctly while debugging, by [@impact27](https://github.com/impact27)
* [PR 235](https://github.com/spyder-ide/spyder-kernels/pull/235) - PR: Set debug state correctly on exception, by [@impact27](https://github.com/impact27)
* [PR 233](https://github.com/spyder-ide/spyder-kernels/pull/233) - PR: Don't save file in runcell, by [@impact27](https://github.com/impact27)

In this release 3 pull requests were closed.

----

## Version 1.9.3 (2020-07-24)

### Issues Closed

* [Issue 236](https://github.com/spyder-ide/spyder-kernels/issues/236) - test_dask_multiprocessing fails with pip packages ([PR 237](https://github.com/spyder-ide/spyder-kernels/pull/237) by [@bnavigator](https://github.com/bnavigator))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 237](https://github.com/spyder-ide/spyder-kernels/pull/237) - PR: Require dask[distributed] for tests, by [@bnavigator](https://github.com/bnavigator) ([236](https://github.com/spyder-ide/spyder-kernels/issues/236))

In this release 1 pull request was closed.

----

## Version 1.9.2 (2020-07-10)

### Pull Requests Merged

* [PR 234](https://github.com/spyder-ide/spyder-kernels/pull/234) - PR: Fix a problem caused by ipykernel 5.3.1, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 231](https://github.com/spyder-ide/spyder-kernels/pull/231) - PR: Send comm config on every message, by [@impact27](https://github.com/impact27)
* [PR 230](https://github.com/spyder-ide/spyder-kernels/pull/230) - PR: Send comm config before any wait just to be sure, by [@impact27](https://github.com/impact27)
* [PR 229](https://github.com/spyder-ide/spyder-kernels/pull/229) - PR: Add warning on console if file is not saved, by [@impact27](https://github.com/impact27)
* [PR 228](https://github.com/spyder-ide/spyder-kernels/pull/228) - PR: Fix post_mortem interaction, by [@dalthviz](https://github.com/dalthviz)
* [PR 227](https://github.com/spyder-ide/spyder-kernels/pull/227) - PR: Create a constant for numeric Numpy types, by [@dalthviz](https://github.com/dalthviz)
* [PR 226](https://github.com/spyder-ide/spyder-kernels/pull/226) - PR: Backport PR 225, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 222](https://github.com/spyder-ide/spyder-kernels/pull/222) - PR: Remove the current working directory from sys.path for Python 3.7+, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 220](https://github.com/spyder-ide/spyder-kernels/pull/220) - PR: Make multithreading patch work for all OSes in Python 3, by [@steff456](https://github.com/steff456) ([12465](https://github.com/spyder-ide/spyder/issues/12465))

In this release 9 pull requests were closed.

----

## Version 1.9.1 (2020-05-06)

### Issues Closed

* [Issue 217](https://github.com/spyder-ide/spyder-kernels/issues/217) - Maximum recursion depth exceeded ([PR 218](https://github.com/spyder-ide/spyder-kernels/pull/218) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 219](https://github.com/spyder-ide/spyder-kernels/pull/219) - PR: Check that startup file exists, by [@impact27](https://github.com/impact27) ([12442](https://github.com/spyder-ide/spyder/issues/12442))
* [PR 218](https://github.com/spyder-ide/spyder-kernels/pull/218) - PR: Avoid an error when computing the shape of Pandas objects, by [@ccordoba12](https://github.com/ccordoba12) ([217](https://github.com/spyder-ide/spyder-kernels/issues/217))
* [PR 215](https://github.com/spyder-ide/spyder-kernels/pull/215) - PR: Fix post mortem functionality, by [@impact27](https://github.com/impact27)
* [PR 212](https://github.com/spyder-ide/spyder-kernels/pull/212) - PR: Set namespace correctly when running in new namespace, by [@impact27](https://github.com/impact27)
* [PR 211](https://github.com/spyder-ide/spyder-kernels/pull/211) - PR: Use Exception instead of ImportError in is_special_kernel_valid, by [@ccordoba12](https://github.com/ccordoba12)

In this release 5 pull requests were closed.

----

## Version 1.9.0 (2020-03-14)

### New features

* Allow IPython magics in code again.
* Allow PyQt applications to be run multiple times.
* Remove `__file__` after running a file.

### Pull Requests Merged

* [PR 209](https://github.com/spyder-ide/spyder-kernels/pull/209) - PR: Improve message about using invalid syntax in cells and files, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 208](https://github.com/spyder-ide/spyder-kernels/pull/208) - PR: Add flag to override data and handle NpzFile instances, by [@dalthviz](https://github.com/dalthviz)
* [PR 206](https://github.com/spyder-ide/spyder-kernels/pull/206) - PR: Move CI to github actions on branch 1.x, by [@goanpeca](https://github.com/goanpeca)
* [PR 204](https://github.com/spyder-ide/spyder-kernels/pull/204) - PR: Remove load_exception in CommBase, by [@impact27](https://github.com/impact27)
* [PR 200](https://github.com/spyder-ide/spyder-kernels/pull/200) - PR: Fix %varexp namespace, by [@impact27](https://github.com/impact27) ([6695](https://github.com/spyder-ide/spyder/issues/6695))
* [PR 199](https://github.com/spyder-ide/spyder-kernels/pull/199) - PR: Prevent completion from changing local objects while debugging, by [@impact27](https://github.com/impact27)
* [PR 198](https://github.com/spyder-ide/spyder-kernels/pull/198) - PR: Add method to check dependencies for special consoles, by [@dalthviz](https://github.com/dalthviz)
* [PR 195](https://github.com/spyder-ide/spyder-kernels/pull/195) - PR: Give access to the running namespace when refreshing variables, by [@impact27](https://github.com/impact27)
* [PR 193](https://github.com/spyder-ide/spyder-kernels/pull/193) - PR: Update test to work with IPython 7.10+, by [@impact27](https://github.com/impact27)
* [PR 192](https://github.com/spyder-ide/spyder-kernels/pull/192) - PR: Resend comm configuration on timeout, by [@impact27](https://github.com/impact27)
* [PR 190](https://github.com/spyder-ide/spyder-kernels/pull/190) - PR: Allow IPython magics in code again, by [@impact27](https://github.com/impact27) ([11023](https://github.com/spyder-ide/spyder/issues/11023))
* [PR 189](https://github.com/spyder-ide/spyder-kernels/pull/189) - PR: Patch PyQt to save created QApplication instances, by [@impact27](https://github.com/impact27) ([2970](https://github.com/spyder-ide/spyder/issues/2970))
* [PR 187](https://github.com/spyder-ide/spyder-kernels/pull/187) - PR: Remove `__file__` after running script, by [@impact27](https://github.com/impact27) ([1918](https://github.com/spyder-ide/spyder/issues/1918))

In this release 13 pull requests were closed.

----

## Version 1.8.1 (2019-12-05)


### Pull Requests Merged

* [PR 185](https://github.com/spyder-ide/spyder-kernels/pull/185) - PR: Process first frame in Pdb

In this release 1 pull request was closed.

----

## Version 1.8.0 (2019-11-18)

### New features

* Add an option to exclude callables and modules in namespace view.
* Add methods to update `sys.path` from Spyder.
* Add an option to execute IPython events in Pdb.

### Pull Requests Merged

* [PR 183](https://github.com/spyder-ide/spyder-kernels/pull/183) - PR: Add an option to namespace view settings to exclude callables and modules
* [PR 182](https://github.com/spyder-ide/spyder-kernels/pull/182) - PR: Use IPython completer for Pdb
* [PR 181](https://github.com/spyder-ide/spyder-kernels/pull/181) - PR: Add path update methods
* [PR 180](https://github.com/spyder-ide/spyder-kernels/pull/180) - PR: Cleanup spydercustomize
* [PR 179](https://github.com/spyder-ide/spyder-kernels/pull/179) - PR: Use a timeout in CommBase if a call passes one different from None
* [PR 178](https://github.com/spyder-ide/spyder-kernels/pull/178) - PR: Correctly set namespace while debugging
* [PR 175](https://github.com/spyder-ide/spyder-kernels/pull/175) - PR: Add an option to execute IPython events in Pdb
* [PR 174](https://github.com/spyder-ide/spyder-kernels/pull/174) - PR: Prevent pdb syntax error from blocking the console ([10588](https://github.com/spyder-ide/spyder/issues/10588))

In this release 8 pull requests were closed.

----

## Version 1.7.0 (2019-11-02)

### New features

* Create a new ZMQ socket for comms.
* Allow different frontends to have different pickle
  protocols.
* Add a way to ignore installed Python libraries while
  debugging

### Pull Requests Merged

* [PR 177](https://github.com/spyder-ide/spyder-kernels/pull/177) - PR: Update ipykernel required version ([2902](https://github.com/spyder-ide/spyder/issues/2902))
* [PR 176](https://github.com/spyder-ide/spyder-kernels/pull/176) - PR: Improve displayed type and value for generic objects
* [PR 169](https://github.com/spyder-ide/spyder-kernels/pull/169) - PR: Create a Comm socket
* [PR 168](https://github.com/spyder-ide/spyder-kernels/pull/168) - PR: Require more recent version of jupyter-client
* [PR 167](https://github.com/spyder-ide/spyder-kernels/pull/167) - PR: Don't demand that a file exists in Pdb
* [PR 166](https://github.com/spyder-ide/spyder-kernels/pull/166) - PR: Allow different frontends to have different pickle protocols
* [PR 152](https://github.com/spyder-ide/spyder-kernels/pull/152) - PR: Add a way to ignore installed Python libraries while debugging

In this release 7 pull requests were closed.

----

## Version 1.6.0 (2019-10-16)

### New features

* Allow IPython magics in Pdb.
* Allow Pdb to run multiline statments.
* Make `runfile` to retrieve code from Spyder.
* Add code completion to Pdb.

### Issues Closed

* [Issue 139](https://github.com/spyder-ide/spyder-kernels/issues/139) - Regression: runfile doesn't execute ipython magic ([PR 143](https://github.com/spyder-ide/spyder-kernels/pull/143))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 163](https://github.com/spyder-ide/spyder-kernels/pull/163) - PR: Fix tests that use setup_kernel
* [PR 162](https://github.com/spyder-ide/spyder-kernels/pull/162) - PR: Improve Pdb sigint handler
* [PR 161](https://github.com/spyder-ide/spyder-kernels/pull/161) - PR: Fix post-mortem debugging
* [PR 157](https://github.com/spyder-ide/spyder-kernels/pull/157) - PR: Fix breakpoint update ([10290](https://github.com/spyder-ide/spyder/issues/10290))
* [PR 154](https://github.com/spyder-ide/spyder-kernels/pull/154) - PR: Allow IPython magics in Pdb
* [PR 153](https://github.com/spyder-ide/spyder-kernels/pull/153) - PR: Add a setting to disable printing the stack on every Pdb command
* [PR 151](https://github.com/spyder-ide/spyder-kernels/pull/151) - PR: Remove Pdb Monkeypatching
* [PR 148](https://github.com/spyder-ide/spyder-kernels/pull/148) - PR: Allow Pdb to run multiline statments
* [PR 143](https://github.com/spyder-ide/spyder-kernels/pull/143) - PR: Make runfile to retrieve code from the Spyder editor and add it to linecache ([1643](https://github.com/spyder-ide/spyder/issues/1643), [139](https://github.com/spyder-ide/spyder-kernels/issues/139))
* [PR 133](https://github.com/spyder-ide/spyder-kernels/pull/133) - PR: Add code completion to Pdb

In this release 10 pull requests were closed.

----

## Version 1.5.0 (2019-09-15)

### New features

* Add a new debugcell builtin command.
* Make runfile work in an empty namespace by default.
* Improve the display of tracebacks.
* Use the highest pickle protocol available to serialize data.
* Use Jupyter comms to communicate with the Spyder frontend.
* This release also contains all fixes present in versions 0.5.1
  and 0.5.2.

### Issues Closed

* [Issue 147](https://github.com/spyder-ide/spyder-kernels/issues/147) - debugfile() got an unexpected keyword argument 'current_namespace' ([PR 150](https://github.com/spyder-ide/spyder-kernels/pull/150))
* [Issue 145](https://github.com/spyder-ide/spyder-kernels/issues/145) - KeyError on comms when restarting the kernel ([PR 146](https://github.com/spyder-ide/spyder-kernels/pull/146))
* [Issue 97](https://github.com/spyder-ide/spyder-kernels/issues/97) - Can't repeat runcell from terminal ([PR 112](https://github.com/spyder-ide/spyder-kernels/pull/112))
* [Issue 73](https://github.com/spyder-ide/spyder-kernels/issues/73) - Select a higher Pickle protocol in case Spyder and the kernel are running in Python 3.4+ ([PR 111](https://github.com/spyder-ide/spyder-kernels/pull/111))

In this release 4 issues were closed.

### Pull Requests Merged

* [PR 150](https://github.com/spyder-ide/spyder-kernels/pull/150) - PR: Add current_namespace kwarg to debugfile ([147](https://github.com/spyder-ide/spyder-kernels/issues/147))
* [PR 146](https://github.com/spyder-ide/spyder-kernels/pull/146) - PR: Set closed flag before deleting comms  ([145](https://github.com/spyder-ide/spyder-kernels/issues/145))
* [PR 144](https://github.com/spyder-ide/spyder-kernels/pull/144) - PR: Solve error with exit command not being defined in the debugger
* [PR 142](https://github.com/spyder-ide/spyder-kernels/pull/142) - PR: Set debug state before asking for input
* [PR 140](https://github.com/spyder-ide/spyder-kernels/pull/140) - PR: Update jupyter-client minimal required version
* [PR 137](https://github.com/spyder-ide/spyder-kernels/pull/137) - PR: Add a way to change foreground color of Sympy repr's
* [PR 136](https://github.com/spyder-ide/spyder-kernels/pull/136) - PR: Ask the frontend to save files before running them
* [PR 134](https://github.com/spyder-ide/spyder-kernels/pull/134) - PR: Improve the display of tracebacks and better handle namespace and __file__ during execution
* [PR 131](https://github.com/spyder-ide/spyder-kernels/pull/131) - PR: Make runfile work in an empty namespace
* [PR 130](https://github.com/spyder-ide/spyder-kernels/pull/130) - PR: Add .pickle files to .gitignore
* [PR 128](https://github.com/spyder-ide/spyder-kernels/pull/128) - PR: Fix deprecated import
* [PR 112](https://github.com/spyder-ide/spyder-kernels/pull/112) - PR: Use the comms API to improve runcell and add a new debugcell command ([97](https://github.com/spyder-ide/spyder-kernels/issues/97))
* [PR 111](https://github.com/spyder-ide/spyder-kernels/pull/111) - PR: Use Jupyter comms to communicate with the Spyder frontend ([73](https://github.com/spyder-ide/spyder-kernels/issues/73))

In this release 13 pull requests were closed.

----

## Version 1.4.0 (2019-06-24)

### New features

* Add entries necessary for the new Object Explorer to
  REMOTE_SETTINGS.
* This release also contains all features and fixes present in
  version 0.5.0

### Pull Requests Merged

* [PR 100](https://github.com/spyder-ide/spyder-kernels/pull/100) - PR: Add object explorer settings to REMOTE_SETTINGS

In this release 1 pull request was closed.

----

## Version 1.3.3 (2019-04-08)

### New features
* This release contains all features and fixes present in versions
  0.4.3 and 0.4.4

### Issues Closed

* [Issue 93](https://github.com/spyder-ide/spyder-kernels/issues/93) - test_np_threshold is failing ([PR 95](https://github.com/spyder-ide/spyder-kernels/pull/95))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 95](https://github.com/spyder-ide/spyder-kernels/pull/95) - PR: Change np.nan for np.inf in test_np_threshold ([93](https://github.com/spyder-ide/spyder-kernels/issues/93))

In this release 1 pull request was closed.

----

## Version 1.3.2 (2019-02-10)

Sister release for 0.4.2

----

## Version 1.3.1 (2019-02-03)

Sister release for 0.4.1

----

## Version 1.3.0 (2019-02-02)

### New features
* Make runcell set __file__ to the path of the file containing the cell
* This release also contains all features and fixes present in version
  0.4.

### Issues Closed

* [Issue 78](https://github.com/spyder-ide/spyder-kernels/issues/78) - Nopython jit of numba is not working in runcell ([PR 79](https://github.com/spyder-ide/spyder-kernels/pull/79))
* [Issue 76](https://github.com/spyder-ide/spyder-kernels/issues/76) - Detect the name of the file currently running the cell ([PR 77](https://github.com/spyder-ide/spyder-kernels/pull/77))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 79](https://github.com/spyder-ide/spyder-kernels/pull/79) - PR: Remove user module reloader from runcell ([78](https://github.com/spyder-ide/spyder-kernels/issues/78))
* [PR 77](https://github.com/spyder-ide/spyder-kernels/pull/77) - PR: Have runcell set __file__ to the path of the file containing the cell  ([76](https://github.com/spyder-ide/spyder-kernels/issues/76))
* [PR 72](https://github.com/spyder-ide/spyder-kernels/pull/72) - PR: Fix numpy printoptions format ([7885](https://github.com/spyder-ide/spyder/issues/7885))

In this release 3 pull requests were closed.

----

## Version 1.2 (2018-12-26)

### New features
* Add the `runcell` command to run cells from Spyder's editor
  without pasting their contents in the console.
* This release also contains all features and fixes present in
  version 0.3.

### Issues Closed

* [Issue 57](https://github.com/spyder-ide/spyder-kernels/issues/57) - Add a test for runcell ([PR 70](https://github.com/spyder-ide/spyder-kernels/pull/70))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 70](https://github.com/spyder-ide/spyder-kernels/pull/70) - PR: Add a test for the runcell command ([57](https://github.com/spyder-ide/spyder-kernels/issues/57))
* [PR 69](https://github.com/spyder-ide/spyder-kernels/pull/69) - PR: Start testing in macOS
* [PR 67](https://github.com/spyder-ide/spyder-kernels/pull/67) - PR: Drop using ci-helpers in our CIs
* [PR 58](https://github.com/spyder-ide/spyder-kernels/pull/58) - PR: runcell trigger post_execute before run_cell to end the run_cell pre_execute
* [PR 7](https://github.com/spyder-ide/spyder-kernels/pull/7) - PR: Add runcell to spydercustomize

In this release 5 pull requests were closed.

----

## Version 1.1 (2018-08-11)

### Issues Closed

* [Issue 14](https://github.com/spyder-ide/spyder-kernels/issues/14) - Startup lines to split with semicolon instead of comma ([PR 15](https://github.com/spyder-ide/spyder-kernels/pull/15))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 15](https://github.com/spyder-ide/spyder-kernels/pull/15) - PR: Separate startup run_lines with semicolon instead of comma ([14](https://github.com/spyder-ide/spyder-kernels/issues/14))

In this release 1 pull request was closed.

----

## Version 1.0.3 (2018-08-09)

Sister release for 0.2.6

----

## Version 1.0.2 (2018-08-09)

Sister release for 0.2.5

----

## Version 1.0.1 (2018-06-25)

Sister release for 0.2.4

----

## Version 1.0.0 (2018-06-24)

Initial release for Spyder 4

----

## Version 0.5.2 (2019-09-15)

### Issues Closed

* [Issue 132](https://github.com/spyder-ide/spyder-kernels/issues/132) - tests use removed pandas.Panel ([PR 135](https://github.com/spyder-ide/spyder-kernels/pull/135))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 149](https://github.com/spyder-ide/spyder-kernels/pull/149) - PR: Add xarray to our test deps in setup.py
* [PR 135](https://github.com/spyder-ide/spyder-kernels/pull/135) - PR: Replace usage of Pandas Panel for Xarray Dataset in our tests ([132](https://github.com/spyder-ide/spyder-kernels/issues/132))

In this release 2 pull requests were closed.

----

## Version 0.5.1 (2019-07-11)

### Issues Closed

* [Issue 121](https://github.com/spyder-ide/spyder-kernels/issues/121) - Add test requirements to setup.py ([PR 122](https://github.com/spyder-ide/spyder-kernels/pull/122))
* [Issue 120](https://github.com/spyder-ide/spyder-kernels/issues/120) - Backport CI configuration from master to 0.x ([PR 123](https://github.com/spyder-ide/spyder-kernels/pull/123))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 125](https://github.com/spyder-ide/spyder-kernels/pull/125) - PR: Fix not including tests in tarballs and wheels
* [PR 123](https://github.com/spyder-ide/spyder-kernels/pull/123) - PR: Backport CI configuration from master to 0.x ([120](https://github.com/spyder-ide/spyder-kernels/issues/120))
* [PR 122](https://github.com/spyder-ide/spyder-kernels/pull/122) - PR: Add tests requirements to setup.py ([121](https://github.com/spyder-ide/spyder-kernels/issues/121))

In this release 3 pull requests were closed.

----

## Version 0.5.0 (2019-06-23)

### New features

* Set Matplotlib backend to inline for kernels started in a terminal.
* Handle option sent from Spyder to show/hide cmd windows generated
  by the subprocess module.

### Issues Closed

* [Issue 108](https://github.com/spyder-ide/spyder-kernels/issues/108) - Set matplotlib backend to inline by default on starting a new kernel ([PR 110](https://github.com/spyder-ide/spyder-kernels/pull/110))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 110](https://github.com/spyder-ide/spyder-kernels/pull/110) - PR: Set Matplotlib backend to inline for kernels started outside Spyder ([108](https://github.com/spyder-ide/spyder-kernels/issues/108))
* [PR 107](https://github.com/spyder-ide/spyder-kernels/pull/107) - PR: Use Readme.md for long description in PyPi
* [PR 104](https://github.com/spyder-ide/spyder-kernels/pull/104) - PR: Handle option to show/hide cmd windows generated by the subprocess module

In this release 3 pull requests were closed.

----

## Version 0.4.4 (2019-04-08)

### Issues Closed

* [Issue 102](https://github.com/spyder-ide/spyder-kernels/issues/102) - Tkinter is now required for version 0.4.3 after patching the turtle code ([PR 103](https://github.com/spyder-ide/spyder-kernels/pull/103))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 106](https://github.com/spyder-ide/spyder-kernels/pull/106) - PR: Skip test_turtle_launch if Tk is not installed
* [PR 103](https://github.com/spyder-ide/spyder-kernels/pull/103) - PR: Enclose turtle customizations in a try/except to avoid a dependency on Tk ([102](https://github.com/spyder-ide/spyder-kernels/issues/102))

In this release 2 pull requests were closed.

----

## Version 0.4.3 (2019-03-31)

### Issues Closed

* [Issue 91](https://github.com/spyder-ide/spyder-kernels/issues/91) - KeyError when running "%reset -f" programmatically ([PR 96](https://github.com/spyder-ide/spyder-kernels/pull/96))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 96](https://github.com/spyder-ide/spyder-kernels/pull/96) - PR:  Avoid error when trying to pop __file__ out of the current namespace ([91](https://github.com/spyder-ide/spyder-kernels/issues/91))
* [PR 92](https://github.com/spyder-ide/spyder-kernels/pull/92) - PR: Include user site-packages directory in the list of excluded paths by the UMR ([8776](https://github.com/spyder-ide/spyder/issues/8776))
* [PR 90](https://github.com/spyder-ide/spyder-kernels/pull/90) - PR: Patch turtle.bye to make it work with multiple runnings of the same code ([6278](https://github.com/spyder-ide/spyder/issues/6278))

In this release 3 pull requests were closed.

----

## Version 0.4.2 (2019-02-07)

### Issues Closed

* [Issue 85](https://github.com/spyder-ide/spyder-kernels/issues/85) - NameError: name 'modpath' is not defined ([PR 86](https://github.com/spyder-ide/spyder-kernels/pull/86))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 88](https://github.com/spyder-ide/spyder-kernels/pull/88) - PR: Improve Cython activation
* [PR 87](https://github.com/spyder-ide/spyder-kernels/pull/87) - PR: Fix running Cython files
* [PR 86](https://github.com/spyder-ide/spyder-kernels/pull/86) - PR: Fix problems with UMR's run method ([85](https://github.com/spyder-ide/spyder-kernels/issues/85))

In this release 3 pull requests were closed.

----

## Version 0.4.1 (2019-02-03)

### Pull Requests Merged

* [PR 84](https://github.com/spyder-ide/spyder-kernels/pull/84) - PR: Better way to skip standard library and site-packages modules from UMR
* [PR 83](https://github.com/spyder-ide/spyder-kernels/pull/83) - PR: Blacklist tensorflow from the UMR ([8697](https://github.com/spyder-ide/spyder/issues/8697))

In this release 2 pull requests were closed.

----

## Version 0.4 (2019-02-02)

### New features
* This release fixes several important issues that prevented
  saving the current namespace to work as expected.

### Issues Closed

* [Issue 75](https://github.com/spyder-ide/spyder-kernels/issues/75) - Namespace serialization silently fails if any object is unserializable, e.g. a Python module ([PR 81](https://github.com/spyder-ide/spyder-kernels/pull/81))
* [Issue 9](https://github.com/spyder-ide/spyder-kernels/issues/9) - Spydata files won't import if the original filename is changed ([PR 80](https://github.com/spyder-ide/spyder-kernels/pull/80))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 82](https://github.com/spyder-ide/spyder-kernels/pull/82) - PR: Enclose calls to load wurlitzer and autoreload in try/except's ([8668](https://github.com/spyder-ide/spyder/issues/8668))
* [PR 81](https://github.com/spyder-ide/spyder-kernels/pull/81) - PR: Fix and improve saving of Spyder namespace with many types of objects ([75](https://github.com/spyder-ide/spyder-kernels/issues/75))
* [PR 80](https://github.com/spyder-ide/spyder-kernels/pull/80) - PR: Fix loading Spydata file with changed filename and other edge-cases in load_dict ([9](https://github.com/spyder-ide/spyder-kernels/issues/9))

In this release 3 pull requests were closed.

----

## Version 0.3 (2018-11-23)

### New features
* Add Wurlitzer as a new dependency on Posix systems.
* Add tests for the console kernel.

### Issues Closed

* [Issue 62](https://github.com/spyder-ide/spyder-kernels/issues/62) - Add support for AppVeyor ([PR 63](https://github.com/spyder-ide/spyder-kernels/pull/63))
* [Issue 60](https://github.com/spyder-ide/spyder-kernels/issues/60) - Only load Wurlitzer in Posix systems ([PR 64](https://github.com/spyder-ide/spyder-kernels/pull/64))
* [Issue 23](https://github.com/spyder-ide/spyder-kernels/issues/23) - Add tests for the console kernel ([PR 37](https://github.com/spyder-ide/spyder-kernels/pull/37))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 64](https://github.com/spyder-ide/spyder-kernels/pull/64) - PR: Don't load Wurlitzer extension on Windows because it has no effect there ([60](https://github.com/spyder-ide/spyder-kernels/issues/60))
* [PR 63](https://github.com/spyder-ide/spyder-kernels/pull/63) - PR: Test on Windows with Appveyor ([62](https://github.com/spyder-ide/spyder-kernels/issues/62))
* [PR 61](https://github.com/spyder-ide/spyder-kernels/pull/61) - PR: Patch multiprocessing to make it work when all variables are removed ([8128](https://github.com/spyder-ide/spyder/issues/8128))
* [PR 59](https://github.com/spyder-ide/spyder-kernels/pull/59) - PR: Filter deprecation warnings in ipykernel ([8103](https://github.com/spyder-ide/spyder/issues/8103))
* [PR 56](https://github.com/spyder-ide/spyder-kernels/pull/56) - PR: Add Wurlitzer to Readme
* [PR 55](https://github.com/spyder-ide/spyder-kernels/pull/55) - PR: Exclude all tests from our tarballs
* [PR 54](https://github.com/spyder-ide/spyder-kernels/pull/54) - PR: Add the Wurlitzer package to capture stdout/stderr from C libraries ([3777](https://github.com/spyder-ide/spyder/issues/3777))
* [PR 53](https://github.com/spyder-ide/spyder-kernels/pull/53) - PR: Remove current working directory from sys.path before starting the console kernel ([8007](https://github.com/spyder-ide/spyder/issues/8007))
* [PR 37](https://github.com/spyder-ide/spyder-kernels/pull/37) - PR: Initial tests for the console kernel ([23](https://github.com/spyder-ide/spyder-kernels/issues/23))
* [PR 36](https://github.com/spyder-ide/spyder-kernels/pull/36) - PR: Make tests to really fail in CircleCI
* [PR 21](https://github.com/spyder-ide/spyder-kernels/pull/21) - PR: Add AUTHORS.txt in MANIFEST.in to include in package

In this release 11 pull requests were closed.

----

## Version 0.2.6 (2018-08-09)

### Pull Requests Merged

* [PR 20](https://github.com/spyder-ide/spyder-kernels/pull/20) - PR: Include license file again in tarball

In this release 1 pull request was closed.

----

## Version 0.2.5 (2018-08-09)

### Pull Requests Merged

* [PR 19](https://github.com/spyder-ide/spyder-kernels/pull/19) - PR: Fix inconsistent EOLs
* [PR 18](https://github.com/spyder-ide/spyder-kernels/pull/18) - PR: Fix legal texts and make them consistent across all files
* [PR 17](https://github.com/spyder-ide/spyder-kernels/pull/17) - PR: Add/update descriptions, links and metadata in setup.py
* [PR 16](https://github.com/spyder-ide/spyder-kernels/pull/16) - PR: Include test suite in manifest
* [PR 11](https://github.com/spyder-ide/spyder-kernels/pull/11) - PR: Add codecov support to see coverage
* [PR 10](https://github.com/spyder-ide/spyder-kernels/pull/10) - PR: Start testing with CircleCI
* [PR 8](https://github.com/spyder-ide/spyder-kernels/pull/8) - PR: Demand specific dependency versions needed by Spyder

In this release 7 pull requests were closed.

----

## Version 0.2.4 (2018-06-25)

### Pull Requests Merged

* [PR 6](https://github.com/spyder-ide/spyder-kernels/pull/6) - PR: Handle deprecated 'summary' method for Pandas

In this release 1 pull request was closed.

----

## Version 0.2.3 (2018-06-23)

### Pull Requests Merged

* [PR 5](https://github.com/spyder-ide/spyder-kernels/pull/5) - PR: Add __version__ to package's init

In this release 1 pull request was closed.

----

## Version 0.2.2 (2018-06-22)

### Pull Requests Merged

* [PR 4](https://github.com/spyder-ide/spyder-kernels/pull/4) - PR: Fix debugging in Python 2

In this release 1 pull request was closed.

----

## Version 0.2.1 (2018-06-22)

### Pull Requests Merged

* [PR 3](https://github.com/spyder-ide/spyder-kernels/pull/3) - PR: Fix debugging

In this release 1 pull request was closed.

----

## Version 0.2 (2018-06-20)

### Pull Requests Merged

* [PR 2](https://github.com/spyder-ide/spyder-kernels/pull/2) - PR: Import our customizations directly here
* [PR 1](https://github.com/spyder-ide/spyder-kernels/pull/1) - PR: Fix some errors in sitecustomize

In this release 2 pull requests were closed.

----

## Version 0.1 (2018-06-18)

Initial release
