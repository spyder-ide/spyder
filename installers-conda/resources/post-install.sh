#!/bin/bash
set -e

echo "*** Starting post install script for __NAME__.app"

cat <<EOF
__PKG_NAME_LOWER__
__NAME__
__VERSION__
__CHANNELS__
__WRITE_CONDARC__
__SHORTCUTS__
__DEFAULT_PREFIX__
__LICENSE__
__FIRST_PAYLOAD_SIZE__
__SECOND_PAYLOAD_SIZE__
__MD5__
__INSTALL_COMMANDS__
__PLAT__
__NAME_LOWER__
EOF

ROOT_PREFIX=$(cd "$2/Library/__PKG_NAME_LOWER__"; pwd)
PREFIX=$(cd "$ROOT_PREFIX/envs/__PKG_NAME_LOWER__"; pwd)

# Installed for all users
app_path="/Applications/__NAME__.app"

if [[ "$PREFIX" == "$HOME"* ]]; then
    # Installed for user
    app_path="$HOME$app_path"
fi

echo "Args = $@"
echo "$(declare -p)"

if [[ -e "$app_path" ]]; then
    if [[ ! -e "/usr/libexec/PlistBuddy" ]]; then
        echo "/usr/libexec/PlistBuddy not installed"
        exit 1
    fi

    echo "Creating python symbolic link..."
    ln -sf "$PREFIX/bin/python" "$app_path/Contents/MacOS/python"

    echo "Modifying application executable..."
    cp -fp "$PREFIX/Menu/__NAME__" "$app_path/Contents/MacOS/__NAME__"

    echo "Patching Info.plist..."
    plist=$app_path/Contents/Info.plist
    /usr/libexec/PlistBuddy -c "Add :LSEnvironment dict" $plist || true
    /usr/libexec/PlistBuddy -c "Add :LSEnvironment:ROOT_PREFIX string" $plist || true
    /usr/libexec/PlistBuddy -c "Set :LSEnvironment:ROOT_PREFIX $ROOT_PREFIX" $plist
    /usr/libexec/PlistBuddy -c "Add :LSEnvironment:PREFIX string" $plist || true
    /usr/libexec/PlistBuddy -c "Set :LSEnvironment:PREFIX $PREFIX" $plist
    /usr/libexec/PlistBuddy -c "Add :LSEnvironment:SPYDER_APP string" $plist || true
    /usr/libexec/PlistBuddy -c "Set :LSEnvironment:SPYDER_APP $app_path" $plist
else
    echo "$app_path does not exist"
fi

echo "*** Post install script for __NAME__.app complete"
