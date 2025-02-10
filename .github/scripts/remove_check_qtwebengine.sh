#!/usr/bin/env bash

set -o pipefail

echo "which spyder: $(which spyder)"
pip show qtwebengine
TO=10s
for i in 1 2; do
    echo "::group::Iteration $i"
    if [[ "$i" == "2" ]]; then
        echo "Removing pyqtwebengine"
        pip remove -y pyqtwebengine
        echo
    fi
    echo "Running Spyder with a timeout of $TO:"
    timeout $TO spyder
    RESULT=$?
    if [[ $RESULT -eq 124 ]]; then
        echo "Spyder succeeded with timeout"
        echo
    else
        echo "Spyder failed with error code $RESULT (should be 124 for timeout)"
        exit 1
    fi
    echo "::endgroup::"
done
