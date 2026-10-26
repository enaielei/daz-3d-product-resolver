"""Conservative portable content-path rules."""

import hashlib
import re
from pathlib import Path, PurePosixPath
from urllib.parse import unquote


class ResolverError(ValueError):
    """A user-actionable validation error."""


def relative(value: str) -> str:
    value = value.replace("\\", "/")
    parts = value.split("/")
    if (
        not value
        or value.startswith("/")
        or any(p in ("", ".", "..") for p in parts)
        or any(re.search(r'[<>:"|?*\x00-\x1f]', p) for p in parts)
        or any(p.endswith((" ", ".")) for p in parts)
        or any(re.match(r"(?i)^(con|prn|aux|nul|com[0-9]|lpt[0-9])(?:\.|$)", p) for p in parts)
    ):
        raise ResolverError(f"Unsafe content path: {value!r}")
    return str(PurePosixPath(value))


def reference(value: str, parent: str = "") -> str | None:
    # DSON object addressing is [id:/|name:/]node:file#asset?property.
    # A node selector is not an operating-system drive or a network URI.
    original = value
    for prefix in ("id:/", "name:/"):
        if value.startswith(prefix):
            value = value[len(prefix) :]
            break
    if ":" in value.split("#", 1)[0]:
        node, value = value.split(":", 1)
        if (
            "#" not in original
            or len(node) == 1
            or node.casefold() in {"http", "https", "file", "ftp", "data"}
            or ":" in value.split("#", 1)[0]
        ):
            raise ResolverError(f"Unsupported external URI: {original}")
    raw = value.split("#", 1)[0]
    if not raw:
        return None
    raw = unquote(raw).replace("\\", "/")
    if ":" in raw or raw.startswith("//"):
        raise ResolverError(f"Unsupported external URI: {value}")
    if raw.startswith("/"):
        return relative(raw[1:])
    # Normalize relative references, but never permit escaping the library.
    parts = list(PurePosixPath(parent).parent.parts) if parent else []
    for part in raw.split("/"):
        if part in ("", "."):
            continue
        if part == "..":
            if not parts:
                raise ResolverError(f"Reference escapes library: {value}")
            parts.pop()
        else:
            parts.append(part)
    return relative("/".join(parts))


def safe_target(root: Path, name: str) -> Path:
    root = root.absolute()
    target = root / relative(name)
    current = target
    while True:
        if current.is_symlink() or current.is_junction():
            raise ResolverError(f"Linked path is not allowed: {current}")
        if current == current.parent:
            break
        current = current.parent
    if not target.resolve().is_relative_to(root.resolve()):
        raise ResolverError(f"Path escapes root: {target}")
    return target


def digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def file_digest(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()
