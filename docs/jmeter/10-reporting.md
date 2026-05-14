# 10. Reporting

You have the results - now you need to communicate them. The report should be clear enough for both technical and non-technical stakeholders to understand whether the system passed or failed.


## Key Metrics to Highlight

Not every metric from the test results belongs in the report. Focus on what stakeholders care about:

| Metric | Why it Matters |
|--------|---------------|
| **90th Percentile Response Time** | The most commonly used SLA metric - "90% of users experienced this or better" |
| **Average Response Time** | Easy to understand, but always pair with percentiles |
| **Throughput (TPS)** | Shows system capacity - how much work it processed |
| **Error Rate** | Did the system stay within acceptable failure limits? |
| **Concurrent Users** | The load level during the test |
| **Test Duration** | How long the steady state lasted |

---

## Report Structure

A practical performance test report structure:

### 1. Summary / Executive Overview
- One paragraph: what was tested, how much load, and the overall result (pass/fail)
- Example: *"Login and checkout flows were tested with 300 concurrent users for 30 minutes. The system met all NFR targets with a 90th percentile response time of 1.2 seconds and 0.3% error rate."*

### 2. Test Scope
- Which flows were tested
- Which environment (URL, infra details if relevant)
- Test date and time

### 3. Load Model
- Number of concurrent users
- Ramp-up period
- Test duration
- Think time between actions

### 4. NFR Targets vs Actual Results

This is the core of the report. Present it as a comparison table:

| Metric | NFR Target | Actual Result | Status |
|--------|-----------|---------------|--------|
| 90th Percentile Response Time | < 2 sec | 1.2 sec | PASS |
| Throughput | >= 100 TPS | 142 TPS | PASS |
| Error Rate | < 1% | 0.3% | PASS |
| Concurrent Users | 300 | 300 | PASS |

### 5. Detailed Results Per Transaction

Break down the results by transaction / flow:

| Transaction | Avg (ms) | 90th (ms) | 95th (ms) | Error % | Throughput |
|-------------|----------|-----------|-----------|---------|------------|
| A - Login | 450 | 820 | 1100 | 0.1% | 45/s |
| B - Dashboard | 320 | 600 | 780 | 0.2% | 42/s |
| C - Search | 580 | 1200 | 1500 | 0.5% | 38/s |

### 6. Key Observations
- Any notable findings - specific transactions that were slower, errors that appeared under peak load, patterns in response time over time
- Include relevant charts from the JMeter web report (Response Times Over Time, Throughput Over Time)

### 7. Recommendations (if applicable)
- If the test failed: what needs to be addressed
- If the test passed: any areas close to the threshold that should be monitored
- Suggestions for the next round of testing (higher load, longer duration, additional flows)

---

## Pass/Fail Against NFRs

The pass/fail decision is straightforward - compare results against the NFRs defined in [Section 2](02-understand-requirements.md).

**Pass:** All metrics are within the defined NFR targets during the steady-state period (exclude the ramp-up phase from the analysis).

**Fail:** One or more metrics exceed the NFR thresholds. When reporting a failure:

- Be specific about which metric failed and by how much
- Identify which transactions contributed to the failure
- If possible, indicate at what load level the failure started (e.g., "response times exceeded 2 seconds when active users reached 250")

> **Important:** Analyze the **steady-state period only**. The ramp-up phase will have inconsistent metrics as the load is still building. Focus on the period where all users are active and the load is stable.

---

## What to Present to Stakeholders

Different audiences need different levels of detail:

| Audience | What They Want |
|----------|---------------|
| **Management / Business** | Pass or fail, one-line summary, risk if applicable |
| **Technical Lead / Architect** | NFR comparison table, per-transaction breakdown, bottleneck analysis |
| **Development Team** | Specific slow endpoints, error details, server-side metrics if available |
| **QA Team** | Full report including methodology, load model, raw data location |

For a quick stakeholder update, the **Summary + NFR table** is usually enough. Have the detailed report ready for follow-up questions.

---

## Tips

- **Lead with the verdict** - don't make stakeholders read through pages of data to find out if the test passed. Put pass/fail at the top

- **Use the JMeter web report charts** - screenshots of Response Times Over Time and Throughput are more impactful than tables of numbers

- **Always include the load model** - without knowing the test conditions, the numbers are meaningless

- **Keep a consistent format** - use the same report structure across all test cycles so results are easy to compare

- **Save everything** - keep the `.jtl` files, `.jmx` scripts, and generated reports. You'll need them for comparison when running the next test cycle

- **Version your reports** - label them clearly (e.g., "Run 1 - Baseline", "Run 2 - After DB optimization") so progress is trackable
