#!/usr/bin/env bash

set -eo pipefail

echo "which spyder: $(which spyder)"
pip show pyqtwebengine
TO=10s
for i in 1 2; do
    echo "::group::Iteration $i"
    if [[ "$i" == "2" ]]; then
        echo "Removing pyqtwebengine"
        pip uninstall -y pyqtwebengine
        echo
    fi
    echo "Running Spyder with a timeout of $TO:"
    set +e
    timeout $TO spyder
    RESULT=$?
    set -e
    if [[ $RESULT -eq 124 ]]; then
        echo "Spyder succeeded with timeout"
        echo
    else
        echo "Spyder failed with error code $RESULT (should be 124 for timeout)"
        exit 1
    fi
    echo "::endgroup::"
done
