# Reviewer Guidelines

Reviewing pull requests (PRs) can take many forms and be reflected across many styles.
To help make the process more clear for contributors, the following guidelines are designed to scope review and specify what areas of feedback block PRs from merging.

**Note:** These guidelines are new; feedback on them is appreciated and can be given via [opening an issue on the main Spyder repo](https://github.com/spyder-ide/spyder/issues/new/choose).

## Etiquette Guidelines

### Communication principles

Reviewing open pull requests (PRs) helps move the project forward.
It is a great way to get familiar with the codebase and should motivate the contributor to keep involved in the project.

- Every PR is an act of generosity.
  Opening with a positive comment will help the author feel rewarded, and your subsequent remarks may be heard more clearly.
  You may feel good also.
- Begin if possible with the large issues, so the author knows they’ve been understood.
Resist the temptation to immediately go line by line, or to open with small pervasive issues.
- Do not let perfect be the enemy of the good.

If you find yourself making many small suggestions that don’t fall into the Review Guidelines, consider the following approaches:
    - Refrain from submitting these.
    - Follow up in a subsequent PR, out of courtesy, you may want to let the original contributor know.
    - Do not rush, take the time to make your comments clear and justify your suggestions in a small number of words (ideally a small paragraph or a short sentence should be enough)
    - You are the face of the project.

Bad days occur to everyone, in that occasion you deserve a break: try to take your time and stay offline.

### Expected reviewer behavior

Pull requests are a key space for community interaction, and reviewing PRs is a vital part of maintaining any project.
With that in mind, this is a process that can benefit from having a clear set of goals for the sake of both the reviewer and the PR author.

All reviewers are expected to follow these guidelines and labels in their review.
If a reviewer forgets, they may be reminded.
If a reviewer refuses, they will be contacted about a violation of [Spyder’s Code of Conduct](https://github.com/spyder-ide/spyder/blob/master/CODE_OF_CONDUCT.md) under `Giving and gracefully accepting constructive feedback`.
As with all aspects of the Code of Conduct, this applies to everyone involved in the discussion (including members of the Spyder organization on GitHub).

Other notes:
- Unless the reviewer has explicit permission on the conversation for that PR, reviewers should not commit to the same branch as the PR being reviewed.
- If more than roughly 20% of review comments fall in the `[optional]` section described below, then it is worth adding this feedback in an issue referencing the PR instead of on the PR directly.
- Whenever practical, reviewers should add comments asking for a specific change as [GitHub suggestions](https://docs.github.com/en/pull-requests/collaborating-with-pull-requests/reviewing-changes-in-pull-requests/commenting-on-a-pull-request#adding-line-comments-to-a-pull-request).

## Reviewing process

### For code-focused review

#### Required items

The following are areas the community expects to be covered in the review of the code on each PR.
Not all of the following individual questions will be relevant for every PR (for example, a bug fix may not need to answer the same questions as a proposal for a new feature), but these are the themes to be addressed.

Review that addresses these questions on a PR will be prefixed with `[required]` so that the PR author(s) are clear that they are blockers.
PR authors are responsible for addressing required reviews for the PR to be eligible for merging.

- [ ] Motivation
    - Do we want this?
    - Would it benefit a meaningful number of users to have this accepted into Spyder?
    - Does it help to solve bugs?
    - Is it a necessary refactoring?

- [ ] Tests
    - Do the tests pass in the continuous integration build?
      If appropriate, help the contributor understand why tests failed.
    - Are regression tests needed?
      If a reproducible bug is being fixed in this PR, one may be needed, and reviewers should help the contributor design and implement them.
      In case the contributor is unable to add the test, the reviewer should do so in a follow-up PR.

 - [ ] Sustainability and maintenance
    - Is the code easy to read and low on redundancy?
    - Should variable names be improved for clarity or consistency?
    - Should comments or docstrings be added or removed?
    - Will the cost of maintaining a new feature be worth its benefits?
    - Will the new code add any dependencies on other projects?

- [ ] User-facing changes
    - What use cases might this change influence?
    - Does the user experience match existing patterns in Spyder?
      If it does not, why was the choice made?
    - Is in-interface text (new or modified) appropriately descriptive and free of spelling or grammar issues that would make its meaning unclear?

#### Optional items

The following are themes that may be helpful to cover on a PR, but are optional.

**Note**: The difference between an objective improvement and a subjective preference isn’t always clear.
Reviewers should recall that the review process is primarily about reducing risk to the project.
When reviewing code, one should aim at preventing situations which may introduce a bug, deprecation or regression.

- [ ] Improvements
    - Could the code easily be rewritten to run much more efficiently for relevant settings?
    - Is the code backwards compatible with previous versions?
      (Or is a deprecation cycle necessary?)
    - Is there feedback that would be helpful for solving future issues surrounding this change?
      Are there non-urgent concerns that the team should be made aware of?
    - If a bug is fixed, does the PR include a non-regression test?
    - Are there images that should be added, resized or optimized?

- [ ] User-facing changes
    - Does the user interface or other visual elements match existing patterns in Spyder?
      If it does not, is there a reason?

Review that addresses these questions on a PR will be prefixed with `[optional]` so that the PR author(s) are clear that this feedback is not a blocker.
Addressing this feedback is considered above-and-beyond, and may be more relevant on some PRs than others.
PR authors may address these reviews, but are not required to do so in order for the PR to be eligible for merging.

### For documentation/website-focused review

#### Required items

The following are areas the community expects to be covered in the review of a documentation-focused PR.
In general, reviewers need to consider whether the content is a good fit, accurate and generally clear to readers, and builds and renders with no simmediate user-visible issues.

Review that addresses these questions on a PR will be prefixed with `[required]` so that the PR author(s) are clear that they are blockers.
PR authors are responsible for addressing required reviews for the PR to be eligible for merging.

**Motivation**

- [ ] Does the change improve the documentation?
- [ ] Would it benefit a meaningful number of users to have this as a part of the documentation?
- [ ] Is it appropriate for the documentation and the section it is placed in?

**Content**

- [ ] Is the information accurate?
- [ ] Is the change sufficiently complete, such that it won’t confuse users if it were to appear in the documentation as-is?
- [ ] Is it clear what the text and images are trying to communicate?

**Images/GIFs**

- [ ] Are screenshots/GIFs reasonably legible and appropriate for the topic?
- [ ] Are all images/GIFs scaled and optimized?
      If needed, reviewers should offer to help with this.

**Technical**

- [ ] Do the tests pass in the continuous integration build?
      If appropriate, help the contributor understand why tests failed.
- [ ] Does any added/changed content render correctly, without user-visible issues?
- [ ] Is the content free from typos and unambiguous grammar errors?

#### Optional items

Feedback asking for substantial, user-visible content additions and improvements to the text and images (rather than critical fixes) may be left as optional review comments, if it is appropriate and important enough to merit discussion on the original PR.
As with all reviews, please primarily consider how a PR would impact documentation stability, clarity, and quality over focusing on purely subjective improvements.
Otherwise, they can be handled in a followup by the reviewer, opened as an issue, or deferred entirely.

Examples include:

- [ ] Could GIFs or screenshots be added or improved?
- [ ] Would this topic benefit from additional elaboration on specific items within the PR’s scope?
- [ ] Could new content be restructured to read more clearly or logically for users?

Review that addresses these topics on a PR will be prefixed with `[optional]` so that the PR author(s) are clear that this feedback is not a blocker.
Addressing this feedback is considered above-and-beyond, and may be more relevant on some PRs than others.
PR authors may address these reviews, but are not required to do so in order for the PR to be eligible for merging.

#### Followup-only items

On all documentation PRs that modify more than a few lines, changes that are less critical/unambiguous, optimization-focused, or those that are not user-visible, should not be suggested on contributor PRs (even with an `[Optional]` tag) unless the author explicitly requests this level of review.

Instead, these changes should be made in a followup pull request by a maintainer or other reviewer.
The specifics are covered in detail in the [Style Guide](https://github.com/spyder-ide/spyder-docs/blob/master/STYLEGUIDE.md), but generally include:

- [ ] Copyediting (diction, phrasing, verbosity, repetition etc)
- [ ] Formatting (spacing, line breaks, etc)
- [ ] reST/Markdown style (roles, directives, markup, etc)
- [ ] Style guide issues (consistency, precise label text, other nits)

## Rebasing and merging process

If a contributor’s pull request has issues with their own commits (too many, trivial, etc), messages (incorrect format, not descriptive, stock, etc) or images (resized, optimized, modified, etc.), the committer should merge the PR using the squash option in GitHub’s interface with an appropriately descriptive message, and neither require that they rebase/amend their commits or do so for them directly on their branch (unless explicitly requested unsolicited by the contributor).
Before performing the squash merge, the reviewer should add a message with a short explanation to the contributor to avoid confusion.

For example,

> Hi @user, thanks for your contribution! Your work is ready to be merged.
Given the [number of messages, large binary assets] present in this PR we will proceed to squash merge.
This just means that all the changes of this PR will be condensed in just one commit in our repository.
Hope to see your future contributions to the project!

If a contributor’s PR has an intractable Git issue involving more than just the contributor’s proposed new commits that would not be fixed by a squash, or might otherwise cause future serious difficulties for them/their repository (e.g. wrong base branch, unrelated commits, spurious merges, etc), reviewers/maintainers should kindly and compassionately explain the issue, provide step by step instructions (i.e. specific Git commands) to solve it, and offer assistance in doing so if the user desires it.

## References

- Much of this document—especially the review questions—is based on [scikit-learn’s code review guidelines](https://scikit-learn.org/stable/developers/contributing.html?highlight=reviewers#code-review-guidelines)
- The Communication Guidelines are a modified version of [NumPy’s communication guidelines](https://numpy.org/devdocs/dev/reviewer_guidelines.html#communication-guidelines)
- Clearly labeling feedback was inspired by [Netlify’s blog post about “feedback ladders”](https://www.netlify.com/blog/2020/03/05/feedback-ladders-how-we-encode-code-reviews-at-netlify/)
- Additional details on how to approach reviews came from s[Nina Zakharenko’s Code Review Skills for People slides](https://www.nnja.io/post/2019/oscon-2019-code-review-skills-for-people/ )
- Many thanks to the Spyder reviewers who helped write and edit this document!
