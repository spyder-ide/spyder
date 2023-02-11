# Python Language Server Configuration
This server can be configured using the `workspace/didChangeConfiguration` method. Each configuration option is described below. Note, a value of `null` means that we do not set a value and thus use the plugin's default value.

| **Configuration Key** | **Type** | **Description** | **Default** 
|----|----|----|----|
| `pylsp.configurationSources` | `array` of unique `string` (one of: `'pycodestyle'`, `'flake8'`) items | List of configuration sources to use. | `["pycodestyle"]` |
| `pylsp.plugins.autopep8.enabled` | `boolean` | Enable or disable the plugin (disabling required to use `yapf`). | `true` |
| `pylsp.plugins.flake8.config` | `string` | Path to the config file that will be the authoritative config source. | `null` |
| `pylsp.plugins.flake8.enabled` | `boolean` | Enable or disable the plugin. | `false` |
| `pylsp.plugins.flake8.exclude` | `array` of `string` items | List of files or directories to exclude. | `[]` |
| `pylsp.plugins.flake8.executable` | `string` | Path to the flake8 executable. | `"flake8"` |
| `pylsp.plugins.flake8.filename` | `string` | Only check for filenames matching the patterns in this list. | `null` |
| `pylsp.plugins.flake8.hangClosing` | `boolean` | Hang closing bracket instead of matching indentation of opening bracket's line. | `null` |
| `pylsp.plugins.flake8.ignore` | `array` of `string` items | List of errors and warnings to ignore (or skip). | `[]` |
| `pylsp.plugins.flake8.maxComplexity` | `integer` | Maximum allowed complexity threshold. | `null` |
| `pylsp.plugins.flake8.maxLineLength` | `integer` | Maximum allowed line length for the entirety of this run. | `null` |
| `pylsp.plugins.flake8.indentSize` | `integer` | Set indentation spaces. | `null` |
| `pylsp.plugins.flake8.perFileIgnores` | `array` of `string` items | A pairing of filenames and violation codes that defines which violations to ignore in a particular file, for example: `["file_path.py:W305,W304"]`). | `[]` |
| `pylsp.plugins.flake8.select` | `array` of unique `string` items | List of errors and warnings to enable. | `null` |
| `pylsp.plugins.jedi.auto_import_modules` | `array` of `string` items | List of module names for jedi.settings.auto_import_modules. | `["numpy"]` |
| `pylsp.plugins.jedi.extra_paths` | `array` of `string` items | Define extra paths for jedi.Script. | `[]` |
| `pylsp.plugins.jedi.env_vars` | `object` | Define environment variables for jedi.Script and Jedi.names. | `null` |
| `pylsp.plugins.jedi.environment` | `string` | Define environment for jedi.Script and Jedi.names. | `null` |
| `pylsp.plugins.jedi_completion.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_completion.include_params` | `boolean` | Auto-completes methods and classes with tabstops for each parameter. | `true` |
| `pylsp.plugins.jedi_completion.include_class_objects` | `boolean` | Adds class objects as a separate completion item. | `false` |
| `pylsp.plugins.jedi_completion.include_function_objects` | `boolean` | Adds function objects as a separate completion item. | `false` |
| `pylsp.plugins.jedi_completion.fuzzy` | `boolean` | Enable fuzzy when requesting autocomplete. | `false` |
| `pylsp.plugins.jedi_completion.eager` | `boolean` | Resolve documentation and detail eagerly. | `false` |
| `pylsp.plugins.jedi_completion.resolve_at_most` | `integer` | How many labels and snippets (at most) should be resolved? | `25` |
| `pylsp.plugins.jedi_completion.cache_for` | `array` of `string` items | Modules for which labels and snippets should be cached. | `["pandas", "numpy", "tensorflow", "matplotlib"]` |
| `pylsp.plugins.jedi_definition.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_definition.follow_imports` | `boolean` | The goto call will follow imports. | `true` |
| `pylsp.plugins.jedi_definition.follow_builtin_imports` | `boolean` | If follow_imports is True will decide if it follow builtin imports. | `true` |
| `pylsp.plugins.jedi_definition.follow_builtin_definitions` | `boolean` | Follow builtin and extension definitions to stubs. | `true` |
| `pylsp.plugins.jedi_hover.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_references.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_signature_help.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_symbols.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.jedi_symbols.all_scopes` | `boolean` | If True lists the names of all scopes instead of only the module namespace. | `true` |
| `pylsp.plugins.jedi_symbols.include_import_symbols` | `boolean` | If True includes symbols imported from other libraries. | `true` |
| `pylsp.plugins.mccabe.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.mccabe.threshold` | `integer` | The minimum threshold that triggers warnings about cyclomatic complexity. | `15` |
| `pylsp.plugins.preload.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.preload.modules` | `array` of unique `string` items | List of modules to import on startup | `[]` |
| `pylsp.plugins.pycodestyle.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.pycodestyle.exclude` | `array` of unique `string` items | Exclude files or directories which match these patterns. | `[]` |
| `pylsp.plugins.pycodestyle.filename` | `array` of unique `string` items | When parsing directories, only check filenames matching these patterns. | `[]` |
| `pylsp.plugins.pycodestyle.select` | `array` of unique `string` items | Select errors and warnings | `null` |
| `pylsp.plugins.pycodestyle.ignore` | `array` of unique `string` items | Ignore errors and warnings | `[]` |
| `pylsp.plugins.pycodestyle.hangClosing` | `boolean` | Hang closing bracket instead of matching indentation of opening bracket's line. | `null` |
| `pylsp.plugins.pycodestyle.maxLineLength` | `integer` | Set maximum allowed line length. | `null` |
| `pylsp.plugins.pycodestyle.indentSize` | `integer` | Set indentation spaces. | `null` |
| `pylsp.plugins.pydocstyle.enabled` | `boolean` | Enable or disable the plugin. | `false` |
| `pylsp.plugins.pydocstyle.convention` | `string` (one of: `'pep257'`, `'numpy'`, `'google'`, `None`) | Choose the basic list of checked errors by specifying an existing convention. | `null` |
| `pylsp.plugins.pydocstyle.addIgnore` | `array` of unique `string` items | Ignore errors and warnings in addition to the specified convention. | `[]` |
| `pylsp.plugins.pydocstyle.addSelect` | `array` of unique `string` items | Select errors and warnings in addition to the specified convention. | `[]` |
| `pylsp.plugins.pydocstyle.ignore` | `array` of unique `string` items | Ignore errors and warnings | `[]` |
| `pylsp.plugins.pydocstyle.select` | `array` of unique `string` items | Select errors and warnings | `null` |
| `pylsp.plugins.pydocstyle.match` | `string` | Check only files that exactly match the given regular expression; default is to match files that don't start with 'test_' but end with '.py'. | `"(?!test_).*\\.py"` |
| `pylsp.plugins.pydocstyle.matchDir` | `string` | Search only dirs that exactly match the given regular expression; default is to match dirs which do not begin with a dot. | `"[^\\.].*"` |
| `pylsp.plugins.pyflakes.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.plugins.pylint.enabled` | `boolean` | Enable or disable the plugin. | `false` |
| `pylsp.plugins.pylint.args` | `array` of non-unique `string` items | Arguments to pass to pylint. | `[]` |
| `pylsp.plugins.pylint.executable` | `string` | Executable to run pylint with. Enabling this will run pylint on unsaved files via stdin. Can slow down workflow. Only works with python3. | `null` |
| `pylsp.plugins.rope_autoimport.enabled` | `boolean` | Enable or disable autoimport. | `false` |
| `pylsp.plugins.rope_autoimport.memory` | `boolean` | Make the autoimport database memory only. Drastically increases startup time. | `false` |
| `pylsp.plugins.rope_completion.enabled` | `boolean` | Enable or disable the plugin. | `false` |
| `pylsp.plugins.rope_completion.eager` | `boolean` | Resolve documentation and detail eagerly. | `false` |
| `pylsp.plugins.yapf.enabled` | `boolean` | Enable or disable the plugin. | `true` |
| `pylsp.rope.extensionModules` | `string` | Builtin and c-extension modules that are allowed to be imported and inspected by rope. | `null` |
| `pylsp.rope.ropeFolder` | `array` of unique `string` items | The name of the folder in which rope stores project configurations and data.  Pass `null` for not using such a folder at all. | `null` |

This documentation was generated from `pylsp/config/schema.json`. Please do not edit this file directly.
