# 9. Execute and Analyze Results

The script is debugged, the load model is defined - now it's time to run the actual load test and make sense of the results. Always run load tests in **CLI mode** (command line), never from the GUI.

## Table of Contents
- [Why CLI Mode](#why-cli-mode)
- [CLI Command](#cli-command)
- [Key Metrics](#key-metrics)
- [JMeter Web Report](#jmeter-web-report)
- [Reading the Results](#reading-the-results)
- [Identifying Bottlenecks](#identifying-bottlenecks)
- [Tips](#tips)

---

## Why CLI Mode

The JMeter GUI is for **building and debugging** scripts only. For actual load tests:

| Mode | Purpose |
|------|---------|
| **GUI** | Script development, debugging with 1-3 threads |
| **CLI** | Running load tests with real thread counts |

**Why not GUI for load tests?**
- GUI rendering (View Results Tree, graphs) consumes significant CPU and memory
- This overhead distorts the results - response times appear higher than they actually are
- The JMeter process can run out of memory and crash mid-test
- CLI mode uses minimal resources, giving you accurate results

---

## CLI Command

### Basic Command

```bat
jmeter -n -t test-plan.jmx -l results.jtl -e -o report-folder
```

| Flag | What it Does |
|------|--------------|
| `-n` | Non-GUI (CLI) mode |
| `-t` | Path to the `.jmx` test plan |
| `-l` | Path to write the results file (`.jtl` or `.csv`) |
| `-e` | Generate HTML report after the test |
| `-o` | Output folder for the HTML report (must not exist or be empty) |

### Example

```bat
jmeter -n -t scripts/login-flow.jmx -l results/login-test-run1.jtl -e -o results/report-run1
```

### Useful Additional Flags

| Flag | What it Does |
|------|--------------|
| `-Jthreads=100` | Override a JMeter property (if your script uses `${__P(threads,10)}`) |
| `-Jduration=1800` | Override test duration via property |
| `-Jrampup=300` | Override ramp-up via property |

Using properties (`${__P(threads,10)}`) in your Thread Group instead of hardcoded values lets you change the load model from the command line without editing the `.jmx` file. The second value (e.g., `10`) is the default if no property is passed.

<!-- TODO: Screenshot - CLI execution output showing test progress -->

### What You See During Execution

While the test runs, JMeter prints a summary line every 30 seconds:

```
summary +   1250 in 00:00:30 =   41.7/s Avg:   245 Min:    12 Max:  1823 Err:     0 (0.00%) Active: 100
summary =   5000 in 00:02:00 =   41.7/s Avg:   240 Min:    12 Max:  2105 Err:     3 (0.06%) Active: 200
```

| Field | Meaning |
|-------|---------|
| `+` line | Stats for the last 30-second interval |
| `=` line | Cumulative stats since the start |
| `41.7/s` | Throughput (requests per second) |
| `Avg: 245` | Average response time (ms) |
| `Min / Max` | Minimum and maximum response time (ms) |
| `Err: 0 (0.00%)` | Error count and percentage |
| `Active: 100` | Currently active threads |

This gives you a live view of how the test is progressing. Watch for errors climbing or response times spiking.

---

## Key Metrics

These are the metrics that matter when analyzing results:

### Response Time

| Metric | What it Tells You |
|--------|-------------------|
| **Average** | Overall average response time - can be misleading if there are outliers |
| **Median (50th percentile)** | Half the requests were faster than this |
| **90th Percentile** | 90% of requests were faster than this - the most commonly reported metric |
| **95th / 99th Percentile** | Used for stricter SLAs |
| **Min / Max** | The fastest and slowest individual requests |

> **Important:** Always report percentiles, not just averages. An average of 500ms could mean all requests took ~500ms, or it could mean 99% took 200ms and 1% took 30 seconds. The percentile tells the real story.

### Throughput

Requests per second (or transactions per second if using Transaction Controllers). This tells you how much work the system is processing.

- Throughput should stabilize during steady state
- If throughput drops while users are constant, the server is struggling
- Compare actual throughput against the NFR target

### Error Rate

The percentage of requests that failed. Failures include:
- HTTP 4xx/5xx responses
- Connection errors / timeouts
- Assertion failures (if assertions are in the script)

The NFR typically defines the acceptable error rate (e.g., < 1%).

---

## JMeter Web Report

The `-e -o` flags generate an HTML report automatically. Open `index.html` in the output folder.

### Report Sections

**Dashboard:**
- Summary statistics (total requests, error %, throughput)
- APDEX (Application Performance Index) score
- Response time over time graph

**Charts:**
- Response Times Over Time - shows how response times change during the test
- Active Threads Over Time - confirms the ramp-up profile
- Transactions Per Second - throughput over time
- Response Time Percentiles - distribution of response times
- Response Time vs Threads - how response time changes as load increases

**Tables:**
- Statistics table - per-sampler breakdown with averages, percentiles, throughput, and error rates
- Errors table - breakdown of error types and which samplers they occurred on

<!-- TODO: Screenshot - JMeter web report dashboard -->
<!-- TODO: Screenshot - JMeter web report Response Times Over Time chart -->
<!-- TODO: Screenshot - JMeter web report statistics table -->

### How Transaction Controllers Appear in the Report

If you used Transaction Controllers with **"Generate parent sample"** checked (see [Section 6](06-script-enhancement.md)):
- The report shows the Transaction Controller name (e.g., `A - Login`) as a single entry
- The total time includes all child requests
- Individual child requests are not shown separately in the statistics table

This is why naming conventions matter - `A - Login`, `B - Dashboard` appear sorted and readable in the report.

---

## Reading the Results

### The Results File (.jtl)

The `.jtl` file contains raw test data - one line per request. You can open it in JMeter's GUI listeners (Aggregate Report, Summary Report) for quick analysis, or use it to regenerate the HTML report.

**To open in JMeter GUI:**
1. Open JMeter (GUI mode)
2. Add a listener (e.g., Aggregate Report, Summary Report)
3. Click **Browse** and select the `.jtl` file

**To regenerate the HTML report from a `.jtl` file:**

```bat
jmeter -g results.jtl -o report-folder
```

### Aggregate Report Columns

| Column | Meaning |
|--------|---------|
| **Label** | Sampler / Transaction Controller name |
| **# Samples** | Total number of requests |
| **Average** | Average response time (ms) |
| **Median** | 50th percentile response time |
| **90% Line** | 90th percentile response time |
| **95% Line** | 95th percentile response time |
| **99% Line** | 99th percentile response time |
| **Min** | Fastest response |
| **Max** | Slowest response |
| **Error %** | Percentage of failed requests |
| **Throughput** | Requests per second |

---

## Identifying Bottlenecks

### High Response Times

- **All requests are slow** → likely a server-side issue (CPU, memory, database)
- **Specific requests are slow** → focus on those endpoints. Could be a slow database query, external service call, or inefficient code
- **Response times increase over time** → possible memory leak, connection pool exhaustion, or growing queue

### High Error Rate

- **Errors from the start** → script issue or environment problem (wrong URL, expired credentials)
- **Errors appear under load** → server capacity issue (connection limits, thread pool exhaustion, timeouts)
- **Specific error codes:**
  - `500` - server error, check server logs
  - `502/503` - server overloaded or down
  - `429` - rate limited
  - `Connection reset / timeout` - server can't accept more connections

### Throughput Plateau

- Throughput stops increasing even though more users are being added
- This means the server has reached its maximum capacity
- Look at response times at this point - they'll be climbing

### Response Time vs Threads

The web report includes a "Response Time vs Threads" chart. The ideal pattern:
- Response time stays flat as threads increase → server handles the load well
- Response time starts climbing at a certain thread count → that's the capacity threshold

---

## Tips

- **Never run load tests from GUI mode** - even for "quick" tests. Use CLI from the start
- **Delete or empty the report folder** before each run - JMeter won't overwrite an existing report folder
- **Name your result files** with the run number or timestamp (e.g., `results-run1.jtl`, `results-20260212.jtl`) so you don't lose previous results
- **Watch the CLI output during the test** - if errors spike or response times explode early, you may want to stop and investigate before wasting time on a full run
- **Run multiple iterations** - one run is not enough. Run at least 2-3 times to confirm results are consistent
- **Compare against NFRs immediately** - check the 90th percentile response time, throughput, and error rate against the targets from [Section 2](02-understand-requirements.md)
