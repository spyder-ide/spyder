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
spy_exe=$(echo ${PREFIX}/envs/*/bin/spyder)
u_spy_exe=${PREFIX}/uninstall-spyder.sh

if [[ ! -e "$spy_exe" ]]; then
    echo "$spy_exe not found. Alias not created."
elif [[ -z "$shell_init" ]]; then
    echo "Aliasing for $SHELL not implemented."
else
    echo "Aliasing Spyder's executable in $shell_init ..."
    m1="# <<<< Added by Spyder <<<<"
    m2="# >>>> Added by Spyder >>>>"
    new_text="$m1\nalias spyder=${spy_exe}\nalias uninstall-spyder=${u_spy_exe}\n$m2"
    sed -i "/$m1/,/$m2/{h;/$m2/ s|.*|${new_text}|; t; d};\${x;/^$/{s||\n${new_text}|;H};x}" $shell_init
fi

echo "Creating uninstall script..."
cat <<EOF > ${u_spy_exe}
#!/bin/bash
echo "You are about to uninstall Spyder."
echo "If you proceed, aliases will be removed from ~/.bashrc (if present)"
echo "and the following file and directory will be removed:"
echo ""
echo "  ${shortcut_path}"
echo "  ${PREFIX}"
echo ""
echo "Do you wish to continue?"
read -p " [yes|NO]: " confirm
if [[ \$confirm != [yY] && \$confirm != [yY][eE][sS] ]]; then
    echo "Uninstall aborted."
    exit 1
fi
rm -rf ${shortcut_path}
rm -rf ${PREFIX}
EOF
if [[ -n "$shell_init" ]]; then
    # Remove aliases from shell startup
    echo "sed -i '/$m1/,/$m2/d' $shell_init" >> ${u_spy_exe}
fi
chmod +x ${u_spy_exe}

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

$ uninstall-spyder

#####################
# !!! IMPORTANT !!! #
#####################

The spyder and uninstall-spyder commands will only be available in new shell
sessions. To make them available in this session you must source your .bashrc
file with:

$ source ~/.bashrc

###############################################################################

EOF

echo "*** Post install script for ${INSTALLER_NAME} complete"
