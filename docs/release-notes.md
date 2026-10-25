## Windows preview

A self-contained offline dependency resolver with a guided desktop interface. No Python setup required.

### Download

- **windows-x64-setup.exe** — recommended per-user installation with Start menu entry and uninstaller.
- **windows-x64-portable.zip** — extract the whole folder and open Daz3DProductResolver.exe.
- **SHA256SUMS.txt** — checksums for both downloads.

### First use

Choose scene files and product source folders, add existing DAZ libraries, then check dependencies.
Review whole products and dropdown choices before installing, or use **Check only** for a read-only
preview. The included README and docs explain each step.

### Status and limitations

This is a preview from the open, unmerged PR #4. It is not a stable-release or merge claim.
Windows 11 x64 is locally tested; portable core tests run on Windows/macOS/Linux. The app/installer
are unsigned. Other desktop platforms, Windows 10 and ARM emulation lack local desktop acceptance.
Static references only; no exhaustive dynamic/script resolution, DIM registration or Smart Content
import. Sources and DAZ settings are preserved. Use one installation at a time with folders idle.

See the tagged source's docs/user-guide.md and docs/troubleshooting.md. Report synthetic reproductions
in Issues; redact private paths and purchased asset information.
