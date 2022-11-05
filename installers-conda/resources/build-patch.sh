mkdir -p "${PREFIX}/Menu"
sed "s/__PKG_VERSION__/${PKG_VERSION}/" "${SRC_DIR}/installers-conda/resources/spyder-menu.json" > "${PREFIX}/Menu/spyder-menu.json"
cp "${SRC_DIR}/img_src/spyder.png" "${PREFIX}/Menu/spyder.png"
cp "${SRC_DIR}/img_src/spyder.icns" "${PREFIX}/Menu/spyder.icns"
cp "${SRC_DIR}/img_src/spyder.ico" "${PREFIX}/Menu/spyder.ico"

if [[ $OSTYPE = "darwin"* ]]; then
    if [[ -z $(which shc) ]]; then
        echo "Installing shc shell script compiler..."
        brew install shc
    fi
    echo "Compiling Spyder.sh..."
    shc -r -f "${SRC_DIR}/installers-conda/resources/Spyder.sh" -o "${PREFIX}/Menu/Spyder"
fi
