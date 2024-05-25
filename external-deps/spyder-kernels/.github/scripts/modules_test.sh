#!/usr/bin/env bash

set -ex

export TEST_CI_WIDGETS=True
export PYTHONPATH=.:./external-deps/spyder-kernels

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
    if [[ $f == spyder/widgets/about.py ]]; then
        continue
    fi
    if [[ $f == spyder/api/__init__.py ]]; then
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
    if [[ $f == spyder/plugins/*/plugin.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/completion/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/onlinehelp/widgets.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/*/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/utils/introspection/old_fallback.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/tours/widgets.py ]]; then
        continue
    fi
    if [[ $f == spyder/api/plugins/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/pylint/main_widget.py ]]; then
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
    if [[ $f == spyder/plugins/completion/*/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/help/utils/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/ipythonconsole/widgets/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/editor/extensions/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/editor/panels/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/findinfiles/widgets/main_widget.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/application/widgets/__init__.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


# Depth 5
for f in spyder/*/*/*/*/*.py; do
    if [[ $f == *test*/*.* ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/completion/*/*/*.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/variableexplorer/widgets/objectexplorer/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/editor/widgets/codeeditor/__init__.py ]]; then
        continue
    fi
    if [[ $f == spyder/plugins/editor/widgets/editorstack/__init__.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done
