@echo off

REM ===============================
REM 0. Navigate to repo root and read properties file
REM ===============================
REM Get the repository root (2 levels up from bin\test\)
cd /d "%~dp0..\.."

setlocal enabledelayedexpansion
SET SLAVE_COUNT=0
SET SLAVE_LIST=
SET PROPS_FILE=%CD%\config.properties
SET SLAVES=%CD%\slaves.txt

if not exist "%PROPS_FILE%" (
    echo ERROR: config.properties not found in %CD%
    pause
    exit /b 1
)

if not exist "%SLAVES%" (
    echo ERROR: slaves.txt not found in %CD%
    pause
    exit /b 1
)

REM Read properties file
for /f "usebackq tokens=1,* delims==" %%A in ("%PROPS_FILE%") do (
    if not "%%A"=="" (
        if not "%%A:~0,1%"=="#" (
            set "%%A=%%B"
        )
    )
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

REM Run JMeter test
jmeter -n -t %test_plan% -l result/result.jtl -e -o result/report -Glogout=%logout% -Jjmeter.save.saveservice.output_format=csv

pause
