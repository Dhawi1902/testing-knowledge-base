@echo off
REM Check status of JMeter servers on all slave VMs

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

echo ========================================
echo  JMeter Servers Status
echo ========================================
echo.

python utils\manage_jmeter_servers.py status

pause
