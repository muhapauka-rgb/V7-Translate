import json
from pathlib import Path
from typing import Dict

from app.config import ESTIMATE_HISTORY_PATH, MODEL_PRESETS


class EstimateService:
    def __init__(self, history_path: Path = ESTIMATE_HISTORY_PATH) -> None:
        self.history_path = history_path

    def estimate_processing_seconds(self, audio_duration_seconds: float, quality_label: str) -> float:
        preset = MODEL_PRESETS.get(quality_label, MODEL_PRESETS["Баланс"])
        history = self._load_history()
        ratio = history.get(quality_label, {}).get("ratio", preset["speed_factor"])
        return max(30.0, audio_duration_seconds * ratio)

    def record_run(
        self,
        audio_duration_seconds: float,
        quality_label: str,
        actual_processing_seconds: float,
    ) -> None:
        if audio_duration_seconds <= 0:
            return

        history = self._load_history()
        current_ratio = actual_processing_seconds / audio_duration_seconds
        current_entry = history.get(
            quality_label,
            {
                "ratio": MODEL_PRESETS.get(quality_label, MODEL_PRESETS["Баланс"])["speed_factor"],
                "samples": 0,
            },
        )

        samples = int(current_entry.get("samples", 0))
        previous_ratio = float(current_entry.get("ratio", current_ratio))
        alpha = 0.35 if samples else 1.0
        blended_ratio = current_ratio * alpha + previous_ratio * (1 - alpha)

        history[quality_label] = {
            "ratio": round(blended_ratio, 4),
            "samples": samples + 1,
        }
        self._save_history(history)

    def _load_history(self) -> Dict[str, Dict[str, float]]:
        if not self.history_path.exists():
            return {}

        try:
            with self.history_path.open("r", encoding="utf-8") as file:
                return json.load(file)
        except (json.JSONDecodeError, OSError):
            return {}

    def _save_history(self, history: Dict[str, Dict[str, float]]) -> None:
        self.history_path.parent.mkdir(parents=True, exist_ok=True)
        with self.history_path.open("w", encoding="utf-8") as file:
            json.dump(history, file, ensure_ascii=False, indent=2)
