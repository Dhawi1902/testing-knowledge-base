# 4. Recording

This section covers how to record your test script using both Fiddler and Blazemeter simultaneously. This dual-recording approach gives you the best of both tools.


## Why Record from Both?

| Tool | What it gives you |
|------|-------------------|
| **Blazemeter** | A `.jmx` file with all endpoints structured and ready to open in JMeter |
| **Fiddler** | A detailed view of every request and response - essential for finding where dynamic values come from during correlation |

By recording the **same session** in both tools at the same time, the captured data matches. When you need to correlate a dynamic value (e.g., token, session ID), you can trace it in Fiddler's response and then apply the extraction in JMeter.

---

## Before You Start

1. Make sure all tools are set up and configured (see [Section 1 - Install Tools](01-install-tools.md))
2. Know the user flow you are going to record (see [Section 2 - Understand Requirements](02-understand-requirements.md))
3. Have test credentials and test data ready
4. Close unnecessary browser tabs and applications to reduce noise

---

## Steps

### 1. Start Fiddler
- Open Fiddler
- **Disable** Capture Traffic (File > Capture Traffic, or press F12) - this prevents Fiddler from capturing all system traffic. Requests coming through the proxy will still be captured

- Clear any existing traffic (Edit > Remove > All Sessions, or Ctrl+X)

### 2. Launch Chrome Through Fiddler Proxy
```
chrome.exe --proxy-server="http=127.0.0.1:8888;https=127.0.0.1:8888"
```
> **Note:** If `chrome.exe` is not in your PATH, use the full path:
> ```
> "C:\Program Files\Google\Chrome\Application\chrome.exe" --proxy-server="http=127.0.0.1:8888;https=127.0.0.1:8888"
> ```

### 3. Start Blazemeter Recording
- Click the Blazemeter extension icon in Chrome
- Give your test a name (e.g., "Login Flow")
- Click the **record** button (red circle)

### 4. Perform the User Flow
- Navigate through the application as a real user would
- Follow the flow you identified in the requirements
- Take your time - don't rush. The think times will be replaced later anyway

### 5. Stop Recording
- Click the **stop** button in Blazemeter (square icon)

- Fiddler doesn't need to be stopped since Capture Traffic was already disabled - it only captured proxy traffic

### 6. Export from Blazemeter
- Click the `.jmx` export button in Blazemeter
- Save the file to your working directory

### 7. Save Fiddler Session
- Save the Fiddler session for reference: File > Save > All Sessions (`.saz` file)
- You'll use this during correlation in the next step

---

## Open the Recording in JMeter

1. Open JMeter
2. File > Open > select the `.jmx` file exported from Blazemeter
3. You should see all the recorded requests under a Thread Group

At this point, the script is raw - it has all the endpoints but:
- Names are auto-generated (not meaningful)
- Dynamic values are hardcoded (needs correlation)
- No parameterization
- No assertions or timers

These will be addressed in the next sections.

<!-- TODO: Screenshot - Blazemeter recording in progress -->
<!-- TODO: Screenshot - Blazemeter export to JMX -->
<!-- TODO: Screenshot - Fiddler with recorded session showing request/response -->
<!-- TODO: Screenshot - Raw JMX opened in JMeter -->

---

## Tips

- **Record once, use everywhere** - a good recording is the foundation. Take time to do it right

- **Save the Fiddler `.saz` file** - you'll keep going back to it during correlation

- **Don't worry about the messy script** - cleanup happens in steps 5 and 6 (correlation and script enhancement)

- **If something goes wrong during recording** - just redo it. It's faster to re-record than to fix a bad recording
