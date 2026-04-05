import re
from typing import Callable, Optional

from app.core.cancellation import CancellationToken
from app.core.errors import UserFacingError
from app.models import Segment

ProgressCallback = Callable[[float], None]
LogCallback = Callable[[str], None]


class TranslationService:
    _argos_patched = False

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
            import argostranslate.translate
        except ImportError as exc:
            raise UserFacingError(
                "Для локального перевода не установлен argostranslate. "
                "Либо установите зависимости, либо снимите галочку перевода."
            ) from exc

        TranslationService._patch_argos_translation(argostranslate.translate)

        languages = argostranslate.translate.get_installed_languages()
        from_language = next((language for language in languages if language.code == "en"), None)
        to_language = next((language for language in languages if language.code == "ru"), None)

        if not from_language or not to_language:
            raise UserFacingError(
                "Локальный переводчик не настроен. Установите языковую модель Argos Translate en -> ru "
                "или отключите перевод в интерфейсе."
            )

        translation = from_language.get_translation(to_language)
        if translation is None:
            raise UserFacingError(
                "Языковая пара en -> ru не найдена в Argos Translate. "
                "Проверьте, что нужная модель установлена."
            )

        return translation

    @staticmethod
    def _patch_argos_translation(argos_translate_module) -> None:
        if TranslationService._argos_patched:
            return

        original_apply = argos_translate_module.apply_packaged_translation

        def safe_apply_packaged_translation(pkg, input_text, translator, num_hypotheses=4):
            try:
                return original_apply(pkg, input_text, translator, num_hypotheses)
            except TypeError as exc:
                if "typing.Self" not in str(exc):
                    raise

                sentences = TranslationService._split_text_for_argos(input_text)
                tokenized = [pkg.tokenizer.encode(sentence) for sentence in sentences]

                target_prefix = None
                if getattr(pkg, "target_prefix", ""):
                    target_prefix = [[pkg.target_prefix]] * len(tokenized)

                translated_batches = translator.translate_batch(
                    tokenized,
                    target_prefix=target_prefix,
                    replace_unknowns=True,
                    max_batch_size=32,
                    beam_size=max(num_hypotheses, 4),
                    num_hypotheses=num_hypotheses,
                )

                hypotheses = [
                    argos_translate_module.Hypothesis("", 0) for _ in range(num_hypotheses)
                ]

                for sentence_batch in translated_batches:
                    for hypothesis_index in range(num_hypotheses):
                        sentence_tokens = sentence_batch.hypotheses[hypothesis_index]
                        decoded = pkg.tokenizer.decode(sentence_tokens).strip()
                        current_value = hypotheses[hypothesis_index].value
                        combined_value = f"{current_value} {decoded}".strip()
                        score = 0.0
                        if hypothesis_index < len(sentence_batch.scores):
                            score = float(sentence_batch.scores[hypothesis_index])
                        combined_score = hypotheses[hypothesis_index].score + score
                        hypotheses[hypothesis_index] = argos_translate_module.Hypothesis(
                            combined_value,
                            combined_score,
                        )

                return hypotheses

        argos_translate_module.apply_packaged_translation = safe_apply_packaged_translation
        TranslationService._argos_patched = True

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
