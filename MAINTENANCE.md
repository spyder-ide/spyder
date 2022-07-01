These are some instructions meant for maintainers of this repo.

* To avoid pushing to our main repo by accident, please use `https` for your `usptream` remote. That should make git to ask for your credentials (at least in Unix systems).
* After merging a PR against the stable branch (e.g. `5.x`), you need to immediately merge it against `master` and push your changes to Github.
  For that you need to perform the following steps in your local clone:

    - git checkout 5.x
    - git fetch upstream
    - git merge upstream/5.x
    - git checkout master
    - git merge 5.x
    - Commit with the following message:

          Merge from 5.x: PR #<pr-number>

          Fixes #<fixed-issue-number>

      If the PR doesn't fix any issue, the second line is unnecessary.
    - git push upstream master

* To merge against `master` a PR that involved updating our spyder-kernels subrepo in the stable branch (e.g. `5.x`), you need to perform the following actions:

    - git checkout master
    - git merge 5.x
    - git reset -- external-deps/spyder-kernels
    - git checkout -- external-deps/spyder-kernels
    - git commit with the files left and the same message format as above.
    - git subrepo pull external-deps/spyder-kernels

* If a PR in spyder-kernels solves an issue in Spyder but was not part of a PR that updated its subrepo, you need to open one that does precisely that, i.e. update its subrepo, in order to fix that issue.

    The same goes for the python-lsp-server and qtconsole subrepos.

* There's a bot that constantly monitors all issues in order to close duplicates or already solved issues and inform users what they can do about them (basically wait to be fixed or update).

    The patterns detected by the bot and the messages shown to users can be configured in `.github/workflows/duplicates.yml` (only avaiable in our `master` branch because there's no need to have it in `5.x`).

    Please open a PR to add new messages or update previous ones, so other members of the team can decide if the messages are appropriate.
