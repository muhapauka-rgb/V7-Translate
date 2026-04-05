from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Optional


@dataclass
class AudioFileInfo:
    file_path: Path
    file_name: str
    extension: str
    size_bytes: int
    duration_seconds: float
    analysis_note: str = ""


@dataclass
class Segment:
    start: float
    end: float
    text_en: str
    text_ru: str = ""


@dataclass
class TranscriptionPayload:
    segments: List[Segment]
    model_name: str
    backend_name: str


@dataclass
class ExportOptions:
    translate_to_ru: bool
    create_docx: bool
    save_pdf: bool
    save_srt: bool
    save_txt: bool


@dataclass
class ProcessingRequest:
    input_path: Path
    output_dir: Path
    quality_label: str
    export_options: ExportOptions


@dataclass
class ProcessingResult:
    success: bool
    audio_info: Optional[AudioFileInfo] = None
    segments: List[Segment] = field(default_factory=list)
    generated_files: List[Path] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    model_name: str = ""
    actual_processing_seconds: float = 0.0
    error_message: str = ""
