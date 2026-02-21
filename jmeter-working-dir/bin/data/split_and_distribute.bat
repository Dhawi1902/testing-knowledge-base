@echo off
REM Split student data and distribute to VMs via SSH
REM Usage: split_and_distribute.bat [offset] [size]
REM Example: split_and_distribute.bat 0 1000

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Split and Distribute Student Data
echo ========================================
echo.

if "%1"=="" (
    echo Using default offset and size from config...
    python utils\split_and_copy_to_vms.py
) else if "%2"=="" (
    echo Usage: split_and_distribute.bat [offset] [size]
    echo Example: split_and_distribute.bat 0 1000
    exit /b 1
) else (
    echo Using offset=%1, size=%2
    python utils\split_and_copy_to_vms.py --offset %1 --size %2
)

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Data distributed successfully!
) else (
    echo.
    echo [ERROR] Failed to distribute data
    exit /b %ERRORLEVEL%
)

pause
