# 14. Automation with Batch Files

Manually starting jmeter-server on each worker, copying files, and running the test gets repetitive fast - especially when you have multiple machines and run tests frequently. Batch files automate these steps.

## Table of Contents
- [Why Automate](#why-automate)
- [Automating Test Execution](#automating-test-execution)
- [Automating Test Data Distribution](#automating-test-data-distribution)
- [Automating Worker Setup](#automating-worker-setup)
- [Combining Everything](#combining-everything)
- [Tips](#tips)

---

## Why Automate

| Manual Step | Time per Run | With Automation |
|-------------|-------------|-----------------|
| Copy CSV files to 5 workers | 5-10 minutes | 30 seconds |
| Start jmeter-server on each worker | 5 minutes | 30 seconds |
| Run the test with correct flags | 1-2 minutes | 10 seconds |
| Organize results with timestamps | 1-2 minutes | Automatic |

For a distributed test with 5 workers, manual setup takes 15+ minutes. A batch script does it in under a minute.

---

## Automating Test Execution

### Basic Run Script

```bat
@echo off
REM run-test.bat - Run a JMeter test in CLI mode

SET JMETER_HOME=C:\apache-jmeter-5.6.3
SET TEST_PLAN=scripts\login-flow.jmx
SET TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%
SET TIMESTAMP=%TIMESTAMP: =0%
SET RESULTS_DIR=results\%TIMESTAMP%

mkdir "%RESULTS_DIR%"

echo Running test: %TEST_PLAN%
echo Results will be saved to: %RESULTS_DIR%

%JMETER_HOME%\bin\jmeter -n -t %TEST_PLAN% -l "%RESULTS_DIR%\results.jtl" -e -o "%RESULTS_DIR%\report"

echo.
echo Test complete. Report: %RESULTS_DIR%\report\index.html
pause
```

This creates a timestamped results folder for each run so you never overwrite previous results.

### Run Script with Parameters

```bat
@echo off
REM run-test-params.bat - Run with configurable thread count and duration
REM Usage: run-test-params.bat [threads] [duration_seconds] [rampup_seconds]

SET JMETER_HOME=C:\apache-jmeter-5.6.3
SET TEST_PLAN=scripts\login-flow.jmx
SET THREADS=%~1
SET DURATION=%~2
SET RAMPUP=%~3

IF "%THREADS%"=="" SET THREADS=10
IF "%DURATION%"=="" SET DURATION=600
IF "%RAMPUP%"=="" SET RAMPUP=60

SET TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%
SET TIMESTAMP=%TIMESTAMP: =0%
SET RESULTS_DIR=results\%TIMESTAMP%_%THREADS%users

mkdir "%RESULTS_DIR%"

echo Running: %THREADS% users, %DURATION%s duration, %RAMPUP%s ramp-up
echo Results: %RESULTS_DIR%

%JMETER_HOME%\bin\jmeter -n -t %TEST_PLAN% ^
  -Jthreads=%THREADS% ^
  -Jduration=%DURATION% ^
  -Jrampup=%RAMPUP% ^
  -l "%RESULTS_DIR%\results.jtl" ^
  -e -o "%RESULTS_DIR%\report"

echo.
echo Test complete. Report: %RESULTS_DIR%\report\index.html
pause
```

**Usage:**

```bat
run-test-params.bat 300 1800 300
```

This runs 300 users for 30 minutes with a 5-minute ramp-up. Requires your `.jmx` to use `${__P(threads,10)}`, `${__P(duration,600)}`, and `${__P(rampup,60)}` in the Thread Group.

---

## Automating Test Data Distribution

### Copy CSV Files to Workers

```bat
@echo off
REM distribute-data.bat - Copy split CSV files to worker machines
REM Assumes testdata/split/worker1/, worker2/, etc. exist (from Python split script)

SET DATA_DIR=testdata\split
SET REMOTE_PATH=C$\jmeter-test\testdata

SET WORKER1=192.168.1.101
SET WORKER2=192.168.1.102
SET WORKER3=192.168.1.103

echo Distributing test data to workers...

echo Copying to Worker 1 (%WORKER1%)...
xcopy /Y /Q "%DATA_DIR%\worker1\*" "\\%WORKER1%\%REMOTE_PATH%\"

echo Copying to Worker 2 (%WORKER2%)...
xcopy /Y /Q "%DATA_DIR%\worker2\*" "\\%WORKER2%\%REMOTE_PATH%\"

echo Copying to Worker 3 (%WORKER3%)...
xcopy /Y /Q "%DATA_DIR%\worker3\*" "\\%WORKER3%\%REMOTE_PATH%\"

echo.
echo Data distribution complete.
pause
```

> **Note:** This uses Windows file sharing (UNC paths). Workers need shared folders or admin shares (`C$`) accessible from the controller machine.

---

## Automating Worker Setup

### Start jmeter-server on All Workers

```bat
@echo off
REM start-workers.bat - Start jmeter-server on all remote machines
REM Requires PsExec or similar remote execution tool

SET JMETER_HOME=C:\apache-jmeter-5.6.3

SET WORKER1=192.168.1.101
SET WORKER2=192.168.1.102
SET WORKER3=192.168.1.103

echo Starting jmeter-server on workers...

echo Starting Worker 1 (%WORKER1%)...
psexec \\%WORKER1% -d %JMETER_HOME%\bin\jmeter-server.bat

echo Starting Worker 2 (%WORKER2%)...
psexec \\%WORKER2% -d %JMETER_HOME%\bin\jmeter-server.bat

echo Starting Worker 3 (%WORKER3%)...
psexec \\%WORKER3% -d %JMETER_HOME%\bin\jmeter-server.bat

echo.
echo All workers started. Waiting 10 seconds for initialization...
timeout /t 10

echo Workers ready.
pause
```

> **Note:** `PsExec` is a Sysinternals tool for remote command execution on Windows. Alternatively, you can use SSH, PowerShell remoting, or have workers run jmeter-server as a Windows service.

### Stop jmeter-server on All Workers

```bat
@echo off
REM stop-workers.bat - Stop jmeter-server on all remote machines

SET WORKER1=192.168.1.101
SET WORKER2=192.168.1.102
SET WORKER3=192.168.1.103

echo Stopping jmeter-server on workers...

psexec \\%WORKER1% taskkill /F /IM java.exe
psexec \\%WORKER2% taskkill /F /IM java.exe
psexec \\%WORKER3% taskkill /F /IM java.exe

echo.
echo All workers stopped.
pause
```

---

## Combining Everything

### Full Distributed Test Script

```bat
@echo off
REM run-distributed.bat - Complete distributed test automation
REM 1. Distribute data  2. Start workers  3. Run test  4. Stop workers

SET JMETER_HOME=C:\apache-jmeter-5.6.3
SET TEST_PLAN=scripts\login-flow.jmx
SET THREADS=100
SET DURATION=1800
SET RAMPUP=300

SET WORKER1=192.168.1.101
SET WORKER2=192.168.1.102
SET WORKER3=192.168.1.103
SET WORKERS=%WORKER1%:1099,%WORKER2%:1099,%WORKER3%:1099

SET TIMESTAMP=%date:~-4%%date:~4,2%%date:~7,2%_%time:~0,2%%time:~3,2%
SET TIMESTAMP=%TIMESTAMP: =0%
SET RESULTS_DIR=results\%TIMESTAMP%_distributed

echo ============================================
echo  Distributed Test - %THREADS% users x 3 workers
echo ============================================

REM Step 1: Distribute test data
echo.
echo [Step 1/4] Distributing test data...
call distribute-data.bat

REM Step 2: Start workers
echo.
echo [Step 2/4] Starting workers...
call start-workers.bat

REM Step 3: Run the test
echo.
echo [Step 3/4] Running test...
mkdir "%RESULTS_DIR%"

%JMETER_HOME%\bin\jmeter -n -t %TEST_PLAN% ^
  -Jthreads=%THREADS% ^
  -Jduration=%DURATION% ^
  -Jrampup=%RAMPUP% ^
  -l "%RESULTS_DIR%\results.jtl" ^
  -e -o "%RESULTS_DIR%\report" ^
  -R %WORKERS%

REM Step 4: Stop workers
echo.
echo [Step 4/4] Stopping workers...
call stop-workers.bat

echo.
echo ============================================
echo  Test complete!
echo  Total users: %THREADS% x 3 = 300
echo  Report: %RESULTS_DIR%\report\index.html
echo ============================================
pause
```

---

## Tips

- **Test your batch scripts with small runs first** - run with 1-2 threads and a short duration to validate the automation before committing to a full load test
- **Use properties in your `.jmx`** - parameterize threads, duration, and ramp-up with `${__P()}` so batch scripts can control the load model without editing the test plan
- **Add error handling** - check if file copy succeeded, if workers are reachable, if the results folder was created. Basic `IF ERRORLEVEL` checks go a long way
- **Keep scripts in the `scripts/` folder** - version control your batch files alongside the test plans
- **Adapt paths for your environment** - the examples use hardcoded IPs and paths. Update them for your actual infrastructure
- **Consider PowerShell** - for more complex automation (parallel remote execution, better error handling), PowerShell scripts may be more maintainable than batch files
