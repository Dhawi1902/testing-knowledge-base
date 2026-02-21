@echo off

REM ===============================
REM 0. Read properties file
REM ===============================
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

REM ===============================
REM Calculate per-slave threads from total
REM student = total threads, student_per_slave = threads per slave
REM ===============================
SET /A STUDENT_PER_SLAVE=%student% / %SLAVE_COUNT%

REM ===============================
REM 1. Get today date (YYYYMMDD)
REM ===============================
set TODAY=%DATE:~-4%%DATE:~4,2%%DATE:~7,2%

REM ===============================
REM 2. Auto-increment run counter
REM ===============================
set COUNT=1
:loop
if exist "%CD%\results\%TODAY%_%COUNT%" (
    set /a COUNT+=1
    goto loop
)

REM ===============================
REM 3. Set paths and create folder
REM ===============================
set RESULT_FOLDER=%CD%\results\%TODAY%_%COUNT%
set TEST_NAME=STUDENT_ENROLMENT_%student%_Student_Testing_%TODAY%_%COUNT%

REM Create the result folder
mkdir "%RESULT_FOLDER%"	

echo =========================================
echo Running JMeter Test
echo Test Plan : %test_plan%
echo Test Name : %TEST_NAME%
echo Total     : %student% students
echo Per Slave : %STUDENT_PER_SLAVE% students
echo Slaves    : %SLAVE_COUNT%
echo Ramp Up   : %rampUp% seconds
echo Think Time: %thinkTime% ms
echo Date      : %TODAY%
echo Run No    : %COUNT%
echo Run ID    : %runId%
echo Folder    : %TODAY%_%COUNT%
echo logout    : %logout%
echo -----------------------------------------
echo Dynatrace Integration
echo TSN       : %dynatrace.tsn%
echo LSN       : %dynatrace.lsn%
echo =========================================

REM ===============================
REM 4. Run JMeter (batch-only, no inline report)
REM ===============================
jmeter -n ^
 -t "%CD%\%test_plan%" ^
 -l "%RESULT_FOLDER%\results.jtl" ^
 -R%SLAVE_LIST% ^
 -GrunId=%runId% ^
 -Gbucket=%bucket% ^
 -Gstudent=%STUDENT_PER_SLAVE% ^
 -GrampUp=%rampUp% ^
 -Gloop=%loop% ^
 -GthinkTime=%thinkTime% ^
 -Gstudent_data=%student_data% ^
 -Glogout=%logout% ^
 -Gsmoke=%smoke% ^
 -Gdynatrace.tsn=%dynatrace.tsn% ^
 -Gdynatrace.lsn=%dynatrace.lsn% ^
 -Ghttpsampler.ignore_failed_embedded_resources=true ^
 -Jjmeter.save.saveservice.output_format=csv

REM ===============================
REM 5. Generate report
REM ===============================
echo.
if /I "%filter_usernames%"=="true" (
    echo Filtering username labels and generating report...
    python "%CD%\utils\filter_jtl.py" "%RESULT_FOLDER%"
    echo.
    echo Test completed successfully.
    echo Folder   : results\%TODAY%_%COUNT%
    echo Original : results\%TODAY%_%COUNT%\results.jtl ^(full audit trail^)
    echo Filtered : results\%TODAY%_%COUNT%\results_filtered.jtl
    echo Report   : results\%TODAY%_%COUNT%\report
) else (
    echo Generating report directly...
    jmeter -g "%RESULT_FOLDER%\results.jtl" -o "%RESULT_FOLDER%\report"
    echo.
    echo Test completed successfully.
    echo Folder  : results\%TODAY%_%COUNT%
    echo Results : results\%TODAY%_%COUNT%\results.jtl
    echo Report  : results\%TODAY%_%COUNT%\report
)
echo.
pause