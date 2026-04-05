from setuptools import setup

APP = ["run.py"]
OPTIONS = {
    "argv_emulation": False,
    "packages": [
        "app",
        "services",
        "PySide6",
        "docx",
        "faster_whisper",
        "argostranslate",
    ],
    "plist": {
        "CFBundleName": "Audio Lesson Transcriber RU",
        "CFBundleDisplayName": "Audio Lesson Transcriber RU",
        "CFBundleIdentifier": "com.v7translate.audio-lesson-transcriber-ru",
        "LSMinimumSystemVersion": "12.0",
    },
}

setup(
    app=APP,
    name="Audio Lesson Transcriber RU",
    options={"py2app": OPTIONS},
    setup_requires=["py2app"],
)
