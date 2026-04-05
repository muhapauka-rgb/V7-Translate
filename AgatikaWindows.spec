from pathlib import Path

from PyInstaller.utils.hooks import collect_all, collect_data_files, collect_submodules

project_dir = Path.cwd()

datas = [
    (str(project_dir / "app" / "ui" / "main_window.qss"), "app/ui"),
    (str(project_dir / "app" / "ui" / "INTERFACE_GUIDE.md"), "app/ui"),
    (str(project_dir / "assets" / "icons" / "belka.svg"), "assets/icons"),
    (str(project_dir / "assets" / "icons" / "belka-256.png"), "assets/icons"),
    (str(project_dir / "assets" / "icons" / "belka-512.png"), "assets/icons"),
]
binaries = []
hiddenimports = [
    "PySide6.QtCore",
    "PySide6.QtGui",
    "PySide6.QtWidgets",
    "PySide6.QtPrintSupport",
]

argos_assets_dir = project_dir / "assets" / "argos"
if argos_assets_dir.exists():
    for argos_model_path in sorted(argos_assets_dir.glob("*.argosmodel")):
        datas.append((str(argos_model_path), "assets/argos"))

for package_name in ["faster_whisper", "ctranslate2", "argostranslate", "docx"]:
    pkg_datas, pkg_binaries, pkg_hiddenimports = collect_all(package_name)
    datas += pkg_datas
    binaries += pkg_binaries
    hiddenimports += pkg_hiddenimports

hiddenimports += collect_submodules("services")
hiddenimports += collect_submodules("app")
datas += collect_data_files("PySide6")


a = Analysis(
    ["run.py"],
    pathex=[str(project_dir)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tkinter", "pytest", "tests", "PySide6.examples", "PySide6.support"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="Переводчик Агатика",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    icon=str(project_dir / "assets" / "icons" / "belka.ico"),
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="Переводчик Агатика",
)
