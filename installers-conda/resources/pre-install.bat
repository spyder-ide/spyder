@rem  Mark as conda-based-app
set menudir=%PREFIX%\envs\spyder-runtime\Menu
if not exist "%menudir%" mkdir "%menudir%"
echo. > "%menudir%\conda-based-app"
