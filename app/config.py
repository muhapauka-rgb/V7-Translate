from pathlib import Path

APP_NAME = "Переводчик Агатика"
BASE_DIR = Path(__file__).resolve().parent.parent
STATE_DIR = BASE_DIR / ".local_state"
TEMP_DIR = BASE_DIR / "temp"
DEFAULT_OUTPUT_DIR = Path.home() / "Downloads" if (Path.home() / "Downloads").exists() else BASE_DIR / "output"
ESTIMATE_HISTORY_PATH = STATE_DIR / "estimate_history.json"

SUPPORTED_EXTENSIONS = {".mp3", ".m4a", ".wav", ".mp4", ".mov"}

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
