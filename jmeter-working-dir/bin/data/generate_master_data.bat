@echo off
REM Generate master student data from JSON configuration
REM This script can be run from anywhere

REM Get the repository root (2 levels up from bin\data\)
cd /d "%~dp0..\.."

echo ========================================
echo  Generate Master Student Data
echo ========================================
echo.

python utils\generate_master_data.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo [SUCCESS] Master data generated successfully!
) else (
    echo.
    echo [ERROR] Failed to generate master data
    exit /b %ERRORLEVEL%
)

pause
