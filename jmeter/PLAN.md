# Performance Testing with JMeter - Knowledge Transfer Plan

## Objective

Document a practical, real-world approach to performance testing using JMeter.
This is not a textbook guide - it's a proven workflow from hands-on experience,
designed to enable someone to independently conduct performance tests.

---

## Document Structure

Recommended approach: **Multi-file with a main README.md as index**.
Each topic gets its own markdown file for easier navigation and maintenance on GitLab.

```
Jmeter-Learn/
├── README.md                        # Main index / table of contents
├── PLAN.md                          # This file
├── docs/
│   ├── 01-install-tools.md          # Step 1
│   ├── 02-understand-requirements.md # Step 2
│   ├── 03-jmeter-elements.md        # Step 3
│   ├── 04-recording.md              # Step 4
│   ├── 05-correlation-parameterization.md # Step 5
│   ├── 06-script-enhancement.md     # Step 6
│   ├── 07-debug.md                  # Step 7
│   ├── 08-load-model.md             # Step 8
│   ├── 09-execute-analyze.md        # Step 9
│   ├── 10-reporting.md              # Step 10
│   ├── 11-backend-listener.md       # Step 11
│   ├── 12-distributed-testing.md    # Step 12
│   ├── 13-test-data-python.md       # Step 13
│   ├── 14-automation-batch.md       # Step 14
│   └── 99-future-to-explore.md      # Appendix
├── scripts/                         # Python scripts, batch files
└── samples/                         # Sample .jmx files, CSV templates
```

---

## Content Outline

### BASICS

#### 1. Install Tools (`01-install-tools.md`)
- JMeter installation and setup
- Fiddler installation
- Blazemeter Chrome extension
- Optional tools: Python, InfluxDB, Grafana
- Verify everything works

#### 2. Understand Requirements and Flow (`02-understand-requirements.md`)
- What to ask before starting (NFRs, SLAs, scope)
- Identifying user journeys / business flows to test
- Deciding what to include (APIs only, static resources, etc.)
- Defining pass/fail criteria

#### 3. JMeter Elements Overview (`03-jmeter-elements.md`)
- Test Plan, Thread Group
- Samplers (HTTP Request, etc.)
- Config Elements (CSV Data Set Config, HTTP Header Manager, etc.)
- Logic Controllers (Transaction Controller, If Controller, etc.)
- Timers (Constant Timer, Gaussian Random Timer, etc.)
- Assertions (Response Assertion, JSON Assertion, etc.)
- Listeners (View Results Tree, Summary Report, etc.)
- Pre-Processors and Post-Processors (extractors, JSR223)
- How elements relate to each other (hierarchy / scope)

#### 4. Recording (`04-recording.md`)
- Why record from both Fiddler and Blazemeter simultaneously
  - Blazemeter: generates .jmx with endpoint structure
  - Fiddler: detailed request/response view for tracing values
- How to set up and start recording in both tools
- Running through the user flow while recording
- Importing Blazemeter recording into JMeter

#### 5. Correlation and Parameterization (`05-correlation-parameterization.md`)
- What is correlation and why it's needed (dynamic values: tokens, session IDs)
- Using Fiddler to trace where values first appear in responses
- Applying extractors in JMeter (RegEx, JSON, CSS/jQuery)
- Parameterization using CSV Data Set Config
- Parameterization using Config Elements / User Defined Variables
- When to use CSV vs Config Elements

#### 6. Script Enhancement (`06-script-enhancement.md`)
- Grouping requests into Transaction Controllers (by page/action)
- Renaming samplers and controllers to meaningful names
- Adding flow logic (If Controller to validate extractions, stop on failure)
- Adding assertions to validate responses
- Adding timers / think time for realistic pacing
- Cleaning up the script (removing unnecessary requests based on requirements)

#### 7. Debug (`07-debug.md`)
- Running with 1 thread to validate the flow
- Using View Results Tree to inspect requests/responses
- Using Debug Sampler to check variables
- Common issues and how to fix them
- Verifying the script is ready for load testing

---

### APPLYING LOAD

#### 8. Design Load Model (`08-load-model.md`)
- Number of concurrent users / threads
- Ramp-up period
- Test duration
- Think time between actions
- Load profiles: ramp-up, steady state, spike
- Calculating load based on requirements

#### 9. Execute and Analyze Results (`09-execute-analyze.md`)
- Running in CLI mode (never GUI for actual load tests)
- CLI command and useful flags
- Key metrics: response time, throughput, error rate, percentiles
- Reading JTL/CSV results
- Using listeners for analysis (Aggregate Report, Summary)
- Identifying bottlenecks from results

#### 10. Reporting (`10-reporting.md`)
- Key metrics to highlight
- What to present to stakeholders
- Pass/fail against NFRs
- Basic report structure

---

### ADVANCED

#### 11. Backend Listener - InfluxDB + Grafana (`11-backend-listener.md`)
- Why use a backend listener (real-time monitoring)
- Setting up InfluxDB
- Setting up Grafana
- Configuring JMeter Backend Listener
- Building a Grafana dashboard

#### 12. Distributed Testing (`12-distributed-testing.md`)
- When and why you need distributed testing
- Architecture (controller + workers)
- Setting up remote machines
- Configuring JMeter for distributed mode
- Running distributed tests

#### 13. Test Data Preparation with Python (`13-test-data-python.md`)
- Why Python for test data
- Generating sequential IDs
- Splitting/distributing CSV data across machines (unique data per worker)
- Ensuring same filename but unique content per machine
- Example Python scripts

#### 14. Automation with Batch Files (`14-automation-batch.md`)
- Why automate with batch files
- Automating test execution
- Automating test data distribution
- Combining with distributed testing
- Example batch scripts

---

### APPENDIX

#### Future / To Explore (`99-future-to-explore.md`)
- Server-side monitoring (CPU, memory, DB connections during test)
- CI/CD integration (GitLab CI pipeline)
- Advanced reporting tools
- Other topics to explore

---

## Approach

- Work section by section, collaboratively
- Each section follows: **Why** (brief context) → **How** (actual steps) → **Tips** (lessons learned)
- Include screenshots where helpful
- Include sample files (.jmx, .csv, .py, .bat) in respective folders
- Keep it practical - "this is how I do it", not textbook theory

---

## Status

| # | Section | Status |
|---|---------|--------|
| 1 | Install Tools | Not Started |
| 2 | Understand Requirements | Not Started |
| 3 | JMeter Elements | Not Started |
| 4 | Recording | Not Started |
| 5 | Correlation & Parameterization | Not Started |
| 6 | Script Enhancement | Not Started |
| 7 | Debug | Not Started |
| 8 | Load Model | Not Started |
| 9 | Execute & Analyze | Not Started |
| 10 | Reporting | Not Started |
| 11 | Backend Listener | Not Started |
| 12 | Distributed Testing | Not Started |
| 13 | Test Data (Python) | Not Started |
| 14 | Automation (Batch) | Not Started |
| 99 | Future / To Explore | Not Started |
