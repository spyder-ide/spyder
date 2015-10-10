#!/usr/bin/env bash

set -ex

# Tell Spyder we're testing our widgets in Travis
export TEST_TRAVIS_WIDGETS=True

for f in spyderlib/*.py; do
    if [[ $f == "spyderlib/restart_app.py" ]]; then
        continue
    fi
    if [[ $f == "spyderlib/spyder.py" ]]; then
        continue
    fi
    if [[ $f == "spyderlib/tour.py" ]]; then
        continue
    fi
    if [[ $f == "spyderlib/start_app.py" ]]; then
        continue
    fi
    if [[ $f == "spyderlib/pil_patch.py" ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done


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
    if [[ $f == spyderlib/widgets/*.py ]]; then
        continue
    fi
    python "$f"
    if [ $? -ne 0 ]; then
        exit 1
    fi
done
