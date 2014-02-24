:: Goes through all .spec files in the directory and feeds them to PyInstaller,
:: or selects files given in first argument.
::
:: @author    Erki Suurjaak
:: @created   15.01.2013
:: @modified  22.02.2014
@echo off
set INITIAL_DIR=%CD%
cd %0\..
set SOURCE_DIR=%CD%
set WILDCARD=*.spec
if not "%1" == "" set WILDCARD=%1

for %%X IN (%WILDCARD%) do call :LOOPBODY %%X
goto :END

:LOOPBODY
:: Runs pyinstaller with %1 spec, copies exe, cleans up.
echo Making EXE for %1.
pyi-build.exe "%1" >> "makeexe.log" 2>&1
if exist dist\*.exe (
    for %%E IN (dist\*.exe) do (
        move %%E "%INITIAL_DIR%" > NUL
        echo Created %%~nE.exe for %1.
    )
    del makeexe.log logdict*.final.*.log
    if exist build rd /q /s build
    if exist dist rd /q /s dist
) else (
    echo %1 result failed, check %SOURCE_DIR%\makeexe.log for errors.
)
echo.
goto :END


:END
cd "%INITIAL_DIR%"
