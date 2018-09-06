#!/usr/bin/env bash

set -ex

export TEST_CI_WIDGETS=True
export PYTHONPATH=.

# Depth 1
for f in spyder/*.py; do
    if [[ $f == *test*/*.* ]]; then
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
    if [[ $f == *test*/*.* ]]; then
        continue
    fi
    if [[ $f == spyder/app/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/qthelpers.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/windows.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/workers.py ]]; then
        continue
    fi
    if [[ $f == spyder/widgets/browser.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 3
for f in spyder/*/*/*.py; do
    if [[ $f == *test*/*.* ]]; then
        continue
    fi
    if [[ $f == spyder/utils/external/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/help/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/introspection/plugin_client.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/introspection/numpy_docstr.py ]]; then
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
    if [[ $f == *test*/*.* ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Spyderplugins
for f in spyder_*/widgets/*.py; do
    if [[ $f == *test*/*.* ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done
