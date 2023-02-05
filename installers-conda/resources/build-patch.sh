
# Create the Menu directory
mkdir -p "${PREFIX}/Menu"

# Copy menu.json template
sed "s/__PKG_VERSION__/${PKG_VERSION}/" "${SRC_DIR}/installers-conda/resources/spyder-menu.json" > "${PREFIX}/Menu/spyder-menu.json"

# Copy application icons
icon_ext="ico"
case $OSTYPE in
    ("darwin"*) icon_ext="icns";;
    ("linux"*) icon_ext="png";;
esac
cp "${SRC_DIR}/img_src/spyder.${icon_ext}" "${PREFIX}/Menu/spyder.${icon_ext}"
