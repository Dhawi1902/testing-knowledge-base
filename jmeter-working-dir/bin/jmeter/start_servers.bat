@echo off
REM Start JMeter servers on all slave VMs

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

echo ========================================
echo  Start JMeter Servers
echo ========================================
echo.

python utils\manage_jmeter_servers.py start

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] JMeter servers started!
) else (
    echo.
    echo [ERROR] Failed to start JMeter servers
    exit /b %ERRORLEVEL%
)

pause
