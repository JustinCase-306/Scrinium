@echo off
rem Scrinium starter.
rem
rem Reihenfolge:
rem   1. Scrinium.exe neben dieser Datei          (installiert / entpackt)
rem   2. dist\Scrinium.exe                        (aus dem Quellcode gebaut)
rem   3. pythonw.exe + main.pyw                   (Python im PATH noetig)
rem
rem Ohne Fenster in der Konsole: start "" statt Aufruf.
setlocal
cd /d "%~dp0"

rem Leer, weil ein global gesetzter Agenten-Pfad PyInstaller beim Bauen
rem ein fremdes cffi einpackt und die fertige EXE dann abstuerzt.
set "PYTHONPATH="

if exist "Scrinium.exe" (
    start "" "%~dp0Scrinium.exe"
    exit /b
)

if exist "dist\Scrinium.exe" (
    start "" "%~dp0dist\Scrinium.exe"
    exit /b
)

rem Kein fertiges Programm: Python starten und den Quellcode nehmen.
set "PYW=%LOCALAPPDATA%\Programs\Python\Python312\pythonw.exe"
if exist "%PYW%" (
    start "" "%PYW%" "%~dp0main.pyw"
    exit /b
)

where pythonw >nul 2>&1
if %ERRORLEVEL%==0 (
    start "" pythonw "%~dp0main.pyw"
    exit /b
)

echo Kein Scrinium gefunden und kein Python installiert.
echo Baue es mit build.bat, oder installiere es mit Scrinium-Setup.exe.
pause
exit /b 1