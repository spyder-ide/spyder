%PYTHON% -m pip install . --no-deps --ignore-installed --no-cache-dir -vvv
if errorlevel 1 exit 1

set MENU_DIR=%PREFIX%\Menu
IF NOT EXIST (%MENU_DIR%) mkdir %MENU_DIR%

copy %SRC_DIR%\img_src\spyder.ico %MENU_DIR%\
if errorlevel 1 exit 1
copy %RECIPE_DIR%\menu-windows.json %MENU_DIR%\spyder_shortcut.json
if errorlevel 1 exit 1

del %SCRIPTS%\spyder_win_post_install.py
del %SCRIPTS%\spyder.bat
del %SCRIPTS%\spyder
