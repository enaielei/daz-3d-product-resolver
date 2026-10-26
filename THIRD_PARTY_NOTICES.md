# Third-party components

The resolver's own code is MIT licensed. Dependencies retain their own licenses.
The Windows folder distribution keeps Qt/PySide/Shiboken as separate replaceable dynamic
libraries. PySide6 and Qt include LGPLv3/GPLv3/commercial licensing options; this project
does not provide a commercial Qt license. Consult the included license texts and the
[Qt for Python licensing page](https://doc.qt.io/qtforpython-6/licenses.html).
Corresponding upstream source and modification information are available from
[Qt for Python](https://code.qt.io/cgit/pyside/pyside-setup.git/) and
[Qt](https://code.qt.io/cgit/qt/). Version numbers are recorded in `uv.lock`.

Other runtime components include CPython (PSF), Typer/Rich/Markdown-it (MIT), Pygments (BSD),
DefusedXML (PSF), Shiboken, and transitive dependencies. PyInstaller uses its GPL license
with a distribution exception. The Windows packaging script includes available distribution
license files under `licenses/`; consult each component's license for exact terms.
No product content is bundled.
