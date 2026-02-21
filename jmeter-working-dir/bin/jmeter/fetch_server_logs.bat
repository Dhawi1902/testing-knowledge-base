@echo off
REM Fetch jmeter-server.log from all slave VMs
REM Usage: fetch_server_logs.bat

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

echo ========================================
echo  Fetch JMeter Server Logs from Slaves
echo ========================================
echo.

python utils\fetch_server_logs.py %*

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] All logs fetched!
) else (
    echo.
    echo [WARNING] Some logs could not be fetched
)

pause
