Spyder Troubleshooting Guide
============================

For an up to date, more comprehensive version of this guide, covering
solutions to specific commonly reported issues along with these more general
troubleshooting strategies, please refer to:
<https://github.com/spyder-ide/spyder/wiki/Troubleshooting-Guide-and-FAQ>
Thanks, and best of luck!


Trouble with Spyder? Read this first!
-------------------------------------

If Spyder crashes or you receive an error message, please read the following
troubleshooting steps before opening a new ticket.  There's a good chance
that someone else has already experienced the same issue, so solving it
yourself will likely get Spyder working again for you as quickly as possible.

**Important Note:** To make sure you're getting the most relevant help for
your problem, please make sure the issue is actually related to Spyder:

*   If the problem appears to be a result of *your own code*,
    Stack Overflow <https://stackoverflow.com/> is a better place to start;
*   If the bug also occurs in the *standard python, IPython, or qtconsole*
    environments, or only with *a specific package*, it is unlikely to be
    something in Spyder, and you should report it to those sources instead.
*   If the problem lies with *your specific install*, uninstalling and clean-
    reinstalling the Anaconda distribution from
    <https://www.anaconda.com/download/> is strongly recommended. As the other
    methods of installing Spyder have many pitfalls for the unwary, we
    generally aren't able to give individual support for install issues.

Just like the programs you code in it, Spyder is written in Python, so
you can often figure out many a problem just by reading the last line of the
traceback or error message from the error dialog or Spyder's internal console,
the latter available from ``Panels`` > ``Internal Console`` under the ``View``
menu. Oftentimes, that alone will tell you how to fix the problem on your own,
but if not, we're here to help.

If you check out our list of issue categories and problem descriptions
and see a question, error message or traceback that looks
familiar, the relevant sub-section will likely be of the most specific help
solving your issue as quickly as possible. If those steps don't work, or
you can't find a similar problem, you can try some **Basic First Aid** (next
section) or, if Spyder won't launch, some **Emergency CPR** (section after)
and see if that clears it up.

Finally, if you still can't get it to work, and the problem is indeed
Spyder-related (see above note), you should consult the the
**Calling for Help** section for other resources to explore and details on how
to submit an issue  to our Github tracker, so the problem can be fixed for
everyone. Thanks for taking the team to read this, and best of luck!



Basic First Aid: General troubleshooting
========================================

These suggestions, while more of a shotgun approach, tend to fix the majority
of reported issues just on their own. In the rough order you should try them:


Recommended troubleshooting steps
---------------------------------

*   **Restart Spyder**, and try what you were doing before again.
*   **Upgrade Spyder** to the latest release, and you might find your issue is
    resolved (along with new features, enhancements, and other bug fixes).
    Minor releases come out every two months, so unless you've updated
    recently, there is a good chance your version isn't the latest; you can
    find out with the ``Check for updates`` command under the ``Help`` menu.
    To perform the update with ``conda`` (strongly recommended), just run
    ``conda update spyder`` from the Anaconda Prompt/Terminal/command line
    (on Windows/Mac/Linux).
*   **Update Spyder's dependencies and environment**, either by installing the
    latest version of your distribution (e.g. the recommended Anaconda), or
    with the relevant "update all" command in the Anaconda Prompt/Terminal/
    command line (on Windows/Mac/Linux). Using ``conda``, you can run
    ``conda update anaconda`` to get the latest stable version of everything.
*   **Restart your machine**, in case the problem lies with a lingering process
    or another such issue.
*   From the Anaconda Prompt/Terminal/command line (on Windows/Mac/Linux),
    **run the command ``spyder --reset``**, which will restore Spyder's config
    files to their defaults, which solves a huge variety of Spyder issues.
    **Note:** This will reset your preferences, as well as any custom keyboard
    shortcuts or syntax highlighting schemes, so you should back up the
    ``.spyder-py3`` folder in your user home directory if you particularly
    care about any of those, so you can restore them should this not solve
    the problem.
*   **Try installing Spyder into a new ``conda`` environment** (recommended) or
    ``virtualenv``, and only installing its dependencies there, and seeing if
    the issue reoccurs. If it does not, it is likely due to another package
    installed on your system, particularly if done with ``pip``, which can
    cause many problems and should be avoided if at all possible.
*   If none of these solve your issue, you should do a full uninstall of Spyder
    by whatever means you originally installed it, and then do a
    **clean install of the latest version of the Anaconda distribution**
    <https://www.anaconda.com/download/>, which is how we recommend you
    install Spyder and keep in up to date. While you are welcome to get Spyder
    working on your own by one of the many other means we offer, we are only
    able to provide individual support for install-related issues for users
    of the Anaconda distribution. In particular, ``pip`` installation, while
    doable, is only really for experts, as there are many pitfalls involved and
    different issues specific to your setup, which is why we recommend using
    ``conda`` whenever possible.


Standard approach to isolating problems
---------------------------------------

If you get the error while running a specific line, block, or script/program,
it may not be an issue with Spyder, but rather something lower down in the
"stack" it depends on. Try running it in the following, in order, if and until
it starts working as you expect, and report the bug, if there is one,
to the last one it *doesn't* work in.

1.  Spyder, of course! Make sure you can reproduce the error, if possible.
2.  **A bare ``qtconsole`` instance**, e.g. launched from Anaconda navigator or
    from the Anaconda Prompt/Terminal/command line (Windows/Mac/Linux) with
    ``jupyter qtconsole``. ``qtconsole`` is the GUI console backend Spyder
    depends on to run its code, so most issues involving Spyder's Console are
    actually something with ``qtconsole`` instead, and can be reported to their
    issue tracker: <https://github.com/jupyter/qtconsole/issues/>
3.  **An IPython command line shell**, launched with e.g. ``ipython`` from the
    Anaconda Prompt/Terminal/command line (Windows/Mac/Linux). Reproducable
    bugs can be reported to their Github page, though make sure to read thier
    guidelines and docs first: <https://github.com/ipython/ipython/issues>
4.  A stock Python interpreter, either run as a script file with
    ``python path/to/your/file.py`` or launched interactively with ``python``,
    from your Anaconda Prompt/Terminal/command line (Windows/Mac/Linux).
    While its not impossible it is a Python bug, t much more likely to be an
    issue with the code itself or a package you are using, or else a
    fundamental behavior, design choice or limitation of the Python language
    that likely won't be fixed anytime soon, so your best sources are the
    Python docs: <https://www.python.org/doc/>, and the other resources listed
    above.

Remember, if the problem reoccurs in a similar or identical way with any of
these methods (other than only Spyder itself), then it is almost certainly not
an issue with Spyder, and would be best handled elsewhere. As as we aren't able
to do much of anything about issues not related to Spyder, a forum like
Stack Overflow <https://stackoverflow.com/> or the relevant package's docs is
a much better place to get  help or report the issue in that case;
see the **Emergency Numbers** section near the end of the document for
other places to look for information and assistance. Best of luck!



Emergency CPR: Spyder won't launch
==================================

Just like in the real world, while it may be scary or disconcerting to have
Spyder not come to life for you, these situations are almost always fixable
so long as you stay calm, keep a cool head, and carefully follow the steps
above and below.


Common solutions
----------------

*   The **basic troubleshooting steps** discussed in the section above, as
    they usually resolve the vast majority of Spyder install-related issues.
*   **Make sure Spyder isn't already running** and no Spyder related windows
    (*e.g.* Variable Explorer dialogs) are left open, and check that the
    preference setting "Use a single instance" (under ``Preferences`` >
    ``General`` > ``Advanced Settings``) isn't checked.
*   Try **starting Spyder via a different means**, such as from a shortcut,
    Anaconda navigator, or the Anaconda Prompt/Terminal/command line
    (on Windows/Mac/Linux) by simply typing ``spyder`` then enter/return,
    and see if any of those work. If so, then something's wrong with your
    install, not Spyder itself, and so we recommend uninstalling and doing a
    clean install of the latest Anaconda <https://www.anaconda.com/download/>.
*   If Anaconda is currently installed "for just you", try uninstalling and
    reinstalling it "for all users" instead, and vice versa, as some systems
    can have issues with one or the other.
*   Reinstall it into your local startup drive, to a directory path and user
    account without spaces, special characters, or unusual permissions.
*   Disable any security software you may be using, such as a firewall or
    antivirus, as these products can occasionally interfere with Spyder or
    its related packages. Make sure to re-enable it if it doesn't fix the
    problem, and if it does, add a rule or exception for Spyder.
*   Run Spyder with administrator rights just in case it is some sort of
    permissions issue
*   Check and repair/reset permissions, your disk, and OS if all else fails


Advanced tricks
---------------

If none of the above solves the problem, you can try starting Spyder directly
from its Python source files which may either get it running, or at least
provide very useful information to help debug the problem further.
The procedure is described on, *e.g.*, this Github issue
<https://github.com/spyder-ide/spyder/issues/6023#issuecomment-354389413>,
which allowed the user to solve a seemingly difficult situation.

The technique essentially boils down to starting Spyder from the
Anaconda Prompt/Terminal/command line (on Windows/Mac/Linux) by manually
running the Spyder startup routine, ``start.py``, with a known
good Python interpreter, and observing the results. To do so, you'll need to
navigate to the Spyder ``app`` directory from the command line, the location
of which varies depending on how you installed it.

With Anaconda, the distribution we recommend, you can find the location(s) of
your packages directory(s) with the command ``conda info``, where the directory
you want is listed under ``package cache``. For a systemwide Anaconda install,
it is usually ``Anaconda3/pkgs`` at the root of your drive, while it varies
depending on your operating system for a per-user install. If both are shown,
you'll need to remember how you first installed Spyder with Anaconda, or just
check both. Inside the Anaconda directory, you should find the directory you're
looking for under ``spyder-3.#.#-py##_#/Lib/site-packages/spyder/app``, where
the ``#``s correspond to the most recent version present.

If using ``pip``, which we don't officially support, you can typically find
the needed directory, from the root of your drive, under
``/Python##/Lib/site-packages/spyder/app``.

In case you're unfamiliar, you can change directories with the
``cd`` command followed by the name of the directory you'd like to navigate to.
Once inside the ``app`` directory, run ``python start.py`` to launch Spyder.
If it doesn't launch, then you should see an error traceback printed; carefully
copy that for future reference and also run ``python mainwindow.py``,
and record your results as well.

In case the command window disappears immediately after the error on Windows,
as is sometimes the case, so you cannot see what it printed  just create a
batch file in the ``app`` directory with with the following content::

    C:/Absolute/Path/To/Your/Python/Executable/python.exe start.py

    pause

which should to the trick. Replace the path with the actual path to the
Python interpreter you want to use, e.g. the one with Anaconda at
``C:/Anaconda#/python.exe`` if installed for all users, or
``C:/Users/YOURUSERNAME/AppData/Local/conda/conda/Python#/python.exe`` if for
just you, replacing # with the Python major version (2 or 3) of the Anaconda
you downloaded. If you're unsure, you can get the correct path by entering
``where python`` in the Anaconda Prompt, and using the first path shown there.
Then, just doulbe click the batch file to run it, and you should see the
output you need.

If reading the output, particularly the last line, doesn't solve the problem,
then record all of it carefully, and post it as part of your bug report
as described under the **Calling for Help** seciton near the end of this
document.



Advanced Treatments: Debugging and patching
===========================================

If you know your way around Python, you can often diagnose and even fix or
patch issues yourself. You can explore the error messages
you're receiving and Spyder's inner workings with the ``Internal Console`` under
the menu item ``View`` > ``Panes`` > ``Internal Console``. If you want more
detailed debug output, open an Anaconda Prompt/Terminal/command line
(on Windows/Mac/Linux), set the enviroment variable SPYDER_DEBUG to the value
"3" (on ``cmd``, use ``set SPYDER_DEBUG=3``; with ``bash``, execute
``SPYDER_DEBUG="3"``, and for ``tcsh``, run ``setenv SPYDER_DEBUG 3``.
Then, launch Spyder from that same shell with ``spyder``, and observe the
results. Even if you don't manage to fix the problem yourself, this output
can be immensely helpful in aiding us to quickly narrow down and solve your
issue for you.

However, if you do feel up to it and think you know where to look and what to
change, you are welcome to take a stab at patching the bug. Just ``clone``
the relevant development version of Spyder (``3.x`` for bug fixes) from our
Github repo: <https://github.com/spyder-ide/spyder/>, edit the relevant Python
code in your favorite editor or IDE (or Spyder itself!), and test your changes
by running it from the cloned repo with ``python bootstrap.py`` from the repo's
root directory (*e.g.* ``spyder``). Then, commit your changes to a github
branch, and submit a Pull Request to the Spyder repo for them to be included in
the next main Spyder distribution!

For a quick, step by step guide to the process, see our ``CONTRIBUTING``
document on Github:
<https://github.com/spyder-ide/spyder/blob/master/CONTRIBUTING.md>,
and for even more about developing Spyder, check out our Github wiki:
<https://github.com/spyder-ide/spyder/wiki>. Thanks for your help!



Emergency Numbers: Additional helpful resources to consult
==========================================================

Aside from this document, there are a number of other sources of documentation
and troubleshooting information you should at least search or skim, before
submitting an issue, as they might already offer an answer or at least help
you better understand the following. Even if we aren't able to help you,
these places might.


Spyder-related platforms
------------------------

*   **Spyder documentation**: <https://pythonhosted.org/spyder/>
    It explains how to use Spyder's basic features and addresses a number of
    common "How can I?" questions that arise. Its still a work in progress,
    so if you discover something missing from the docs, please submit an
    issue or pull request to add it!
*   **Spyder dev documentation**: <https://github.com/spyder-ide/spyder/wiki>
    Along with additional general information about Spyder and its features,
    our wiki has information about how to develop and test Spyder, our
    development roadmap and the features planned in the next release, other
    common questions, the changelog, and much more.
*   **Spyder website**: <https://spyder-ide.github.io/>
    While it is still under very early alpha development and isn't polished for
    public consumption, it does contain basic information about Spyder and
    links to many other helpful resources.
*   **Spyder Google Group**: <http://groups.google.com/group/spyderlib>
    Great for your more help-related questions, particularly those
    you aren't sure are a full-on Spyder issue, or you'd like to give
    more general feedback or ask questions of the team.
*   **Spyder Gitter**: <https://gitter.im/spyder-ide/public>
    If you've got a quick question to ask the team and are looking for a quick
    answer, this is a great place to chat directly with the Spyder developers.
*   **Stack Overflow**: <https://stackoverflow.com/questions/tagged/spyder>
    Particularly if your question is more programming related, or has more to
    do with something particular to your own code that you just can't get
    working, this is a great place to start searching and posting. It has an
    active Spyder community as well, with new Spyder-related questions posted
    every day, and the developers, especially the lead maintainer, are active
    in answering them.


Python help and problems
------------------------

*   **Google/your favorite search engine:** One never fails to be surprised
    how many problems can be solved by a simple Google search!
*   **Official Python Help page**: <https://www.python.org/about/help/>
    A great resource that lists a number of places you can get help, support
    and learning resources for the Python language and its packages.
*   **Python Documentation**: <https://www.python.org/doc/>
    A number of issues can be explained due to quirks in the language
    itself or misunderstandings as to how it behaves, and so those and much
    more can be found here.
*   **r/Python**: <https://www.reddit.com/r/Python/> and
    **r/learnpython**: <https://www.reddit.com/r/learnpython/>
    The former is aimed more at general Python usage and the latter more at
    beginners, but both are popular places to ask about and discuss issues
    with Python and its packages.


Data science/SciPy resources:
-----------------------------

*   **Anaconda Support**: <https://www.anaconda.com/support/>
    Offers free community help and documentation for the Anaconda applications,
    installing the Anaconda distribution, and using the `conda` package and
    environment manager, as well as paid support options.
*   **SciPy.org Website**: <https://www.scipy.org/>
    The central home of the scipy stack, with information, documentation,
    help, and bug tracking for many of the core packages used with Spyder,
    including NumPy, SciPy, Matplotlib, Pandas, Sympy, and IPython.
*   **Project Jupyter**: <https://jupyter.org/>
    Development hub for IPython, Spyder's ``qtconsole``, Jupyter notebooks
    used with the ``spyder-notebook`` plugin, and more.
*   **Data Science Stack Exchange**: <https://datascience.stackexchange.com/>
    For questions that relate more to data science than programming
    specifically, data science stack exchange is a good place to ask and
    answer them.



Calling For Help: Still have a problem?
=======================================

If you can't find your issue here, you're fairly sure its Spyder-related,
and a full course of general troubleshooting didn't solve it, then you'll
want to submit it to our issue tracker so our team can take a look at it
for you. You'll need a github account to do that, so make sure you have one
before you begin (a good idea anyway).

**Important Note:** Before you submit an issue, make sure you've searched a
description of the problem, and a relevant portion of the error traceback, on
both Google and the Spyder repository/Issue tracker (see above or below) to
make sure it hasn't been submitted before. We currently have over 5,000
submitted issues in the past few years, along with over 1,500 stack overflow
questions tagged ``spyder`` and thousands of Google Groups posts, among others,
so it is quite likely your issue or problem has been reported/solved before.
If that's the case, your issue will be closed your issue as a duplicate,
so be sure to check first!


Ways to submit an issue
-----------------------

**If you are able to launch Spyder**, the best way to do so is to simply
select ``Submit Issue`` from the ``Help`` menu or, better yet, right from
the error dialog if present, which will automatically take you to the
correct page; prefill an error report with your environment details, key
versions and dependencies; give you a basic structure to fill in as needed;
and (if the latter) automatically insert the error/traceback for you.

**If Spyder won't launch** (or otherwise isn't available), you can also
submit a report manually at our Issues page on Github
<https://github.com/spyder-ide/spyder/issues>. Unlike the above,
you'll need to manually provide the versions of everything
(Spyder, Python, OS, Qt/PyQt, Anaconda, and Spyder's dependencies)
as listed in the error report template; see below for more on that.


Must-have and helpful items to include
--------------------------------------

**Please include as much as possible of the following in your report**
to maximize your chances of getting relevant help and our ability to diagnose,
reproduce and solve your issue. In particular, *be sure to include the first
two items, as without these we will usually be unable to isolate the problem
in order to confirm and fix it, and the issue will be automatically closed
after one week (7 days) if we don't hear from you.*

The key items, in rough order of priority:

*   The full, **complete error message or traceback** copy/pasted or
    automatically entered exactly as displayed by Spyder:

    -   Auto-generated reports directly from the error dialog should include
        this automatically, but double check to make sure.
    -   You can copy and paste this from the the "Show Details" section of the
        error dialog.
    -   If not present, or a dialog is not displayed, you can also find it
        printed to Spyder's Internal Console, located under the ``View`` menu
        at ``Panels`` > ``Internal Console``.
    -   If you prefer, or if Spyder won't start, you can start Spyder from the
        Anaconda Prompt/Terminal/command line (Windows/Mac/Linux) with
        ``spyder`` and copy the output printed there.

    It is a common problem that tracebacks, whether automatic or copy/pasted,
    are incomplete/cut off, which tends to omit the information (the last
    few lines) most critical to diagnosing or solving the issue. Accordingly,
    carefully check the included traceback to be sure this isn't the case,
    and try one of the other sources in the list above if so, as otherwise
    we'll probably have to close your issue as we can't solve it without that.

    *If you are reporting a specific behavior* rather than an error, or the
    message does not fully explain what occurs, please *describe in detail
    what actually happened, and what you expected Spyder to do*.

*   A **detailed, step by step description of exactly what you did** leading up
    to the error/crash/behavior occurring, complete with (minimal) code that
    triggers it, if possible/applicable. The more specific you are here, the
    easier and faster the problem can be reproduced and fixed.

*   **Information about Spyder and its environment**, as listed in the error
    report template (if not already filled in automatically by Spyder, via
    ``Help`` > ``Report Issue``), which you can find under ``About Spyder`` in
    the ``Help`` menu, along with its key dependencies, shown in the dialog
    under ``Help`` > ``Dependencies`` (there's a button to copy-paste them).
    If Spyder won't launch, you can get the Core Components information from
    ``conda`` or Anaconda Navigator, and paste output of ``conda list`` from
    Anaconda Prompt/Terminal/command line (on Windows/Mac/Linux) for the rest.

*   **How you installed Spyder** and any other relevant packages,
    *e.g.* Anaconda/``conda`` (highly recommended), another
    distribution like WinPython, through MacPorts or your distribution's
    package manner, using ``pip``, manually from source, etc, and **whether
    Spyder has worked before** since you installed it. *Note that
    unfortunately, we generally cannot provide individual support for
    installation issues with methods other than ``conda``/Anaconda.

*   **What else you've tried to fix it**, *e.g.* from this guide or elsewhere
    on the web, whether you've seen it reported anywhere else, replicated it
    on multiple machines, or (if appropriate) **tried to reproduce it in
    standalone Qtconsole, IPython, and/or the plain Python** interpreter.

*   **Whether the problem occurred consistently before** in similar situations,
    only some of the time, or is this the first time you observed it?

*   **Anything else special or unusual** about your system, environment,
    packages, or specific usage that might have anything to do with the problem


Important note about pasting code into Github
---------------------------------------------

If including block(s) of code in your report, be sure to precede and follow it
with a line of three backticks \`\`\` to get a code block like this::

    Your Code Here!

Otherwise, your code will likely contain random formatting or missing
indentation, making it difficult or impossible for others to examine and run
to reproduce and fix your issue. Plus, it looks much nicer, too.


Next steps and thank you!
-------------------------

Once you submit your report, our team will try to get back to you as soon as
possible, often within 24 hours or less, to try to isolate the problem on our
end and help you fix/work around it on yours.

Thanks for using Spyder, and we appreciate your help making it even better!
