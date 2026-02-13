# 7. Debug

After enhancing the script with transaction controllers, assertions, extractors, and timers, you need to verify it actually works end-to-end before running any load. Debugging is about running the script with a single user and making sure every request succeeds, every extraction works, and every assertion passes.

## Table of Contents
- [Run with 1 Thread](#run-with-1-thread)
- [View Results Tree](#view-results-tree)
- [Debug Sampler](#debug-sampler)
- [Common Issues and Fixes](#common-issues-and-fixes)
- [Verify the Script is Ready](#verify-the-script-is-ready)
- [Tips](#tips)

---

## Run with 1 Thread

Always debug with a **single thread** (1 user) running **1 loop**. This isolates script issues from load-related issues.

**Thread Group settings for debugging:**
- **Number of Threads:** `1`
- **Ramp-Up Period:** `0`
- **Loop Count:** `1`

Run the test from the **GUI** during debugging - this is one of the few times GUI mode is appropriate. You need the visual feedback from listeners to inspect what's happening.

<!-- TODO: Screenshot - Thread Group configured for debug (1 thread, 1 loop) -->

> **Important:** GUI mode is for debugging only. Never use it for actual load testing - it consumes too much memory and distorts results.

---

## View Results Tree

This is your primary debugging tool. It shows every request and response in detail.

**Add it:** Right-click Thread Group > Add > Listener > **View Results Tree**

### What to Check for Each Request

**Sampler Result tab:**
- **Response code** - should be `200` (or the expected code for that endpoint)
- **Response message** - `OK`, not error messages
- **Load time** - sanity check, not a performance measurement in GUI mode

**Request tab:**
- Verify the **URL** is correct
- Verify **headers** are present (Authorization, Content-Type, etc.)
- Verify the **request body** has the correct data - check that variables like `${token}` are resolved to actual values, not sent as literal `${token}`

**Response Data tab:**
- Verify the response body contains expected data
- If extracting values from this response, confirm the target value is actually present

<!-- TODO: Screenshot - View Results Tree showing a successful request (green) -->
<!-- TODO: Screenshot - View Results Tree showing a failed request (red) -->
<!-- TODO: Screenshot - View Results Tree Request tab showing resolved variables -->
<!-- TODO: Screenshot - View Results Tree Response Data tab -->

### Reading the Colors

| Color | Meaning |
|-------|---------|
| **Green** | Request succeeded and all assertions passed |
| **Red** | Request failed or an assertion failed |

A red entry doesn't always mean the server returned an error. It could mean:
- The request returned `200` but an assertion failed (e.g., response didn't contain expected text)
- The request returned a non-2xx status code
- A connection error occurred

Click on the red entry and check the **Sampler Result** tab for the actual failure reason.

---

## Debug Sampler

The Debug Sampler dumps all JMeter variables at a specific point in the test. This is essential for verifying that extractors captured the correct values.

**Add it:** Right-click on a sampler (after the one with the extractor) > Add > Sampler > **Debug Sampler**

**Debug Sampler settings:**
- **JMeter properties:** `False` (you usually don't need these)
- **JMeter variables:** `True` (this is what you want)
- **System properties:** `False`

Place the Debug Sampler **after the request that extracts a value**. Then look at it in the View Results Tree - the Response Data tab will show all variables and their current values.

```
Thread Group
├── A - Login
│   ├── 01 - POST - Submit Login
│   │   └── JSON Extractor: authToken
│   ├── Debug Sampler              ← check authToken here
│   └── 02 - GET - Fetch Profile
│       └── JSON Extractor: userId
├── Debug Sampler                  ← check userId here
├── B - Dashboard
│   └── ...
```

**What to look for in the Debug Sampler output:**
- Your variable name appears with the correct value: `authToken=eyJhbGciOi...`
- If the variable shows `NOT_FOUND` or is missing entirely, the extraction failed
- Check `variableName_matchNr` - this tells you how many matches the extractor found. `0` means no match

<!-- TODO: Screenshot - Debug Sampler configuration -->
<!-- TODO: Screenshot - Debug Sampler output in View Results Tree showing extracted variables -->

> **Tip:** Remove or disable Debug Samplers before running load tests. They add unnecessary overhead and clutter the results.

---

## Common Issues and Fixes

### Unresolved Variables

**Symptom:** Request body or URL contains literal `${variableName}` instead of the actual value.

**Cause:** The variable was never set - either the extractor didn't run, didn't match, or is scoped incorrectly.

**Fix:**
1. Check the extractor is attached to the correct request (the one whose response contains the value)
2. Check the extractor configuration - JSON path, regex, or CSS selector might be wrong
3. Check the **scope** - an extractor under a sampler only applies to that sampler's response. If the variable needs to be available to later requests, make sure it's in the right place in the hierarchy
4. Run the Debug Sampler after the extractor to see what value (if any) was captured

### Assertion Failures on Valid Responses

**Symptom:** Request shows red in View Results Tree but the response looks correct.

**Cause:** The assertion is too strict or checking the wrong thing.

**Fix:**
1. Click the red entry and check the **Assertion Result** section in the Sampler Result tab
2. Common mistakes:
   - Checking for exact text that varies (e.g., timestamp in the response)
   - Wrong JSON path in JSON Assertion
   - Response Assertion checking Response Body when the value is in the headers
3. Adjust the assertion to match what the server actually returns

### Authentication Failures Partway Through the Script

**Symptom:** First few requests succeed, then subsequent requests fail with `401` or `403`.

**Cause:** Token extraction failed or the token expired between requests.

**Fix:**
1. Use Debug Sampler to verify the token was extracted correctly
2. Check that the `Authorization` header in subsequent requests uses `${token}` and not a hardcoded value from the recording
3. Check that `HTTP Header Manager` with the token is scoped correctly - it should be at Thread Group level or under a controller that covers all requests needing it
4. If using cookies, check that **HTTP Cookie Manager** is present at the Thread Group level

### Redirect Issues

**Symptom:** Getting `302` responses or unexpected HTML instead of the expected API response.

**Cause:** JMeter follows redirects by default. The extractor might be running on the original response, not the final redirected response.

**Fix:**
1. Check **"Follow Redirects"** and **"Redirect Automatically"** settings on the HTTP Request sampler
2. If you need to extract from the redirect response, you may need to uncheck "Follow Redirects" and handle the redirect manually
3. Check if the redirect URL is different from what was recorded (e.g., environment-specific URL)

### Encoding Issues

**Symptom:** Special characters in request bodies appear garbled, or the server rejects the request.

**Cause:** Character encoding mismatch - the request is not sending UTF-8 or the expected encoding.

**Fix:**
1. Check the `Content-Type` header includes charset: `Content-Type: application/json; charset=UTF-8`
2. In the HTTP Request sampler, check the **"Content encoding"** field
3. If sending form data, make sure URL-encoded values are properly encoded

---

## Verify the Script is Ready

Before moving to load testing, go through this checklist:

| Check | How to Verify |
|-------|---------------|
| All requests are green | Run with 1 thread and check View Results Tree - no red entries |
| Variables are resolved | Debug Samplers show correct values, no `${literal}` in requests |
| Assertions pass | No assertion failures in the results |
| Flow completes end-to-end | The last request in the script executes successfully |
| Multiple users work | Run with 2-3 threads to verify CSV parameterization and concurrency |
| No hardcoded dynamic values | Search the `.jmx` for any remaining hardcoded tokens, session IDs, or timestamps from the recording |
| Debug elements removed/disabled | Remove or disable Debug Samplers and View Results Tree before load testing |

### Quick Multi-User Validation

After the single-thread run passes, bump it to **2-3 threads** with your CSV data:
- Verify each thread picks up a different row from the CSV
- Verify there are no conflicts between threads (e.g., shared state issues)
- This catches parameterization mistakes before you scale to full load

---

## Tips

- **Debug one issue at a time** - fix the first red request, run again, fix the next one. Don't try to fix everything at once
- **Use the Debug Sampler liberally during development** - add them after every extractor until the flow works, then remove them
- **Save the Fiddler session** - having the original `.saz` file open while debugging lets you compare what the real browser sent vs what JMeter is sending
- **Check the JMeter log** - if something fails silently, look at `jmeter.log` in the `bin/` folder (or the log panel at the bottom of the GUI). Groovy errors, plugin issues, and file-not-found errors often show up here
- **Compare against Fiddler** - if a request fails in JMeter but worked during recording, open the Fiddler `.saz` and compare headers, cookies, and body side by side. The difference is usually the cause
