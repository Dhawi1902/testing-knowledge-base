@echo off
REM Remove all files inside parent folder on all slave VMs (keeps directories)

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Clear Files on Slave VMs
echo ========================================
echo.

python utils\clear_files_on_slaves.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Files cleared on slave VMs!
) else (
    echo.
    echo [ERROR] Failed to clear files on slave VMs
    exit /b %ERRORLEVEL%
)

pause
