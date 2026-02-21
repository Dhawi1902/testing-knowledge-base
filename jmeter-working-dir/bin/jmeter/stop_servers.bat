@echo off
REM Stop JMeter servers on all slave VMs

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

echo ========================================
echo  Stop JMeter Servers
echo ========================================
echo.

python utils\manage_jmeter_servers.py stop

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] JMeter servers stopped!
) else (
    echo.
    echo [ERROR] Failed to stop JMeter servers
    exit /b %ERRORLEVEL%
)

pause
