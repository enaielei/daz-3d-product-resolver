# Windows preview releases

The normal CI builds/tests a self-contained PyInstaller folder and an Inno Setup per-user
installer, then exercises silent install, installed-app launch and uninstall in a temporary
workspace folder. The test suppresses shortcut/uninstall registration and checks that an
unrelated content sentinel survives uninstall. Real content libraries are never used.

Compiler: Inno Setup 6.7.3, immutable official release URL and SHA256 pinned in
`packaging/prepare_inno.ps1`. Portable compiler mode avoids host installation/configuration.
Python dependencies and PyInstaller are locked in uv.lock. Build on Windows:

```powershell
uv sync --locked --all-extras
uv run python packaging/build_windows.py
./packaging/prepare_inno.ps1
uv run python packaging/build_release.py --iscc work/tools/inno/ISCC.exe
./packaging/smoke_installer.ps1 -Installer dist/release/Daz3DProductResolver-0.1.0-windows-x64-setup.exe
```

Outputs: installer EXE, portable ZIP and SHA256SUMS.txt under dist/release. The installer's
normal mode adds only the app, Start menu shortcut, optional desktop shortcut and standard
Windows uninstall entry. It never manages DAZ libraries/settings or deletes installed content.
Uninstall does not use recursive directory deletion for user-created files.

After reviewing CI evidence, an authorized maintainer can tag a tested commit
`v<pyproject-version>-preview.<number>`. The tag workflow reruns portable/desktop validation and
publishes the three artifacts as a GitHub prerelease only if all checks pass. Preview tags can
refer to an unmerged PR commit; publishing one does not authorize merging that PR.
Do not move published tags or replace release assets silently. New builds get new preview tags.
No signing credentials are required or configured; artifacts are currently unsigned.

GitHub Wiki is enabled but unused. User/developer documentation lives in version-controlled
docs so changes are reviewed with their code and bundled with the matching release. Issues
define scope, the dedicated Project tracks work, PRs carry review/checks, and Releases carry
downloads. A separate wiki would duplicate these guides until it has distinct content to own.
