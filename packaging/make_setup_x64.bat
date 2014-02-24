:: Creates NSIS setup file for 64-bit executable, assumed to be in working
:: directory, named skyperious_%conf.Version%_x64.exe. Can be given in
:: argument; version number is parsed from filename.
::
:: @author    Erki Suurjaak
:: @created   13.01.2013
:: @modified  22.02.2014
@echo off
set INITIAL_DIR=%CD%
cd %0\..
set SETUPDIR=%CD%
cd ../src
if [%1] == [] (
    for /F %%I IN ('python -c "import conf; print conf.Version"') do set VERSION=%%I
) else (
    for /f "tokens=2 delims=_ " %%a in ("%1") do (set VERSION=%%a)
)
set EXEFILE=%INITIAL_DIR%\skyperious_%VERSION%_x64.exe
cd %SETUPDIR%
if not exist "%EXEFILE%" echo %EXEFILE% missing. && goto :EOF
set DESTFILE=skyperious_%VERSION%_x64_setup.exe
echo Creating 64-bit installer for Skyperious %VERSION%.
if exist "%DESTFILE%" echo Removing previous %DESTFILE%. & del "%DESTFILE%"
if exist skyperious.exe del skyperious.exe
copy /V "%EXEFILE%" skyperious.exe > NUL
set NSISDIR=C:\Program Files (x86)\Nullsoft Scriptable Install System
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files\Nullsoft Scriptable Install System
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files (x86)\NSIS
if not exist "%NSISDIR%" set NSISDIR=C:\Program Files\NSIS
"%NSISDIR%\makensis.exe" /DPRODUCT_VERSION=%VERSION% "%SETUPDIR%\exe_setup_x64.nsi"
del skyperious.exe > NUL
echo.
if exist "%DESTFILE%" echo Successfully created Skyperious source distribution %DESTFILE%.
move "%DESTFILE%" "%INITIAL_DIR%" > NUL
cd "%INITIAL_DIR%"
