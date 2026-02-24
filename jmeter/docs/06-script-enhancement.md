# 6. Script Enhancement

After correlation and parameterization, the script works but it's messy - auto-generated names, flat structure, no validation. This step turns it into a clean, maintainable, and robust test plan.

## Table of Contents
- [Group Requests into Transaction Controllers](#group-requests-into-transaction-controllers)
- [Rename Samplers and Controllers](#rename-samplers-and-controllers)
- [Add Flow Logic](#add-flow-logic)
- [Add Assertions](#add-assertions)
- [Add Timers / Think Time](#add-timers--think-time)
- [Clean Up Unnecessary Requests](#clean-up-unnecessary-requests)
- [Tips](#tips)

---

## Group Requests into Transaction Controllers

A single user action (e.g., clicking "Login") typically triggers multiple HTTP requests - the page, AJAX calls, API calls, etc. Group these related requests into a **Transaction Controller** so they are treated as one unit.

**Before (flat structure):**
```
Thread Group
├── /login (GET)
├── /api/auth/token (POST)
├── /api/user/profile (GET)
├── /dashboard (GET)
├── /api/dashboard/stats (GET)
├── /api/notifications (GET)
```

**After (grouped):**
```
Thread Group
├── A - Login Page
│   ├── 01 - GET - Login Page /login
│   └── 02 - POST - Submit Login /api/auth/token
├── B - Dashboard
│   ├── 03 - GET - Fetch User Profile /api/user/profile
│   ├── 04 - GET - Dashboard Page /dashboard
│   ├── 05 - GET - Fetch Stats /api/dashboard/stats
│   └── 06 - GET - Fetch Notifications /api/notifications
```

**How to identify which requests belong together:**
- Refer to your Fiddler recording - requests that fired together after a single user action belong in one group
- Look at the timing - requests that happened within a short window are usually from the same page/action

**Transaction Controller settings:**
- Uncheck **"Generate parent sample"** - this ensures the report captures all individual requests under the transaction, not just an aggregated parent. You'll see each request separately in the report, which is useful for identifying which specific request within a flow is slow

> **Note:** With "Generate parent sample" unchecked, the `.jtl` file will contain both the TC entry and individual sub-result entries (with `-0`, `-1`, etc. suffixes). These sub-results typically make up ~80-85% of the raw `.jtl` file. Always filter them out before generating reports — see [Section 9](09-execute-analyze.md#filtering-the-jtl-before-generating-reports).

<!-- TODO: Screenshot - Transaction Controller with Generate parent sample unchecked -->
<!-- TODO: Screenshot - Before and after grouping in JMeter tree -->

### Optional: Outer Transaction Controller for User Tracking

When using login-based flows, you can optionally wrap the entire flow in a parent Transaction Controller named `${username}`. Leave **"Generate parent sample" unchecked** - same as all other TCs - so that inner TCs and individual requests still appear in the `.jtl` file.

```
Thread Group
├── TC: ${username}                    ← outer TC, Generate parent sample UNCHECKED
│   ├── A - Login
│   │   ├── 01 - POST - Submit Login
│   │   └── ...
│   ├── B - Dashboard
│   │   └── ...
│   └── C - Search
│       └── ...
```

- The outer TC creates one row per user in the `.jtl` file, making it easy to spot which user failed
- For deeper analysis, match the thread number in the `.jtl` to find the specific request that caused the failure
- Before generating the web report, **always filter the `.jtl`** — this removes sub-results (child samples like `A - Login-0`, `A - Login-1`) which typically make up ~80-85% of the file, plus username rows and unresolved variables. See [Section 9 - Filtering Results](09-execute-analyze.md#filtering-the-jtl-before-generating-reports)

---

## Rename Samplers and Controllers

Blazemeter generates names based on URLs which are hard to read. Rename everything to be meaningful.

**My naming convention:**

| Element | Format | Example |
|---------|--------|---------|
| Transaction Controller | `A-Z - <Action>` | `A - Login`, `B - Dashboard`, `C - Search` |
| HTTP Request (< 100 samplers) | `01 - METHOD - <Description>` | `01 - POST - Submit Login`, `02 - GET - Fetch User Profile` |

- The **letter prefix** (`A`, `B`, `C`, ...) on Transaction Controllers keeps them sorted alphabetically in the report. In the JMeter web report, TCs are sorted below samplers - using A-Z lets you see the grouped actions in flow order
- The **numbered prefix** (`01`, `02`, ...) on samplers keeps them sorted in execution order in the report

**Before:**
```
├── https://app.example.com/api/auth/token
├── https://app.example.com/api/user/profile
```

**After:**
```
├── A - Login
│   ├── 01 - POST - Submit Login /api/auth/token
│   └── 02 - GET - Fetch User Profile /api/user/profile
├── B - Dashboard
│   ├── 03 - GET - Dashboard Page /dashboard
│   └── 04 - GET - Fetch Stats /api/dashboard/stats
```

> **Tip:** Clear, consistent naming pays off when reading reports. `A - Login` in the report is instantly understandable. `/api/auth/token` is not. The letter and number prefixes ensure the report order matches the actual flow.

---

## Add Flow Logic

Use **If Controllers** to validate that critical values were extracted before proceeding. This prevents the script from continuing with bad data and producing misleading results.

### Stop on Extraction Failure

If a critical value (e.g., auth token) was not extracted, stop the thread instead of continuing with garbage requests:

```
TC - Login
├── POST - Submit Login Credentials
│   └── JSON Extractor: authToken
├── If Controller: ${__groovy("${authToken}" != "" && "${authToken}" != "NOT_FOUND")}
│   ├── TC - Dashboard
│   │   ├── GET - Dashboard Page
│   │   └── ...
│   └── TC - Search
│       └── ...
```

**If Controller configuration:**
- **Condition:** `${__groovy("${authToken}" != "" && "${authToken}" != "NOT_FOUND")}`
- Check **"Interpret Condition as Variable Expression"** is **unchecked** when using `__groovy`

If the token extraction fails, the If Controller evaluates to false and skips everything inside it. The thread ends cleanly without sending broken requests.

<!-- TODO: Screenshot - If Controller configuration -->

### Alternative: Stop Thread on Failure

You can also use a JSR223 PostProcessor to stop the thread immediately:

```groovy
if (vars.get("authToken") == null || vars.get("authToken") == "NOT_FOUND") {
    log.error("Auth token extraction failed - stopping thread")
    ctx.getThread().interrupt()
}
```

---

## Add Assertions

Assertions validate that the server response is correct - not just fast. A request might return HTTP 200 but contain an error message in the body.

### Where to Add Assertions

Add assertions to **critical requests** - not every single one. Focus on:
- Login / authentication responses
- Key API responses that return data you depend on
- Responses where you extract values (confirm the response is valid before extracting)

### Common Assertion Patterns

**Response Code check:**
- Response Assertion > Response Code > Equals > `200`

**Response body contains expected value:**
- Response Assertion > Response Body > Contains > `"success": true`

**JSON value check:**
- JSON Assertion > JSON Path: `$.status` > Expected Value: `success`

<!-- TODO: Screenshot - Response Assertion configuration -->
<!-- TODO: Screenshot - JSON Assertion configuration -->

> **Tip:** Don't over-assert. Too many assertions add processing overhead during load tests. Assert on what matters - login success, key data present, no error messages.

---

## Add Timers / Think Time

Without timers, JMeter fires requests as fast as possible. Real users don't behave this way - they read pages, fill forms, think. Timers simulate this.

### Where to Place Timers

Place timers **between Transaction Controllers** (between user actions), not between individual requests within a transaction. Requests within a transaction should fire together like they do in a real browser.

```
Thread Group
├── TC - Login Page
├── Constant Timer (3000ms)          ← user reads the dashboard
├── TC - Dashboard
├── Gaussian Random Timer (2000ms)   ← user decides what to search
├── TC - Search Product
```

### Which Timer to Use

| Timer | Use Case |
|-------|----------|
| **Constant Timer** | Fixed delay - simple and predictable |
| **Gaussian Random Timer** | Randomized delay - more realistic. Set deviation and constant delay offset |
| **Constant Throughput Timer** | When you need to hit a specific TPS target |

### Think Time Values

- Typical think time: **2-5 seconds** between actions
- Depends on the flow - login might have shorter think time, filling a form might be longer
- Ask stakeholders or check analytics if available
- During script development, you can use short timers (1 second) just to verify they work

---

## Clean Up Unnecessary Requests

Based on your requirements (see [Section 2](02-understand-requirements.md)), decide what to keep or remove:

- **Third-party calls** (analytics, tracking, ads) - usually remove unless they are in scope
- **Static resources** (images, CSS, JS) - keep if testing full page load, remove if testing APIs only
- **Duplicate requests** - recording sometimes captures duplicate calls, remove them
- **OPTIONS preflight requests** - usually can be removed unless CORS is being tested

> **Important:** Don't blindly remove static resources. If page load performance is in scope, static resources could be the bottleneck. Always refer back to requirements.

---

## Tips

- **Enhance incrementally** - don't try to do everything at once. Group and rename first, then add logic, then assertions, then timers
- **Run after each change** - run with 1 thread after each enhancement to make sure nothing broke
- **Use consistent naming** - decide on a naming convention early and stick to it across all scripts
- **Transaction Controllers = your report structure** - whatever you name your TCs is what shows up in the final report. Name them from the business perspective
