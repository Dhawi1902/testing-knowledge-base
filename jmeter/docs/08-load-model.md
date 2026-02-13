# 8. Design Load Model

The script works with 1 user - now you need to define how to apply load. The load model determines how many users, how fast they ramp up, how long the test runs, and what the pacing looks like. All of this comes from the requirements gathered in [Section 2](02-understand-requirements.md).

## Table of Contents
- [Key Parameters](#key-parameters)
- [Load Profiles](#load-profiles)
- [Calculating Load from Requirements](#calculating-load-from-requirements)
- [Thread Group Configuration](#thread-group-configuration)
- [Tips](#tips)

---

## Key Parameters

| Parameter | What it Controls |
|-----------|-----------------|
| **Number of Threads (Users)** | How many virtual users run concurrently |
| **Ramp-Up Period** | How long it takes to start all threads |
| **Loop Count / Duration** | How many times each user repeats the flow, or how long the test runs |
| **Think Time** | Delay between user actions (configured via Timers in the script) |

### Number of Threads

This is the number of concurrent virtual users. It comes directly from the NFRs - "the system should support 500 concurrent users."

Each thread executes the entire script independently. If you have 500 threads, you have 500 users running the flow at the same time.

### Ramp-Up Period

The time (in seconds) to start all threads. JMeter distributes thread starts evenly across this period.

**Example:** 100 threads with a 60-second ramp-up = ~1.67 new users per second.

**Why not start all users at once?**
- Starting 500 users simultaneously creates an unrealistic spike
- Real users arrive gradually over time
- A sudden spike can crash the server before it reaches steady state, giving you misleading results

**General guideline:** Ramp up over 1-5 minutes depending on the total user count. The goal is to reach full load gradually.

### Loop Count vs Duration

You have two options:

| Option | When to Use |
|--------|-------------|
| **Loop Count** (e.g., 1, 5, 10) | When you want each user to complete the flow a fixed number of times |
| **Infinite + Duration** | When you want the test to run for a specific time period (e.g., 30 minutes) - this is the most common for load tests |

For load tests, you typically use **Infinite loop** with a **Duration** (e.g., 1800 seconds = 30 minutes). This lets users continuously repeat the flow for the entire test duration.

### Think Time

Think time is configured in the script using Timers (see [Section 6 - Script Enhancement](06-script-enhancement.md)), not in the Thread Group. But it directly impacts the load model because it controls the pacing between actions.

**Impact on throughput:**
- Shorter think time = each user completes more iterations = higher throughput
- Longer think time = each user completes fewer iterations = lower throughput
- The same 100 users with 2-second think time generate more load than 100 users with 10-second think time

---

## Load Profiles

Different test types use different load shapes. The three most common:

### Ramp-Up to Steady State

The standard load test profile. Gradually increase users, hold at the target for a sustained period, then ramp down.

```
Users
  ^
  |         ┌──────────────────┐
  |        /                    \
  |       /                      \
  |      /                        \
  |     /                          \
  └────/────────────────────────────\──────> Time
       Ramp-Up    Steady State    Ramp-Down
```

**Use when:** Validating the system handles the expected concurrent user load over time. This is the most common profile.

**Thread Group settings:**
- **Threads:** target concurrent users (e.g., 500)
- **Ramp-Up:** gradual increase (e.g., 300 seconds / 5 minutes)
- **Duration:** total test time including ramp-up (e.g., 2100 seconds / 35 minutes for 5 min ramp + 30 min steady)

### Stress Test (Step-Up)

Incrementally increase load in steps to find the breaking point.

```
Users
  ^
  |                          ┌────
  |                    ┌─────┘
  |              ┌─────┘
  |        ┌─────┘
  |  ┌─────┘
  └──┘──────────────────────────────> Time
     50   100   150   200   250
```

**Use when:** You want to find the maximum capacity or the point where performance degrades.

**How to implement:** Use multiple Thread Groups with staggered start times, or use the **Stepping Thread Group** plugin (from JMeter Plugins Manager). Each step adds more users and holds for a period before adding more.

### Spike Test

Sudden burst of users to test how the system handles a traffic surge.

```
Users
  ^
  |     ┌──┐
  |     │  │
  |     │  │
  | ────┘  └────────
  └─────────────────────> Time
```

**Use when:** Testing auto-scaling, recovery behavior, or how the system handles sudden traffic surges (e.g., flash sale, marketing campaign).

**How to implement:** Use a short ramp-up period (e.g., 10 seconds) with a high thread count, or use the **Ultimate Thread Group** plugin for precise control over the spike shape.

---

## Calculating Load from Requirements

If you have a throughput target (e.g., "100 transactions per second"), you need to calculate how many threads are required.

### The Formula

```
Threads = TPS × Average Response Time (seconds) × (1 + Think Time factor)
```

**Simplified version:**

```
Threads = Target TPS × (Average Response Time + Average Think Time)
```

### Example Calculation

**Requirements:**
- Target: 100 TPS
- Expected average response time: 1 second
- Think time between actions: 3 seconds

**Calculation:**
```
Threads = 100 × (1 + 3) = 400 users
```

You need approximately **400 concurrent users** to achieve 100 TPS with those response times and think times.

> **Important:** This is an estimate. Actual results depend on server performance, network latency, and script complexity. Start with the calculated number, run the test, check actual throughput, and adjust.

### When Requirements Give Concurrent Users Only

If the NFR says "500 concurrent users" without a TPS target:
- Configure 500 threads
- Use realistic think times
- The resulting TPS is whatever the system produces under that load
- Report the observed TPS, response times, and error rates

### When Requirements Give TPS Only

If the NFR says "achieve 200 TPS" without specifying users:
- Use the formula above to estimate threads
- Alternatively, use a **Constant Throughput Timer** to control the request rate directly
- Adjust thread count until you hit the target TPS

---

## Thread Group Configuration

### Standard Load Test Example

**Scenario:** 300 concurrent users, 30-minute steady state, 5-minute ramp-up.

| Setting | Value |
|---------|-------|
| Number of Threads | 300 |
| Ramp-Up Period | 300 (seconds) |
| Loop Count | Infinite (check "Infinite") |
| Duration | 2100 (seconds) — 5 min ramp + 30 min steady + ~0 min ramp-down |
| Startup Delay | 0 |

<!-- TODO: Screenshot - Thread Group configured for a standard load test -->

### Adding a Ramp-Down

JMeter's default Thread Group doesn't have a built-in ramp-down. Options:
- **Just stop** - the test ends and all threads stop. This is fine for most cases since you analyze the steady-state period only
- **Use the Ultimate Thread Group plugin** - gives full control over ramp-up, hold, and ramp-down

### Multiple Scenarios (Thread Groups)

If you have multiple user flows (e.g., 70% browse, 20% search, 10% purchase), create separate Thread Groups for each:

```
Test Plan
├── Thread Group: Browse (210 users - 70%)
│   └── [browse flow script]
├── Thread Group: Search (60 users - 20%)
│   └── [search flow script]
└── Thread Group: Purchase (30 users - 10%)
    └── [purchase flow script]
```

Set all Thread Groups to start at the same time. The user distribution reflects the expected real-world mix.

---

## Tips

- **Start small** - don't jump to 500 users immediately. Run with 10, then 50, then 100. Validate results at each level before scaling up
- **The formula is a starting point** - always validate with actual test results and adjust. Real-world throughput depends on many factors
- **Ramp-up matters** - too fast creates unrealistic spikes, too slow wastes test time. 1-5 minutes is typical
- **Duration should be long enough** - at least 15-30 minutes of steady state to observe trends, memory leaks, and connection pool behavior
- **Think time is part of the model** - changing think time changes the effective load. Keep it consistent across test runs for comparable results
- **Document your load model** - record the thread count, ramp-up, duration, and think time for each test run. You'll need this for the report
