import time
import threading

import pytest

import plugins.services.service_technique_worker_pool as pool_mod
import plugins.frontends.frontend_web as web_mod
from plugins.frontends.frontend_web import _VideoFrameError, _missing_video_frames, _render_video_frames, _video_worker_count


def _svc(monkeypatch, *, cpu=8, budget=1000):
    monkeypatch.setattr(pool_mod.os, "cpu_count", lambda: cpu)
    monkeypatch.setattr(pool_mod, "psutil", None)
    return pool_mod.TechniqueWorkerPoolService({
        "technique_worker_memory_budget_mb": budget,
        "technique_worker_queue_timeout_s": 0.01,
    })


def test_memory_gate_admits_small_jobs_within_budget(monkeypatch):
    svc = _svc(monkeypatch, cpu=4, budget=1000)
    a = svc._claim_slot(200, time.monotonic() + 0.05)
    b = svc._claim_slot(200, time.monotonic() + 0.05)
    assert svc._active == 2
    assert svc._reserved_mb == pytest.approx(a + b)
    svc._release_slot(a)
    svc._release_slot(b)
    assert svc._active == 0


def test_memory_gate_blocks_over_budget_job(monkeypatch):
    svc = _svc(monkeypatch, cpu=4, budget=500)
    first = svc._claim_slot(300, time.monotonic() + 0.05)
    with pytest.raises(pool_mod.TechniqueWorkerBusy):
        svc._claim_slot(300, time.monotonic() + 0.01)
    svc._release_slot(first)


def test_memory_observation_updates_rolling_estimate(monkeypatch):
    svc = _svc(monkeypatch)
    svc._observe_job(500, 200 * 1024 * 1024, 0.2)
    assert svc._estimate_mb == pytest.approx(200)
    svc._observe_job(500, 400 * 1024 * 1024, 0.2)
    assert svc._estimate_mb == pytest.approx(400)


def test_cpu_cap_limits_concurrency_even_with_ram(monkeypatch):
    svc = _svc(monkeypatch, cpu=3, budget=10000)
    slots = [svc._claim_slot(50, time.monotonic() + 0.05) for _ in range(2)]
    with pytest.raises(pool_mod.TechniqueWorkerBusy):
        svc._claim_slot(50, time.monotonic() + 0.01)
    for slot in slots:
        svc._release_slot(slot)


def test_min_idle_is_automatic_from_cpu_capacity(monkeypatch):
    assert _svc(monkeypatch, cpu=1).min_idle == 0
    assert _svc(monkeypatch, cpu=4).min_idle == 1


def test_video_worker_count_is_pool_or_cpu_derived(monkeypatch):
    class Pool:
        active_limit = 12

    monkeypatch.setattr(web_mod.os, "cpu_count", lambda: 10)
    assert _video_worker_count(30, Pool()) == 12
    assert _video_worker_count(30, None) == 9


def test_video_missing_frames_are_rejected(tmp_path):
    good = tmp_path / "frame.png"
    good.write_bytes(b"ok")
    assert _missing_video_frames([good, None, tmp_path / "gone.png"]) == [2, 3]


def test_video_frame_failure_cancels_unsubmitted_frames(tmp_path):
    seen = []
    cancel = threading.Event()
    frame_paths = [None] * 5

    def render_one(i):
        seen.append(i)
        if i == 0:
            raise RuntimeError("boom")
        while not cancel.wait(0.01):
            pass
        raise RuntimeError("cancelled")

    with pytest.raises(_VideoFrameError):
        _render_video_frames(5, 2, render_one, cancel, frame_paths, lambda _n: None)

    assert cancel.is_set()
    assert 0 in seen
    assert set(seen) <= {0, 1}
