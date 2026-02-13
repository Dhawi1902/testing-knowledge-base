# 12. Distributed Testing

When a single machine can't generate enough load (CPU or memory maxes out before reaching the target thread count), you distribute the load across multiple machines. JMeter has built-in support for this using a controller-worker architecture.

## Table of Contents
- [When You Need Distributed Testing](#when-you-need-distributed-testing)
- [Architecture](#architecture)
- [Setting Up Remote Machines](#setting-up-remote-machines)
- [Configuring JMeter for Distributed Mode](#configuring-jmeter-for-distributed-mode)
- [Running Distributed Tests](#running-distributed-tests)
- [Important Considerations](#important-considerations)
- [Tips](#tips)

---

## When You Need Distributed Testing

Signs that a single machine is not enough:
- CPU usage on the load generator is consistently above **80%** during the test
- JMeter runs out of memory (OutOfMemoryError)
- You can't reach the target thread count without the machine slowing down
- Response times are inflated because the load generator itself is the bottleneck, not the server

**Rule of thumb:** A single machine can typically handle **300-1000 threads** depending on the script complexity, hardware specs, and whether you're making lightweight API calls or heavy page loads. Monitor your load generator machine during tests.

---

## Architecture

```
                    ┌──────────────────┐
                    │   Controller     │
                    │  (your machine)  │
                    │                  │
                    │  Sends .jmx      │
                    │  Collects results│
                    └──────┬───────────┘
                           │
              ┌────────────┼────────────┐
              │            │            │
       ┌──────▼──┐  ┌──────▼──┐  ┌──────▼──┐
       │ Worker 1 │  │ Worker 2 │  │ Worker 3 │
       │ (remote) │  │ (remote) │  │ (remote) │
       │          │  │          │  │          │
       │ Runs the │  │ Runs the │  │ Runs the │
       │ test     │  │ test     │  │ test     │
       └──────────┘  └──────────┘  └──────────┘
```

- **Controller** - the machine that sends the test plan and collects results. Does not generate load itself (by default)
- **Workers** - remote machines that actually run the test and generate load
- Each worker runs the **same** test plan with the **same** thread count
- If you configure 100 threads and have 3 workers, you get **300 total threads**

---

## Setting Up Remote Machines

Each worker machine needs:

1. **Same JMeter version** as the controller
2. **Same Java version** as the controller
3. **Same plugins** installed (if your script uses any)
4. **Test data files** (CSV files) copied to the same path on each machine - or use the same filename with different content per machine (see [Section 13](13-test-data-python.md))
5. **Network access** to the target application
6. **Network access** from the controller (firewall rules allowing the JMeter RMI port)

### Start the JMeter Server on Each Worker

On each remote machine, run:

```bat
jmeter-server
```

Or on Windows:

```bat
jmeter-server.bat
```

This starts the JMeter server process, listening for connections from the controller. Default RMI port is `1099`.

<!-- TODO: Screenshot - jmeter-server running on a remote machine -->

---

## Configuring JMeter for Distributed Mode

On the **controller** machine, edit `jmeter.properties` (in the JMeter `bin/` folder):

```properties
remote_hosts=worker1-ip:1099,worker2-ip:1099,worker3-ip:1099
```

Replace `worker1-ip`, `worker2-ip`, etc. with the actual IP addresses of your worker machines.

### RMI Configuration

If workers are on a different network or behind a firewall, you may need to configure RMI settings in `jmeter.properties`:

```properties
# On the controller
server.rmi.ssl.disable=true

# On each worker (in their jmeter.properties)
server.rmi.ssl.disable=true
server.rmi.localport=1099
```

> **Note:** Disabling RMI SSL is acceptable for internal testing networks. For production or external networks, configure proper SSL certificates.

---

## Running Distributed Tests

### From CLI (Recommended)

Run on all configured remote hosts:

```bat
jmeter -n -t test-plan.jmx -l results.jtl -r
```

The `-r` flag tells JMeter to run on all remote hosts listed in `remote_hosts`.

To run on specific workers only:

```bat
jmeter -n -t test-plan.jmx -l results.jtl -R worker1-ip:1099,worker2-ip:1099
```

### What Happens During Execution

1. Controller sends the `.jmx` file to all workers
2. Each worker starts the test with the configured thread count
3. Workers send results back to the controller in real-time
4. Controller aggregates all results into the single `.jtl` file
5. When the test ends, the controller generates the report (if `-e -o` flags were used)

---

## Important Considerations

### Thread Count is Per Worker

If the test plan has **100 threads** and you have **3 workers**, the total is **300 threads**. Adjust your Thread Group accordingly:

| Target Total Users | Workers | Threads Per Worker (in .jmx) |
|-------------------|---------|-------------------------------|
| 300 | 3 | 100 |
| 500 | 5 | 100 |
| 1000 | 4 | 250 |

### CSV Data Distribution

If each user needs unique data (e.g., unique login credentials), you need to split the CSV data so each worker gets different rows. Two approaches:

1. **Same filename, different content** - each worker has a file named `users.csv` but with different rows. This is the cleanest approach (see [Section 13](13-test-data-python.md))
2. **Thread Group offset** - use the same full CSV on all machines and configure CSV Data Set Config sharing mode

### Files Are Not Automatically Distributed

JMeter sends the `.jmx` file to workers, but **not** supporting files like:
- CSV data files
- JAR files for plugins
- External scripts

You must copy these to each worker machine manually or via a script (see [Section 14](14-automation-batch.md)).

### Timers and Think Time

Timers work the same in distributed mode. Each worker applies think time independently.

### Backend Listener in Distributed Mode

If using a Backend Listener for Grafana monitoring, each worker sends data directly to InfluxDB. The results are automatically merged in Grafana since they share the same `application` and `testTitle` fields.

---

## Tips

- **Test with 1 worker first** - validate the distributed setup works before adding more workers
- **Monitor worker machines** - check CPU and memory on workers during the test to ensure they're not overloaded
- **Keep JMeter versions in sync** - mismatched versions between controller and workers cause silent failures
- **Use the same network** - controller and workers should ideally be on the same network or low-latency connection. High latency between controller and workers can affect result collection
- **Automate worker setup** - when you have many workers, manually copying files and starting jmeter-server is tedious. Use batch scripts (see [Section 14](14-automation-batch.md))
- **Check firewall rules** - the most common distributed testing issue is connectivity. Verify workers can be reached from the controller before starting the test
