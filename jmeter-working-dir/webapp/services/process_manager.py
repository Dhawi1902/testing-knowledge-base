import asyncio
import re
import subprocess
from pathlib import Path

# Regex to parse JMeter summary lines (both "summary +" and "summary =")
# Example: summary =  10000 in 00:01:40 =  100.0/s Avg:   148 Min:     5 Max:  2400 Err:    45 (0.45%)
_SUMMARY_RE = re.compile(
    r"summary\s+[+=]\s+(\d+)\s+in\s+\S+\s+=\s+([\d.]+)/s\s+"
    r"Avg:\s+(\d+)\s+Min:\s+(\d+)\s+Max:\s+(\d+)\s+"
    r"Err:\s+(\d+)\s+\(([\d.]+)%\)"
)


class ProcessManager:
    """Manages subprocesses with output buffering and streaming.

    Output is drained into a buffer by a background task, so:
    - Multiple WebSocket clients can connect/reconnect without losing history
    - The process stdout is always consumed (never blocks)
    - Buffer persists until the next start() call
    """

    def __init__(self):
        self._active_process: subprocess.Popen | None = None
        self._active_label: str = ""
        self._post_commands: list[list[str]] = []
        self._cwd: str | None = None
        self._lock = asyncio.Lock()
        self._output_buffer: list[str] = []
        self._drain_task: asyncio.Task | None = None
        self._run_info: dict = {}
        self._post_processing: bool = False
        self._live_stats: dict = {}

    @property
    def is_running(self) -> bool:
        return self._active_process is not None and self._active_process.poll() is None

    @property
    def is_post_processing(self) -> bool:
        """True after the main process exits but post-commands are still running."""
        return self._post_processing

    @property
    def active_label(self) -> str:
        return self._active_label if self.is_running or self._post_processing else ""

    @property
    def output_buffer(self) -> list[str]:
        """Returns a copy of all buffered output lines."""
        return list(self._output_buffer)

    @property
    def run_info(self) -> dict:
        """Metadata about the current/last run."""
        return dict(self._run_info)

    @property
    def live_stats(self) -> dict:
        """Latest parsed JMeter summary stats (throughput, avg RT, etc.)."""
        return dict(self._live_stats)

    @property
    def is_draining(self) -> bool:
        """True if the background drain task is still running."""
        return self._drain_task is not None and not self._drain_task.done()

    def start(self, cmd: list[str], cwd: str | Path | None = None, label: str = "",
              post_commands: list[list[str]] | None = None,
              run_info: dict | None = None) -> subprocess.Popen:
        """Start a subprocess. Raises if one is already running."""
        if self.is_running:
            raise RuntimeError(f"A process is already running: {self._active_label}")
        self._cwd = str(cwd) if cwd else None
        self._post_commands = post_commands or []
        self._run_info = run_info or {}
        self._output_buffer = []
        self._post_processing = False
        self._live_stats = {}
        self._active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=self._cwd,
            text=True,
            bufsize=1,
        )
        self._active_label = label
        # Start background drain task
        loop = asyncio.get_running_loop()
        self._drain_task = loop.create_task(self._drain_output())
        return self._active_process

    def _parse_summary_line(self, line: str) -> None:
        """Parse JMeter summary lines and update _live_stats."""
        m = _SUMMARY_RE.search(line)
        if not m:
            return
        # Only update from cumulative "summary =" lines
        if "summary =" not in line:
            return
        self._live_stats = {
            "total_samples": int(m.group(1)),
            "throughput": float(m.group(2)),
            "avg": int(m.group(3)),
            "min": int(m.group(4)),
            "max": int(m.group(5)),
            "error_count": int(m.group(6)),
            "error_pct": float(m.group(7)),
        }

    async def _drain_output(self):
        """Background task: reads process stdout and post-commands into buffer."""
        proc = self._active_process
        if not proc or not proc.stdout:
            return
        loop = asyncio.get_running_loop()
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            stripped = line.rstrip("\n")
            self._output_buffer.append(stripped)
            self._parse_summary_line(stripped)
        await loop.run_in_executor(None, proc.wait)

        # Enter post-processing state
        self._post_processing = True

        # Run post-commands sequentially (with timeout matching regeneration: 600s)
        for post_cmd in self._post_commands:
            self._output_buffer.append(f"\n--- Running: {' '.join(post_cmd)} ---")
            try:
                post_proc = subprocess.Popen(
                    post_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=self._cwd,
                    text=True,
                    bufsize=1,
                )
                while True:
                    line = await loop.run_in_executor(None, post_proc.stdout.readline)
                    if not line:
                        break
                    self._output_buffer.append(line.rstrip("\n"))
                try:
                    post_proc.wait(timeout=600)
                except subprocess.TimeoutExpired:
                    post_proc.kill()
                    post_proc.wait()
                    self._output_buffer.append("--- Timed out (10 min limit) ---")
                    continue
                self._output_buffer.append(f"--- Finished (exit code {post_proc.returncode}) ---")
            except Exception as e:
                self._output_buffer.append(f"--- Error: {e} ---")

        # Post-process: remove disabled graph panels from report HTML
        result_dir = self._run_info.get("result_dir")
        if result_dir:
            result_path = Path(result_dir)
            try:
                from services.report_properties import cleanup_report_html
                report_path = result_path / "report"
                if report_path.is_dir():
                    cleanup_report_html(report_path)
                    self._output_buffer.append("--- Cleaned up disabled graph panels from report HTML ---")
            except Exception as e:
                self._output_buffer.append(f"--- Report HTML cleanup error: {e} ---")

        # Exit post-processing state
        self._post_processing = False

    async def subscribe_output(self, start_index: int = 0):
        """Async generator: yields buffered lines from start_index, then tails new ones until drain completes."""
        idx = start_index
        while True:
            # Yield all available buffered lines
            while idx < len(self._output_buffer):
                yield self._output_buffer[idx]
                idx += 1
            # If drain is done, yield any final lines and exit
            if not self.is_draining:
                while idx < len(self._output_buffer):
                    yield self._output_buffer[idx]
                    idx += 1
                break
            await asyncio.sleep(0.1)

    async def stream_output(self):
        """Backward-compatible wrapper: yields all output from the start."""
        async for line in self.subscribe_output(0):
            yield line

    def stop(self):
        """Terminate the active process."""
        if self._active_process and self._active_process.poll() is None:
            try:
                self._active_process.terminate()
                try:
                    self._active_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._active_process.kill()
            except OSError:
                pass
        self._active_process = None
        self._active_label = ""
        self._post_processing = False

    def return_code(self) -> int | None:
        if self._active_process:
            return self._active_process.poll()
        return None


# Singleton for JMeter test execution
jmeter_process_manager = ProcessManager()

# Separate manager for scripts
script_process_manager = ProcessManager()
