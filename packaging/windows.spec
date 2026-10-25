# Build from repository root: uv run pyinstaller packaging/windows.spec --noconfirm
from pathlib import Path

root = Path(SPECPATH).parent
a = Analysis(
    [str(root / 'packaging' / 'desktop.py')],
    pathex=[str(root / 'src')],
    binaries=[], datas=[], hiddenimports=[], hookspath=[], hooksconfig={},
    runtime_hooks=[], excludes=['PySide6.QtWebEngineCore', 'PySide6.QtWebEngineWidgets'],
    noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name='Daz3DProductResolver',
          debug=False, bootloader_ignore_signals=False, strip=False, upx=False, console=False)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name='Daz3DProductResolver')
