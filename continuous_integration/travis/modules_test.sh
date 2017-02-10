#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing our widgets in Travis
export TEST_CI_WIDGETS=True

# Checkout the right branch
cd $FULL_SPYDER_CLONE

if [ $TRAVIS_PULL_REQUEST != "false" ] ; then
    git checkout travis_pr_$TRAVIS_PULL_REQUEST
else
    git checkout $TRAVIS_BRANCH
fi

# Depth 1
for f in spyder/*.py; do
    if [[ $f == *test*/test_* ]]; then
        continue
    fi
    if [[ $f == spyder/pyplot.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 2
for f in spyder/*/*.py; do
    if [[ $f == *test*/test_* ]]; then
        continue
    fi
    if [[ $f == spyder/app/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/inputhooks.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/qthelpers.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/windows.py ]]; then
        continue
    fi
    # TODO: Understand why formlayout is failing in Travis!!
    if [[ $f == spyder/widgets/formlayout.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 3
for f in spyder/*/*/*.py; do
    if [[ $f == *test*/test_* ]]; then
        continue
    fi
    if [[ $f == spyder/external/*/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/external/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/help/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/ipython/start_kernel.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/ipython/spyder_kernel.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/site/sitecustomize.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/introspection/plugin_client.py ]]; then
        continue
    fi
    if [[ $f == spyder/widgets/externalshell/systemshell.py ]]; then
        continue
    fi
    if [[ $f == spyder/widgets/ipythonconsole/__init__.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 4
for f in spyder/*/*/*/*.py; do
    if [[ $f == *test*/test_* ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Spyderplugins
for f in spyder_*/widgets/*.py; do
    if [[ $f == *test*/test_* ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done
