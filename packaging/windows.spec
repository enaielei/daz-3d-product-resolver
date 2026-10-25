# Build from repository root: uv run pyinstaller packaging/windows.spec --noconfirm
from pathlib import Path
import os
import sys

# Restrict build-time DLL lookup to Python, Qt and Windows. In particular, unrelated
# tools on PATH can provide an incompatible icuuc.dll that shadows Windows system ICU.
windows = Path(os.environ['SystemRoot'])
os.environ['PATH'] = os.pathsep.join(map(str, [
    Path(sys.prefix) / 'Scripts', Path(sys.base_prefix), windows / 'System32', windows,
]))

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
