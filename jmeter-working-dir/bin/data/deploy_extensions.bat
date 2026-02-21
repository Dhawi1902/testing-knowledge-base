@echo off
REM Deploy JMeter extensions to all slave VMs
REM Place JAR files in extensions/ folder before running

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Deploy JMeter Extensions to Slaves
echo ========================================
echo.

python utils\deploy_extensions.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Extensions deployed!
) else (
    echo.
    echo [ERROR] Deployment failed
    exit /b %ERRORLEVEL%
)

pause
