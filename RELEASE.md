# Instructions to release a new Spyder version

To release a new version of Spyder you need to follow these steps:

## Update translation strings (at least one week before the release)

* Install [gettext-helpers](https://github.com/spyder-ide/gettext-helpers) from source.
* Update the `*.pot` and `*.po` translation files by following these steps:
  * Run `spyder-gettext scan spyder` to update localization files.
  * Check that no warning messages are emmitted by that command.
  * Create and merge a new PR with these updated files.
  * Once merged, the new strings are now available on Crowdin.
* Close the current translation PR and delete the `translate/<branch-name>` branch associated with it.
* Go to the [integrations page](https://crowdin.com/project/spyder/settings#integration) on Crowdin and press `Sync now` to open a new translation PR.
* Request translators on a Github issue to update their translations on Crowdin. This can take between a couple of days to a couple of weeks depending on the amount of strings to translate. It's necessary to wait for that before proceeding to the next step.


## Before starting the release

### Merge translations PR from Crowdin

* Checkout the translation PR and update the `*.mo` files in there by running `spyder-gettext compile spyder`.
* Squash all commits in that PR into a single one. This commit will include the `*.pot`, `*.po` and `*.mo` file changes.
* Rename the PR title to be `PR: Update translations from Crowdin`.
* Once that's done, merge the PR to finish the process.
* Don't forget to remove your local checkout of `translate/<branch-name>` because that's going to be outdated for next time.

### Update core dependencies

* Release a new version of spyder-kernels, if required.
* Release a new version version of python-language-server, if required.
* In a PR update `setup.py`, `spyder/dependencies.py` and `spyder/plugins/ipythonconsole/plugin.py` with the new versions of those two packages. Also update their respective subrepos.


## To do the release

* Close the current milestone Github

* git pull or git fetch/merge

* Update CHANGELOG.md with `loghub spyder-ide/spyder -m vX.X.X`

* Add sections for `New features` and `Important fixes` in CHANGELOG.md. For this take a look at closed issues and PRs for the current milestone.

* git commit with "Update Changelog"

* Update Announcements.md (this goes to our Google group)

* git commit with "Update Announcements".

* `git clean -xfdi` and select option `1`.

* Update version in `__init__.py` (set release version, remove 'dev0')

* `git add .` and git commit with `Release X.X.X`

* python setup.py sdist

* Activate environment with pip packages (conda env or virtualenv)

* pip install -U pip setuptools twine wheel

* python3 setup.py bdist_wheel

* twine check dist/*

* twine upload dist/*

* git tag -a vX.X.X -m 'Release X.X.X'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* `git add .` and git commit with `Back to work [ci skip]`

* git checkout master

* git merge 4.x

* git commit with `Release X.X.X [ci skip]`

* git push upstream master

* git push upstream 4.x

* git push upstream --tags

* Publish release in our Github Releases page

* Publish release announcements to our list
