# 11. Backend Listener - InfluxDB + Grafana

The JMeter web report is generated **after** the test finishes. If you want to monitor results **in real-time** while the test is running, you need a Backend Listener that streams data to InfluxDB, which Grafana then visualizes as a live dashboard.

## Table of Contents
- [Why Use a Backend Listener](#why-use-a-backend-listener)
- [Architecture](#architecture)
- [Setting Up InfluxDB](#setting-up-influxdb)
- [Setting Up Grafana](#setting-up-grafana)
- [Configuring JMeter Backend Listener](#configuring-jmeter-backend-listener)
- [Building a Grafana Dashboard](#building-a-grafana-dashboard)
- [Tips](#tips)

---

## Why Use a Backend Listener

| Without Backend Listener | With Backend Listener |
|--------------------------|----------------------|
| Results visible only after the test ends | Live metrics during the test |
| No way to spot issues in real-time | Can see errors and response time spikes as they happen |
| Must wait for the full run to complete | Can decide to stop early if something is clearly wrong |
| Only JMeter report | Rich Grafana dashboards with custom visualizations |

The backend listener is especially valuable for long-running tests (30+ minutes) and distributed testing where you need a centralized view of all worker results.

---

## Architecture

```
JMeter ──(Backend Listener)──> InfluxDB ──(Data Source)──> Grafana
                                  │                          │
                            Time-series DB              Dashboard UI
                            Stores metrics              Visualizes data
```

- **JMeter** sends metrics (response times, throughput, errors) to InfluxDB via the Backend Listener
- **InfluxDB** stores the time-series data
- **Grafana** reads from InfluxDB and displays live charts

---

## Setting Up InfluxDB

### InfluxDB 1.x (Simpler Setup)

InfluxDB 1.x is simpler to set up with JMeter's built-in Backend Listener. InfluxDB 2.x works too but requires additional configuration.

**Steps:**
1. Download InfluxDB from [https://portal.influxdata.com/downloads/](https://portal.influxdata.com/downloads/)
2. Extract and run `influxd` (the InfluxDB server)
3. Create a database for JMeter data:

```
influx
> CREATE DATABASE jmeter
> SHOW DATABASES
> EXIT
```

**Default port:** `8086`

<!-- TODO: Screenshot - InfluxDB running and database created -->

### InfluxDB 2.x

If using InfluxDB 2.x:
1. Create a bucket named `jmeter`
2. Create an API token with write access to that bucket
3. Note the organization name - you'll need it for the Backend Listener configuration

---

## Setting Up Grafana

**Steps:**
1. Download Grafana from [https://grafana.com/grafana/download](https://grafana.com/grafana/download)
2. Install and start the Grafana service
3. Open Grafana in browser: `http://localhost:3000`
4. Default credentials: `admin` / `admin` (change on first login)

### Add InfluxDB as a Data Source

1. Go to **Configuration** (gear icon) > **Data Sources** > **Add data source**
2. Select **InfluxDB**
3. Configure:
   - **URL:** `http://localhost:8086`
   - **Database:** `jmeter` (for InfluxDB 1.x)
   - For InfluxDB 2.x: set the appropriate auth token, organization, and bucket
4. Click **Save & Test** - should show "Data source is working"

<!-- TODO: Screenshot - Grafana data source configuration for InfluxDB -->

---

## Configuring JMeter Backend Listener

**Add it:** Right-click Thread Group > Add > Listener > **Backend Listener**

### Configuration for InfluxDB 1.x

| Setting | Value |
|---------|-------|
| **Backend Listener implementation** | `org.apache.jmeter.visualizers.backend.influxdb.InfluxdbBackendListenerClient` |
| **influxdbUrl** | `http://localhost:8086/write?db=jmeter` |
| **application** | Your test name (e.g., `login-flow`) - used to filter in Grafana |
| **measurement** | `jmeter` (default) |
| **summaryOnly** | `false` (set to `true` if you only want aggregate data, not per-sampler) |
| **samplersRegex** | `.*` (all samplers) or a specific pattern |
| **testTitle** | Name for this test run (e.g., `Run1-300users`) |

### Configuration for InfluxDB 2.x

| Setting | Value |
|---------|-------|
| **influxdbUrl** | `http://localhost:8086/api/v2/write?org=YOUR_ORG&bucket=jmeter` |
| **influxdbToken** | Your API token |

Everything else is the same as 1.x.

<!-- TODO: Screenshot - Backend Listener configuration in JMeter -->

### Placement

Place the Backend Listener at the **Thread Group level** so it captures all requests. Only one Backend Listener is needed per test plan.

---

## Building a Grafana Dashboard

### Option 1: Import a Pre-Built Dashboard

The community has pre-built JMeter dashboards for Grafana. The most popular one:

1. Go to **Dashboards** > **Import**
2. Enter the dashboard ID from [Grafana's dashboard library](https://grafana.com/grafana/dashboards/) - search for "JMeter"
3. Select your InfluxDB data source
4. Click **Import**

### Option 2: Build Your Own

Create a new dashboard and add panels for:

**Essential panels:**
- **Active Threads Over Time** - confirms the load profile
- **Response Time Over Time** - average and percentiles
- **Throughput (TPS)** - requests per second
- **Error Rate Over Time** - percentage of failed requests
- **Response Time Per Transaction** - breakdown by Transaction Controller name

**InfluxDB query example** (for average response time over time):

```sql
SELECT mean("avg") FROM "jmeter" WHERE "application" = 'login-flow' AND $timeFilter GROUP BY time($__interval)
```

<!-- TODO: Screenshot - Grafana dashboard during a live test -->

### Filtering by Test Run

Use the `testTitle` field set in the Backend Listener to filter dashboards by specific test runs. Add a Grafana variable for `testTitle` so you can switch between runs using a dropdown.

---

## Tips

- **Start InfluxDB and Grafana before the test** - the Backend Listener will fail silently if InfluxDB is not running
- **Use the `application` field** - set it to a meaningful test name so you can filter results in Grafana when running multiple tests
- **Backend Listener adds minimal overhead** - it's safe to use during load tests, unlike GUI listeners
- **Keep the default `summaryOnly=false`** - this gives you per-sampler data which is much more useful for analysis
- **InfluxDB retention** - configure a retention policy if you don't want test data accumulating indefinitely (e.g., keep data for 30 days)
- **Share the Grafana dashboard URL** - anyone on the network can watch the test in real-time from their browser
