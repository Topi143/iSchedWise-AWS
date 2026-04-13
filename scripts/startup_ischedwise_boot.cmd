@echo off
setlocal EnableExtensions

set "EXIT_CODE=0"

if /I "%~1"=="--help" goto :help
if /I "%~1"=="/?" goto :help

set "SCRIPT_DIR=%~dp0"
for %%I in ("%SCRIPT_DIR%..") do set "PROJECT_DIR=%%~fI"

set "XAMPP_DIR_INPUT=%XAMPP_DIR%"
set "ISCHEDWISE_XAMPP_DIR_INPUT=%ISCHEDWISE_XAMPP_DIR%"
set "PROGRAMFILES_X86=%ProgramFiles(x86)%"
set "XAMPP_DIR="
set "XAMPP_ATTEMPTED="
set "CLOUDFLARED_EXE="
set "LOG_DIR=%PROJECT_DIR%\scripts\logs"
set "LOG_FILE=%LOG_DIR%\startup_boot.log"

set "DRY_RUN=0"
if /I "%~1"=="--dry-run" set "DRY_RUN=1"

if not exist "%LOG_DIR%" mkdir "%LOG_DIR%" >nul 2>&1

call :log "============================================================"
call :log "startup_ischedwise_boot.cmd started"
call :log "PROJECT_DIR=%PROJECT_DIR%"
call :log "DRY_RUN=%DRY_RUN%"
call :resolveXamppDir
if errorlevel 1 (
    call :log "[WARN] XAMPP directory not auto-resolved. Service-based startup may still work."
    call :log "[WARN] Set ISCHEDWISE_XAMPP_DIR if fallback launchers are needed."
) else (
    call :log "[INFO] Resolved XAMPP_DIR=%XAMPP_DIR%"
)

if not exist "%PROJECT_DIR%\run.py" (
    call :log "[ERROR] run.py not found in %PROJECT_DIR%."
    call :log "[ERROR] Set PROJECT_DIR manually in this file if you moved the script."
    goto :fail
)

call :requireAdmin %*
if errorlevel 2 goto :fail
if errorlevel 1 goto :final

call :startCloudflared
if errorlevel 1 goto :fail

call :startXamppStack
if errorlevel 1 goto :fail

call :startISchedWise
if errorlevel 1 goto :fail

call :log "[OK] Startup sequence completed."
goto :final

:help
echo Usage:
echo   startup_ischedwise_boot.cmd
echo   startup_ischedwise_boot.cmd --dry-run
echo.
echo Actions:
echo   1. Ensure admin privileges
echo   2. Run: cloudflared tunnel run topi_pc
echo   3. Start XAMPP MySQL and Apache
echo   4. Start iSchedWise via run.py
echo.
echo Optional environment override:
echo   set ISCHEDWISE_XAMPP_DIR=D:\xampp
goto :final

:log
echo [%date% %time%] %~1
>>"%LOG_FILE%" echo [%date% %time%] %~1
exit /b 0

:requireAdmin
if "%DRY_RUN%"=="1" (
    call :log "[DRY-RUN] Skipping admin elevation check."
    exit /b 0
)

net session >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    call :log "[OK] Admin privileges confirmed."
    exit /b 0
)

call :log "[INFO] Requesting administrator privileges..."
if "%~1"=="" (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -Verb RunAs"
) else (
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath '%~f0' -ArgumentList '%*' -Verb RunAs"
)

if errorlevel 1 (
    call :log "[ERROR] Elevation failed or was cancelled."
    exit /b 2
)

call :log "[INFO] Elevated process started. Exiting current process."
exit /b 1

:resolveXamppDir
if defined XAMPP_DIR if exist "%XAMPP_DIR%\mysql_start.bat" if exist "%XAMPP_DIR%\apache_start.bat" exit /b 0

set "XAMPP_DIR="
set "XAMPP_ATTEMPTED="

if defined ISCHEDWISE_XAMPP_DIR_INPUT if not defined XAMPP_DIR call :considerXamppCandidate "%ISCHEDWISE_XAMPP_DIR_INPUT%"
if defined XAMPP_DIR_INPUT if not defined XAMPP_DIR call :considerXamppCandidate "%XAMPP_DIR_INPUT%"
if not defined XAMPP_DIR call :considerXamppCandidate "C:\xampp"
if defined ProgramFiles if not defined XAMPP_DIR call :considerXamppCandidate "%ProgramFiles%\xampp"
if defined PROGRAMFILES_X86 if not defined XAMPP_DIR call :considerXamppCandidate "%PROGRAMFILES_X86%\xampp"
if not defined XAMPP_DIR call :considerXamppCandidate "D:\xampp"
if not defined XAMPP_DIR call :considerXamppCandidate "E:\xampp"

if defined XAMPP_DIR exit /b 0
exit /b 1

:considerXamppCandidate
set "CANDIDATE_DIR=%~1"
if not defined CANDIDATE_DIR exit /b 0

if not defined XAMPP_ATTEMPTED (
    set "XAMPP_ATTEMPTED=%CANDIDATE_DIR%"
) else (
    set "XAMPP_ATTEMPTED=%XAMPP_ATTEMPTED%; %CANDIDATE_DIR%"
)

if exist "%CANDIDATE_DIR%\mysql_start.bat" if exist "%CANDIDATE_DIR%\apache_start.bat" set "XAMPP_DIR=%CANDIDATE_DIR%"
exit /b 0

:ensureXamppRunner
set "RUNNER_NAME=%~1"
set "RUNNER_LABEL=%~2"

if not defined XAMPP_DIR call :resolveXamppDir
if not defined XAMPP_DIR (
    call :log "[ERROR] %RUNNER_LABEL% fallback requested but XAMPP directory was not found."
    if defined XAMPP_ATTEMPTED call :log "[ERROR] Checked XAMPP paths: %XAMPP_ATTEMPTED%"
    call :log "[ERROR] Set ISCHEDWISE_XAMPP_DIR to your XAMPP installation directory."
    exit /b 1
)

if not exist "%XAMPP_DIR%\%RUNNER_NAME%" (
    call :log "[ERROR] %RUNNER_LABEL% fallback launcher not found: %XAMPP_DIR%\%RUNNER_NAME%"
    exit /b 1
)

exit /b 0

:startCloudflared
tasklist /FI "IMAGENAME eq cloudflared.exe" 2>nul | find /I "cloudflared.exe" >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    call :log "[OK] cloudflared.exe already running. Skipping new launch."
    exit /b 0
)

set "CLOUDFLARED_CMD="
if defined CLOUDFLARED_EXE if exist "%CLOUDFLARED_EXE%" set "CLOUDFLARED_CMD=%CLOUDFLARED_EXE%"
if not defined CLOUDFLARED_CMD (
    for /f "delims=" %%I in ('where cloudflared 2^>nul') do (
        if not defined CLOUDFLARED_CMD set "CLOUDFLARED_CMD=%%I"
    )
)

if not defined CLOUDFLARED_CMD (
    call :log "[ERROR] cloudflared not found. Add it to PATH or set CLOUDFLARED_EXE."
    exit /b 1
)

if "%DRY_RUN%"=="1" (
    call :log "[DRY-RUN] Would run: %CLOUDFLARED_CMD% tunnel run topi_pc"
    exit /b 0
)

start "iSchedWise Cloudflared Tunnel" /min "%COMSPEC%" /k "\"%CLOUDFLARED_CMD%\" tunnel run topi_pc"
if errorlevel 1 (
    call :log "[ERROR] Failed to start cloudflared tunnel command window."
    exit /b 1
)

call :log "[OK] cloudflared tunnel command launched."
exit /b 0

:startXamppStack
set "MYSQL_SERVICE="
for %%S in (mysql MySQL mysql80 MySQL80 MySQL57 mysql57 MariaDB) do (
    sc query "%%S" >nul 2>&1
    if not errorlevel 1 if not defined MYSQL_SERVICE set "MYSQL_SERVICE=%%S"
)

if defined MYSQL_SERVICE (
    call :startService "%MYSQL_SERVICE%" "MySQL"
    if errorlevel 1 exit /b 1
) else (
    call :ensureXamppRunner "mysql_start.bat" "MySQL"
    if errorlevel 1 exit /b 1

    call :log "[INFO] MySQL service not registered; using %XAMPP_DIR%\mysql_start.bat launcher."
    if "%DRY_RUN%"=="1" (
        call :log "[DRY-RUN] Would run: %XAMPP_DIR%\mysql_start.bat"
    ) else (
        start "XAMPP MySQL" /min "%COMSPEC%" /c "\"%XAMPP_DIR%\mysql_start.bat\""
        if errorlevel 1 (
            call :log "[ERROR] MySQL fallback launcher failed from %XAMPP_DIR%\mysql_start.bat."
            exit /b 1
        )
        call :waitForPort "3306" "MySQL" "30"
        if errorlevel 1 exit /b 1
    )
)

set "APACHE_SERVICE="
for %%S in (Apache2.4 Apache2.2 Apache24 Apache2_4 ApacheHTTPServer) do (
    sc query "%%S" >nul 2>&1
    if not errorlevel 1 if not defined APACHE_SERVICE set "APACHE_SERVICE=%%S"
)

if defined APACHE_SERVICE (
    call :startService "%APACHE_SERVICE%" "Apache"
    if errorlevel 1 exit /b 1
) else (
    call :ensureXamppRunner "apache_start.bat" "Apache"
    if errorlevel 1 exit /b 1

    call :log "[INFO] Apache service not registered; using %XAMPP_DIR%\apache_start.bat launcher."
    if "%DRY_RUN%"=="1" (
        call :log "[DRY-RUN] Would run: %XAMPP_DIR%\apache_start.bat"
    ) else (
        start "XAMPP Apache" /min "%COMSPEC%" /c "\"%XAMPP_DIR%\apache_start.bat\""
        if errorlevel 1 (
            call :log "[ERROR] Apache fallback launcher failed from %XAMPP_DIR%\apache_start.bat."
            exit /b 1
        )
        call :waitForPort "80" "Apache" "20"
        if errorlevel 1 (
            call :log "[WARN] Apache port 80 was not detected. Continuing startup; verify Apache config if needed."
        )
    )
)

call :log "[OK] XAMPP stack startup complete."
exit /b 0

:startService
set "SERVICE_NAME=%~1"
set "SERVICE_LABEL=%~2"

sc query "%SERVICE_NAME%" | find /I "RUNNING" >nul 2>&1
if "%ERRORLEVEL%"=="0" (
    call :log "[OK] %SERVICE_LABEL% service (%SERVICE_NAME%) already running."
    exit /b 0
)

if "%DRY_RUN%"=="1" (
    call :log "[DRY-RUN] Would start %SERVICE_LABEL% service (%SERVICE_NAME%)."
    exit /b 0
)

call :log "[INFO] Starting %SERVICE_LABEL% service (%SERVICE_NAME%)..."
net start "%SERVICE_NAME%" >nul 2>&1
if not errorlevel 1 (
    if /I "%SERVICE_LABEL%"=="MySQL" (
        call :waitForPort "3306" "%SERVICE_LABEL%" "30"
        if errorlevel 1 exit /b 1
    )
    if /I "%SERVICE_LABEL%"=="Apache" (
        call :waitForPort "80" "%SERVICE_LABEL%" "20"
        if errorlevel 1 call :log "[WARN] Apache port 80 was not detected. Continuing startup; verify Apache config if needed."
    )
    call :log "[OK] %SERVICE_LABEL% service started."
    exit /b 0
)

sc start "%SERVICE_NAME%" >nul 2>&1
if errorlevel 1 (
    call :log "[ERROR] Could not start %SERVICE_LABEL% service (%SERVICE_NAME%)."
    exit /b 1
)

timeout /t 4 /nobreak >nul
sc query "%SERVICE_NAME%" | find /I "RUNNING" >nul 2>&1
if errorlevel 1 (
    call :log "[ERROR] %SERVICE_LABEL% service did not reach RUNNING state."
    exit /b 1
)

if /I "%SERVICE_LABEL%"=="MySQL" (
    call :waitForPort "3306" "%SERVICE_LABEL%" "30"
    if errorlevel 1 exit /b 1
)
if /I "%SERVICE_LABEL%"=="Apache" (
    call :waitForPort "80" "%SERVICE_LABEL%" "20"
    if errorlevel 1 call :log "[WARN] Apache port 80 was not detected. Continuing startup; verify Apache config if needed."
)

call :log "[OK] %SERVICE_LABEL% service started."
exit /b 0

:startISchedWise
call :isPortListening5000
if "%ERRORLEVEL%"=="0" (
    call :log "[OK] Port 5000 already listening; iSchedWise launch skipped."
    exit /b 0
)

set "PYTHON_CMD=%PROJECT_DIR%\venv\Scripts\python.exe"
if not exist "%PYTHON_CMD%" (
    set "PYTHON_CMD="
    for /f "delims=" %%I in ('where python 2^>nul') do (
        if not defined PYTHON_CMD set "PYTHON_CMD=%%I"
    )
)

if not defined PYTHON_CMD (
    call :log "[ERROR] Python executable not found (venv or PATH)."
    exit /b 1
)

if "%DRY_RUN%"=="1" (
    call :log "[DRY-RUN] Would run: %PYTHON_CMD% %PROJECT_DIR%\run.py"
    exit /b 0
)

start "iSchedWise App" /min /D "%PROJECT_DIR%" "%COMSPEC%" /k "\"%PYTHON_CMD%\" \"%PROJECT_DIR%\run.py\""
if errorlevel 1 (
    call :log "[ERROR] Failed to launch iSchedWise app command window."
    exit /b 1
)

call :waitForPort "5000" "iSchedWise" "30"
if errorlevel 1 (
    call :log "[ERROR] iSchedWise did not open port 5000 after launch. Check run.py output window."
    exit /b 1
)

call :log "[OK] iSchedWise launch command started."
exit /b 0

:waitForPort
set "WAIT_PORT=%~1"
set "WAIT_LABEL=%~2"
set "WAIT_SECONDS=%~3"

if not defined WAIT_PORT exit /b 1
if not defined WAIT_LABEL set "WAIT_LABEL=Service"
if not defined WAIT_SECONDS set "WAIT_SECONDS=30"

for /l %%I in (1,1,%WAIT_SECONDS%) do (
    call :isPortListening "%WAIT_PORT%"
    if not errorlevel 1 (
        call :log "[OK] %WAIT_LABEL% is listening on port %WAIT_PORT%."
        exit /b 0
    )
    if "%%I"=="1" call :log "[INFO] Waiting for %WAIT_LABEL% to listen on port %WAIT_PORT%..."
    timeout /t 1 /nobreak >nul
)

call :log "[ERROR] %WAIT_LABEL% did not listen on port %WAIT_PORT% within %WAIT_SECONDS% seconds."
exit /b 1

:isPortListening
set "PORT_TO_CHECK=%~1"
if not defined PORT_TO_CHECK exit /b 1
netstat -ano -p tcp | findstr /R /I /C:":%PORT_TO_CHECK% .*LISTENING" >nul 2>&1
exit /b %ERRORLEVEL%

:isPortListening5000
call :isPortListening "5000"
exit /b %ERRORLEVEL%

:fail
set "EXIT_CODE=1"
call :log "[FAIL] Startup sequence failed."
goto :final

:final
set "FINAL_EXIT=%EXIT_CODE%"
endlocal & exit /b %FINAL_EXIT%
