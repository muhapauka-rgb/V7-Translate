import os
import sys
from pathlib import Path

APP_NAME = "Переводчик Агатика"
BASE_DIR = Path(__file__).resolve().parent.parent

SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4", ".mov"}


def _get_user_data_dir() -> Path:
    if sys.platform.startswith("win"):
        appdata = os.environ.get("APPDATA")
        if appdata:
            return Path(appdata) / "AgatikaTranslator"
    return Path.home() / ".agatika_translator"


USER_DATA_DIR = _get_user_data_dir()
STATE_DIR = USER_DATA_DIR / "state"
TEMP_DIR = USER_DATA_DIR / "temp"
ESTIMATE_HISTORY_PATH = STATE_DIR / "estimate_history.json"


def _get_windows_downloads_dir() -> Path | None:
    candidates = []
    user_profile = os.environ.get("USERPROFILE")
    if user_profile:
        candidates.append(Path(user_profile) / "Downloads")

    one_drive = os.environ.get("OneDrive")
    if one_drive:
        candidates.append(Path(one_drive) / "Downloads")

    candidates.append(Path.home() / "Downloads")

    for candidate in candidates:
        if candidate.exists():
            return candidate

    return None


def _get_default_output_dir() -> Path:
    if sys.platform.startswith("win"):
        downloads_dir = _get_windows_downloads_dir()
        if downloads_dir and downloads_dir.exists():
            return downloads_dir

    downloads_dir = Path.home() / "Downloads"
    if downloads_dir.exists():
        return downloads_dir

    return USER_DATA_DIR / "output"


DEFAULT_OUTPUT_DIR = _get_default_output_dir()


def get_resource_path(relative_path: str) -> Path:
    if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
        return Path(sys._MEIPASS) / relative_path
    return BASE_DIR / relative_path

MODEL_PRESETS = {
    "Быстро": {
        "model_candidates": ["base", "tiny"],
        "speed_factor": 0.45,
        "beam_size": 1,
        "description": "Быстрый черновой режим для длинных файлов.",
    },
    "Баланс": {
        "model_candidates": ["small", "medium"],
        "speed_factor": 0.9,
        "beam_size": 3,
        "description": "Оптимальный баланс скорости и качества.",
    },
    "Максимально точно": {
        "model_candidates": ["large-v3", "medium"],
        "speed_factor": 1.7,
        "beam_size": 5,
        "description": "Максимально точный режим, если хватает ресурсов Mac.",
    },
}
