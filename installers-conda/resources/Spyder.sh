#!/bin/bash
eval "$($SHELL -l -c "declare -x")"

eval "$("$ROOT_PREFIX/_conda.exe" shell.bash activate "$PREFIX")"

$(dirname "$0")/python $CONDA_PREFIX/bin/spyder "$@"
