from setuptools import setup

from app.config import APP_NAME

APP = ["run.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": [
        "app",
        "services",
        "docx",
        "faster_whisper",
        "argostranslate",
    ],
    "includes": [
        "PySide6.QtCore",
        "PySide6.QtGui",
        "PySide6.QtWidgets",
        "PySide6.QtPrintSupport",
    ],
    "excludes": [
        "PySide6.examples",
        "PySide6.support",
        "PySide6.scripts",
        "tkinter",
        "test",
        "tests",
        "pytest",
    ],
    "resources": [
        "app/ui/main_window.qss",
        "app/ui/INTERFACE_GUIDE.md",
        "assets/icons/belka.svg",
        "assets/icons/belka-256.png",
        "assets/icons/belka-512.png",
    ],
    "iconfile": "assets/icons/belka.icns",
    "plist": {
        "CFBundleName": APP_NAME,
        "CFBundleDisplayName": APP_NAME,
        "CFBundleIdentifier": "com.muhapauka.agatika-translator",
        "CFBundleShortVersionString": "1.0.0",
        "CFBundleVersion": "1",
        "NSHighResolutionCapable": True,
        "LSApplicationCategoryType": "public.app-category.productivity",
        "LSMinimumSystemVersion": "12.0",
    },
}

setup(
    app=APP,
    name=APP_NAME,
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
