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

REM Read properties file (includes results_dir, test_plan, etc.)
for /f "usebackq tokens=1,* delims==" %%A in ("%PROPS_FILE%") do (
    if not "%%A"=="" (
        if not "%%A:~0,1%"=="#" (
            set "%%A=%%B"
        )
    )
)

REM Default results_dir if not set in config.properties
if "!results_dir!"=="" set "results_dir=results/jmeter-report"

REM Read slaves.txt and build comma-separated list
FOR /F "eol=# tokens=*" %%A IN (slaves.txt) DO (
    IF "!SLAVE_LIST!"=="" (
        SET SLAVE_LIST=%%A
    ) ELSE (
        SET SLAVE_LIST=!SLAVE_LIST!,%%A
    )
    SET /A SLAVE_COUNT+=1
)


REM ===============================
REM 1. Get today date (YYYYMMDD)
REM ===============================
set TODAY=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%

REM ===============================
REM 2. Auto-increment run counter
REM ===============================
set COUNT=1
:loop
if exist "%CD%\!results_dir!\%TODAY%\%TODAY%_%COUNT%" (
    set /a COUNT+=1
    goto loop
)

REM ===============================
REM 3. Set paths and create folder
REM ===============================
set RESULT_FOLDER=%CD%\!results_dir!\%TODAY%\%TODAY%_%COUNT%
set TEST_NAME=STUDENT_ENROLMENT_%student%_Student_Testing_%TODAY%_%COUNT%

REM Create the result folder
mkdir "%RESULT_FOLDER%"

echo =========================================
echo Running JMeter Test
echo Test Plan : %test_plan%
echo Test Name : %TEST_NAME%
echo Slaves    : %SLAVE_COUNT%
echo Date      : %TODAY%
echo Run No    : %COUNT%
echo Run ID    : %runId%
echo Folder    : %TODAY%_%COUNT%
echo Results   : !results_dir!
echo hosts     : %SLAVE_LIST%
echo =========================================

@REM REM ===============================
@REM REM 4. Run JMeter (batch-only)
@REM REM ===============================
@REM jmeter -n ^
@REM  -t "%CD%/%test_plan%" ^
@REM  -l "%RESULT_FOLDER%/results.jtl" ^
@REM  -e -o "%RESULT_FOLDER%/report" ^
@REM  -R%SLAVE_LIST% ^
@REM  -GrunId=%runId% ^
@REM  -Gstudent=%student% ^
@REM  -GrampUp=%rampUp% ^
@REM  -Gstudent_data=%student_data% ^
@REM  -Jjmeter.save.saveservice.output_format=csv

echo.
echo Test completed successfully.
echo Folder  : %RESULT_FOLDER%
echo Results : %RESULT_FOLDER%/results.jtl
echo Report  : %RESULT_FOLDER%/report
echo.
pause
