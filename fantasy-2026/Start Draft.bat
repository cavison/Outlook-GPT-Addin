@echo off
setlocal
title On the Clock - 2026 Draft Assistant
cd /d "%~dp0"

echo.
echo   ON THE CLOCK - 2026 fantasy draft assistant
echo   ==========================================
echo.

if not exist "fantasy-draft.py" goto nofile

rem --- find a Python we can use -------------------------------------------
set "PY="
where py >nul 2>nul
if %errorlevel% equ 0 set "PY=py"
if defined PY goto checkver
where python >nul 2>nul
if %errorlevel% equ 0 set "PY=python"
if defined PY goto checkver
where python3 >nul 2>nul
if %errorlevel% equ 0 set "PY=python3"
if defined PY goto checkver
goto nopython

:checkver
"%PY%" -c "import sys; sys.exit(0 if sys.version_info >= (3,8) else 1)" >nul 2>nul
if %errorlevel% neq 0 goto oldpython

rem --- go ------------------------------------------------------------------
echo   Starting up. Your browser should open in a second.
echo   If it does not, go to:  http://127.0.0.1:8712
echo.
echo   KEEP THIS WINDOW OPEN for the whole draft.
echo   Closing it stops the assistant. Your picks stay saved either way.
echo.
"%PY%" fantasy-draft.py
echo.
echo   Stopped. Your draft is saved in the fantasy-draft-data folder
echo   right next to this file.
echo.
pause
exit /b 0

:nofile
echo   PROBLEM: fantasy-draft.py is not in this folder.
echo.
echo   This file and fantasy-draft.py have to sit in the SAME folder.
echo   Move them together, then run this again.
echo.
pause
exit /b 1

:nopython
echo   PROBLEM: Python is not installed on this computer.
echo.
echo   1. Get it from  https://www.python.org/downloads/
echo   2. Run the installer.
echo   3. On the very first screen, TICK THE BOX that says
echo      "Add python.exe to PATH". This matters - it is easy to miss.
echo   4. Finish, then double-click this file again.
echo.
echo   Opening the download page for you...
start "" "https://www.python.org/downloads/"
pause
exit /b 1

:oldpython
echo   PROBLEM: the Python on this computer is too old.
echo   Version 3.8 or newer is needed.
echo.
echo   Install a current version from https://www.python.org/downloads/
echo   and tick "Add python.exe to PATH" on the first screen.
echo.
start "" "https://www.python.org/downloads/"
pause
exit /b 1
