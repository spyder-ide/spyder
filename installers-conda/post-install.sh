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
    echo "Creating python symbolic link..."
    ln -sf "$PREFIX/bin/python" "$app_path/Contents/MacOS/python"

    echo "Modifying application executable..."
cat <<EOF > $app_path/Contents/MacOS/__NAME__
#!/bin/bash
eval "\$(/bin/bash -l -c "declare -x")"
eval "\$("$ROOT_PREFIX/_conda.exe" shell.bash activate "$PREFIX")"
export SPYDER_APP=0
\$(dirname \$BASH_SOURCE)/python $PREFIX/bin/spyder "\$@"

EOF
else
    echo "$app_path does not exist"
fi

echo "*** Post install script for __NAME__.app complete"
