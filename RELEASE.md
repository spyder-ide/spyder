# Instructions to release a new Spyder version

To release a new version of Spyder you need to follow these steps:

## Update translation strings (at least one week before the release)

* Install [gettext-helpers](https://github.com/spyder-ide/gettext-helpers) from source.

* Create a new PR to update our `*.pot` and `*.po` files by running

      spyder-gettext scan spyder

* Check that no warnings are emitted by that command. If they are, then fix them in the same PR.

* Merge that PR.

* Close the current translation PR, i.e. the one with the title `New Crowdin updates`.

* Delete the `translate/<branch-name>` branch associated to that PR.

* Go to the integrations page on Crowdin:

  https://crowdin.com/project/spyder/settings#integration-github

* Press `Sync now` there to open a new translation PR.

* Send a message to translators on Crowdin to update their translations:

  https://crowdin.com/messages

  An example of that message can be found in

  https://github.com/spyder-ide/spyder/issues/14117

## Before starting the release

### Merge translations from Crowdin

* Checkout the translations branch with

      git checkout translate/<branch-name>

* Squash all commits in that branch to leave only one with the command

      git rebase --interactive HEAD~N

  where N is the number of commits on it.

* Change the commit message with

      git commit --amend

  to be `Update and compile translations [ci skip]`

* Generate the `mo` files by running

      spyder-gettext compile spyder

* Remove `mo` files that are still not part of version control.

* Add those files to the previous commit with

      git add .
      git commit --amend --no-edit

* Push your changes to the translation PR with

      git push -f upstream translate/<branch-name>

* Rename the PR title to be `PR: Update translations from Crowdin`.

* Merge the PR.

* Don't forget to remove your local checkout of `translate/<branch-name>` because that's going to be outdated for next time.

* Update the `master` branch with

      git checkout 4.x
      git fetch upstream
      git merge upstream/4.x
      git checkout master
      git merge 4.x
      Merge from 4.x: PR #xxxxx
      git push upstream master

### Update core dependencies

* Release a new version of `spyder-kernels`, if required.

* Release a new version of `python-language-server`, if required.

* Create a new branch in your fork with the name `update-core-deps`

* In case a new version is not part of the `defaults` channel yet, you need to copy it to our channel with the following command:

      anaconda copy conda-forge/pyls-spyder/0.3.2 --to-label dev --to-owner spyder-ide

  *Note*: For this you need to install first the `anaconda-client` package in your `base` environment and open an account in https://anaconda.org/

* Update the version of any packages required before the release in the following files:

  - `setup.py`
  - `spyder/dependencies.py`
  - `requirements/conda.txt`
  - `binder/environment.yml`
  - `spyder/plugins/ipythonconsole/plugin.py`

* Commit with

      git add .
      git commit -m "Update core dependencies"

* Update our subrepos with the following commands, but only if new versions are available!

      git subrepo pull external-deps/spyder-kernels
      git subrepo pull external-deps/python-language-server

* Merge this PR following the procedure mentioned on `MAINTENANCE.md`

## To do the release

* Close the current milestone on Github

* git pull or git fetch/merge

* Update CHANGELOG.md with `loghub spyder-ide/spyder -m vX.X.X`

* Add sections for `New features` and `Important fixes` in CHANGELOG.md. For this take a look at closed issues and PRs for the current milestone.

* `git add .` and `git commit -m "Update Changelog"`

* Update Announcements.md (this goes to our Google group)

* `git add .` and `git commit -m "Update Announcements"`

* `git clean -xfdi` and select option `1`.

* Update version in `__init__.py` (set release version, remove 'dev0')

* `git add .` and `git commit -m "Release X.X.X"`

* python setup.py sdist

* Activate environment with pip packages only

* pip install -U pip setuptools twine wheel

* python3 setup.py bdist_wheel

* twine check dist/*

* twine upload dist/*

* Check in PyPI that the new release was published correctly

* git tag -a vX.X.X -m 'Release X.X.X'

* Update version in `__init__.py` (add 'dev0' and increment minor)

* `git add .` and `git commit -m "Back to work [ci skip]"`

* git checkout master

* git merge 5.x

* git commit -m "Release X.X.X [ci skip]"

* git push upstream master

* git push upstream 5.x

* git push upstream --tags


## After the release

* Publish release in our Github Releases page.

* Publish release announcements to our list.

* Merge PRs on Conda-forge that update the `spyder-kernels` and `python-language-server` feedstocks.

  **Notes**:

  - Review carefully the release notes of those packages to see if it's necessary to add new dependencies or update the constraints on the current ones (e.g. `jedi >=0.17.2`).
  - After merging each of those PRs, give a ping to the Anaconda team telling them that these packages are required for the new Spyder version. You need to use the handle `@anaconda-pkg-build` for that. Here is an example of this kinf of messages:

    https://github.com/conda-forge/spyder-kernels-feedstock/pull/58#issuecomment-725664085

* After those PRs are merged, go to

  https://github.com/conda-forge/spyder-feedstock

  and merge the corresponding PR for the new release.

  **Notes**:

  - Don't forget to add new dependencies and update constraints on the rest of them. For that, you need to compare line by line the contents of the `recipe/meta.yaml` file in the feedstock with

    https://github.com/spyder-ide/spyder/blob/4.x/requirements/conda.txt
  - After merging, give a ping to `@anaconda-pkg-build` about the new release.
