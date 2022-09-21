#!/bin/bash
set -e

echo "*** Starting pre install script for Spyder installer"

echo "Args = $@"
echo "$(declare -p)"

# quit the application
echo "Quitting Spyder.app..."
osascript -e 'quit app "Spyder.app"' 2> /dev/null

PREFIX=$(cd "$2/__NAME_LOWER__"; pwd)
ROOT_PREFIX=$(cd "$PREFIX/../../"; pwd)

if [[ "$PREFIX" == "$HOME"* ]]; then
    # Installed for user
    app_path="$HOME/Applications/Spyder.app"
else
    # Installed for all users
    app_path="/Applications/Spyder.app"
fi

# Delete the application
if [[ -e "$app_path" ]]; then
    echo "Removing $app_path..."
    rm -r "$app_path"
fi

# Delete the environment
if [[ -e "$ROOT_PREFIX" ]]; then
    echo "Removing $ROOT_PREFIX"
    rm -r "$ROOT_PREFIX"
fi

echo "*** Pre install script for Spyder installer complete"
