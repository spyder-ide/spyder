REM Tell Spyder we're testing the app
set TEST_CI_APP=True

REM Set extra packages
set EXTRA_PACKAGES=pandas sympy pillow

if %USE_QT_API%==PyQt4 (
    set EXTRA_PACKAGES=%EXTRA_PACKAGES% matplotlib
)

REM Move to a tmp dir before doing the installation
mkdir C:\projects\tmp
cd C:\projects\tmp

REM Install the package we created
conda install -q -y --use-local spyder==3.0.0b1

REM Install extra packages
conda install -q -y %EXTRA_PACKAGES%

REM Test that the app starts correctly
echo ------- Testing the app ---------
echo.
echo %time%
spyder || exit 1
echo Sucess!
echo %time%
echo.
echo ---------------------------------
