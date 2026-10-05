@echo off
rem Build Scrinium:  build.bat            -> Scrinium.exe
rem                  build.bat --test     -> run tests first
rem                  build.bat installer  -> also build Scrinium-Setup.exe
setlocal
cd /d "%~dp0"

rem WICHTIG: PYTHONPATH/PYTHONHOME muessen leer sein.
rem Steht global z.B. der Pfad eines Agenten im PATH, zieht PyInstaller
rem deren cffi mit - und die fertige EXE startet dann mit
rem "Version mismatch: cffi 2.0.0 ... 2.1.1" und nicht.
set "PYTHONPATH="
set "PYTHONHOME="

rem Use the project venv when present, else whatever python is on PATH.
set "PY=python"
if exist ".venv\Scripts\python.exe" set "PY=.venv\Scripts\python.exe"

if /i "%~1"=="--test" (
    echo Running tests ...
    "%PY%" -m pytest tests\ -q --tb=short || exit /b 1
)

rem A running Scrinium.exe would lock dist\.
taskkill /F /IM Scrinium.exe /T >nul 2>&1

if not exist "assets\scrinium.ico" "%PY%" -m scrinium.icons

echo Building Scrinium.exe ...
"%PY%" -m PyInstaller --noconfirm --clean Scrinium.spec || exit /b 1
if not exist "dist\Scrinium.exe" (
    echo [ERROR] dist\Scrinium.exe missing.
    exit /b 1
)

if /i not "%~1"=="installer" goto done

echo Building Scrinium-Setup.exe ...
"%PY%" -m PyInstaller --noconfirm --clean Installer.spec || exit /b 1

:done
echo.
echo OK:
for %%F in (dist\*.exe) do echo   %%~zF bytes  %%~nxF
endlocal