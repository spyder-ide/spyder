@echo off
IF EXIST "%~dpn0\..\..\python.exe" (
	"%~dpn0\..\..\python.exe" "%~dpn0" %*
) ELSE (
	python.exe "%~dpn0" %*
)
