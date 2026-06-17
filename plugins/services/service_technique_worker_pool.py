"""Warm disposable subprocess pool for canvas technique execution."""

from __future__ import annotations

import logging
import os
import queue
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from pathlib import Path

try:
    import psutil
except ImportError:
    psutil = None

from plugins.BaseService import BaseService

logger = logging.getLogger("TechniqueWorkerPool")
READY_TIMEOUT_S = 8.0


class TechniqueWorkerBusy(RuntimeError):
    """Raised when all warm technique workers are occupied too long."""


class TechniqueWorkerJobTimeout(RuntimeError):
    """Raised when a worker job exceeds the per-technique timeout."""


@dataclass
class TechniqueWorkerResult:
    returncode: int
    stdout: bytes
    stderr: bytes
    memory_killed: bool = False
    peak_bytes: int = 0
    duration_s: float = 0.0


class TechniqueWorkerPoolService(BaseService):
    model_name = "technique_worker_pool"
    shared = True
    config_settings = [
        ("Technique Worker Memory Budget (MB)", "technique_worker_memory_budget_mb", "RAM budget for active technique sandbox processes.", 4096, {"type": "integer"}),
        ("Technique Worker Queue Timeout (s)", "technique_worker_queue_timeout_s", "Seconds a render waits for a technique worker before failing busy.", 10, {"type": "integer"}),
    ]

    def __init__(self, config: dict):
        super().__init__()
        self.cpu_limit = max(1, (os.cpu_count() or 1) - 1)
        self.max_workers = self.cpu_limit
        self.min_idle = 1 if self.max_workers > 1 else 0
        self.queue_timeout_s = max(0.1, float(config.get("technique_worker_queue_timeout_s", 10)))
        self.memory_budget_mb = max(128.0, float(config.get("technique_worker_memory_budget_mb", 4096)))
        self.active_limit = self.cpu_limit
        self._idle: queue.Queue[subprocess.Popen] = queue.Queue()
        self._lock = threading.Lock()
        self._gate = threading.Condition(self._lock)
        self._all: set[subprocess.Popen] = set()
        self._active = 0
        self._reserved_mb = 0.0
        self._estimate_mb = 0.0
        self._warming = 0
        self._stopping = False
        self._entry, self._env, self._cwd = self._worker_context()

    def _load(self) -> bool:
        self._stopping = False
        self._loaded = True
        self._ensure_idle()
        return True

    def unload(self):
        with self._lock:
            self._stopping = True
            procs = list(self._all)
            while True:
                try: procs.append(self._idle.get_nowait())
                except queue.Empty: break
        for proc in procs:
            self._kill(proc)
        with self._lock:
            self._all.clear()
        self._loaded = False

    def run_job(self, *, job_path: str, timeout_s: float, memory_mb: int) -> TechniqueWorkerResult:
        if not self.loaded:
            raise TechniqueWorkerBusy("technique worker pool is not loaded")
        deadline = time.monotonic() + self.queue_timeout_s
        reserve_mb = self._claim_slot(memory_mb, deadline)
        proc = None
        try:
            proc = self._take_idle(deadline)
            self._ensure_idle()
            result = self._run_checked_out(proc, job_path, timeout_s, memory_mb)
            self._observe_job(memory_mb, result.peak_bytes, result.duration_s)
            return result
        finally:
            if proc is not None:
                self._forget(proc)
            self._release_slot(reserve_mb)
            self._ensure_idle()

    def _claim_slot(self, memory_mb: int, deadline: float) -> float:
        reserve_mb = self._reserve_mb(memory_mb)
        with self._gate:
            while not self._can_start(reserve_mb):
                timeout = max(0.0, deadline - time.monotonic())
                if timeout <= 0 or not self._gate.wait(timeout):
                    raise TechniqueWorkerBusy("renderer busy; retry shortly")
            self._active += 1
            self._reserved_mb += reserve_mb
            return reserve_mb

    def _release_slot(self, reserve_mb: float) -> None:
        with self._gate:
            self._active = max(0, self._active - 1)
            self._reserved_mb = max(0.0, self._reserved_mb - reserve_mb)
            self._gate.notify_all()

    def _can_start(self, reserve_mb: float) -> bool:
        if self._active >= self.cpu_limit:
            return False
        budget = self._effective_budget_mb()
        return self._active == 0 or self._reserved_mb + reserve_mb <= budget

    def _reserve_mb(self, memory_mb: int) -> float:
        base = self._estimate_mb or max(64.0, float(memory_mb))
        return min(max(64.0, base * 1.25), self._effective_budget_mb())

    def _observe_job(self, memory_mb: int, peak_bytes: int, duration_s: float) -> None:
        if peak_bytes <= 0:
            return
        peak_mb = peak_bytes / (1024 * 1024)
        with self._lock:
            floor = max(64.0, min(float(memory_mb), peak_mb))
            self._estimate_mb = max((self._estimate_mb or floor) * 0.8 + peak_mb * 0.2, floor)
        logger.debug("technique worker job peak=%.0fMB estimate=%.0fMB duration=%.2fs", peak_mb, self._estimate_mb, duration_s)

    def _effective_budget_mb(self) -> float:
        budget = self.memory_budget_mb
        if psutil is not None:
            try:
                budget = min(budget, psutil.virtual_memory().available / (1024 * 1024))
            except Exception:
                pass
        return max(64.0, budget * 0.85)

    def _take_idle(self, deadline: float):
        self._ensure_idle()
        timeout = max(0.0, deadline - time.monotonic())
        try:
            return self._idle.get(timeout=timeout)
        except queue.Empty:
            raise TechniqueWorkerBusy("renderer busy; no warm technique worker became ready")

    def _ensure_idle(self):
        if not self.loaded:
            return
        with self._lock:
            while (
                not self._stopping
                and self._idle.qsize() + self._warming < self.min_idle + self._active
                and self._active + self._idle.qsize() + self._warming < self.max_workers
            ):
                self._warming += 1
                threading.Thread(target=self._warm_one, daemon=True, name="technique-worker-warm").start()

    def _warm_one(self):
        proc = None
        try:
            proc = subprocess.Popen(
                [sys.executable, "-I", "-B", str(self._entry), "--worker"],
                stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                env=self._env, cwd=self._cwd,
            )
            with self._lock:
                self._all.add(proc)
            line = self._readline_timeout(proc, READY_TIMEOUT_S)
            if line.strip() != b"READY":
                raise RuntimeError(f"worker did not become ready: {line!r}")
            with self._lock:
                if self._stopping:
                    raise RuntimeError("pool stopping")
            self._idle.put(proc)
            proc = None
        except Exception as e:
            logger.debug("technique worker warm failed: %s", e)
            if proc is not None:
                self._kill(proc)
        finally:
            with self._lock:
                self._warming = max(0, self._warming - 1)
            self._ensure_idle()

    def _run_checked_out(self, proc, job_path: str, timeout_s: float, memory_mb: int) -> TechniqueWorkerResult:
        stop = threading.Event()
        mem = {"killed": False, "peak": 0}
        wd = self._watch_memory(proc, max(64, int(memory_mb)) * 1024 * 1024, stop, mem)
        t0 = time.time()
        try:
            try:
                stdout, stderr = proc.communicate(input=(job_path + "\n").encode("utf-8"), timeout=timeout_s)
            except subprocess.TimeoutExpired:
                self._kill(proc)
                raise TechniqueWorkerJobTimeout(f"exceeded {timeout_s:.0f}s timeout")
        finally:
            stop.set()
            if wd is not None:
                wd.join(timeout=1.0)
        return TechniqueWorkerResult(proc.returncode, stdout or b"", stderr or b"", mem["killed"], mem["peak"], time.time() - t0)

    def _watch_memory(self, proc, cap: int, stop: threading.Event, mem: dict):
        if psutil is None:
            return None
        def run():
            try: p = psutil.Process(proc.pid)
            except psutil.Error: return
            while not stop.wait(0.2):
                try:
                    rss = p.memory_info().rss + sum((c.memory_info().rss for c in p.children(recursive=True)), 0)
                except psutil.Error:
                    return
                mem["peak"] = max(mem["peak"], rss)
                if rss > cap:
                    mem["killed"] = True
                    self._kill(proc)
                    return
        t = threading.Thread(target=run, daemon=True, name=f"technique-worker-mem-{proc.pid}")
        t.start()
        return t

    def _readline_timeout(self, proc, timeout: float) -> bytes:
        out: queue.Queue[bytes] = queue.Queue(maxsize=1)
        threading.Thread(target=lambda: out.put(proc.stdout.readline() if proc.stdout else b""), daemon=True).start()
        try:
            return out.get(timeout=timeout)
        except queue.Empty:
            self._kill(proc)
            return b""

    def _forget(self, proc):
        with self._lock:
            self._all.discard(proc)

    def _kill(self, proc):
        try:
            if proc.poll() is None:
                proc.kill()
        except OSError:
            pass
        try:
            proc.wait(timeout=1.0)
        except Exception:
            pass

    def _worker_context(self):
        root = Path(__file__).resolve().parents[2]
        entry = root / "plugins" / "techniques" / "helpers" / "technique_sandbox_entry.py"
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONPATH"] = str(root) + (os.pathsep + env["PYTHONPATH"] if "PYTHONPATH" in env else "")
        return entry, env, str(root)


def build_services(config: dict) -> dict:
    return {"technique_worker_pool": TechniqueWorkerPoolService(config or {})}
