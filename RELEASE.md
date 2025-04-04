# Instructions to release a new Spyder version

To release a new version of Spyder you need to follow these steps:


## Create backport PR for new minor versions

Before releasing a new minor version (e.g. 6.1.0 after 6.0.x) that needs to include many changes only available in `master`, it's necessary to create a PR to backport those changes to the stable branch.

For that you need to run the following commands:

- `git checkout 6.x`
- `git checkout -b backport-for-minor-version`
- `git diff master 6.x > minor.patch`
- `patch -p1 -R < minor.patch`
- `git add .` and `git commit -m "Backport changes for X.X.X"`


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

* Update the `<branch-name>` branch as necessary. For example, if translations were done for the stable branch `6.x`, you could do the update with

      git checkout 6.x
      git fetch upstream
      git merge upstream/6.x

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

* For spyder-kernels:

  - Switch to the stable branch

        git checkout 6.x

  - Create a new branch in your fork with the name `update-spyder-kernels`

  - Update version in
    - `setup.py`
    - `spyder/dependencies.py`
    - `requirements/{main,windows,macos,linux}.yml`
    - `binder/environment.yml`
    - `spyder/plugins/ipythonconsole/__init__.py` (look up for the constants `SPYDER_KERNELS_MIN_VERSION` and `SPYDER_KERNELS_MAX_VERSION`)

      **Note**: Usually, the version of `spyder-kernels` for validation in the IPython Console only needs to be updated for minor or major releases of that package or when doing alphas for Spyder. For bugfix releases the value should remain the same to not hassle users using custom interpreters into updating `spyder-kernels` in their environments. However, this depends on the type of bugs resolved and if it's worthy to reinforce the need of an update even for those versions.

  - Commit with

        git add .
        git commit -m "Update spyder-kernels"

  - Update our subrepo with the following command, but only if a new version is available!

        git subrepo pull external-deps/spyder-kernels

  - Merge this PR to the stable branch.

* For other dependencies

  - Create a new branch in your fork with the name `update-core-deps`

  - Update the version of any packages required before the release in the following files:

    - `setup.py` (look up for the `install_requires` variable and also for the `Loosen constraints to ensure dev versions still work` patch)
    - `spyder/dependencies.py`
    - `requirements/{main,windows,macos,linux}.yml`
    - `binder/environment.yml`

  - Commit with

        git add .
        git commit -m "Update core dependencies"

  - Update our subrepos with the following commands, but only if new versions are available!

        git subrepo pull external-deps/python-lsp-server
        git subrepo pull external-deps/qtconsole

  - Merge this PR following the procedure mentioned on [`MAINTENANCE.md`](MAINTENANCE.md)

### Check release candidate

* For pre-releases of a new bug fix version

    - Switch to the stable branch

          git checkout 6.x

    - Update version in `__init__.py` (set release version, remove 'dev0', add 'rcX'), then

          git add .
          git commit -m "Release X.X.XrcX"

    - Follow the instructions in the **To do the PyPI release and version tag** section, from the `git clean -xfdi` one onwards.

    - Publish the release to Conda-forge by doing a PR against the `rc` branch of the [spyder-feedstock repo](https://github.com/conda-forge/spyder-feedstock).

        - Create branch for the update

              git checkout rc
              git fetch upstream
              git merge upstream/rc
              git checkout -b update_X.X.XrcX

        - Update `rc` branch in the Spyder feedstock with the latest changes in the `main` one:

            - Create patches between the branches and apply them

                  git checkout main
                  git fetch upstream
                  git merge upstream/main
                  git diff main rc recipe/ ":(exclude)recipe/conda_build_config.yaml" > recipe.patch
                  git diff main rc conda-forge.yml > conda-forge.patch
                  git checkout update_X.X.XrcX
                  patch -p1 -R < recipe.patch
                  patch -p1 -R < conda-forge.patch

            - Fix conflicts, if any, and add new files.

            - Commit with `Update rc channel`.

        - Update the Spyder version to the rc one just released and reset build number to `0`.

        - Create PR with the title `Update to X.X.XrcX`

        - Re-render the feedstock.

    - Publish the release in our [Github Releases page](https://github.com/spyder-ide/spyder/releases) to check the installers are built as expected.

    - Download and test the installation of the resulting installers.

* For pre-releases of a new minor or major version:

    - Switch to master

          git checkout master

    - Update version in `__init__.py` (set release version, remove 'dev0', add 'rcX'), then

          git add .
          git commit -m "Release X.X.XrcX [ci skip]"

    - Push changes to master

          git push upstream master

    - Manually activate the following workflows (see [Running a workflow](https://docs.github.com/en/actions/managing-workflow-runs/manually-running-a-workflow#running-a-workflow)) via the `Run workflow` button:
        - [Nightly conda-based installers (`installers-conda.yml` workflow)](https://github.com/spyder-ide/spyder/actions/workflows/installers-conda.yml)

    - Download and test the installation of the resulting artifacts.

* If one of the previous steps fails, merge a fix PR and start the process again with an incremented 'rcX' commit.


## Update Changelog, Announcements and metadata files

* Create a PR in master to update those files by following the steps below.

* For a new major release (e.g. 6.0.0):

    - In `CHANGELOG.md`, move entry for current version to the `Older versions` section and add one for the new version.
    - `git add .` and `git commit -m "Add link to changelog of new major version"`
    - In `.github/workflows/test-*.yml`, add `6.*` to the `branches` sections and remove the oldest branch from them (e.g. `4.*`).
    - `git add .` and `git commit -m "CI: Update workflows to run in new stable branch [ci skip]"`

* For the first alpha of a new major version (e.g 7.0.0a1):

    - Add a new file called `changelogs/Spyder-X+1.md` to the tree (e.g. `changelogs/Spyder-7.md`).
    - Add `changelogs/Spyder-X+1.md` to `MANIFEST.in`, remove `changelogs/Spyder-X.md` from it and add that path to the `check-manifest/ignore` section of `setup.cfg`.

* Update `changelogs/Spyder-X.md` (`changelogs/Spyder-6.md` for Spyder 6 for example) with `loghub spyder-ide/spyder -m vX.X.X`

* Add sections for `New features`, `Important fixes` and `New API features` in `changelogs/Spyder-X.md`. For this take a look at closed issues and PRs for the current milestone.

* `git add .` and `git commit -m "Update Changelog"`

* Update [Announcements.md](Announcements.md) (this goes to our Google group) removing the outdated announcement of the same kind (major, minor, or beta/release candidate)

* `git add .` and `git commit -m "Update Announcements"`

* Update [org.spyder_ide.spyder.appdata.xml](scripts/org.spyder_ide.spyder.appdata.xml) adding the version to be released over the `<releases>` tag

* `git add .` and `git commit -m "Update metadata files"`

* Once merged, backport the PR that contains these changes to the stable branch (e.g. `6.x`)


## To do the PyPI release and version tag

* Close the current milestone on Github

* git pull or git fetch/merge the respective branch that will be released (e.g `6.x` - stable branch or `master` - alphas/betas/rcs of a new minor/major version).

* For a new major release (e.g. version 6.0.0 after 5.5.6):

    - `git checkout -b 6.x`
    - `git checkout master`
    - Update version in `__init__.py` to reflect next minor version as dev version (i.e `6.1.0a1.dev0`).
    - `git add .` and `git commit -m "Bump version to new minor version"`
    - `git checkout 6.x`

* Update version in `__init__.py` (Remove '{a/b/rc}X' and 'dev0' for stable versions; or remove 'dev0' for pre-releases)

* `git add .` and `git commit -m "Release X.X.X"`

* `git clean -xfdi` and select option `1`

* `python setup.py sdist`

    *Note*: This needs to be done on a Linux machine to prevent getting permission errors on executable files (see [#21892](https://github.com/spyder-ide/spyder/issues/21892) and [#14494](https://github.com/spyder-ide/spyder/issues/14494)).

* Activate environment with pip packages only

* `pip install -U pip setuptools twine wheel`

* `python setup.py bdist_wheel`

    *Note*: This needs to be done on a Linux machine to prevent getting permission errors in executable files (see [#21892](https://github.com/spyder-ide/spyder/issues/21892) and [#14494](https://github.com/spyder-ide/spyder/issues/14494)).

* Install generated wheel locally and check for errors

* `twine check --strict dist/*`

* `twine upload dist/*`

* Check in PyPI that the new release was published correctly

* `git tag -a vX.X.X -m "Release X.X.X"`

* Update version in `__init__.py`:
    - Add 'a1', 'dev0' and increment patch version for final version releases
    - Add 'dev0' and increment alpha/beta/rc version for pre-releases

* `git add .` and `git commit -m "Back to work [ci skip]"`

* Push changes and new tag to the corresponding branches. When doing a stable release from `6.x`, for example, you could push changes with

      git push upstream 6.x
      git push upstream --tags


## After the PyPI release

* Merge PR on Conda-forge for Spyder. For that you can go to the [spyder-feedstock repo](https://github.com/conda-forge/spyder-feedstock) and merge the corresponding PR for the new release (usually an automatic PR will appear that can be either merged as it is or be use as boilerplate).

  **Notes**:

  - Don't forget to add new dependencies and update constraints on the rest of them. For that, you need to compare line by line the contents of the `recipe/meta.yaml` file in the feedstock with [setup.py](https://github.com/spyder-ide/spyder/blob/master/setup.py)

* Update Binder related elements when the new Spyder version is available in Conda-forge:
  - Update the Spyder version on the environment file ([`binder/environment.yml`](https://github.com/spyder-ide/binder-environments/blob/spyder-stable/binder/environment.yml)) of the ([`spyder-stable` branch](https://github.com/spyder-ide/binder-environments/tree/spyder-stable)) in the `binder-environments` repo.
  - Update `environment.yml` files of the [`master`](https://github.com/spyder-ide/binder-environments/blob/master/binder/environment.yml) branch of `binder-environments` with the contents of the `binder/environment.yml` file present on this repo.
  - Update `environment.yml` files of the [`6.x`](https://github.com/spyder-ide/binder-environments/blob/6.x/binder/environment.yml) branches of `binder-environments` with the contents of the `binder/environment.yml` file present on this repo.

* Publish release in our [Github Releases page](https://github.com/spyder-ide/spyder/releases):
  - Copy the contents of the previous release description (updating the relevant information and links to point to the new Spyder version and changelog entry).
  - Edit the previous release description to only have the changelog line.

* Publish release announcement to our [list](https://groups.google.com/group/spyderlib) (following [Announcements.md](Announcements.md)) after the installers have been built.
