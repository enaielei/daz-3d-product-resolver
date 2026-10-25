"""Shared planning API: dependency graph selection and immutable file expectations."""

from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from zipfile import BadZipFile

from .dson import DSON_SUFFIXES, MAX_DSON_BYTES, references
from .index import Entry, Inventory, Product, materialize
from .paths import ResolverError, file_digest, relative, safe_target


@dataclass
class Operation:
    path: str
    product: str
    entry: Entry
    expected: str | None
    action: str  # copy, skip, conflict, keep, replace


@dataclass
class Plan:
    destination: str | None
    products: list[Product]
    operations: list[Operation]
    missing: list[str] = field(default_factory=list)
    ambiguities: dict[str, list[str]] = field(default_factory=dict)
    reports: list[str] = field(default_factory=list)
    configuration: dict = field(default_factory=dict)

    @property
    def estimated_bytes(self):
        return sum(o.entry.size for o in self.operations if o.action in {"copy", "replace"})

    @property
    def blocked(self):
        return bool(
            self.missing
            or self.ambiguities
            or any(o.action == "conflict" for o in self.operations)
            or any(r.startswith("ERROR:") for r in self.reports)
        )

    def to_dict(self):
        return {**asdict(self), "estimated_bytes": self.estimated_bytes, "blocked": self.blocked}

    @classmethod
    def from_dict(cls, data):
        return cls(
            data["destination"],
            [
                Product(p["id"], p["source"], p["archive"], [Entry(**e) for e in p["files"]])
                for p in data["products"]
            ],
            [Operation(**{**o, "entry": Entry(**o["entry"])}) for o in data["operations"]],
            data.get("missing", []),
            data.get("ambiguities", {}),
            data.get("reports", []),
            data.get("configuration", {}),
        )


def library_file(library: Path, name: str) -> Path | None:
    """Resolve DAZ's case-insensitive library paths consistently on all core platforms."""
    current = library
    for part in relative(name).split("/"):
        safe_target(current, part)
        if not current.is_dir():
            return None
        matches = [p for p in current.iterdir() if p.name.casefold() == part.casefold()]
        if len(matches) > 1:
            raise ResolverError(f"Case-colliding library path: {name}")
        if not matches:
            return None
        current = matches[0]
    safe_target(library, current.relative_to(library).as_posix())
    return current if current.is_file() else None


def make_plan(
    inventory: Inventory,
    destination: Path | None = None,
    scenes: list[Path] | None = None,
    libraries: list[Path] | None = None,
    choices: dict[str, str] | None = None,
    conflicts: dict[str, str] | None = None,
    cancel: Callable[[], bool] = lambda: False,
) -> Plan:
    choices, conflicts = choices or {}, conflicts or {}
    plan = Plan(str(destination.absolute()) if destination else None, [], [])
    plan.configuration = {
        "sources": [{"path": p.source, "provenance": "user"} for p in inventory.products],
        "libraries": [{"path": str(p), "provenance": "user"} for p in libraries or []],
        "destination": {"path": str(destination) if destination else None, "provenance": "user"},
    }
    plan.reports.extend(inventory.reports)
    if any("Ambiguous product boundary" in r for r in inventory.reports):
        plan.reports.append("ERROR: Explicit product roots required for ambiguous sources")
    lookup: dict[str, list[tuple[Product, Entry]]] = {}
    for product in inventory.products:
        for entry in product.files:
            lookup.setdefault(entry.path.casefold(), []).append((product, entry))
    selected = {}
    visited = set()
    queue: list[tuple[str, bytes]] = []
    libraries = list(dict.fromkeys([p.absolute() for p in libraries or []]))
    if destination and destination.absolute() not in libraries:
        libraries.insert(0, destination.absolute())
    for scene in scenes or []:
        try:
            if scene.suffix.casefold() not in DSON_SUFFIXES:
                raise ResolverError("Only DUF/DSF scene inputs supported")
            safe_target(scene.absolute().parent, scene.name)
            with scene.open("rb") as stream:
                data = stream.read(MAX_DSON_BYTES + 1)
            parent = ""
            for library in libraries:
                if scene.absolute().is_relative_to(library):
                    parent = scene.absolute().relative_to(library).as_posix()
                    break
            queue.append((parent, data))
        except (OSError, ResolverError) as exc:
            plan.reports.append(f"ERROR: {scene}: {exc}")
    if not scenes:
        selected = {p.id: p for p in inventory.products}
    while queue:
        if cancel():
            raise ResolverError("Cancelled")
        parent, data = queue.pop()
        try:
            refs = references(data, parent)
        except (ValueError, OSError, EOFError, RecursionError) as exc:
            plan.reports.append(f"ERROR: {parent or 'scene'}: {exc}")
            continue
        for name in refs:
            key = name.casefold()
            if key in visited:
                continue
            visited.add(key)
            try:
                existing = next((p for lib in libraries if (p := library_file(lib, name))), None)
                if existing:
                    if existing.suffix.casefold() in DSON_SUFFIXES:
                        with existing.open("rb") as stream:
                            queue.append((name, stream.read(MAX_DSON_BYTES + 1)))
                    continue
                candidates = lookup.get(key, [])
                if not candidates:
                    plan.missing.append(name)
                    continue
                chosen = choices.get(name, choices.get(key))
                if chosen:
                    candidates = [(p, e) for p, e in candidates if p.id == chosen]
                    if not candidates:
                        raise ResolverError(f"Invalid product choice for {name}")
                # Full product inventories must agree, not merely the referenced file.
                if len(candidates) > 1:
                    for candidate, _ in candidates:
                        materialize(candidate, cancel)
                signatures = {
                    tuple((e.path.casefold(), e.sha256) for e in p.files) for p, _ in candidates
                }
                if len(signatures) > 1:
                    plan.ambiguities[name] = [p.id for p, _ in candidates]
                    continue
                product, entry = candidates[0]
                selected[product.id] = product
                if Path(name).suffix.casefold() in DSON_SUFFIXES:
                    queue.append((entry.path, product.read(entry, MAX_DSON_BYTES)))
            except (OSError, ValueError, BadZipFile, RuntimeError) as exc:
                plan.reports.append(f"ERROR: {name}: {exc}")
    plan.products = list(selected.values())
    targets: dict[str, Operation] = {}
    for product in plan.products:
        try:
            materialize(product, cancel)
        except (OSError, ValueError, BadZipFile, RuntimeError) as exc:
            plan.reports.append(f"ERROR: {product.source}: {exc}")
            continue
        for entry in product.files:
            key = entry.path.casefold()
            if key in targets:
                if targets[key].entry.sha256 != entry.sha256:
                    plan.reports.append(f"ERROR: Selected products disagree: {entry.path}")
                continue
            target = library_file(destination.absolute(), entry.path) if destination else None
            expected = file_digest(target) if target else None
            action = (
                "copy"
                if expected is None
                else ("skip" if expected == entry.sha256 else conflicts.get(entry.path, "conflict"))
            )
            if action not in {"copy", "skip", "conflict", "keep", "replace"}:
                raise ResolverError(f"Invalid conflict decision for {entry.path}")
            op = Operation(
                target.relative_to(destination.absolute()).as_posix() if target else entry.path,
                product.id,
                entry,
                expected,
                action,
            )
            targets[key] = op
            plan.operations.append(op)
    return plan
