@echo off
REM Create folder on all slave VMs

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Create Folder on Slave VMs
echo ========================================
echo.

python utils\create_folder_on_slaves.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Folder created on slave VMs!
) else (
    echo.
    echo [ERROR] Failed to create folder on slave VMs
    exit /b %ERRORLEVEL%
)

pause
