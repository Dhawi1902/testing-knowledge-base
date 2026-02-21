@echo off
setlocal enabledelayedexpansion

REM Usage: run_distributed.bat <jmx_file>
REM Example: run_distributed.bat script/jmeter/MAYA-Student.jmx

REM Get the repository root (2 levels up from bin\jmeter\)
cd /d "%~dp0..\.."

SET JMX_FILE=%1
SET SLAVE_LIST=
SET SLAVE_COUNT=0

REM Check if JMX file is provided
IF "%JMX_FILE%"=="" (
    ECHO Error: Please provide a JMX file
    ECHO Usage: run_distributed.bat ^<jmx_file^>
    ECHO Example: run_distributed.bat script/jmeter/MAYA-Student.jmx
    pause
    exit /b 1
)

REM Read slaves.txt and build comma-separated list
FOR /F "eol=# tokens=*" %%A IN (slaves.txt) DO (
    IF "!SLAVE_LIST!"=="" (
        SET SLAVE_LIST=%%A
    ) ELSE (
        SET SLAVE_LIST=!SLAVE_LIST!,%%A
    )
    SET /A SLAVE_COUNT+=1
)

REM Generate timestamp for results
FOR /F "tokens=2-4 delims=/ " %%a IN ('date /t') CALL :SET_DATE %%a %%b %%c
FOR /F "tokens=1-2 delims=: " %%a IN ('time /t') SET TIME_STAMP=%%a%%b
SET TIMESTAMP=%DATE_STAMP%_%TIME_STAMP%

ECHO ========================================
ECHO Distributed JMeter Test
ECHO ========================================
ECHO Test Plan: %JMX_FILE%
ECHO Slaves: %SLAVE_COUNT% (%SLAVE_LIST%)
ECHO ========================================
ECHO.

REM Run JMeter in distributed mode
REM Backend listener runs only on master, not on slaves
jmeter -n -t %JMX_FILE% -R%SLAVE_LIST% -l results/distributed_%TIMESTAMP%.jtl -e -o results/html_%TIMESTAMP%/ -Jmode.gui=false -Jremote_hosts=%SLAVE_LIST%

ECHO.
ECHO ========================================
ECHO Test completed
ECHO Results: results/html_%TIMESTAMP%/
ECHO ========================================

pause
GOTO :EOF

:SET_DATE
SET DATE_STAMP=%3%2%1
GOTO :EOF
