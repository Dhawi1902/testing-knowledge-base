@echo off
setlocal enabledelayedexpansion

REM ============================================================
REM  Distribute split test data CSVs to JMeter slave machines
REM  Requires: pscp (PuTTY) - download from putty.org
REM  Usage: distribute_test_data.bat [slaves_file]
REM ============================================================

set "REPO_ROOT=%~dp0.."
set "SLAVES_FILE=%REPO_ROOT%\slaves.txt"
set "DATA_DIR=%REPO_ROOT%\data\test_data"
set "REMOTE_DIR=/home/opc/jmeter-PT/linux/test_data"
set "SSH_USER=root"
set "CSV_FILENAME=student_data.csv"

REM Allow override of slaves file via argument
if not "%~1"=="" set "SLAVES_FILE=%~1"

REM Prompt for password once
set /p "SSH_PASS=Enter SSH password for %SSH_USER%: "

if not exist "%SLAVES_FILE%" (
    echo ERROR: Slaves file not found: %SLAVES_FILE%
    exit /b 1
)

if not exist "%DATA_DIR%" (
    echo ERROR: Test data directory not found: %DATA_DIR%
    echo Run split_test_data.py first to generate the split files.
    exit /b 1
)

echo ============================================================
echo  Distributing test data to JMeter slaves
echo  Source:  %DATA_DIR%
echo  Remote:  %SSH_USER%@slave:%REMOTE_DIR%/%CSV_FILENAME%
echo ============================================================
echo.

set SUCCESS=0
set FAIL=0

for /f "usebackq eol=# tokens=*" %%S in ("%SLAVES_FILE%") do (
    set "SLAVE=%%S"
    REM Trim whitespace
    for /f "tokens=* delims= " %%A in ("!SLAVE!") do set "SLAVE=%%A"

    if not "!SLAVE!"=="" (
        set "LOCAL_FILE=%DATA_DIR%\!SLAVE!\%CSV_FILENAME%"

        if exist "!LOCAL_FILE!" (
            echo [*] Transferring to !SLAVE! ...
            pscp -pw !SSH_PASS! "!LOCAL_FILE!" %SSH_USER%@!SLAVE!:%REMOTE_DIR%/%CSV_FILENAME%
            if !errorlevel! equ 0 (
                echo [OK] !SLAVE! - transfer complete
                set /a SUCCESS+=1
            ) else (
                echo [FAIL] !SLAVE! - transfer failed
                set /a FAIL+=1
            )
        ) else (
            echo [SKIP] !SLAVE! - no data file found at !LOCAL_FILE!
            set /a FAIL+=1
        )
        echo.
    )
)

echo ============================================================
echo  Done: %SUCCESS% succeeded, %FAIL% failed
echo ============================================================

endlocal
