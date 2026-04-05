from pathlib import Path
import re
from typing import Callable, Optional

from app.config import get_resource_path
from app.core.cancellation import CancellationToken
from app.core.errors import UserFacingError
from app.models import Segment

ProgressCallback = Callable[[float], None]
LogCallback = Callable[[str], None]


class TranslationService:
    @staticmethod
    def translate_segments(
        segments: list[Segment],
        cancellation_token: Optional[CancellationToken] = None,
        progress_callback: Optional[ProgressCallback] = None,
        log_callback: Optional[LogCallback] = None,
    ) -> list[Segment]:
        token = cancellation_token or CancellationToken()
        translator = TranslationService._build_argos_translator()

        if log_callback:
            log_callback("Использую локальный backend перевода: Argos Translate.")

        translated_segments = []
        total_segments = max(len(segments), 1)
        for index, segment in enumerate(segments, start=1):
            token.check_cancelled()
            translated_segments.append(
                Segment(
                    start=segment.start,
                    end=segment.end,
                    text_en=segment.text_en,
                    text_ru=translator.translate(segment.text_en).strip(),
                )
            )

            if progress_callback:
                progress_callback(index / total_segments)

        return translated_segments

    @staticmethod
    def _build_argos_translator():
        try:
            import argostranslate.package
            import ctranslate2
        except ImportError as exc:
            raise UserFacingError(
                "Для локального перевода не установлен argostranslate. "
                "Либо установите зависимости, либо снимите галочку перевода."
            ) from exc

        TranslationService._install_bundled_argos_model(
            argostranslate_package_module=argostranslate.package,
        )

        package_obj = TranslationService._find_installed_argos_package(
            argostranslate_package_module=argostranslate.package,
        )
        if package_obj is None:
            raise UserFacingError(
                "Языковая пара en -> ru не найдена в Argos Translate. "
                "Проверьте, что нужная модель установлена."
            )

        return DirectArgosTranslator(package_obj, ctranslate2)

    @staticmethod
    def _install_bundled_argos_model(
        argostranslate_package_module,
    ) -> None:
        if TranslationService._find_installed_argos_package(argostranslate_package_module) is not None:
            return

        package_path = TranslationService._find_bundled_argos_model()
        if package_path is None:
            return

        try:
            argostranslate_package_module.install_from_path(str(package_path))
        except Exception:
            return

    @staticmethod
    def _find_installed_argos_package(argostranslate_package_module):
        try:
            installed_packages = argostranslate_package_module.get_installed_packages()
        except Exception:
            return None

        return next(
            (
                package_obj
                for package_obj in installed_packages
                if getattr(package_obj, "from_code", None) == "en"
                and getattr(package_obj, "to_code", None) == "ru"
            ),
            None,
        )

    @staticmethod
    def _find_bundled_argos_model() -> Optional[Path]:
        assets_dir = get_resource_path("assets/argos")
        if not assets_dir.exists():
            return None

        package_files = sorted(assets_dir.glob("*.argosmodel"))
        if not package_files:
            return None

        return package_files[0]

    @staticmethod
    def _split_text_for_argos(text: str) -> list[str]:
        parts = [part.strip() for part in re.split(r"(?<=[.!?])\s+", text) if part.strip()]
        if not parts:
            return [text]

        chunks: list[str] = []
        current = ""
        for part in parts:
            candidate = f"{current} {part}".strip()
            if current and len(candidate) > 220:
                chunks.append(current)
                current = part
            else:
                current = candidate

        if current:
            chunks.append(current)

        return chunks or [text]


class DirectArgosTranslator:
    def __init__(self, package_obj, ctranslate2_module) -> None:
        self.package_obj = package_obj
        self.translator = ctranslate2_module.Translator(
            str(package_obj.package_path / "model"),
            device="cpu",
        )

    def translate(self, input_text: str) -> str:
        paragraphs = input_text.split("\n")
        translated_paragraphs = [self._translate_paragraph(paragraph) for paragraph in paragraphs]
        return "\n".join(translated_paragraphs)

    def _translate_paragraph(self, paragraph: str) -> str:
        if not paragraph.strip():
            return paragraph

        sentences = TranslationService._split_text_for_argos(paragraph)
        tokenized = [self.package_obj.tokenizer.encode(sentence) for sentence in sentences]

        target_prefix = None
        if getattr(self.package_obj, "target_prefix", ""):
            target_prefix = [[self.package_obj.target_prefix]] * len(tokenized)

        translated_batches = self.translator.translate_batch(
            tokenized,
            target_prefix=target_prefix,
            replace_unknowns=True,
            max_batch_size=32,
            beam_size=4,
            num_hypotheses=1,
        )

        decoded_sentences = []
        for sentence_batch in translated_batches:
            sentence_tokens = sentence_batch.hypotheses[0]
            decoded_sentences.append(self.package_obj.tokenizer.decode(sentence_tokens).strip())

        return " ".join(part for part in decoded_sentences if part).strip()
