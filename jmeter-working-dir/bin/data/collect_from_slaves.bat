@echo off
REM Collect parent folder from all slave VMs to local machine

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Collect Folder from Slave VMs
echo ========================================
echo.

python utils\collect_from_slaves.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Files collected from slave VMs!
) else (
    echo.
    echo [ERROR] Failed to collect files from slave VMs
    exit /b %ERRORLEVEL%
)

pause
