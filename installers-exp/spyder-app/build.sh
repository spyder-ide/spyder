#!/bin/bash

$PYTHON -m pip install . --no-deps --ignore-installed --no-cache-dir -vvv

mkdir -p "${PREFIX}/Menu"
sed "s/__PKG_VERSION__/${PKG_VERSION}/" "${SRC_DIR}/installers-exp/menuinst_config.json" > "${PREFIX}/Menu/spyder-menu.json"
cp "${SRC_DIR}/img_src/spyder.png" "${PREFIX}/Menu/spyder.png"
cp "${SRC_DIR}/img_src/spyder.icns" "${PREFIX}/Menu/spyder.icns"
cp "${SRC_DIR}/img_src/spyder.ico" "${PREFIX}/Menu/spyder.ico"

rm -rf $PREFIX/man
rm -f $PREFIX/bin/spyder_win_post_install.py
rm -rf $SP_DIR/Sphinx-*
