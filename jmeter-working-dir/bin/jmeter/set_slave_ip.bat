@echo off
REM Update SLAVE_IP in start-slave.sh on each slave VM to its own private IP

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

echo ========================================
echo  Set SLAVE_IP on Slave VMs
echo ========================================
echo.

python utils\set_slave_ip.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] SLAVE_IP updated on all VMs!
) else (
    echo.
    echo [ERROR] Failed to update SLAVE_IP
    exit /b %ERRORLEVEL%
)

pause
