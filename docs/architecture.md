# Architecture and acceptance boundaries

`discovery` reads relevant DIM INI fields and isolated Windows Studio4/Studio6 registry
values. DIM library destinations and Studio mappings remain separate. Qt array ordering
is preserved. Empty DIM manifest/thumbnail overrides use inferred public shared defaults;
these are estimates, not evidence those folders exist. No account or configuration writes.
Other versions, macOS and Linux settings layouts require additional adapters.

`index` reads metadata inventories of extracted products and ZIPs. Payload hashes are streamed
only for selected or competing products during planning; ZIPs remain unextracted. Installation
revalidates full selected inventories and hashes. DIM Content-target
manifest entries identify content; conventional wrappers are a fallback. Archive-level
Manifest/Supplement plumbing is excluded, documentation inside content or recognized root
documentation folders is copied. Application/plugin targets and known binary payloads are
reported unsupported. Ambiguous root mixtures require explicit product-root selection.
Product IDs are local path-derived identifiers, not DAZ SKU claims.

`dson` parses bounded plain/gzip JSON and static URL/image-file references, including
image-library maps. It handles URI escaping, fragments, library-root and relative paths.
Node-qualified references follow the official
[DSON asset addressing specification](https://docs.daz3d.com/public/dson_spec/format_description/asset_addressing/start).
Decoded DSON documents are bounded to 256 MiB; larger files are reported unsupported.
Local fragment references do not create files. The graph follows referenced DUF/DSF files
and detects cycles. Existing mapped libraries precede source lookup. Whole selected products
are copied, but optional unreferenced presets do not expand the graph. This does not resolve
dynamic, autoloaded, scripted, encrypted or every proprietary dependency.

`engine` creates a read-only plan shared by Typer and PySide6. Source path IDs and hashes
identify competing products. Differing inventories require a choice even when their referenced
files agree. Selected products with conflicting payloads block installation. Existing differing
files require per-file keep/replace decisions. Existing byte-identical files are skipped.

`install` checks source hashes, current destination state, overlap, resource/free-space bounds,
and path safety before writes. It keeps replacement backups and durable JSON write-ahead
journals under `.daz-product-resolver`, independently of DIM. Files are staged then atomically
replaced and hashes verified. Exceptions/cancellation roll back safe writes; recovery retains
user modifications. Recovery can leave empty directories and retained backup/journal files.
It is a single-writer tool: do not run concurrent installs, edit journals, or mutate content
during transactions. Power-loss guarantees depend on filesystem behavior. Backups consume
space until manually reviewed and removed. No DIM registration or Smart Content import.

Qt runs discovery, indexing, planning and installation on background workers. Cancellation
is cooperative at file boundaries; hashing/reading a large file can delay cancellation.
The review surface displays the complete JSON plan and accepts explicit per-file decisions.
Core CI on three OSes is distinct from desktop acceptance: only Windows is a packaging target.
Real source previews are local private outputs, never committed or used for installation tests.
