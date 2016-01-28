#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing our widgets in Travis
export TEST_CI_WIDGETS=True

# Checkout the right branch
cd $FULL_SPYDER_CLONE

if [ $TRAVIS_PULL_REQUEST != "false" ] ; then
    git checkout travis_pr_$TRAVIS_PULL_REQUEST
else
    git checkout master
fi

# Depth 1
for f in spyderlib/*.py; do
    if [[ $f == spyderlib/restart_app.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/spyder.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/tour.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/start_app.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/pyplot.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 2
for f in spyderlib/*/*.py; do
    if [[ $f == spyderlib/plugins/*.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/qt/*.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/utils/qthelpers.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/utils/windows.py ]]; then
        continue
    fi
    # TODO: Understand why formlayout is failing in Travis!!
    if [[ $f == spyderlib/widgets/formlayout.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 3
for f in spyderlib/*/*/*.py; do
    if [[ $f == spyderlib/external/*/*.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/utils/external/*.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/utils/help/*.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/utils/introspection/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/widgets/externalshell/systemshell.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/widgets/externalshell/inputhooks.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/widgets/externalshell/sitecustomize.py ]]; then
        continue
    fi
    if [[ $f == spyderlib/widgets/externalshell/start_ipython_kernel.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done

# Spyderplugins
for f in spyplugins/ui/*/widgets/*.py; do
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done
