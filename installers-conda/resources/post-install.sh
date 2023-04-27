#!/bin/bash
set -e

echo "*** Running post install script for ${INSTALLER_NAME} ..."

echo "Args = $@"
echo "Environment variables:"
env | sort
echo ""

# ----
name_lower=$(echo ${INSTALLER_NAME} | tr 'A-Z' 'a-z')

if [[ $OSTYPE = "darwin"* ]]; then
    shortcut_path="/Applications/Spyder.app"
    [[ ${PREFIX} = "$HOME"* ]] && shortcut_path="${HOME}${shortcut_path}"
else
    shortcut_path="$HOME/.local/share/applications/${name_lower}_${name_lower}.desktop"
fi

spy_exe=${PREFIX}/envs/spyder-rt/bin/spyder
u_spy_exe=${PREFIX}/uninstall-spyder.sh
m1="# >>> Added by Spyder >>>"
m2="# <<< Added by Spyder <<<"

case $SHELL in
    (*"zsh") shell_init=$HOME/.zshrc ;;
    (*"bash") shell_init=$HOME/.bashrc ;;
esac

# ----
echo "Creating uninstall script..."
cat <<EOF > ${u_spy_exe}
#!/bin/bash

echo "You are about to uninstall Spyder."
echo "If you proceed, aliases will be removed from ~/.bashrc (if present)"
echo "and the following will be removed:"
echo "  ${shortcut_path}"
echo "  ${PREFIX}"
echo ""
echo "Do you wish to continue?"
read -p " [yes|NO]: " confirm
if [[ \$confirm != [yY] && \$confirm != [yY][eE][sS] ]]; then
    echo "Uninstall aborted."
    exit 1
fi

if [[ \$OSTYPE = "darwin"* ]]; then
    echo "Quitting Spyder.app..."
    osascript -e 'quit app "Spyder.app"' 2> /dev/null
fi

# Remove shortcut and environment
rm -rf ${shortcut_path}
rm -rf ${PREFIX}

# Remove aliases from shell startup
if [[ -e ${shell_init} ]]; then
	sed -i '/$m1/,/$m2/d' ${shell_init}
fi
EOF
chmod +x ${u_spy_exe}

# ----
echo "Creating aliases in $shell_init ..."
new_text="$m1\nalias uninstall-spyder=${u_spy_exe}"
if [[ $OSTYPE = "linux"* ]]; then
    new_text=${new_text}"\nalias spyder=${spy_exe}"
fi
new_text=${new_text}"\n$m2"
sed -i "/$m1/,/$m2/{h;/$m2/ s|.*|${new_text}|; t; d};\${x;/^$/{s||\n${new_text}|;H};x}" $shell_init

# ----
if [[ $OSTYPE = "linux"* ]]; then
    cat <<EOF

###############################################################################
Spyder can be launched by standard methods in Gnome and KDE desktop
environments. Additionally, Spyder can be launched in Gtk-based desktop
environments (e.g. Xfce) from the command line:

$ gtk-launch spyder

Spyder can also be launched from the command line for all Linux variants
by:

$ spyder

To uninstall Spyder, run the following from the command line:

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
fi

echo "*** Post install script for ${INSTALLER_NAME} complete"
