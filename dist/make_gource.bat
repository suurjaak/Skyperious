:: Runs Gource on the local Git directory and converts result into mkv video
:: with FFmpeg. Note: intermediary .ppm file can easily be 10G+.
::
:: @author    Erki Suurjaak
:: @created   13.01.2013
:: @modified  22.02.2014
@echo off
set INITIAL_DIR=%CD%
cd %0\..
cd..
set SOURCE_DIR=%CD%
set GOURCE_DIR=C:\Program Files\Gource
set FFMPEG_DIR=C:\Program Files\multimedia\ffmpeg
if not exist "%GOURCE_DIR%" set GOURCE_DIR=C:\Program Files (x86)\Gource
if not exist "%FFMPEG_DIR%" set FFMPEG_DIR=C:\Program Files (x86)\ffmpeg
if not exist "%GOURCE_DIR%" echo Gource not found & goto :END
if not exist "%FFMPEG_DIR%" echo FFMPEG not found & goto :END
set PPM_PATH=%INITIAL_DIR%\gource.ppm
for /f "tokens=2-4 delims=/. " %%a in ('date /t') do (set TODAY=%%c-%%b-%%a)
set OUT_PATH=%INITIAL_DIR%\gource.%TODAY%.avi
echo Making gource.%TODAY%.avi from local Git directory. To stop, press Escape in Gource window.

:: Gource parameter info: 
:: "--auto-skip-seconds 1800" skip to next if nothing happens for 1800 seconds
:: "--stop-at-time 10" stop after 10 seconds; "--time-scale" valid values 0..4
"%GOURCE_DIR%\gource" --viewport 1280x720 --output-ppm-stream "%PPM_PATH%" --time-scale 2 --seconds-per-day 10 --file-idle-time 0 --highlight-dirs --key --max-file-lag -1 --hide mouse,users,usernames --output-framerate 30 --logo res\Icon32x32_32bit.png --logo-offset 1235x30 --title "Skyperious private branch history" --path "%SOURCE_DIR%"
:: FFMPEG parameter info: "-y" overwrite output, "-r 60" fps 60, "-f image2pipe" force format, "-vcodec ppm" force video codec,
if not ERRORLEVEL 1 "%FFMPEG_DIR%\bin\ffmpeg" -y -r 30 -f image2pipe -vcodec ppm -i "%PPM_PATH%" -f avi -c:v mpeg4 -b:v 4000k "%OUT_PATH%"
if exist "%OUT_PATH%" echo. & echo Created gource.%TODAY%.avi.
del "%PPM_PATH%"

:END
cd "%INITIAL_DIR%"
