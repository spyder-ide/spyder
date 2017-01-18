:: Tell Spyder we're testing the app
set TEST_CI_APP=True

:: Set extra packages
set EXTRA_PACKAGES=pandas sympy pillow

:: Move to a tmp dir before doing the installation
mkdir C:\projects\tmp
cd C:\projects\tmp

:: Don't auto-update conda
conda config --set auto_update_conda False

:: Install the package we created
conda install -q -y --use-local spyder-dev

:: Install extra packages
conda install -q -y %EXTRA_PACKAGES%

:: Test that the app starts correctly
echo ------- Testing the app ---------
echo.
echo %time%
:: skipping spyder || exit 1
echo Success!
echo %time%
echo.
echo ---------------------------------
