@echo off
chcp 65001 > NUL

REM Check git version
git --version > NUL 2>&1
if %ERRORLEVEL% neq 0 (
    echo Cannot find Git executable, make sure it is installed and added to your PATH.
    pause
    exit /B 0
)

REM Check python version
for /f "delims= " %%i in ('python --version') do set python_version=%%i
if not defined python_version (
    echo Cannot find Python executable, make sure it is installed and added to your PATH.
    pause
    exit /B 0
) else (
    call :compareVersions %python_version:Python =% "3.6"
    if %errorlevel% equ -1 (
        echo Python 3.6 or newer required. %python_version% found.
        pause
        exit /B 0
    )
)

REM Create the virtual env if necessary
if not exist ".venv" (
    echo Creating virtual env
	python -m venv .venv
)

REM Activate and update the virtual env
call .venv\Scripts\activate.bat
pip install -Ur requirements.txt

REM Check libopus
python3 -c "exit(__import__('discord').opus.is_loaded())" > NUL 2>&1
if %ERRORLEVEL% equ 0 (
    echo Cannot find libopus on your system, make sure it is installed.
    pause
    exit /B 0
)

del /Q panda.log
python panda.py

REM Deactivate the virtual env
deactivate
pause
exit /b 0


:compareVersions  version1  version2
::
:: Compares two version numbers and returns the result in the ERRORLEVEL
::
:: Returns 1 if version1 > version2
::         0 if version1 = version2
::        -1 if version1 < version2
::
:: The nodes must be delimited by . or , or -
::
:: Nodes are normally strictly numeric, without a 0 prefix. A letter suffix
:: is treated as a separate node
::
setlocal enableDelayedExpansion
set "v1=%~1"
set "v2=%~2"
call :divideLetters v1
call :divideLetters v2
:loop
call :parseNode "%v1%" n1 v1
call :parseNode "%v2%" n2 v2
if %n1% gtr %n2% exit /b 1
if %n1% lss %n2% exit /b -1
if not defined v1 if not defined v2 exit /b 0
if not defined v1 exit /b -1
if not defined v2 exit /b 1
goto :loop


:parseNode  version  nodeVar  remainderVar
for /f "tokens=1* delims=.,-" %%A in ("%~1") do (
  set "%~2=%%A"
  set "%~3=%%B"
)
exit /b


:divideLetters  versionVar
for %%C in (a b c d e f g h i j k l m n o p q r s t u v w x y z) do set "%~1=!%~1:%%C=.%%C!"
exit /b