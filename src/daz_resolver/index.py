"""Read-only inventories of whole extracted products and ZIP packages."""

import stat
import zipfile
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path

from defusedxml import ElementTree

from .paths import ResolverError, digest, file_digest, relative, safe_target

MAX_FILES = 200_000
MAX_FILE_BYTES = 2 * 1024**3
MAX_PACKAGE_BYTES = 32 * 1024**3
CONTENT_DIRS = {
    "data",
    "runtime",
    "people",
    "props",
    "environments",
    "poses",
    "animals",
    "cameras",
    "lights",
    "materials",
    "scripts",
    "shader presets",
    "render presets",
    "scenes",
    "light presets",
}
WRAPPERS = {"content", "my library", "my daz 3d library"}
SOFTWARE_SUFFIXES = {".exe", ".msi", ".dll", ".dylib", ".so", ".pkg"}


@dataclass
class Entry:
    path: str
    member: str
    size: int
    sha256: str


@dataclass
class Product:
    id: str
    source: str
    archive: bool
    files: list[Entry]

    def read(self, entry: Entry) -> bytes:
        source = Path(self.source)
        safe_target(source.parent, source.name)
        if self.archive:
            with zipfile.ZipFile(source) as archive:
                info = archive.getinfo(entry.member)
                validate_member(info)
                if info.file_size != entry.size:
                    raise ResolverError(f"Source changed: {source}")
                with archive.open(info) as stream:
                    data = stream.read(MAX_FILE_BYTES + 1)
        else:
            data = safe_target(source, entry.member).read_bytes()
        if len(data) != entry.size or digest(data) != entry.sha256:
            raise ResolverError(f"Source changed: {source}: {entry.member}")
        return data


@dataclass
class Inventory:
    products: list[Product] = field(default_factory=list)
    reports: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def validate_member(info: zipfile.ZipInfo):
    relative(info.filename.rstrip("/"))
    if stat.S_ISLNK(info.external_attr >> 16) or info.flag_bits & 1:
        raise ResolverError(f"Encrypted or linked ZIP member: {info.filename}")
    if info.file_size > MAX_FILE_BYTES or (
        info.file_size > 1024**2 and info.file_size / max(info.compress_size, 1) > 1000
    ):
        raise ResolverError(f"Archive resource limit: {info.filename}")


def archive_product(path: Path) -> Product:
    entries = []
    with zipfile.ZipFile(path) as archive:
        infos = archive.infolist()
        if len(infos) > MAX_FILES or sum(i.file_size for i in infos) > MAX_PACKAGE_BYTES:
            raise ResolverError("Archive resource limit")
        for info in infos:
            validate_member(info)
        files = [i for i in infos if not i.is_dir()]
        names = {i.filename.casefold(): i for i in files}
        if len(names) != len(files):
            raise ResolverError("Duplicate/case-colliding archive members")
        manifest = names.get("manifest.dsx")
        selected = {}
        if manifest:
            if manifest.file_size > 8 * 1024**2:
                raise ResolverError("Manifest resource limit")
            root = ElementTree.fromstring(archive.read(manifest))
            for node in root.iter("File"):
                if node.get("ACTION", "Install").casefold() != "install":
                    continue
                if node.get("TARGET", "").casefold() != "content":
                    raise ResolverError("Unsupported application/plugin installer target")
                name = relative(node.get("VALUE", ""))
                if not name.casefold().startswith("content/"):
                    raise ResolverError("Manifest Content target lacks Content/ prefix")
                info = names.get(name.casefold())
                if info is None:
                    raise ResolverError(f"Manifest member absent: {name}")
                selected[info.filename] = name.split("/", 1)[1]
        else:
            for info in files:
                parts = info.filename.split("/")
                if parts[0].casefold() in WRAPPERS and len(parts) > 1:
                    selected[info.filename] = "/".join(parts[1:])
            if not selected:
                raise ResolverError("Archive has no supported Content wrapper or DIM manifest")
        # Include documentation beside Content, excluding installer plumbing.
        for info in files:
            if info.filename.split("/")[0].casefold() in {"documentation", "docs", "readme's"}:
                selected[info.filename] = info.filename
        for member, target in sorted(selected.items()):
            if Path(target).suffix.casefold() in SOFTWARE_SUFFIXES:
                raise ResolverError("Unsupported application/plugin installer payload")
            data = archive.read(member)
            entries.append(Entry(relative(target), member, len(data), digest(data)))
    if not entries:
        raise ResolverError("Empty/unsupported package")
    return Product(digest(str(path).encode())[:16], str(path), True, entries)


def extracted_product(path: Path) -> Product:
    entries = []
    total = 0
    wrappers = [p for p in path.iterdir() if p.is_dir() and p.name.casefold() in WRAPPERS]
    wrapper = wrappers[0] if len(wrappers) == 1 else None
    for item in sorted(path.rglob("*")):
        safe_target(path, item.relative_to(path).as_posix())
        if not item.is_file():
            continue
        if item.suffix.casefold() in SOFTWARE_SUFFIXES:
            raise ResolverError("Unsupported application/plugin installer payload")
        name = relative(item.relative_to(path).as_posix())
        target = name
        if wrapper:
            if item.is_relative_to(wrapper):
                target = item.relative_to(wrapper).as_posix()
            elif name.split("/")[0].casefold() not in {"documentation", "docs", "readme's"}:
                continue
        elif name.casefold() in {"manifest.dsx", "supplement.dsx"}:
            continue
        size = item.stat().st_size
        total += size
        if size > MAX_FILE_BYTES or total > MAX_PACKAGE_BYTES or len(entries) >= MAX_FILES:
            raise ResolverError("Extracted product resource limit")
        entries.append(Entry(target, name, size, file_digest(item)))
    return Product(digest(str(path).encode())[:16], str(path), False, entries)


def index_sources(
    sources: list[Path],
    product_roots: list[Path] | None = None,
    cancel: Callable[[], bool] = lambda: False,
) -> Inventory:
    result = Inventory()
    roots: set[Path] = set()
    archives: set[Path] = set()
    explicit = {p.resolve() for p in product_roots or []}

    def visit(path: Path):
        if cancel():
            raise ResolverError("Cancelled")
        safe_target(path.parent, path.name)
        if path.is_file():
            if path.suffix.casefold() == ".zip":
                archives.add(path)
            return
        children = sorted(path.iterdir())
        if path in explicit:
            roots.add(path)
            return
        wrappers = [p for p in children if p.is_dir() and p.name.casefold() in WRAPPERS]
        direct = [p for p in children if p.is_dir() and p.name.casefold() in CONTENT_DIRS]
        nested = [
            p
            for p in children
            if p.is_dir()
            and p.name.casefold() not in CONTENT_DIRS | WRAPPERS
            and any(
                c.is_dir() and c.name.casefold() in CONTENT_DIRS | WRAPPERS for c in p.iterdir()
            )
        ]
        if (direct and (wrappers or nested)) or len(wrappers) > 1:
            result.reports.append(f"Ambiguous product boundary; select --product-root: {path}")
            return
        if direct:
            roots.add(path)
            return
        if wrappers:
            roots.add(path)
            return
        for child in children:
            visit(child)

    for source in sources:
        try:
            visit(source.absolute())
        except (OSError, ResolverError) as exc:
            result.reports.append(f"{source}: {exc}")
    for path in sorted(roots | archives):
        try:
            product = archive_product(path) if path in archives else extracted_product(path)
            keys = [entry.path.casefold() for entry in product.files]
            if len(keys) != len(set(keys)):
                raise ResolverError("Case-colliding product files")
            result.products.append(product)
        except (OSError, ValueError, zipfile.BadZipFile, ElementTree.ParseError) as exc:
            result.reports.append(f"{path}: {exc}")
    return result
