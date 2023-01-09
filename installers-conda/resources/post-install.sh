#!/bin/bash
set -e

echo "*** Running post install script for __NAME__ ..."

cat <<EOF
* __PKG_NAME_LOWER__
* __NAME__
* __VERSION__
* __CHANNELS__
* __WRITE_CONDARC__
* __SHORTCUTS__
* __DEFAULT_PREFIX__
* __LICENSE__
* __FIRST_PAYLOAD_SIZE__
* __SECOND_PAYLOAD_SIZE__
* __MD5__
* __INSTALL_COMMANDS__
* __PLAT__
* __NAME_LOWER__
EOF

echo "Args = $@"
echo "$(declare -p)"

if [[ $OSTYPE == "darwin"* ]]; then
    # macOS
    ENV_PREFIX=$(cd "${PREFIX}/envs/__NAME_LOWER__"; pwd)
    app_path="$(dirname ${DSTROOT})/Applications/__NAME__.app"

    if [[ -e "$app_path" ]]; then
        echo "Creating python symbolic link..."
        ln -sf "${ENV_PREFIX}/bin/python" "$app_path/Contents/MacOS/python"
    else
        echo "ERROR: $app_path does not exist"
        exit 1
    fi

else
    # Linux
    name_lower=${INSTALLER_NAME,,}
    app_path="$HOME/.local/share/applications/${name_lower}_${name_lower}.desktop"
    if [[ -e ${app_path} ]]; then
        echo "Renaming ${app_path}..."
        mv -f "${app_path}" "$(dirname ${app_path})/${name_lower}.desktop"
    else
        echo "${app_path} does not exist"
    fi

    spyder_exe=$(echo ${PREFIX}/envs/*/bin/spyder)
    if [[ -e "$spyder_exe" ]]; then
        case $SHELL in
            (*"zsh") init_file=$HOME/.zshrc ;;
            (*"bash") init_file=$HOME/.bashrc ;;
        esac
        echo "Aliasing Spyder's executable in $init_file ..."
        sed -i "/alias spyder=/{h;s|=.*|=${spyder_exe}|};\${x;/^$/{s||\nalias spyder=${spyder_exe}|;H};x}" $init_file
    else
        echo "$spyder_exe not found. Alias not created."
    fi

    cat <<EOF

Spyder can be launched by standard methods in Gnome and KDE desktop
environments. Additionally, Spyder can be launched in Gnome desktop
environments from the command line:

$ gtk-launch spyder

Spyder can be launched from the command line for all Linux variants
by:

$ spyder


EOF

fi

echo "*** Post install script for __NAME__ complete"
