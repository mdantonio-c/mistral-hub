"""Flag-gated phase instrumentation for observed-data extraction (issue 852).

Recording happens only when PERF_INSTRUMENTATION=1 and the request user id is in
PERF_BENCH_USERS; otherwise every function here is a cheap no-op.
Records are written to PERF_DIR as <request_id>.api.json (backend) and
<request_id>.task.json (celery worker) and exposed by endpoints/perf.py.
"""

import contextvars
import json
import os
import resource
import socket
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional

from restapi.env import Env
from restapi.utilities.logs import log

ENABLED = Env.get_bool("PERF_INSTRUMENTATION")
FAKE_NOW_ENABLED = Env.get_bool("PERF_FAKE_NOW")
BENCH_QUEUE = Env.get("PERF_BENCH_QUEUE", "").strip()
BENCH_USERS = {
    int(u) for u in Env.get("PERF_BENCH_USERS", "").split(",") if u.strip().isdigit()
}
PERF_DIR = Path("/logs/perf")
SCHEMA_VERSION = 1
PEAK_RSS_METHOD = "VmHWM after writing 5 to /proc/self/clear_refs at task start"

_current: contextvars.ContextVar = contextvars.ContextVar("perf_recorder", default=None)


def is_bench_user(user_id: Optional[int]) -> bool:
    return ENABLED and user_id in BENCH_USERS


def bench_queue(user_id: Optional[int]) -> Optional[str]:
    """Dedicated celery queue for benchmark users (D-04), None if not applicable."""
    if BENCH_QUEUE and is_bench_user(user_id):
        return BENCH_QUEUE
    return None


def fake_now(user_id: Optional[int], value: Any) -> Optional[datetime]:
    """Per-request fake "now" (D-10) as naive UTC, honoured only for benchmark users."""
    if value is None or not FAKE_NOW_ENABLED or user_id not in BENCH_USERS:
        return None
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if value.tzinfo is not None:
        value = value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


def _read_proc(path: str) -> Dict[str, int]:
    values = {}
    try:
        with open(path) as f:
            for line in f:
                key, _, rest = line.partition(":")
                parts = rest.split()
                if parts and parts[0].isdigit():
                    values[key] = int(parts[0])
    except OSError:
        pass
    return values


def _snapshot() -> Dict[str, float]:
    ru_self = resource.getrusage(resource.RUSAGE_SELF)
    ru_children = resource.getrusage(resource.RUSAGE_CHILDREN)
    io = _read_proc("/proc/self/io")
    status = _read_proc("/proc/self/status")
    return {
        "t": time.perf_counter(),
        "cpu_user": ru_self.ru_utime,
        "cpu_sys": ru_self.ru_stime,
        "cpu_children": ru_children.ru_utime + ru_children.ru_stime,
        "read_bytes": io.get("read_bytes", 0),
        "write_bytes": io.get("write_bytes", 0),
        "rchar": io.get("rchar", 0),
        "wchar": io.get("wchar", 0),
        "rss_kb": status.get("VmRSS", 0),
    }


def _delta(start: Dict[str, float], end: Dict[str, float]) -> Dict[str, Any]:
    return {
        "wall_s": round(end["t"] - start["t"], 6),
        "cpu_user_s": round(end["cpu_user"] - start["cpu_user"], 6),
        "cpu_sys_s": round(end["cpu_sys"] - start["cpu_sys"], 6),
        "cpu_children_s": round(end["cpu_children"] - start["cpu_children"], 6),
        "io_read_bytes": end["read_bytes"] - start["read_bytes"],
        "io_write_bytes": end["write_bytes"] - start["write_bytes"],
        "io_rchar": end["rchar"] - start["rchar"],
        "io_wchar": end["wchar"] - start["wchar"],
        "rss_start_mb": round(start["rss_kb"] / 1024, 1),
        "rss_end_mb": round(end["rss_kb"] / 1024, 1),
    }


class Phase:
    def __init__(self, recorder: "Recorder", name: str) -> None:
        t0 = time.perf_counter()
        self.recorder = recorder
        self.name = name
        self.parent = recorder.open[-1].name if recorder.open else None
        self.counters: Dict[str, Any] = {}
        recorder.open.append(self)
        self.start = _snapshot()
        recorder.overhead_s += time.perf_counter() - t0

    def end(
        self, error: bool = False, incomplete: bool = False, **counters: Any
    ) -> None:
        t0 = time.perf_counter()
        rec = self.recorder
        if self not in rec.open:
            return
        rec.open.remove(self)
        self.counters.update(counters)
        item: Dict[str, Any] = {"name": self.name, "parent": self.parent}
        item.update(_delta(self.start, _snapshot()))
        item["counters"] = self.counters
        if error:
            item["error"] = True
        if incomplete:
            item["incomplete"] = True
        rec.phases.append(item)
        rec.overhead_s += time.perf_counter() - t0


class _NoopPhase:
    counters: Dict[str, Any] = {}

    def end(
        self, error: bool = False, incomplete: bool = False, **counters: Any
    ) -> None:
        pass


_NOOP = _NoopPhase()


class Recorder:
    def __init__(
        self,
        side: str,
        user_id: int,
        request_id: Optional[int],
        task_id: Optional[str],
        reset_peak: bool,
    ) -> None:
        self.side = side
        self.user_id = user_id
        self.request_id = request_id
        self.task_id = task_id
        self.started_at = datetime.utcnow()
        self.labels: Dict[str, Any] = {}
        self.phases: List[Dict[str, Any]] = []
        self.open: List[Phase] = []
        self.overhead_s = 0.0
        self.peak_reset = False
        if reset_peak:
            try:
                with open("/proc/self/clear_refs", "w") as f:
                    f.write("5")
                self.peak_reset = True
            except OSError:
                pass
        self.start = _snapshot()

    def to_dict(self) -> Dict[str, Any]:
        for p in list(reversed(self.open)):
            p.end(incomplete=True)
        end = _snapshot()
        record: Dict[str, Any] = {
            "schema": SCHEMA_VERSION,
            "side": self.side,
            "request_id": self.request_id,
            "task_id": self.task_id,
            "user_id": self.user_id,
            "host": socket.gethostname(),
            "pid": os.getpid(),
            "started_at": self.started_at.isoformat() + "Z",
            "ended_at": datetime.utcnow().isoformat() + "Z",
        }
        record.update(_delta(self.start, end))
        if self.side == "task":
            hwm_kb = _read_proc("/proc/self/status").get("VmHWM", 0)
            record["peak_rss_mb"] = round(hwm_kb / 1024, 1)
            record["peak_rss_method"] = (
                PEAK_RSS_METHOD if self.peak_reset else "VmHWM (process lifetime)"
            )
        record["labels"] = self.labels
        submission = self.labels.get("submission_date")
        if submission:
            record["queue_wait_s"] = round(
                (self.started_at - datetime.fromisoformat(submission)).total_seconds(),
                3,
            )
        record["phases"] = self.phases
        record["overhead_s"] = round(self.overhead_s, 6)
        return record


def start(
    side: str,
    user_id: Optional[int],
    request_id: Optional[int] = None,
    task_id: Optional[str] = None,
    reset_peak: bool = False,
) -> Optional[Recorder]:
    """Start a recorder for the current request/task; always resets the previous one."""
    rec = None
    if is_bench_user(user_id):
        rec = Recorder(side, user_id, request_id, task_id, reset_peak)
    _current.set(rec)
    return rec


def active() -> bool:
    return _current.get() is not None


def begin(name: str):
    rec = _current.get()
    if rec is None:
        return _NOOP
    return Phase(rec, name)


@contextmanager
def phase(name: str) -> Iterator[Dict[str, Any]]:
    rec = _current.get()
    if rec is None:
        yield {}
        return
    p = Phase(rec, name)
    try:
        yield p.counters
    except BaseException:
        p.end(error=True)
        raise
    p.end()


def label(**labels: Any) -> None:
    rec = _current.get()
    if rec is not None:
        rec.labels.update(labels)


def finish(**ids: Any) -> None:
    """Write the record (if any) and detach the recorder. Never raises."""
    rec = _current.get()
    _current.set(None)
    if rec is None:
        return
    try:
        if "request_id" in ids:
            rec.request_id = ids["request_id"]
        if "task_id" in ids:
            rec.task_id = ids["task_id"]
        if rec.request_id is None:
            return
        PERF_DIR.mkdir(parents=True, exist_ok=True)
        path = PERF_DIR.joinpath(f"{rec.request_id}.{rec.side}.json")
        tmp = path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(rec.to_dict(), default=str))
        tmp.replace(path)
    except Exception as exc:  # instrumentation must never break an extraction
        log.warning("perf: unable to write record: {}", exc)


def can_read(caller_id: int, owner_id: int, caller_is_admin: bool) -> bool:
    if caller_is_admin:
        return True
    return caller_id == owner_id and caller_id in BENCH_USERS


def read_record(request_id: int) -> Optional[Dict[str, Any]]:
    record: Dict[str, Any] = {"request_id": request_id}
    found = False
    for side in ("api", "task"):
        path = PERF_DIR.joinpath(f"{request_id}.{side}.json")
        if path.is_file():
            record[side] = json.loads(path.read_text())
            found = True
    return record if found else None
