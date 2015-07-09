:: Goes through all .spec files in the directory and feeds them to PyInstaller,
:: or selects files given in first argument.
::
:: @author    Erki Suurjaak
:: @created   15.01.2013
:: @modified  23.04.2015
@echo off
set SOURCE_DIR=%CD%
set WILDCARD=*.spec
if not "%1" == "" set WILDCARD=%1

for %%X IN (%WILDCARD%) do call :LOOPBODY %%X
goto :EOF

:: Runs pyinstaller with %1 spec, copies exe, cleans up.
:LOOPBODY
echo Making EXE for %1.
call pyinstaller.bat "%1" >> "makeexe.log" 2>&1
if exist dist\*.exe (
    FOR %%E IN (dist\*.exe) DO (
        move %%E . > NUL
        echo Found %%~nE.exe for %1.
    )
    del makeexe.log logdict*.final.*.log
    if exist build rd /q /s build
    if exist dist rd /q /s dist
) else (
    echo No new EXE found for %1, check %SOURCE_DIR%\makeexe.log for errors.
)
echo.
goto :EOF
