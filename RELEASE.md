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

  https://crowdin.com/project/spyder/apps/system/github

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

      git checkout 5.x
      git fetch upstream
      git merge upstream/5.x
      git checkout master
      git merge 5.x
      Merge from 5.x: PR #xxxxx
      git push upstream master

### Update core dependencies

* Release a new version of `spyder-kernels`, if required.

* Release a new version of `python-lsp-server`, if required.

* Release a new version of `qtconsole`, if required.

* Merge PRs on Conda-forge that update the `spyder-kernels`, `python-lsp-server` and `qtconsole` feedstocks (usually an automatic PR will appear that can be either merged as it is or be used as boilerplate):

  - `spyder-kernels`: https://github.com/conda-forge/spyder-kernels-feedstock

  - `python-lsp-server`: https://github.com/conda-forge/python-lsp-server-feedstock

  - `qtconsole`: https://github.com/conda-forge/qtconsole-feedstock

  **Notes**:

  - Review carefully the release notes of those packages to see if it's necessary to add new dependencies or update the constraints on the current ones (e.g. `jedi >=0.17.2`).

* Create a new branch in your fork with the name `update-core-deps`

* Update the version of any packages required before the release in the following files:

  - `setup.py` (look up for the `install_requires` variable and also for the `Loosen constraints to ensure dev versions still work` patch )
  - `spyder/dependencies.py`
  - `requirements/{main,windows,macos,linux}.yml`
  - `binder/environment.yml`
  - `spyder/plugins/ipythonconsole/__init__.py` (look up for the constants `SPYDER_KERNELS_MIN_VERSION` and `SPYDER_KERNELS_MAX_VERSION`)

      **Note**: Usually, the version of `spyder-kernels` for validation in the IPython Console only needs to be updated for minor or major releases of that package. For bugfix releases the value should remain the same to not hassle users using custom interpreters into updating `spyder-kernels` in their environments. However, this depends on the type of bugs resolved and if it's worthy to reinforce the need of an update even for those versions.

* Commit with

      git add .
      git commit -m "Update core dependencies"

* Update our subrepos with the following commands, but only if new versions are available!

      git subrepo pull external-deps/spyder-kernels
      git subrepo pull external-deps/python-lsp-server
      git subrepo pull external-deps/qtconsole

* Merge this PR following the procedure mentioned on [`MAINTENANCE.md`](MAINTENANCE.md)

### Check release candidate

* Update version in `__init__.py` (set release version, remove '.dev0', add 'rcX'), then

      git add .
      git commit -m "Release X.X.XrcX [ci skip]"
      git push upstream 5.x

* Manually activate the following workflows (see [Running a workflow](https://docs.github.com/en/actions/managing-workflow-runs/manually-running-a-workflow#running-a-workflow)):
    - Create Windows Installer *
    - Create macOS App Bundle and DMG *
    - Create conda-based installers for Linux

      **Note:** For the Windows and macOS installers you need to trigger their workflows through the [GitHub REST API](https://docs.github.com/en/rest/actions/workflows?apiVersion=2022-11-28#create-a-workflow-dispatch-event) or using the [GitHub CLI](https://cli.github.com/manual/gh_workflow_run) (the GitHub CLI is available at https://cli.github.com/). In case the GitHub CLI is used, you need to run:

      * For the `Create Windows Installer` workflow:

            gh workflow run installer-win.yml --ref 5.x

      * For the `Create macOS App Bundle and DMG` workflow:

            gh workflow run installer-macos.yml --ref 5.x

* Download and test the installation of the resulting artifacts.

* If one of the previous steps fail, merge a fix PR and start the process again with an incremented 'rcX' commit.

## To do the release

* Close the current milestone on Github

* git pull or git fetch/merge

* Update `changelogs/Spyder-5.md` with `loghub spyder-ide/spyder -m vX.X.X`

* Add sections for `New features`, `Important fixes` and `New API features` in `changelogs/Spyder-5.md`. For this take a look at closed issues and PRs for the current milestone.

* `git add .` and `git commit -m "Update Changelog"`

* Update [Announcements.md](Announcements.md) (this goes to our Google group) removing the outdated announcement of the same kind (major, minor, or beta/release candidate)

* `git add .` and `git commit -m "Update Announcements"`

* `git clean -xfdi` and select option `1`.

* Update version in `__init__.py` (set release version, remove 'dev0')

* `git add .` and `git commit -m "Release X.X.X"`

* python setup.py sdist

* Activate environment with pip packages only

* pip install -U pip setuptools twine wheel

* python setup.py bdist_wheel

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

* Publish release in our Github Releases page:
  - Copy the contents of the previous release description (updating the relevant information and links to point to the new Spyder version and changelog entry).
  - Edit the previous release description to only have the changelog line.

* Merge PR on Conda-forge for Spyder. For that you can go to

  https://github.com/conda-forge/spyder-feedstock

  and merge the corresponding PR for the new release (usually an automatic PR will appear that can be either merged as it is or be use as boilerplate).

  **Notes**:

  - Don't forget to add new dependencies and update constraints on the rest of them. For that, you need to compare line by line the contents of the `recipe/meta.yaml` file in the feedstock with

    https://github.com/spyder-ide/spyder/blob/5.x/setup.py
  - After merging, give a ping to `@anaconda-pkg-build` about the new release.

* Update Binder related elements when the new Spyder version is available in Conda-forge:
  - Update the Spyder version on the environment file ([`binder/environment.yml`](https://github.com/spyder-ide/binder-environments/blob/spyder-stable/binder/environment.yml)) of the ([`spyder-stable` branch](https://github.com/spyder-ide/binder-environments/tree/spyder-stable)) in the `binder-environments` repo.
  - Update `environment.yml` files of the [`master`](https://github.com/spyder-ide/binder-environments/blob/master/binder/environment.yml) and [`5.x`](https://github.com/spyder-ide/binder-environments/blob/5.x/binder/environment.yml) branches of `binder-environments` with the contents of the `binder/environment.yml` file present on this repo.

* Publish release announcement to our [list](https://groups.google.com/group/spyderlib) (following [Announcements.md](Announcements.md)) after the installers have been built.
