echo "aaaaaaa"
set TEMP_DIR=%1
echo "%TEMP_DIR%"

@echo off
echo "This is a temporary file created by win32" > %TEMP_DIR%\output_file.txt
exit
