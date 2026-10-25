"""Journaled installation, verification and conservative crash recovery."""

import json
import os
import shutil
import uuid
from collections.abc import Callable
from pathlib import Path

from .engine import Plan, library_file
from .index import archive_product, extracted_product
from .paths import ResolverError, file_digest, safe_target

RECORDS = ".daz-product-resolver"


def save_journal(path: Path, value: dict):
    temporary = path.with_suffix(".tmp")
    with temporary.open("w", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2)
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary, path)


def rollback(journal: Path) -> list[str]:
    state = json.loads(journal.read_text(encoding="utf-8"))
    root = Path(state["destination"])
    retained = []
    for item in reversed(state["writes"]):
        target = safe_target(root, item["path"])
        current = file_digest(target) if target.is_file() else None
        if current == item["after"]:
            if item["backup"]:
                backup = safe_target(journal.parent, item["backup"])
                if file_digest(backup) != item["before"]:
                    raise ResolverError("Backup changed; manual recovery required")
                shutil.copyfile(backup, target)
            else:
                target.unlink()
        elif current != item["before"]:
            retained.append(item["path"])
    state["status"] = "recovery-needed" if retained else "rolled-back"
    state["retained_user_changes"] = retained
    save_journal(journal, state)
    return retained


def recover(destination: Path) -> dict[str, list[str]]:
    records = safe_target(destination.absolute(), RECORDS)
    results = {}
    if records.exists():
        for journal in sorted(records.glob("*/journal.json")):
            safe_target(records, journal.relative_to(records).as_posix())
            state = json.loads(journal.read_text(encoding="utf-8"))
            if Path(state["destination"]).resolve() != destination.resolve():
                raise ResolverError("Journal destination mismatch")
            if state["status"] in {"installing", "recovery-needed"}:
                results[journal.parent.name] = rollback(journal)
    return results


def install(
    plan: Plan,
    cancel: Callable[[], bool] = lambda: False,
    progress: Callable[[int, int, str], None] = lambda *_: None,
) -> dict:
    if not plan.destination:
        raise ResolverError("Explicit destination required")
    if plan.blocked:
        raise ResolverError("Resolve missing dependencies, ambiguities and conflicts first")
    root = Path(plan.destination).absolute()
    safe_target(root.parent, root.name)
    products = {p.id: p for p in plan.products}
    required = {e.path.casefold() for p in plan.products for e in p.files}
    if required != {op.path.casefold() for op in plan.operations}:
        raise ResolverError("Plan does not contain whole selected products")
    for product in plan.products:
        source = Path(product.source).resolve()
        if root.resolve().is_relative_to(source) or source.is_relative_to(root.resolve()):
            raise ResolverError("Unsafe source/destination overlap")
    seen = set()
    for op in plan.operations:
        if op.path.casefold() in seen or op.path.split("/")[0].casefold() == RECORDS:
            raise ResolverError("Duplicate or reserved destination path")
        seen.add(op.path.casefold())
        if op.product not in products or op.entry not in products[op.product].files:
            raise ResolverError("Invalid plan product/entry")
        if op.path.casefold() != op.entry.path.casefold():
            raise ResolverError("Plan cannot remap product files")
        if len(op.entry.sha256) != 64:
            raise ResolverError("Plan payload hashes required")
        if op.action not in {"copy", "skip", "keep", "replace"}:
            raise ResolverError("Invalid plan action")
        if (
            (op.action == "copy" and op.expected is not None)
            or (op.action in {"keep", "replace", "skip"} and op.expected is None)
            or (op.action == "skip" and op.expected != op.entry.sha256)
        ):
            raise ResolverError("Inconsistent plan expectations")
        target = safe_target(root, op.path)
        actual = library_file(root, op.path)
        if actual and actual != target:
            raise ResolverError(f"Stale destination casing: {op.path}")
        if target.exists() and not target.is_file():
            raise ResolverError(f"Destination is not a file: {op.path}")
        current = file_digest(target) if target.exists() else None
        if current != op.expected:
            raise ResolverError(f"Stale destination: {op.path}; re-plan")
        if cancel():
            raise ResolverError("Cancelled")
    # Validate every selected source, including files marked keep/skip, before writes.
    for product in plan.products:
        if cancel():
            raise ResolverError("Cancelled")
        refreshed = (archive_product if product.archive else extracted_product)(
            Path(product.source)
        )
        if refreshed.files != product.files:
            raise ResolverError(f"Source inventory changed: {product.source}; re-plan")
    pending = [o for o in plan.operations if o.action in {"copy", "replace"}]
    if not pending:
        return {"status": "verified", "written": 0, "journal": None}
    existing = root
    while not existing.exists():
        existing = existing.parent
    needed = sum(o.entry.size for o in pending) + sum(
        safe_target(root, o.path).stat().st_size for o in pending if o.action == "replace"
    )
    if shutil.disk_usage(existing).free < needed + 1024**2:
        raise ResolverError("Insufficient free space")
    records = safe_target(root, RECORDS)
    if records.exists():
        for old in records.glob("*/journal.json"):
            safe_target(root, old.relative_to(root).as_posix())
            if json.loads(old.read_text(encoding="utf-8"))["status"] in {
                "installing",
                "recovery-needed",
            }:
                raise ResolverError("Interrupted operation requires recover before installation")
    root.mkdir(parents=True, exist_ok=True)
    transaction = safe_target(root, f"{RECORDS}/{uuid.uuid4().hex}")
    transaction.mkdir(parents=True)
    journal = transaction / "journal.json"
    state = {"version": 1, "destination": str(root), "status": "installing", "writes": []}
    save_journal(journal, state)
    try:
        for i, op in enumerate(pending):
            if cancel():
                raise ResolverError("Cancelled")
            target = safe_target(root, op.path)
            current = file_digest(target) if target.exists() else None
            if current != op.expected:
                raise ResolverError(f"Destination changed during install: {op.path}")
            temporary = transaction / "payload.tmp"
            products[op.product].stage(op.entry, temporary, cancel)
            backup = None
            if op.action == "replace":
                backup = f"backup/{i}"
                backup_path = transaction / backup
                backup_path.parent.mkdir(exist_ok=True)
                shutil.copyfile(target, backup_path)
            state["writes"].append(
                {
                    "path": op.path,
                    "before": op.expected,
                    "after": op.entry.sha256,
                    "backup": backup,
                }
            )
            save_journal(journal, state)
            target.parent.mkdir(parents=True, exist_ok=True)
            safe_target(root, op.path)
            os.replace(temporary, target)
            if file_digest(target) != op.entry.sha256:
                raise ResolverError(f"Verification failed: {op.path}")
            progress(i + 1, len(pending), op.path)
        # Final verification catches changes made while other files were being installed.
        for op in plan.operations:
            if cancel():
                raise ResolverError("Cancelled")
            expected = op.expected if op.action == "keep" else op.entry.sha256
            if file_digest(safe_target(root, op.path)) != expected:
                raise ResolverError(f"Final verification failed: {op.path}")
        state["status"] = "verified"
        save_journal(journal, state)
    except BaseException:
        rollback(journal)
        raise
    return {"status": "verified", "written": len(pending), "journal": str(journal)}
