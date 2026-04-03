# 2. Understand Requirements and Flow

Before opening JMeter, you need to understand **what** you are testing and **why**. Skipping this step leads to wasted effort - building scripts for the wrong flows or testing with unrealistic numbers.


## What to Ask

Before starting, gather the following information from stakeholders (BA, dev team, project manager):

### Application Under Test
- What is the application / system being tested?
- What is the environment? (URL, credentials, VPN required?)
- Is it a web application, API, or both?

### Scope
- Which user flows / business scenarios need to be tested?
- Are we testing the full end-to-end flow or specific APIs only?
- Do we need to include static resources (images, CSS, JS) or just API calls?

### Non-Functional Requirements (NFRs)
- Expected number of concurrent users
- Expected response time thresholds (e.g., < 2 seconds for page load)
- Expected throughput (e.g., X transactions per second)
- Acceptable error rate (e.g., < 1%)

### Test Data
- What test data is needed? (usernames, account numbers, product IDs, etc.)
- Is the test data already available or does it need to be created?
- Can test data be reused across runs or does it need to be unique each time?

### Environment and Constraints
- Which environment will the test run against? (SIT, UAT, staging, pre-prod)
- Are there any rate limits or firewalls to be aware of?
- Is there a specific test window / schedule?
- Do we need coordination with other teams? (e.g., DBA for monitoring, infra for scaling)

---

## Identify User Flows

Based on the requirements, list out the user journeys to be tested. For example:

| # | Flow | Description |
|---|------|-------------|
| 1 | Login | User logs in with valid credentials |
| 2 | Search | User searches for a product and views results |
| 3 | Add to Cart | User adds an item to the cart |
| 4 | Checkout | User completes the purchase |

> **Tip:** Focus on the **critical business flows** - the ones that matter most to the business and are used most frequently by real users.

---

## Define Pass/Fail Criteria

Based on the NFRs, define clear criteria so you know when the test passes or fails:

| Metric | Target |
|--------|--------|
| Response Time (90th percentile) | < 2 seconds |
| Throughput | >= 100 TPS |
| Error Rate | < 1% |
| Concurrent Users | 500 |

> **Note:** These numbers come from the stakeholders, not from you. If NFRs are not provided, ask for them. Testing without clear targets makes the results meaningless - you won't know if the system "passed" or not.

---

## Tips

- **Get it in writing** - requirements change, having documented NFRs protects you when stakeholders question results later
- **Don't assume** - if requirements are vague, ask. "Test the system performance" is not a requirement
- **Start small** - even if the scope is large, start with the most critical flow first, then expand
- **Requirements drive everything** - the flows you test, the data you prepare, the load model you design, and the metrics you report all come from this step
