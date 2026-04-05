import re

from app.utils.time_utils import humanize_duration


def format_bytes(size_bytes: int) -> str:
    value = float(size_bytes)
    units = ["Б", "КБ", "МБ", "ГБ", "ТБ"]
    unit_index = 0

    while value >= 1024 and unit_index < len(units) - 1:
        value /= 1024
        unit_index += 1

    if unit_index == 0:
        return f"{int(value)} {units[unit_index]}"
    return f"{value:.1f} {units[unit_index]}"


def format_estimate_window(estimate_seconds: float) -> str:
    low = max(30, int(estimate_seconds * 0.8))
    high = max(low + 30, int(estimate_seconds * 1.25))
    return f"Ориентировочно: {humanize_duration(low)} - {humanize_duration(high)}"


def sanitize_filename(value: str) -> str:
    sanitized = re.sub(r'[<>:"/\\|?*]+', "_", value).strip()
    return sanitized or "result"
