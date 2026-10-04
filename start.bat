@echo off
rem Scrinium starter. Prefer the bundled exe, fall back to pythonw.
setlocal
cd /d "%~dp0"
set "PYTHONPATH="

if exist "dist\Scrinium.exe" (
    start "" "dist\Scrinium.exe"
    exit /b
)
if exist "Scrinium.exe" (
    start "" "Scrinium.exe"
    exit /b
)

set "SYS=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%SYS%" (
    start "" "%SYS%" "%~dp0main.pyw"
) else (
    start "" pythonw "%~dp0main.pyw"
)
exit /b