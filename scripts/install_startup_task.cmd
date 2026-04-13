@echo off
setlocal EnableExtensions

set "EXIT_CODE=0"
set "TASK_NAME=iSchedWiseAutoStart"
set "SCRIPT_DIR=%~dp0"
set "RUNNER_SCRIPT=%SCRIPT_DIR%startup_ischedwise_boot.cmd"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help
if /I "%~1"=="remove" goto :remove

if not exist "%RUNNER_SCRIPT%" (
    echo [ERROR] Missing runner script:
    echo         %RUNNER_SCRIPT%
    echo [ERROR] Create startup_ischedwise_boot.cmd first.
    set "EXIT_CODE=1"
    goto :final
)

call :requireAdmin %*
if errorlevel 2 (
    set "EXIT_CODE=1"
    goto :final
)
if errorlevel 1 goto :final

echo [INFO] Creating or updating startup task "%TASK_NAME%"...
schtasks /Create /F /TN "%TASK_NAME%" /SC ONSTART /RU "SYSTEM" /RL HIGHEST /TR "\"%RUNNER_SCRIPT%\"" >nul
if errorlevel 1 (
    echo [ERROR] Failed to create startup task.
    echo [ERROR] Run this script from an elevated Command Prompt.
    set "EXIT_CODE=1"
    goto :final
)

echo [OK] Startup task installed.
echo [INFO] Test now:  schtasks /Run /TN "%TASK_NAME%"
echo [INFO] Verify:    schtasks /Query /TN "%TASK_NAME%" /V /FO LIST
echo [INFO] Remove:    %~nx0 remove
goto :final

:remove
call :requireAdmin %*
if errorlevel 2 (
    set "EXIT_CODE=1"
    goto :final
)
if errorlevel 1 goto :final

schtasks /Query /TN "%TASK_NAME%" >nul 2>&1
if errorlevel 1 (
    echo [INFO] Task "%TASK_NAME%" does not exist. Nothing to remove.
    goto :final
)

echo [INFO] Removing startup task "%TASK_NAME%"...
schtasks /Delete /TN "%TASK_NAME%" /F >nul
if errorlevel 1 (
    echo [ERROR] Failed to remove task "%TASK_NAME%".
    set "EXIT_CODE=1"
    goto :final
)

echo [OK] Startup task removed.
goto :final

:help
echo Usage:
echo   install_startup_task.cmd
echo   install_startup_task.cmd remove
echo.
echo This script creates a Task Scheduler entry that runs at Windows startup:
echo   - Task name: iSchedWiseAutoStart
echo   - Trigger:   At system startup
echo   - User:      SYSTEM
echo   - Privilege: Highest
echo   - Action:    startup_ischedwise_boot.cmd
goto :final

:requireAdmin
net session >nul 2>&1
if "%ERRORLEVEL%"=="0" exit /b 0

if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
)

if errorlevel 1 (
    echo [ERROR] Elevation failed or was cancelled.
    exit /b 2
)

echo [INFO] Elevated process started. Exiting current process.
exit /b 1

:final
set "FINAL_EXIT=%EXIT_CODE%"
endlocal & exit /b %FINAL_EXIT%
