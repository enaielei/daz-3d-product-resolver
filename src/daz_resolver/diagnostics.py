"""Private local diagnostics: no account data, no telemetry, no product payloads."""

import json
import os
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path

from . import __build__, __version__


def diagnostics_root():
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
    elif sys.platform == "darwin":
        base = Path.home() / "Library/Logs"
    else:
        base = Path(os.environ.get("XDG_STATE_HOME", Path.home() / ".local/state"))
    return base / "daz-3d-product-resolver/logs"


def plan_summary(plan):
    """Bounded UI/log representation; never walk/copy the entire payload inventory."""
    counts = {}
    for op in plan.operations:
        counts[op.action] = counts.get(op.action, 0) + 1
    return {
        "destination": plan.destination,
        "blocked": plan.blocked,
        "estimated_bytes": plan.estimated_bytes,
        "payload_verification": plan.configuration.get("payload_verification"),
        "operation_counts": counts,
        "products": [
            {
                "id": p.id,
                "source": p.source,
                "files": len(p.files),
                "bytes": sum(e.size for e in p.files),
            }
            for p in plan.products[:100]
        ],
        "product_count": len(plan.products),
        "missing_count": len(plan.missing),
        "missing_sample": plan.missing[:100],
        "ambiguity_count": len(plan.ambiguities),
        "overlap_count": len(plan.overlaps),
        "overlap_sample": dict(list(plan.overlaps.items())[:100]),
        "reports": plan.reports[:100],
        "report_count": len(plan.reports),
        "detail": "Summary only. Export the full plan for all file/provider records.",
    }


class RunDiagnostics:
    def __init__(self, root: Path | None, operation: str, configuration: dict):
        self.started = time.monotonic()
        self.last = 0.0
        self.path = None
        self.error = None
        if root is not None:
            try:
                root.mkdir(parents=True, exist_ok=True)
                stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
                self.path = root / f"{stamp}-{uuid.uuid4().hex[:8]}.jsonl"
                self.write(
                    "started",
                    {
                        "version": __version__,
                        "build": __build__,
                        "operation": operation,
                        "configuration": configuration,
                    },
                )
            except OSError as exc:
                self.error = str(exc)

    def write(self, event, value):
        if self.path is None or self.error:
            return
        try:
            record = {
                "event": event,
                "elapsed_seconds": round(time.monotonic() - self.started, 3),
                **value,
            }
            with self.path.open("a", encoding="utf-8") as stream:
                stream.write(json.dumps(record, ensure_ascii=True) + "\n")
        except OSError as exc:
            self.error = str(exc)

    def progress(self, current, total, text):
        if time.monotonic() - self.last >= 2:
            self.write("progress", {"current": current, "total": total, "stage": text})
            self.last = time.monotonic()

    def finish(self, result):
        plan = result[0] if isinstance(result, tuple) else result
        self.write(
            "completed", {"result": plan_summary(plan) if hasattr(plan, "operations") else plan}
        )
