# Release

To release a new version of Spyder you need to follow these steps:

## Localization updates

* Install [gettext-helpers](https://github.com/spyder-ide/gettext-helpers) from source.

* Update `*.pot` and `*.po` files to update translation strings by following these steps:
  * Run `spyder-gettext scan spyder` to update localization files.
  * Create and merge a new PR with these updated files
  * Once merged, the new strings are now available on [Crowdin](https://crowdin.com/project/spyder).
  * Request translators to update the translation strings on [Crowdin](https://crowdin.com/project/spyder). This process can take between a couple of days to a couple of weeks depending on the amount of strings to translate and we need to wait before proceeding to the next step.

* Close the automatic translation bot PR `translate/<branch-name>`,
* Delete the branch to recreate the branch automatically without conflicts (if any)
  * Using this command: `git push origin --delete translate/<branch-name>`.
  * Or, on the [github website](https://github.com/spyder-ide/spyder/branches)

* Wait for the new `translate/<branch-name>` PR to be created by the `spyder-bot`. This branch should be created within 10 minutes.

* Update `*.mo` files to update translation strings by following these steps:

  * Run `spyder-gettext compile spyder` to update localization binary files.

* Update the translation PR `translate/<branch-name>` to include these files and squash all commits into 1 single commit. These commits will include the `*.pot`, `*.po` and `*.mo` file changes. Once this has been accomplished merge the PR. Localization updates are now ready.

## Release updates

* Close the current release on Zenhub

* git pull or git fetch/merge

* Update CHANGELOG.md with `loghub spyder-ide/spyder -zr "spyder vX.X.X"`

* Update Announcements.md

* git clean -xfdi

* Update version in `__init__.py` (set release version, remove 'dev0')

* git add and git commit with `Release X.X.X`

* python setup.py sdist

* activate py2env-with-latest-setuptools && python2 setup.py bdist_wheel

* activate py3env-with-latest-setuptools && python3 setup.py bdist_wheel

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* git add and git commit with `Back to work [ci skip]`

* git checkout master

* git merge 4.x

* git commit with `Release X.X.X [ci skip]`

* git push upstream master

* git push upstream 4.x

* git push upstream --tags

* Publish release announcements to our list and the SciPy list

* Publish release in our Github Releases page
