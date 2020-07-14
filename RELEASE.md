# Release

To release a new version of Spyder you need to follow these steps:

## Localization updates

* Install [gettext-helpers](https://github.com/spyder-ide/gettext-helpers) from source.
* Update the `*.pot` and `*.po` translation files by following these steps:
  * Run `spyder-gettext scan spyder` to update localization files.
  * Create and merge a new PR with these updated files.
  * Once merged, the new strings are now available on Crowdin.
* Close the current translation PR and delete the `translate/<branch-name>` branch associated with it.
* Go to the [integrations page](https://crowdin.com/project/spyder/settings#integration) on Crowdin and press `Sync now` to open a new translation PR.
* Request translators on a Github issue to update their translations on Crowdin. This can take between a couple of days to a couple of weeks depending on the amount of strings to translate. It's necessary to wait for that before proceeding to the next step.
* Checkout the translation PR and update the `*.mo` files in there by running `spyder-gettext compile spyder`.
* Squash all commits in that PR into a single one. This commit will include the `*.pot`, `*.po` and `*.mo` file changes.
* Once that's done, merge the PR to finish the process.
* Don't forget to remove your local checkout of `translate/<branch-name>` because that's going to be outdated for next time.

## Release updates

* Close the current project Github

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

* twine check dist/*

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
