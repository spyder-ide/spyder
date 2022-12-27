
# Create the Menu directory
mkdir -p "${PREFIX}/Menu"

# Copy menu.json template
sed "s/__PKG_VERSION__/${PKG_VERSION}/" "${SRC_DIR}/installers-conda/resources/spyder-menu.json" > "${PREFIX}/Menu/spyder-menu.json"

# Copy application icons
case $OSTYPE in
    ("darwin"*)
        cp "${SRC_DIR}/img_src/spyder.icns" "${PREFIX}/Menu/spyder.icns";;
    ("linux"*)
        cp "${SRC_DIR}/branding/logo/logomark/spyder-logomark-background.png" "${PREFIX}/Menu/spyder.png";;
    (*)
        cp "${SRC_DIR}/img_src/spyder.ico" "${PREFIX}/Menu/spyder.ico"
esac
