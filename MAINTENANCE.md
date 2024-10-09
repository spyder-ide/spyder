These are some instructions meant for maintainers of this repo.

* To avoid pushing to our main repo by accident, please use `https` for your `usptream` remote. That should make git to ask for your credentials (at least in Unix systems).

* After merging a PR that needs to be included in stable branch (e.g. `6.x`), you need to call the `meeseeksdev` bot by adding a comment to the same PR with the followng syntax:

    `@meeseeksdev please backport to 6.x`

* If `meeseeksdev` fails to do the backport, you need to manually open a PR against the stable branch to do it with the following actions:

    - `git checkout 6.x`
    - `git checkout -b backport-pr-<number>`
    - `git cherry-pick -m 1 <commit that was merged to master for that PR>`
    - Solve conflicts

* If a PR that involved updating our spyder-kernels subrepo and needs to be included in the stable branch (e.g. `6.x`), you need to manually create a PR against it with the following actions:

    - `git checkout 6.x`
    - `git checkout -b backport-pr-<number>`
    - `git cherry-pick -m 1 <commit that was merged to master for that PR>`
    - `git reset -- external-deps/spyder-kernels`
    - `git checkout -- external-deps/spyder-kernels`
    - `git commit` with the files left
    - `git subrepo pull external-deps/spyder-kernels`

* If a PR in spyder-kernels solves an issue in Spyder but was not part of a PR that updated its subrepo, you need to open one that does precisely that, i.e. update its subrepo, in order to fix that issue.

    The same goes for the python-lsp-server and qtconsole subrepos.

* There's a bot that constantly monitors all issues in order to close duplicates or already solved issues and inform users what they can do about them (basically wait to be fixed or update).

    The patterns detected by the bot and the messages shown to users can be configured in `.github/workflows/duplicates.yml` (only avaiable in our `master` branch because there's no need to have it in the stable one).

    Please open a PR to add new messages or update previous ones, so other members of the team can decide if the messages are appropriate.
