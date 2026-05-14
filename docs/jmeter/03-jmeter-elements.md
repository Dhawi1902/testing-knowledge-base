# 3. JMeter Elements Overview

Before you start recording and building scripts, you need to understand the building blocks of JMeter. This section covers the elements you'll use most often and how they relate to each other.


## Test Plan

The **Test Plan** is the root element - the container for everything. Every JMeter script starts with a Test Plan. It holds all Thread Groups, controllers, samplers, and configurations.

<!-- TODO: Screenshot - Test Plan element -->

---

## Thread Group

The **Thread Group** represents a group of virtual users. This is where you define:

- **Number of Threads (users)** - how many virtual users to simulate

- **Ramp-up Period** - how long to take to start all threads (e.g., 100 users over 60 seconds)

- **Loop Count** - how many times each user repeats the flow (or infinite with a duration)

During script development, you'll typically use **1 thread** and **1 loop** to debug. The real numbers come later in step 8 (Load Model).

<!-- TODO: Screenshot - Thread Group configuration -->

---

## Samplers

Samplers are the actual **requests** sent to the server. The most common one is:

### HTTP Request
Sends an HTTP/HTTPS request to the server. You configure:
- Protocol (http/https)
- Server name or IP
- Port
- Method (GET, POST, PUT, DELETE, etc.)
- Path
- Parameters or body data

<!-- TODO: Screenshot - HTTP Request sampler -->

Other samplers exist (JDBC Request, JMS, FTP, etc.) but HTTP Request is used in the majority of performance tests.

---

## Config Elements

Config elements provide **default values and shared configuration** for samplers. They don't send requests themselves - they configure how requests are sent.

### HTTP Request Defaults
Sets default values (protocol, server, port) so you don't repeat them in every HTTP Request sampler. If the server or port changes, you update it in one place.

<!-- TODO: Screenshot - HTTP Request Defaults -->

### HTTP Header Manager
Adds headers to requests (e.g., `Content-Type`, `Authorization`, `Accept`). Can be placed at the Test Plan level to apply to all requests, or under a specific sampler for that request only.

### HTTP Cookie Manager
Handles cookies automatically - stores cookies from responses and sends them with subsequent requests, just like a browser would. Essential for session-based applications.

### CSV Data Set Config
Reads test data from a CSV file and assigns values to JMeter variables. Used for parameterization - feeding different data (usernames, passwords, IDs) to each virtual user.

- **Filename** - path to the CSV file

- **Variable Names** - comma-separated names to assign to each column

- **Sharing Mode** - controls how data is shared across threads

<!-- TODO: Screenshot - CSV Data Set Config -->

### User Defined Variables
Stores key-value pairs as variables. Useful for environment-specific values (URLs, ports) that you want to change in one place.

---

## Logic Controllers

Logic controllers determine the **order and conditions** for executing samplers.

### Transaction Controller
Groups multiple requests that belong to the **same page or action**. This is critical for meaningful reporting - you see "Login Page" as a single transaction rather than 5 separate API calls.

- Leave **"Generate parent sample"** unchecked so individual requests are visible in the report for detailed analysis

<!-- TODO: Screenshot - Transaction Controller -->

### If Controller
Executes child elements only when a condition is true. Used for:
- Stopping the script if a critical value was not extracted (e.g., token is empty)
- Branching flows based on business logic

Example condition: `${__groovy("${token}" != "")}`

### Loop Controller
Repeats child elements a specified number of times. Useful when a user action needs to repeat within a flow (e.g., add 3 items to cart).

### Simple Controller
A basic container for organizing samplers. No logic - just grouping for readability.

---

## Timers

Timers add **delays between requests** to simulate realistic user behavior. Without timers, JMeter fires requests as fast as possible, which is not how real users behave.

### Constant Timer
Adds a fixed delay (in milliseconds) between requests.

### Gaussian Random Timer
Adds a randomized delay based on a Gaussian distribution. More realistic than a constant timer since real users don't wait exactly the same time.

### Constant Throughput Timer
Controls the throughput (requests per minute) rather than the delay. Useful when you need to achieve a specific TPS.

> **Tip:** Timers apply to all samplers in their scope (same level and below). Place them carefully.

---

## Assertions

Assertions **validate the response** from the server. A request might return HTTP 200 but still have the wrong content. Assertions catch this.

### Response Assertion
Checks the response body, headers, or status code for expected values (contains, matches, equals).

### JSON Assertion
Validates specific values in a JSON response using JSONPath.

### Duration Assertion
Fails if the response time exceeds a threshold.

> **Tip:** Always add assertions for critical requests. Without them, you might be load testing error pages and think everything is fine.

---

## Listeners

Listeners **collect and display test results**. Used during debugging and analysis.

### View Results Tree
Shows detailed request/response data for each sampler. Essential for debugging - you can see exactly what was sent and received.

> **Warning:** Disable this during actual load tests. It consumes a lot of memory and affects test performance.

### Summary Report
Shows aggregate results in a table - average response time, min, max, throughput, error rate per sampler.

### Aggregate Report
Similar to Summary Report but includes percentile data (90th, 95th, 99th percentile response times).

### Backend Listener
Sends results in real-time to an external system (e.g., InfluxDB) for live monitoring. Covered in [Section 11](11-backend-listener.md).

---

## Pre-Processors and Post-Processors

### Pre-Processors
Execute **before** a sampler runs. Used to set up data or modify the request dynamically.

- **JSR223 PreProcessor** - run Groovy/Java code before a request

### Post-Processors
Execute **after** a sampler runs. Used to extract values from responses for use in subsequent requests.

- **Regular Expression Extractor** - extract values using regex

- **JSON Extractor** - extract values from JSON responses using JSONPath

- **CSS/jQuery Extractor** - extract values from HTML using CSS selectors

- **JSR223 PostProcessor** - run Groovy/Java code after a request

> **Note:** Post-processors are the core of **correlation** - extracting dynamic values (tokens, session IDs) from responses and passing them to the next request. This is covered in detail in [Section 5](05-correlation-parameterization.md).

---

## How Elements Relate - Scope and Hierarchy

JMeter uses a **tree structure**. Where you place an element determines its scope:

```
Test Plan
└── Thread Group
    ├── HTTP Cookie Manager          ← applies to all requests in this Thread Group
    ├── HTTP Request Defaults         ← applies to all requests in this Thread Group
    ├── Transaction Controller: Login
    │   ├── HTTP Request: GET /login
    │   ├── HTTP Request: POST /auth
    │   │   └── JSON Extractor        ← only applies to POST /auth
    │   └── Response Assertion         ← only applies to POST /auth (last sibling)
    ├── Constant Timer                 ← applies to all requests in this Thread Group
    └── View Results Tree              ← collects results from all requests
```

**Key rules:**

- **Config elements** (Cookie Manager, Defaults, CSV) at Thread Group level apply to all samplers below

- **Extractors and assertions** placed under a specific sampler only apply to that sampler

- **Timers** apply to all samplers in their scope

- **Listeners** collect data from all samplers in their scope

Understanding scope is critical - a misplaced element can cause hard-to-debug issues.
