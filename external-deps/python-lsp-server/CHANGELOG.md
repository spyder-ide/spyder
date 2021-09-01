# History of changes

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
