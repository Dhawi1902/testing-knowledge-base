import asyncio
import subprocess
import signal
from pathlib import Path


class ProcessManager:
    """Manages subprocesses with output streaming. Only one JMeter test at a time."""

    def __init__(self):
        self._active_process: subprocess.Popen | None = None
        self._active_label: str = ""
        self._lock = asyncio.Lock()

    @property
    def is_running(self) -> bool:
        return self._active_process is not None and self._active_process.poll() is None

    @property
    def active_label(self) -> str:
        return self._active_label if self.is_running else ""

    def start(self, cmd: list[str], cwd: str | Path | None = None, label: str = "") -> subprocess.Popen:
        """Start a subprocess. Raises if one is already running."""
        if self.is_running:
            raise RuntimeError(f"A process is already running: {self._active_label}")
        self._active_process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            cwd=str(cwd) if cwd else None,
            text=True,
            bufsize=1,
        )
        self._active_label = label
        return self._active_process

    async def stream_output(self):
        """Async generator yielding stdout lines from the active process."""
        proc = self._active_process
        if not proc or not proc.stdout:
            return
        loop = asyncio.get_event_loop()
        while True:
            line = await loop.run_in_executor(None, proc.stdout.readline)
            if not line:
                break
            yield line.rstrip("\n")
        proc.wait()

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

    def return_code(self) -> int | None:
        if self._active_process:
            return self._active_process.poll()
        return None


# Singleton for JMeter test execution
jmeter_process_manager = ProcessManager()

# Separate manager for scripts
script_process_manager = ProcessManager()
