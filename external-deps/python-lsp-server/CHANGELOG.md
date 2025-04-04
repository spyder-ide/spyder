# History of changes

## Version 1.12.0 (2024/08/25)

### New features

* Add support for `window/logMessage`.
* Add version support to `workspace/publishDiagnostics`.
* Add `extendSelect` option to flake8 plugin.
* Allow Jedi's `extra_paths` to be placed in front of `sys.path`.
* Bump flake8 to 7.1

### Pull Requests Merged

* [PR 586](https://github.com/python-lsp/python-lsp-server/pull/586) - Update versions of Github actions used on CI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 585](https://github.com/python-lsp/python-lsp-server/pull/585) - Fix linting issues reported by the latest version of Ruff, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 584](https://github.com/python-lsp/python-lsp-server/pull/584) - Use `%r` to have a better log, by [@tebeka](https://github.com/tebeka)
* [PR 581](https://github.com/python-lsp/python-lsp-server/pull/581) - Set return type to `None` for functions without returns, by [@agserrano3](https://github.com/agserrano3)
* [PR 576](https://github.com/python-lsp/python-lsp-server/pull/576) - Bump flake8 to 7.1, by [@bnavigator](https://github.com/bnavigator)
* [PR 573](https://github.com/python-lsp/python-lsp-server/pull/573) - Add `window/logMessage` support, by [@Dylmay](https://github.com/Dylmay)
* [PR 570](https://github.com/python-lsp/python-lsp-server/pull/570) - Fix Fedora instructions, by [@penguinpee](https://github.com/penguinpee)
* [PR 565](https://github.com/python-lsp/python-lsp-server/pull/565) - Add version support to `workspace/publishDiagnostics`, by [@Dylmay](https://github.com/Dylmay)
* [PR 560](https://github.com/python-lsp/python-lsp-server/pull/560) - Use macOS 13 to run our tests on CI, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 559](https://github.com/python-lsp/python-lsp-server/pull/559) - Add `extendSelect` option to flake8 plugin, by [@Susensio](https://github.com/Susensio)
* [PR 547](https://github.com/python-lsp/python-lsp-server/pull/547) - Infer end position for Pylint diagnostics, by [@Wuestengecko](https://github.com/Wuestengecko)
* [PR 527](https://github.com/python-lsp/python-lsp-server/pull/527) - Allow `extra_paths` to be placed in front of `sys.path`, by [@mrclary](https://github.com/mrclary)

In this release 12 pull requests were closed.

----

## Version 1.11.0 (2024/03/29)

### New features

* Remove the `rope_rename` plugin. People that were using it need to install
  the `pylsp-rope` third-party plugin instead.
* Add support for Pylint 3.1

### Issues Closed

* [Issue 255](https://github.com/python-lsp/python-lsp-server/issues/255) - Confusion about rename support ([PR 515](https://github.com/python-lsp/python-lsp-server/pull/515) by [@doolio](https://github.com/doolio))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 543](https://github.com/python-lsp/python-lsp-server/pull/543) - Bump pylint to `>=3.1,<4`, by [@bnavigator](https://github.com/bnavigator)
* [PR 541](https://github.com/python-lsp/python-lsp-server/pull/541) - Add fallback for `ujson` import, by [@Savalek](https://github.com/Savalek)
* [PR 538](https://github.com/python-lsp/python-lsp-server/pull/538) - Remove `.config/flake8` reference in Readme, by [@justin-f-perez](https://github.com/justin-f-perez)
* [PR 536](https://github.com/python-lsp/python-lsp-server/pull/536) - Fix isort plugin name in Readme, by [@Piraty](https://github.com/Piraty)
* [PR 515](https://github.com/python-lsp/python-lsp-server/pull/515) - Remove built-in `rope_rename` plugin, by [@doolio](https://github.com/doolio) ([255](https://github.com/python-lsp/python-lsp-server/issues/255))
* [PR 470](https://github.com/python-lsp/python-lsp-server/pull/470) - Add contributing guide to setup dev environment, by [@staticf0x](https://github.com/staticf0x)

In this release 6 pull requests were closed.

----

## Version 1.10.1 (2024/03/12)

### Issues Closed

* [Issue 529](https://github.com/python-lsp/python-lsp-server/issues/529) - Autoimports: sqlite3.OperationalError: database is locked ([PR 530](https://github.com/python-lsp/python-lsp-server/pull/530) by [@last-partizan](https://github.com/last-partizan))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 530](https://github.com/python-lsp/python-lsp-server/pull/530) - Fix progress reporting with autoimport plugin, by [@last-partizan](https://github.com/last-partizan) ([529](https://github.com/python-lsp/python-lsp-server/issues/529))
* [PR 528](https://github.com/python-lsp/python-lsp-server/pull/528) - Improve error message about missing `websockets` module, by [@tomplus](https://github.com/tomplus)

In this release 2 pull requests were closed.

----

## Version 1.10.0 (2024/01/21)

### New features

* Add support for notebook document completions.
* Add support for flake8 version 7.

### Issues Closed

* [Issue 513](https://github.com/python-lsp/python-lsp-server/issues/513) - Different versions of autopep can be installed as optional dependencies ([PR 514](https://github.com/python-lsp/python-lsp-server/pull/514) by [@doolio](https://github.com/doolio))
* [Issue 478](https://github.com/python-lsp/python-lsp-server/issues/478) - Considering pointing to python-lsp-isort rather than pyls-isort in the README ([PR 483](https://github.com/python-lsp/python-lsp-server/pull/483) by [@doolio](https://github.com/doolio))
* [Issue 474](https://github.com/python-lsp/python-lsp-server/issues/474) - AutoImport can break when being called by multiple threads ([PR 498](https://github.com/python-lsp/python-lsp-server/pull/498) by [@tkrabel](https://github.com/tkrabel))
* [Issue 373](https://github.com/python-lsp/python-lsp-server/issues/373) - file path auto completion add \ in path string ([PR 497](https://github.com/python-lsp/python-lsp-server/pull/497) by [@i-aki-y](https://github.com/i-aki-y))
* [Issue 256](https://github.com/python-lsp/python-lsp-server/issues/256) - Flake8 Severity too high ([PR 490](https://github.com/python-lsp/python-lsp-server/pull/490) by [@kunhtkun](https://github.com/kunhtkun))

In this release 5 issues were closed.

### Pull Requests Merged

* [PR 517](https://github.com/python-lsp/python-lsp-server/pull/517) - Combine ruff.toml into pyproject.toml, by [@doolio](https://github.com/doolio)
* [PR 514](https://github.com/python-lsp/python-lsp-server/pull/514) - Fix optional dependency version for autopep8, by [@doolio](https://github.com/doolio) ([513](https://github.com/python-lsp/python-lsp-server/issues/513))
* [PR 510](https://github.com/python-lsp/python-lsp-server/pull/510) - Bump flake8 to version 7, by [@bnavigator](https://github.com/bnavigator)
* [PR 507](https://github.com/python-lsp/python-lsp-server/pull/507) - Fix extra end line increment in autopep8 plugin, by [@remisalmon](https://github.com/remisalmon)
* [PR 502](https://github.com/python-lsp/python-lsp-server/pull/502) - Use ruff as linter and code formatter, by [@tkrabel](https://github.com/tkrabel)
* [PR 499](https://github.com/python-lsp/python-lsp-server/pull/499) - Make autoimport cache generation non-blocking, by [@tkrabel](https://github.com/tkrabel)
* [PR 498](https://github.com/python-lsp/python-lsp-server/pull/498) - Update rope to 1.11.0 for multi-threading capabilities, by [@tkrabel](https://github.com/tkrabel) ([474](https://github.com/python-lsp/python-lsp-server/issues/474))
* [PR 497](https://github.com/python-lsp/python-lsp-server/pull/497) - Fix path completion when client doesn't support code snippets, by [@i-aki-y](https://github.com/i-aki-y) ([373](https://github.com/python-lsp/python-lsp-server/issues/373))
* [PR 490](https://github.com/python-lsp/python-lsp-server/pull/490) - Refine diagnostic severity for flake8, by [@kunhtkun](https://github.com/kunhtkun) ([256](https://github.com/python-lsp/python-lsp-server/issues/256))
* [PR 487](https://github.com/python-lsp/python-lsp-server/pull/487) - Replace call to `python` with `sys.executable` in Pylint plugin, by [@jspricke](https://github.com/jspricke)
* [PR 486](https://github.com/python-lsp/python-lsp-server/pull/486) - Add support for notebook document completions, by [@smacke](https://github.com/smacke)
* [PR 483](https://github.com/python-lsp/python-lsp-server/pull/483) - Point to a more up to date isort plugin in README, by [@doolio](https://github.com/doolio) ([478](https://github.com/python-lsp/python-lsp-server/issues/478))

In this release 12 pull requests were closed.

----

## Version 1.9.0 (2023/11/06)

### New features

* Support `initializationOptions` to configure the server.
* Add code completions to the autoimport plugin.
* Add support for Pylint 3.
* Pass `extendIgnore` argument to Flake8.
* Add new `pylsp_workspace_configuration_changed` hookspec so that plugins can
  react when client sends a configuration change to the server.

### Issues Closed

* [Issue 460](https://github.com/python-lsp/python-lsp-server/issues/460) - rope_autoimport doesn't initialize after `workspace/didChangeConfiguration` message ([PR 461](https://github.com/python-lsp/python-lsp-server/pull/461) by [@tkrabel-db](https://github.com/tkrabel-db))
* [Issue 403](https://github.com/python-lsp/python-lsp-server/issues/403) - Add code action for implementing auto-import ([PR 471](https://github.com/python-lsp/python-lsp-server/pull/471) by [@tkrabel-db](https://github.com/tkrabel-db))
* [Issue 195](https://github.com/python-lsp/python-lsp-server/issues/195) - Maybe use initializationOptions as additional source of settings ([PR 459](https://github.com/python-lsp/python-lsp-server/pull/459) by [@tkrabel-db](https://github.com/tkrabel-db))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 481](https://github.com/python-lsp/python-lsp-server/pull/481) - Revert "Rename `_utils` module to `utils`", by [@ccordoba12](https://github.com/ccordoba12)
* [PR 480](https://github.com/python-lsp/python-lsp-server/pull/480) - Rename `_utils` module to `utils`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 475](https://github.com/python-lsp/python-lsp-server/pull/475) - Raise supported Pylint upper version, by [@bnavigator](https://github.com/bnavigator)
* [PR 473](https://github.com/python-lsp/python-lsp-server/pull/473) - Improve/simplify README Development section, by [@tkrabel](https://github.com/tkrabel)
* [PR 471](https://github.com/python-lsp/python-lsp-server/pull/471) - Add code completions to `rope_autoimport` plugin, by [@tkrabel-db](https://github.com/tkrabel-db) ([403](https://github.com/python-lsp/python-lsp-server/issues/403))
* [PR 469](https://github.com/python-lsp/python-lsp-server/pull/469) - Pass argument `extendIgnore` to flake8, by [@UnkwUsr](https://github.com/UnkwUsr)
* [PR 466](https://github.com/python-lsp/python-lsp-server/pull/466) - Ignore notebook names on cell completion for autoimport, by [@tkrabel-db](https://github.com/tkrabel-db)
* [PR 464](https://github.com/python-lsp/python-lsp-server/pull/464) - Minor bug fix in Rope autoimport plugin, by [@tkrabel-db](https://github.com/tkrabel-db)
* [PR 462](https://github.com/python-lsp/python-lsp-server/pull/462) - Make workspace/didChangeConfig work with notebook documents, by [@tkrabel-db](https://github.com/tkrabel-db)
* [PR 461](https://github.com/python-lsp/python-lsp-server/pull/461) - Load `rope_autoimport` cache on `workspace/didChangeConfiguration`, by [@tkrabel-db](https://github.com/tkrabel-db) ([460](https://github.com/python-lsp/python-lsp-server/issues/460))
* [PR 459](https://github.com/python-lsp/python-lsp-server/pull/459) - Support `initializationOptions` to configure the server, by [@tkrabel-db](https://github.com/tkrabel-db) ([195](https://github.com/python-lsp/python-lsp-server/issues/195))
* [PR 457](https://github.com/python-lsp/python-lsp-server/pull/457) - Fix missing signatures for docstrings in Markdown, by [@staticf0x](https://github.com/staticf0x)

In this release 12 pull requests were closed.

----

## Version 1.8.2 (2023/10/09)

### Issues Closed

* [Issue 453](https://github.com/python-lsp/python-lsp-server/issues/453) - notebookDocumentSync notebookSelector type error ([PR 454](https://github.com/python-lsp/python-lsp-server/pull/454) by [@smacke](https://github.com/smacke))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 454](https://github.com/python-lsp/python-lsp-server/pull/454) - Fix notebook document selector not being a list in capabilities, by [@smacke](https://github.com/smacke) ([453](https://github.com/python-lsp/python-lsp-server/issues/453))

In this release 1 pull request was closed.

----

## Version 1.8.1 (2023/10/05)

### Issues Closed

* [Issue 439](https://github.com/python-lsp/python-lsp-server/issues/439) - `includeDeclaration` is no longer respected in `textDocument/references` ([PR 440](https://github.com/python-lsp/python-lsp-server/pull/440) by [@krassowski](https://github.com/krassowski))
* [Issue 438](https://github.com/python-lsp/python-lsp-server/issues/438) - flake8 can error out when deleting lines ([PR 441](https://github.com/python-lsp/python-lsp-server/pull/441) by [@krassowski](https://github.com/krassowski))
* [Issue 413](https://github.com/python-lsp/python-lsp-server/issues/413) - textDocument/rename reports positions outside of the document ([PR 450](https://github.com/python-lsp/python-lsp-server/pull/450) by [@ccordoba12](https://github.com/ccordoba12))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 450](https://github.com/python-lsp/python-lsp-server/pull/450) - Fix renaming when file has no EOLs, by [@ccordoba12](https://github.com/ccordoba12) ([413](https://github.com/python-lsp/python-lsp-server/issues/413))
* [PR 449](https://github.com/python-lsp/python-lsp-server/pull/449) - Increase minimal required version of autopep8 to `>=2.0.4,<2.1.0`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 447](https://github.com/python-lsp/python-lsp-server/pull/447) - Fix numpy go-to-definition by taking it off autoimport list for this case, by [@smacke](https://github.com/smacke)
* [PR 443](https://github.com/python-lsp/python-lsp-server/pull/443) - Allow Jedi "goto" to perform multiple hops for "go to definition", by [@smacke](https://github.com/smacke)
* [PR 441](https://github.com/python-lsp/python-lsp-server/pull/441) - Pass a single copy of the document's source around for flake8, by [@krassowski](https://github.com/krassowski) ([438](https://github.com/python-lsp/python-lsp-server/issues/438))
* [PR 440](https://github.com/python-lsp/python-lsp-server/pull/440) - Fix `include_declaration` handling in references request, by [@krassowski](https://github.com/krassowski) ([439](https://github.com/python-lsp/python-lsp-server/issues/439))
* [PR 436](https://github.com/python-lsp/python-lsp-server/pull/436) - Add black reformatting commit to `.git-blame-ignore-revs`, by [@krassowski](https://github.com/krassowski)

In this release 7 pull requests were closed.

----

## Version 1.8.0 (2023/09/08)

### New features

* Add notebooks suppport and make go-to-definition work for them.
* Add support for Pyflakes 3.1, Pycodestyle 2.11 and Jedi 0.19.
* Drop support for Python 3.7.

### Issues Closed

* [Issue 429](https://github.com/python-lsp/python-lsp-server/issues/429) - Error in Pyflakes plugin: 'NoneType' has no len() ([PR 433](https://github.com/python-lsp/python-lsp-server/pull/433) by [@smacke](https://github.com/smacke))
* [Issue 414](https://github.com/python-lsp/python-lsp-server/issues/414) - Support Jedi 0.19 ([PR 416](https://github.com/python-lsp/python-lsp-server/pull/416) by [@bnavigator](https://github.com/bnavigator))
* [Issue 412](https://github.com/python-lsp/python-lsp-server/issues/412) - Add support for pyflakes 3.1 ([PR 415](https://github.com/python-lsp/python-lsp-server/pull/415) by [@yan12125](https://github.com/yan12125))
* [Issue 406](https://github.com/python-lsp/python-lsp-server/issues/406) - flake8_lint plugin: Popen fails when no workspace given by language server client on Windows ([PR 434](https://github.com/python-lsp/python-lsp-server/pull/434) by [@smacke](https://github.com/smacke))
* [Issue 392](https://github.com/python-lsp/python-lsp-server/issues/392) - Using black as an autoformatter ([PR 419](https://github.com/python-lsp/python-lsp-server/pull/419) by [@tkrabel-db](https://github.com/tkrabel-db))
* [Issue 384](https://github.com/python-lsp/python-lsp-server/issues/384) - Replace `setuptools`/`pkg_resources` with `importlib(.|_)metadata` ([PR 385](https://github.com/python-lsp/python-lsp-server/pull/385) by [@bollwyvl](https://github.com/bollwyvl))
* [Issue 314](https://github.com/python-lsp/python-lsp-server/issues/314) - Failed to handle requests after exit ([PR 432](https://github.com/python-lsp/python-lsp-server/pull/432) by [@smacke](https://github.com/smacke))

In this release 7 issues were closed.

### Pull Requests Merged

* [PR 434](https://github.com/python-lsp/python-lsp-server/pull/434) - Don't set cwd in Popen kwargs when document root is empty (flake8), by [@smacke](https://github.com/smacke) ([406](https://github.com/python-lsp/python-lsp-server/issues/406))
* [PR 433](https://github.com/python-lsp/python-lsp-server/pull/433) - Fix null reference for syntax errors due to invalid encodings (Pyflakes), by [@smacke](https://github.com/smacke) ([429](https://github.com/python-lsp/python-lsp-server/issues/429), [429](https://github.com/python-lsp/python-lsp-server/issues/429))
* [PR 432](https://github.com/python-lsp/python-lsp-server/pull/432) - Use invalid request handler rather than raising key error for requests after shutdown, by [@smacke](https://github.com/smacke) ([314](https://github.com/python-lsp/python-lsp-server/issues/314))
* [PR 419](https://github.com/python-lsp/python-lsp-server/pull/419) - Format the whole repo with Black, by [@tkrabel-db](https://github.com/tkrabel-db) ([392](https://github.com/python-lsp/python-lsp-server/issues/392))
* [PR 418](https://github.com/python-lsp/python-lsp-server/pull/418) - Converge unit tests for test_language_server and test_notebook_document, by [@tkrabel-db](https://github.com/tkrabel-db)
* [PR 417](https://github.com/python-lsp/python-lsp-server/pull/417) - Drop support for Python 3.7, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 416](https://github.com/python-lsp/python-lsp-server/pull/416) - Bump Jedi upper pin to <0.20, by [@bnavigator](https://github.com/bnavigator) ([414](https://github.com/python-lsp/python-lsp-server/issues/414))
* [PR 415](https://github.com/python-lsp/python-lsp-server/pull/415) - Add support for pyflakes 3.1 and pycodestyle 2.11, by [@yan12125](https://github.com/yan12125) ([412](https://github.com/python-lsp/python-lsp-server/issues/412))
* [PR 408](https://github.com/python-lsp/python-lsp-server/pull/408) - Notebook protocol go-to-definition support, by [@jasongrout](https://github.com/jasongrout)
* [PR 389](https://github.com/python-lsp/python-lsp-server/pull/389) - Add notebooks suppport to pylsp, by [@tkrabel-db](https://github.com/tkrabel-db)
* [PR 385](https://github.com/python-lsp/python-lsp-server/pull/385) - Find `entry_points` with `importlib(.|_)metadata`, drop `setuptools` from `dependencies`, by [@bollwyvl](https://github.com/bollwyvl) ([384](https://github.com/python-lsp/python-lsp-server/issues/384))

In this release 11 pull requests were closed.

----

## Version 1.7.4 (2023/06/29)

### Issues Closed

* [Issue 393](https://github.com/python-lsp/python-lsp-server/issues/393) - Environment path doesn't expand user directory

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 394](https://github.com/python-lsp/python-lsp-server/pull/394) - Resolve homedir references in Jedi environment path, by [@odiroot](https://github.com/odiroot)
* [PR 381](https://github.com/python-lsp/python-lsp-server/pull/381) - Report progress even when initialization fails, by [@syphar](https://github.com/syphar)
* [PR 380](https://github.com/python-lsp/python-lsp-server/pull/380) - Fix pylint hang on file with many errors, by [@hetmankp](https://github.com/hetmankp)

In this release 3 pull requests were closed.

----

## Version 1.7.3 (2023/05/15)

### Issues Closed

* [Issue 369](https://github.com/python-lsp/python-lsp-server/issues/369) - Failed to load hook pylsp_lint: [Errno 2] No such file or directory: '' ([PR 371](https://github.com/python-lsp/python-lsp-server/pull/371) by [@Ultimator14](https://github.com/Ultimator14))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 377](https://github.com/python-lsp/python-lsp-server/pull/377) - Update yapf requirement to 0.33+, by [@bnavigator](https://github.com/bnavigator)
* [PR 371](https://github.com/python-lsp/python-lsp-server/pull/371) - Fix empty cwd value for pylint, by [@Ultimator14](https://github.com/Ultimator14) ([369](https://github.com/python-lsp/python-lsp-server/issues/369))
* [PR 364](https://github.com/python-lsp/python-lsp-server/pull/364) - Add Arch Linux installation command to Readme, by [@GNVageesh](https://github.com/GNVageesh)

In this release 3 pull requests were closed.

----

## Version 1.7.2 (2023/04/02)

### Issues Closed

* [Issue 325](https://github.com/python-lsp/python-lsp-server/issues/325) - WorkDoneProgress tokens not initialized properly by the server ([PR 328](https://github.com/python-lsp/python-lsp-server/pull/328) by [@syphar](https://github.com/syphar))
* [Issue 260](https://github.com/python-lsp/python-lsp-server/issues/260) - yapf formatting fails when pyproject.toml is in the workspace ([PR 346](https://github.com/python-lsp/python-lsp-server/pull/346) by [@bnavigator](https://github.com/bnavigator))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 346](https://github.com/python-lsp/python-lsp-server/pull/346) - Add toml dependency for yapf and constrain yapf to be less than 0.32, by [@bnavigator](https://github.com/bnavigator) ([260](https://github.com/python-lsp/python-lsp-server/issues/260))
* [PR 345](https://github.com/python-lsp/python-lsp-server/pull/345) - Raise upper bound of autopep8, by [@bnavigator](https://github.com/bnavigator)
* [PR 340](https://github.com/python-lsp/python-lsp-server/pull/340) - Bump pydocstyle to 6.3, by [@bnavigator](https://github.com/bnavigator)
* [PR 328](https://github.com/python-lsp/python-lsp-server/pull/328) - Initialize LSP progress token before using it and remove progress for sync plugins, by [@syphar](https://github.com/syphar) ([325](https://github.com/python-lsp/python-lsp-server/issues/325))

In this release 4 pull requests were closed.

----

## Version 1.7.1 (2023/01/17)

### Issues Closed

* [Issue 332](https://github.com/python-lsp/python-lsp-server/issues/332) - Failed to load hook pylsp_lint: too many values to unpack (expected 3) ([PR 329](https://github.com/python-lsp/python-lsp-server/pull/329) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 338](https://github.com/python-lsp/python-lsp-server/pull/338) - Use shlex.split() to split pylint flags, by [@hfrentzel](https://github.com/hfrentzel)
* [PR 337](https://github.com/python-lsp/python-lsp-server/pull/337) - Improve Jedi file completions for directories, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 334](https://github.com/python-lsp/python-lsp-server/pull/334) - Include missing Pylint "information" category, by [@juliangilbey](https://github.com/juliangilbey)
* [PR 333](https://github.com/python-lsp/python-lsp-server/pull/333) - Add top constraint to Pylint and fix constraint for `whatthepatch`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 329](https://github.com/python-lsp/python-lsp-server/pull/329) - Fix pydocstyle linting with its 6.2.0 version, by [@ccordoba12](https://github.com/ccordoba12) ([332](https://github.com/python-lsp/python-lsp-server/issues/332))
* [PR 327](https://github.com/python-lsp/python-lsp-server/pull/327) - Use `sys.executable` instead of `python` in Pylint plugin, by [@bnavigator](https://github.com/bnavigator)

In this release 6 pull requests were closed.

----

## Version 1.7.0 (2022/12/29)

### New features

* Add a new plugin to provide autoimport functionality (disabled by default).
* Add progress reporting.
* Make `jedi_definition` plugin follow definitions to `pyi` files.
* Add support for flake8 version 6.
* Add support for Yapf ignore patterns.
* Add mccabe setting to flake8 plugin.

### Issues Closed

* [Issue 317](https://github.com/python-lsp/python-lsp-server/issues/317) - Is there a configuration option to enable jumping to builtin module stubs? ([PR 321](https://github.com/python-lsp/python-lsp-server/pull/321) by [@bzoracler](https://github.com/bzoracler))
* [Issue 307](https://github.com/python-lsp/python-lsp-server/issues/307) - Autoimport keep throwing exception when delete a line ([PR 309](https://github.com/python-lsp/python-lsp-server/pull/309) by [@douo](https://github.com/douo))
* [Issue 301](https://github.com/python-lsp/python-lsp-server/issues/301) - `textDocument/documentSymbol` returns empty result for non-existing files ([PR 302](https://github.com/python-lsp/python-lsp-server/pull/302) by [@rear1019](https://github.com/rear1019))
* [Issue 292](https://github.com/python-lsp/python-lsp-server/issues/292) - List of allowed values for pylsp.plugins.pydocstyle.convention in CONFIGURATION.md incorrect ([PR 295](https://github.com/python-lsp/python-lsp-server/pull/295) by [@doolio](https://github.com/doolio))
* [Issue 201](https://github.com/python-lsp/python-lsp-server/issues/201) - Progress support ([PR 236](https://github.com/python-lsp/python-lsp-server/pull/236) by [@syphar](https://github.com/syphar))
* [Issue 34](https://github.com/python-lsp/python-lsp-server/issues/34) - Auto-import? ([PR 199](https://github.com/python-lsp/python-lsp-server/pull/199) by [@bagel897](https://github.com/bagel897))

In this release 6 issues were closed.

### Pull Requests Merged

* [PR 323](https://github.com/python-lsp/python-lsp-server/pull/323) - Don't show signature for modules in hovers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 322](https://github.com/python-lsp/python-lsp-server/pull/322) - Change Pylint run to set cwd correctly, by [@Corentin-pro](https://github.com/Corentin-pro)
* [PR 321](https://github.com/python-lsp/python-lsp-server/pull/321) - Expose setting to follow builtin and extension definitions to stub files, by [@bzoracler](https://github.com/bzoracler) ([317](https://github.com/python-lsp/python-lsp-server/issues/317))
* [PR 319](https://github.com/python-lsp/python-lsp-server/pull/319) - Fix Pycodestyle linting with line endings other than LF , by [@ccordoba12](https://github.com/ccordoba12)
* [PR 318](https://github.com/python-lsp/python-lsp-server/pull/318) - Ensure proper document match to avoid empty outline (Symbols), by [@mnauw](https://github.com/mnauw)
* [PR 316](https://github.com/python-lsp/python-lsp-server/pull/316) - Support Flake8 version 6, by [@bnavigator](https://github.com/bnavigator)
* [PR 312](https://github.com/python-lsp/python-lsp-server/pull/312) - Update Readme with link to python-lsp-ruff and mention to code actions, by [@jhossbach](https://github.com/jhossbach)
* [PR 311](https://github.com/python-lsp/python-lsp-server/pull/311) - Make flake8 respect configuration, by [@delfick](https://github.com/delfick)
* [PR 309](https://github.com/python-lsp/python-lsp-server/pull/309) - Fix autoimport raising AttributeError in some cases, by [@douo](https://github.com/douo) ([307](https://github.com/python-lsp/python-lsp-server/issues/307))
* [PR 306](https://github.com/python-lsp/python-lsp-server/pull/306) - Fix the completion of `include_function_objects`, by [@llan-ml](https://github.com/llan-ml)
* [PR 305](https://github.com/python-lsp/python-lsp-server/pull/305) - Report autoimport progress, by [@bagel897](https://github.com/bagel897)
* [PR 302](https://github.com/python-lsp/python-lsp-server/pull/302) - Fix symbols for non-existing (unsaved) files, by [@rear1019](https://github.com/rear1019) ([301](https://github.com/python-lsp/python-lsp-server/issues/301))
* [PR 300](https://github.com/python-lsp/python-lsp-server/pull/300) - Fix autoimport plugin not being disabled by default, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 296](https://github.com/python-lsp/python-lsp-server/pull/296) - Update outdated username in docs, by [@bagel897](https://github.com/bagel897)
* [PR 295](https://github.com/python-lsp/python-lsp-server/pull/295) - Update allowed values for pydocstyle convention in CONFIGURATION.md, by [@doolio](https://github.com/doolio) ([292](https://github.com/python-lsp/python-lsp-server/issues/292))
* [PR 290](https://github.com/python-lsp/python-lsp-server/pull/290) - Fix Debian package name, by [@jspricke](https://github.com/jspricke)
* [PR 236](https://github.com/python-lsp/python-lsp-server/pull/236) - Add progress reporting, by [@syphar](https://github.com/syphar) ([201](https://github.com/python-lsp/python-lsp-server/issues/201))
* [PR 199](https://github.com/python-lsp/python-lsp-server/pull/199) - Add a plugin to provide autoimport functionality, by [@bagel897](https://github.com/bagel897) ([34](https://github.com/python-lsp/python-lsp-server/issues/34))
* [PR 63](https://github.com/python-lsp/python-lsp-server/pull/63) - Add mccabe setting to flake8, by [@baco](https://github.com/baco)
* [PR 60](https://github.com/python-lsp/python-lsp-server/pull/60) - Add support for Yapf ignore patterns, by [@jjlorenzo](https://github.com/jjlorenzo)

In this release 20 pull requests were closed.

----

## Version 1.6.0 (2022/11/02)

### New features

* Migrate to MarkupContent and convert docstrings to Markdown by default.
* Add support for flake8 version 5.
* Add function objects to Jedi completions.
* Don't include class and functions objects by default in Jedi completions.

### Issues Closed

* [Issue 273](https://github.com/python-lsp/python-lsp-server/issues/273) - Completion result have "typeParameter" duplicates   ([PR 274](https://github.com/python-lsp/python-lsp-server/pull/274) by [@airportyh](https://github.com/airportyh))
* [Issue 265](https://github.com/python-lsp/python-lsp-server/issues/265) - Server warns when optional modules do not exist ([PR 266](https://github.com/python-lsp/python-lsp-server/pull/266) by [@doolio](https://github.com/doolio))
* [Issue 264](https://github.com/python-lsp/python-lsp-server/issues/264) - Errors in CONFIGURATION.md? ([PR 267](https://github.com/python-lsp/python-lsp-server/pull/267) by [@doolio](https://github.com/doolio))
* [Issue 263](https://github.com/python-lsp/python-lsp-server/issues/263) - Conflict between README and CONFIGURATION ([PR 267](https://github.com/python-lsp/python-lsp-server/pull/267) by [@doolio](https://github.com/doolio))
* [Issue 245](https://github.com/python-lsp/python-lsp-server/issues/245) - Add alternative ways to install python-lsp-server ([PR 248](https://github.com/python-lsp/python-lsp-server/pull/248) by [@nougcat](https://github.com/nougcat))
* [Issue 244](https://github.com/python-lsp/python-lsp-server/issues/244) - Add function objects to completions ([PR 246](https://github.com/python-lsp/python-lsp-server/pull/246) by [@llan-ml](https://github.com/llan-ml))
* [Issue 243](https://github.com/python-lsp/python-lsp-server/issues/243) - `Failed to load hook pylsp_completions: 'NoneType' object has no attribute 'type'` when working with Numpy 1.23 ([PR 281](https://github.com/python-lsp/python-lsp-server/pull/281) by [@gav451](https://github.com/gav451))
* [Issue 22](https://github.com/python-lsp/python-lsp-server/issues/22) - Consider using docstring_to_markdown for markdown hover and documentation ([PR 80](https://github.com/python-lsp/python-lsp-server/pull/80) by [@krassowski](https://github.com/krassowski))
* [Issue 21](https://github.com/python-lsp/python-lsp-server/issues/21) - Migrate from deprecated MarkedString to MarkupContent ([PR 80](https://github.com/python-lsp/python-lsp-server/pull/80) by [@krassowski](https://github.com/krassowski))

In this release 9 issues were closed.

### Pull Requests Merged

* [PR 285](https://github.com/python-lsp/python-lsp-server/pull/285) - Don't include class objects by default in completions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 281](https://github.com/python-lsp/python-lsp-server/pull/281) - Improve how Jedi handles Numpy, by [@gav451](https://github.com/gav451) ([243](https://github.com/python-lsp/python-lsp-server/issues/243))
* [PR 274](https://github.com/python-lsp/python-lsp-server/pull/274) - Make default for `include_function_objects` false, by [@airportyh](https://github.com/airportyh) ([273](https://github.com/python-lsp/python-lsp-server/issues/273))
* [PR 272](https://github.com/python-lsp/python-lsp-server/pull/272) - Include params only for classes and functions, by [@llan-ml](https://github.com/llan-ml)
* [PR 267](https://github.com/python-lsp/python-lsp-server/pull/267) - Update the configuration schema for consistency, by [@doolio](https://github.com/doolio) ([264](https://github.com/python-lsp/python-lsp-server/issues/264), [263](https://github.com/python-lsp/python-lsp-server/issues/263))
* [PR 266](https://github.com/python-lsp/python-lsp-server/pull/266) - Prefer info log message for missing optional modules, by [@doolio](https://github.com/doolio) ([265](https://github.com/python-lsp/python-lsp-server/issues/265))
* [PR 262](https://github.com/python-lsp/python-lsp-server/pull/262) - Fix options not being passed to yapf format, by [@masad-frost](https://github.com/masad-frost)
* [PR 261](https://github.com/python-lsp/python-lsp-server/pull/261) - PR: Include all symbols that Jedi reports as declared in a file when `add_import_symbols` is `False`, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 258](https://github.com/python-lsp/python-lsp-server/pull/258) - Fix pylint message in tests, by [@bnavigator](https://github.com/bnavigator)
* [PR 257](https://github.com/python-lsp/python-lsp-server/pull/257) - Add support for flake8 version 5, by [@bnavigator](https://github.com/bnavigator)
* [PR 250](https://github.com/python-lsp/python-lsp-server/pull/250) - Include traceback when plugin fails to load, by [@j2kun](https://github.com/j2kun)
* [PR 248](https://github.com/python-lsp/python-lsp-server/pull/248) - Add more installation instructions to Readme, by [@nougcat](https://github.com/nougcat) ([245](https://github.com/python-lsp/python-lsp-server/issues/245))
* [PR 246](https://github.com/python-lsp/python-lsp-server/pull/246) - Add support for including function objects, by [@llan-ml](https://github.com/llan-ml) ([244](https://github.com/python-lsp/python-lsp-server/issues/244))
* [PR 242](https://github.com/python-lsp/python-lsp-server/pull/242) - Remove redundant wheel dep from pyproject.toml, by [@mgorny](https://github.com/mgorny)
* [PR 241](https://github.com/python-lsp/python-lsp-server/pull/241) - Update release instructions to use new build mechanism, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 80](https://github.com/python-lsp/python-lsp-server/pull/80) - Migrate to MarkupContent and convert docstrings to Markdown, by [@krassowski](https://github.com/krassowski) ([22](https://github.com/python-lsp/python-lsp-server/issues/22), [21](https://github.com/python-lsp/python-lsp-server/issues/21))

In this release 16 pull requests were closed.

----

## Version 1.5.0 (2022/07/10)

### New features

* Add `DiagnosticTag` tags for Pylint, Pycodestyle, and Flake8 plugins.
* Add support to connect to the server through websockets.
* Allow multiple per-file-ignores for the same pattern in Flake8 plugin.
* Parse YAPF diffs into TextEdits.
* Add support for LSP formatting `options` parameter.

### Issues Closed

* [Issue 230](https://github.com/python-lsp/python-lsp-server/issues/230) - Flake8 reports wrong severity level for code Fxxx ([PR 234](https://github.com/python-lsp/python-lsp-server/pull/234) by [@lcheylus](https://github.com/lcheylus))
* [Issue 220](https://github.com/python-lsp/python-lsp-server/issues/220) - Flake8 reports wrong severity level for E999 ([PR 223](https://github.com/python-lsp/python-lsp-server/pull/223) by [@jhossbach](https://github.com/jhossbach))
* [Issue 219](https://github.com/python-lsp/python-lsp-server/issues/219) - Add .flake8 to the discovery paths ([PR 233](https://github.com/python-lsp/python-lsp-server/pull/233) by [@lcheylus](https://github.com/lcheylus))
* [Issue 209](https://github.com/python-lsp/python-lsp-server/issues/209) - Rope completions enabled or disabled by default? ([PR 210](https://github.com/python-lsp/python-lsp-server/pull/210) by [@rchl](https://github.com/rchl))
* [Issue 157](https://github.com/python-lsp/python-lsp-server/issues/157) - Please add basic usage documentation ([PR 185](https://github.com/python-lsp/python-lsp-server/pull/185) by [@jgollenz](https://github.com/jgollenz))
* [Issue 144](https://github.com/python-lsp/python-lsp-server/issues/144) - Add `DiagnosticTag` tags for pylint, pycodestyle, and flake8 ([PR 229](https://github.com/python-lsp/python-lsp-server/pull/229) by [@krassowski](https://github.com/krassowski))
* [Issue 140](https://github.com/python-lsp/python-lsp-server/issues/140) - Flake8 plugins issues ([PR 215](https://github.com/python-lsp/python-lsp-server/pull/215) by [@yeraydiazdiaz](https://github.com/yeraydiazdiaz))
* [Issue 117](https://github.com/python-lsp/python-lsp-server/issues/117) - Websockets built-in support ([PR 128](https://github.com/python-lsp/python-lsp-server/pull/128) by [@npradeep357](https://github.com/npradeep357))

In this release 8 issues were closed.

### Pull Requests Merged

* [PR 234](https://github.com/python-lsp/python-lsp-server/pull/234) - Report Flake8 errors with Error severity level, by [@lcheylus](https://github.com/lcheylus) ([230](https://github.com/python-lsp/python-lsp-server/issues/230))
* [PR 233](https://github.com/python-lsp/python-lsp-server/pull/233) - Fix documentation for location of Flake8 configuration files, by [@lcheylus](https://github.com/lcheylus) ([219](https://github.com/python-lsp/python-lsp-server/issues/219))
* [PR 231](https://github.com/python-lsp/python-lsp-server/pull/231) - Use Numpy less than 1.23 in our tests, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 229](https://github.com/python-lsp/python-lsp-server/pull/229) - Add `DiagnosticTag` support, by [@krassowski](https://github.com/krassowski) ([144](https://github.com/python-lsp/python-lsp-server/issues/144))
* [PR 228](https://github.com/python-lsp/python-lsp-server/pull/228) - Improve schema type compliance, improve CONFIGURATION.md, by [@krassowski](https://github.com/krassowski)
* [PR 225](https://github.com/python-lsp/python-lsp-server/pull/225) - Add autopep8.enabled to the configuration schema, by [@j2kun](https://github.com/j2kun)
* [PR 223](https://github.com/python-lsp/python-lsp-server/pull/223) - Change severity level for flake8 errors, by [@jhossbach](https://github.com/jhossbach) ([220](https://github.com/python-lsp/python-lsp-server/issues/220))
* [PR 221](https://github.com/python-lsp/python-lsp-server/pull/221) - Remove preload module from Readme, by [@bageljrkhanofemus](https://github.com/bageljrkhanofemus)
* [PR 217](https://github.com/python-lsp/python-lsp-server/pull/217) - Allow multiple per-file-ignores for the same pattern in flake8 plugin, by [@dedi](https://github.com/dedi)
* [PR 215](https://github.com/python-lsp/python-lsp-server/pull/215) - Remove reference to pyls-flake8 in Readme, by [@yeraydiazdiaz](https://github.com/yeraydiazdiaz) ([140](https://github.com/python-lsp/python-lsp-server/issues/140))
* [PR 211](https://github.com/python-lsp/python-lsp-server/pull/211) - Restore the copyright headers in `setup.cfg` and `pyproject.toml`, by [@KOLANICH](https://github.com/KOLANICH)
* [PR 210](https://github.com/python-lsp/python-lsp-server/pull/210) - Match rope_completions setting documentation with reality, by [@rchl](https://github.com/rchl) ([209](https://github.com/python-lsp/python-lsp-server/issues/209))
* [PR 207](https://github.com/python-lsp/python-lsp-server/pull/207) - Move the project metadata into `PEP 621`-compliant `pyproject.toml`, by [@KOLANICH](https://github.com/KOLANICH)
* [PR 187](https://github.com/python-lsp/python-lsp-server/pull/187) - Add plugins for pylint and flake8 to readme, by [@bageljrkhanofemus](https://github.com/bageljrkhanofemus)
* [PR 185](https://github.com/python-lsp/python-lsp-server/pull/185) - Mention `pylsp` command in README, by [@jgollenz](https://github.com/jgollenz) ([157](https://github.com/python-lsp/python-lsp-server/issues/157))
* [PR 181](https://github.com/python-lsp/python-lsp-server/pull/181) - Fix section that was misplaced in changelog, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 136](https://github.com/python-lsp/python-lsp-server/pull/136) - Parse YAPF diffs into TextEdits (instead of sending the full doc), by [@masad-frost](https://github.com/masad-frost)
* [PR 134](https://github.com/python-lsp/python-lsp-server/pull/134) - Add support for LSP formatting `options` parameter, by [@masad-frost](https://github.com/masad-frost)
* [PR 128](https://github.com/python-lsp/python-lsp-server/pull/128) - Add web sockets support, by [@npradeep357](https://github.com/npradeep357) ([117](https://github.com/python-lsp/python-lsp-server/issues/117))

In this release 19 pull requests were closed.

----

## Version 1.4.1 (2022/03/27)

### Pull Requests Merged

* [PR 179](https://github.com/python-lsp/python-lsp-server/pull/179) - Fix Yapf formatting with CRLF line endings, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 174](https://github.com/python-lsp/python-lsp-server/pull/174) - Improved documentation regarding configuration, by [@spookylukey](https://github.com/spookylukey)

In this release 2 pull requests were closed.

----

## Version 1.4.0 (2022/03/11)

### New features

* Support pycodestyle indent-size option
* Add `DiagnosticTag` constants from LSP 3.15
* Drop support for Python 3.6

### Issues Closed

* [Issue 153](https://github.com/python-lsp/python-lsp-server/issues/153) - Plugin crash crashes whole diagnostic ([PR 158](https://github.com/python-lsp/python-lsp-server/pull/158) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 150](https://github.com/python-lsp/python-lsp-server/issues/150) - README.md: Windows users trying to install the *extras* in `cmd.exe` need to use double quotes instead of single quotes ([PR 163](https://github.com/python-lsp/python-lsp-server/pull/163) by [@ScientificProgrammer](https://github.com/ScientificProgrammer))
* [Issue 147](https://github.com/python-lsp/python-lsp-server/issues/147) - C extensions printing on import break pylint diagnostics
* [Issue 143](https://github.com/python-lsp/python-lsp-server/issues/143) - Still shows diagnostics on closed files ([PR 165](https://github.com/python-lsp/python-lsp-server/pull/165) by [@ccordoba12](https://github.com/ccordoba12))
* [Issue 126](https://github.com/python-lsp/python-lsp-server/issues/126) - Use git-based versioning

In this release 5 issues were closed.

### Pull Requests Merged

* [PR 165](https://github.com/python-lsp/python-lsp-server/pull/165) - Clear diagnostics when closing documents, by [@ccordoba12](https://github.com/ccordoba12) ([143](https://github.com/python-lsp/python-lsp-server/issues/143))
* [PR 163](https://github.com/python-lsp/python-lsp-server/pull/163) - Update single quotes to double quotes for install command examples, by [@ScientificProgrammer](https://github.com/ScientificProgrammer) ([150](https://github.com/python-lsp/python-lsp-server/issues/150))
* [PR 158](https://github.com/python-lsp/python-lsp-server/pull/158) - Prevent third-party plugins with faulty hooks to crash the server, by [@ccordoba12](https://github.com/ccordoba12) ([153](https://github.com/python-lsp/python-lsp-server/issues/153))
* [PR 154](https://github.com/python-lsp/python-lsp-server/pull/154) - Prevent faulty third-party plugins to crash the server, by [@arian-f](https://github.com/arian-f)
* [PR 151](https://github.com/python-lsp/python-lsp-server/pull/151) - Fix Autopep8 and Yapf formatting with CR line endings, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 148](https://github.com/python-lsp/python-lsp-server/pull/148) - Fix pygame greeting breaking pylint diagnostics, by [@piotr-machura](https://github.com/piotr-machura)
* [PR 142](https://github.com/python-lsp/python-lsp-server/pull/142) - Add `DiagnosticTag` constants from LSP 3.15, by [@krassowski](https://github.com/krassowski)
* [PR 141](https://github.com/python-lsp/python-lsp-server/pull/141) - Support pycodestyle indent-size option, by [@mnauw](https://github.com/mnauw)
* [PR 138](https://github.com/python-lsp/python-lsp-server/pull/138) - Make pylint test Python version independent, by [@jspricke](https://github.com/jspricke)
* [PR 137](https://github.com/python-lsp/python-lsp-server/pull/137) - Add license info to `setup.py` so it will show up in wheel installs, by [@itsbenweeks](https://github.com/itsbenweeks)
* [PR 130](https://github.com/python-lsp/python-lsp-server/pull/130) - Update Python base version to 3.7+, by [@npradeep357](https://github.com/npradeep357)
* [PR 84](https://github.com/python-lsp/python-lsp-server/pull/84) - Move the package metadata from setup.py to setup.cfg, by [@KOLANICH](https://github.com/KOLANICH) ([84](https://github.com/python-lsp/python-lsp-server/issues/84))

In this release 12 pull requests were closed.

----

## Version 1.3.3 (2021-12-13)

### Issues Closed

* [Issue 123](https://github.com/python-lsp/python-lsp-server/issues/123) - Resolving completion triggers an error ([PR 125](https://github.com/python-lsp/python-lsp-server/pull/125) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 133](https://github.com/python-lsp/python-lsp-server/pull/133) - Fix test_syntax_error_pylint_py3 for Python 3.10, by [@ArchangeGabriel](https://github.com/ArchangeGabriel)
* [PR 125](https://github.com/python-lsp/python-lsp-server/pull/125) - Fix error when resolving completion items for Rope, by [@ccordoba12](https://github.com/ccordoba12) ([123](https://github.com/python-lsp/python-lsp-server/issues/123))

In this release 2 pull requests were closed.

----

## Version 1.3.2 (2021-11-25)

### Issues Closed

* [Issue 121](https://github.com/python-lsp/python-lsp-server/issues/121) - Error on triggering completions in import context ([PR 122](https://github.com/python-lsp/python-lsp-server/pull/122) by [@ccordoba12](https://github.com/ccordoba12))

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 122](https://github.com/python-lsp/python-lsp-server/pull/122) - Fix formatting a log message, by [@ccordoba12](https://github.com/ccordoba12) ([121](https://github.com/python-lsp/python-lsp-server/issues/121))

In this release 1 pull request was closed.

----

## Version 1.3.1 (2021-11-22)

### Pull Requests Merged

* [PR 118](https://github.com/python-lsp/python-lsp-server/pull/118) - Fix tests for Jedi 0.18.1, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 1.3.0 (2021-11-22)

### New features

* Create a cache for code snippets to speed up completions.

### Important changes

* Option `jedi_completion.resolve_at_most_labels` was renamed to `jedi_completion.resolve_at_most`
  because now it controls how many labels and snippets will be resolved per request.
* Option `jedi_completion.cache_labels_for` was renamed to `jedi_completion.cache_for` because now
  it controls the modules for which labels and snippets should be cached.
* Update requirements on Pylint, flake8, pycodestyle, pyflakes and autopep8.

### Pull Requests Merged

* [PR 112](https://github.com/python-lsp/python-lsp-server/pull/112) - Fix another test with Python 3.10, by [@jspricke](https://github.com/jspricke)
* [PR 111](https://github.com/python-lsp/python-lsp-server/pull/111) - Use sys.executable in flake8 plugin to make tests pass on systems that don't provide a python link, by [@0-wiz-0](https://github.com/0-wiz-0)
* [PR 108](https://github.com/python-lsp/python-lsp-server/pull/108) - Fix test with Python 3.10, by [@jspricke](https://github.com/jspricke)
* [PR 102](https://github.com/python-lsp/python-lsp-server/pull/102) - Update requirements on flake8 and its dependencies, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 99](https://github.com/python-lsp/python-lsp-server/pull/99) - Adjust readme to pylsp-mypy rename, by [@chaoflow](https://github.com/chaoflow)
* [PR 94](https://github.com/python-lsp/python-lsp-server/pull/94) - Unpin Pylint, by [@bnavigator](https://github.com/bnavigator)
* [PR 83](https://github.com/python-lsp/python-lsp-server/pull/83) - Create a cache for snippets, by [@ccordoba12](https://github.com/ccordoba12)

In this release 7 pull requests were closed.

----

## Version 1.2.4 (2021-10-11)

### Pull Requests Merged

* [PR 96](https://github.com/python-lsp/python-lsp-server/pull/96) - Pin flake8 to be less than version 4, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 1.2.3 (2021-10-04)

### Pull Requests Merged

* [PR 93](https://github.com/python-lsp/python-lsp-server/pull/93) - Document how to write python-lsp-server plugin + add pylsp-rope to Readme, by [@lieryan](https://github.com/lieryan)
* [PR 88](https://github.com/python-lsp/python-lsp-server/pull/88) - Fix pylint test without pylsp installed, by [@jspricke](https://github.com/jspricke)

In this release 2 pull requests were closed.

----

## Version 1.2.2 (2021-09-01)

### Pull Requests Merged

* [PR 78](https://github.com/python-lsp/python-lsp-server/pull/78) - Require Pylint less than 2.10, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 71](https://github.com/python-lsp/python-lsp-server/pull/71) - Improve how we determine if a symbol was imported from other libraries, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 67](https://github.com/python-lsp/python-lsp-server/pull/67) - Recognize the "I" pylint stdio message category, by [@Wuestengecko](https://github.com/Wuestengecko)
* [PR 66](https://github.com/python-lsp/python-lsp-server/pull/66) - Remove temp file and ignore that kind of files, by [@ccordoba12](https://github.com/ccordoba12)

In this release 4 pull requests were closed.

----

## Version 1.2.1 (2021-08-04)

### Issues Closed

* [Issue 65](https://github.com/python-lsp/python-lsp-server/issues/65) - Release v1.2.1

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 64](https://github.com/python-lsp/python-lsp-server/pull/64) - Catch errors when getting docstrings on _resolve_completion, by [@ccordoba12](https://github.com/ccordoba12)

In this release 1 pull request was closed.

----

## Version 1.2.0 (2021-08-01)

### New features

* Implement completion item resolve requests for faster completions.
* Initialize workspaces from the initialize request.

### Issues Closed

* [Issue 55](https://github.com/python-lsp/python-lsp-server/issues/55) - Is emanspeaks/pyls-flake8 the preferred plugin for flake8 linting? ([PR 57](https://github.com/python-lsp/python-lsp-server/pull/57) by [@GerardoGR](https://github.com/GerardoGR))
* [Issue 48](https://github.com/python-lsp/python-lsp-server/issues/48) - Workspace folders not initialized properly ([PR 49](https://github.com/python-lsp/python-lsp-server/pull/49) by [@rchl](https://github.com/rchl))
* [Issue 24](https://github.com/python-lsp/python-lsp-server/issues/24) - Where to put structured documentation now? ([PR 51](https://github.com/python-lsp/python-lsp-server/pull/51) by [@krassowski](https://github.com/krassowski))

In this release 3 issues were closed.

### Pull Requests Merged

* [PR 62](https://github.com/python-lsp/python-lsp-server/pull/62) - Make use_document_path equal to True when getting definitions and hovers, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 59](https://github.com/python-lsp/python-lsp-server/pull/59) - Validate if shared_data is not None when resolving completion items, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 58](https://github.com/python-lsp/python-lsp-server/pull/58) - Do not call `get_signatures()` if snippets are disabled, by [@krassowski](https://github.com/krassowski)
* [PR 57](https://github.com/python-lsp/python-lsp-server/pull/57) - Document internal flake8 plugin schema and configuration, by [@GerardoGR](https://github.com/GerardoGR) ([55](https://github.com/python-lsp/python-lsp-server/issues/55))
* [PR 53](https://github.com/python-lsp/python-lsp-server/pull/53) - Fix skipping imported symbols, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 51](https://github.com/python-lsp/python-lsp-server/pull/51) - Restore the JSON schema, add human-readable configuration, by [@krassowski](https://github.com/krassowski) ([24](https://github.com/python-lsp/python-lsp-server/issues/24))
* [PR 49](https://github.com/python-lsp/python-lsp-server/pull/49) - Initialize workspaces from the initialize request, by [@rchl](https://github.com/rchl) ([48](https://github.com/python-lsp/python-lsp-server/issues/48))
* [PR 46](https://github.com/python-lsp/python-lsp-server/pull/46) - Improve release instructions, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 26](https://github.com/python-lsp/python-lsp-server/pull/26) - Implement cached label resolution and label resolution limit, by [@krassowski](https://github.com/krassowski)
* [PR 25](https://github.com/python-lsp/python-lsp-server/pull/25) - Feature/completion item/resolve, by [@krassowski](https://github.com/krassowski)

In this release 10 pull requests were closed.

----

## Version 1.1.0 (2021-06-25)

### New features

* Add support for flake8 per-file-ignores
* Add --version CLI argument and return version in InitializeResult

### Issues Closed

* [Issue 30](https://github.com/python-lsp/python-lsp-server/issues/30) - pylsp_document_symbols raising TypeError from os.path.samefile ([PR 31](https://github.com/python-lsp/python-lsp-server/pull/31) by [@douglasdavis](https://github.com/douglasdavis))
* [Issue 19](https://github.com/python-lsp/python-lsp-server/issues/19) - Linter and tests are failing on due to new "consider-using-with" ([PR 20](https://github.com/python-lsp/python-lsp-server/pull/20) by [@krassowski](https://github.com/krassowski))

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 44](https://github.com/python-lsp/python-lsp-server/pull/44) - Add --version CLI argument and return version in InitializeResult, by [@nemethf](https://github.com/nemethf)
* [PR 42](https://github.com/python-lsp/python-lsp-server/pull/42) - Fix local timezone, by [@e-kwsm](https://github.com/e-kwsm)
* [PR 38](https://github.com/python-lsp/python-lsp-server/pull/38) - Handling list merge in _utils.merge_dicts()., by [@GaetanLepage](https://github.com/GaetanLepage)
* [PR 32](https://github.com/python-lsp/python-lsp-server/pull/32) - PR: Update third-party plugins in README, by [@haplo](https://github.com/haplo)
* [PR 31](https://github.com/python-lsp/python-lsp-server/pull/31) - Catch a TypeError from os.path.samefile, by [@douglasdavis](https://github.com/douglasdavis) ([30](https://github.com/python-lsp/python-lsp-server/issues/30))
* [PR 28](https://github.com/python-lsp/python-lsp-server/pull/28) - Add support for flake8 per-file-ignores, by [@brandonwillard](https://github.com/brandonwillard)
* [PR 20](https://github.com/python-lsp/python-lsp-server/pull/20) - PR: Address pylint's "consider-using-with" warnings, by [@krassowski](https://github.com/krassowski) ([19](https://github.com/python-lsp/python-lsp-server/issues/19))
* [PR 18](https://github.com/python-lsp/python-lsp-server/pull/18) - Fix Jedi type map (use types offered by modern Jedi), by [@krassowski](https://github.com/krassowski)

In this release 8 pull requests were closed.

----

## Version 1.0.1 (2021-04-22)

### Issues Closed

* [Issue 16](https://github.com/python-lsp/python-lsp-server/issues/16) - Release v1.0.1

In this release 1 issue was closed.

### Pull Requests Merged

* [PR 15](https://github.com/python-lsp/python-lsp-server/pull/15) - PR: Update pyflakes and pycodestyle dependency versions, by [@andfoy](https://github.com/andfoy)
* [PR 14](https://github.com/python-lsp/python-lsp-server/pull/14) - PR: Small fix in Readme, by [@yaegassy](https://github.com/yaegassy)

In this release 2 pull requests were closed.

----

## Version 1.0.0 (2021/04/14)

### Issues Closed

* [Issue 13](https://github.com/python-lsp/python-lsp-server/issues/13) - Release v1.0.0
* [Issue 4](https://github.com/python-lsp/python-lsp-server/issues/4) - Transition plan

In this release 2 issues were closed.

### Pull Requests Merged

* [PR 12](https://github.com/python-lsp/python-lsp-server/pull/12) - PR: Use python-lsp-jsonrpc instead of python-jsonrpc-server, by [@andfoy](https://github.com/andfoy)
* [PR 11](https://github.com/python-lsp/python-lsp-server/pull/11) - PR: Remove references to VSCode in Readme, by [@ccordoba12](https://github.com/ccordoba12)
* [PR 10](https://github.com/python-lsp/python-lsp-server/pull/10) - PR: Rename namespace to pylsp and package to python-lsp-server, by [@andfoy](https://github.com/andfoy)
* [PR 9](https://github.com/python-lsp/python-lsp-server/pull/9) - TST: accept folding of decorator parameters in Python 3.9, by [@bnavigator](https://github.com/bnavigator) ([8](https://github.com/python-lsp/python-lsp-server/issues/8))
* [PR 7](https://github.com/python-lsp/python-lsp-server/pull/7) - Unpin numpy, by [@bnavigator](https://github.com/bnavigator)
* [PR 6](https://github.com/python-lsp/python-lsp-server/pull/6) - Rewrite README from rst to md, by [@xiaoxiae](https://github.com/xiaoxiae)
* [PR 5](https://github.com/python-lsp/python-lsp-server/pull/5) - Update README.rst, by [@marimeireles](https://github.com/marimeireles)
* [PR 3](https://github.com/python-lsp/python-lsp-server/pull/3) - Fix CI tests by temporarily pinning numpy; update repo paths, by [@krassowski](https://github.com/krassowski)
* [PR 2](https://github.com/python-lsp/python-lsp-server/pull/2) - bump jedi compatibility: compare to Path-like object, by [@bnavigator](https://github.com/bnavigator)

In this release 9 pull requests were closed.
