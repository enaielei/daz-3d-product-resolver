"""Static, schema-aware DSON references; no script execution or autoload inference."""

import gzip
import io
import json

from .paths import ResolverError, reference

MAX_DSON_BYTES = 256 * 1024**2
DSON_SUFFIXES = {".duf", ".dsf"}


def references(data: bytes, parent: str = "") -> list[str]:
    if data.startswith(b"\x1f\x8b"):
        with gzip.GzipFile(fileobj=io.BytesIO(data)) as stream:
            data = stream.read(MAX_DSON_BYTES + 1)
    if len(data) > MAX_DSON_BYTES:
        raise ResolverError("DSON resource limit")
    try:
        document = json.loads(data)
    except (ValueError, UnicodeError) as exc:
        raise ResolverError("Malformed, encrypted, or unsupported DSON") from exc
    if not isinstance(document, dict) or "asset_info" not in document:
        raise ResolverError("Unsupported DSON document (asset_info absent)")
    found = []

    def walk(node, context=""):
        if isinstance(node, dict):
            for key, value in node.items():
                if key in {
                    "asset_info",
                    "vertices",
                    "normals",
                    "polylist",
                    "uvs",
                    "deltas",
                    "vertex_weights",
                    "joint_weights",
                    "polygon_groups",
                    "polygon_material_groups",
                }:
                    continue
                # DSON instance URLs, image maps, UV sets and channel image files.
                if key in {"url", "image_file"} and isinstance(value, str):
                    if key == "image_file" or context != "asset_info":
                        resolved = reference(value, parent)
                        if resolved:
                            found.append(resolved)
                elif isinstance(value, (dict, list)):
                    walk(value, key)
        elif isinstance(node, list):
            for value in node:
                walk(value, context)

    walk(document)
    return list(dict.fromkeys(found))
