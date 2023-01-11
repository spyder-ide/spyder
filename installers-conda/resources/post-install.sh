#!/bin/bash
set -e

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "$(declare -p)"

name_lower=${INSTALLER_NAME,,}
_shortcut_path="$HOME/.local/share/applications/${name_lower}_${name_lower}.desktop"
shortcut_path="$(dirname ${_shortcut_path})/${name_lower}.desktop"
if [[ -e ${_shortcut_path} ]]; then
    echo "Renaming ${_shortcut_path}..."
    mv -f "${_shortcut_path}" "${shortcut_path}"
else
    echo "${_shortcut_path} does not exist"
fi

case $SHELL in
    (*"zsh") shell_init=$HOME/.zshrc ;;
    (*"bash") shell_init=$HOME/.bashrc ;;
esac
spyder_exe=$(echo ${PREFIX}/envs/*/bin/spyder)


if [[ ! -e "$spyder_exe" ]]; then
    echo "$spyder_exe not found. Alias not created."
elif [[ -z "$shell_init" ]]; then
    echo "Aliasing for $SHELL not implemented."
else
    echo "Aliasing Spyder's executable in $shell_init ..."
    sed -i "/alias spyder=/{h;s|=.*|=${spyder_exe}|};\${x;/^$/{s||\nalias spyder=${spyder_exe}|;H};x}" $shell_init
fi

echo "Creating uninstall script..."
cat <<EOF > ${PREFIX}/uninstall.sh
#!/bin/bash
rm -rf ${shortcut_path}
rm -rf ${PREFIX}
EOF
chmod +x ${PREFIX}/uninstall.sh

cat <<EOF

###############################################################################
Spyder can be launched by standard methods in Gnome and KDE desktop
environments. Additionally, Spyder can be launched in Gtk-based desktop
environments (e.g. Xfce) from the command line:

$ gtk-launch spyder

Spyder can also be launched from the command line for all Linux variants
by:

$ spyder

To uninstall Spyder, you need to run from the following from the command line:

$ ${PREFIX}/uninstall.sh

###############################################################################

EOF

echo "*** Post install script for ${INSTALLER_NAME} complete"
