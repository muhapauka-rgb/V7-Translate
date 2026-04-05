from datetime import datetime
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QPlainTextEdit,
    QProgressBar,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from app.config import APP_NAME, DEFAULT_OUTPUT_DIR, MODEL_PRESETS
from app.core.worker import ProcessingWorker
from app.models import AudioFileInfo, ExportOptions, ProcessingRequest, ProcessingResult
from app.utils.format_utils import format_bytes, format_estimate_window
from app.utils.time_utils import format_seconds_hhmmss
from services.audio_service import AudioService
from services.estimate_service import EstimateService
from services.export_service import ExportService


class ExportOptionsDialog(QDialog):
    def __init__(self, export_preferences: dict[str, bool], parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Форматы сохранения")
        self.setModal(True)
        self.setMinimumWidth(320)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(10)

        description = QLabel("Выберите, какие файлы сохранить после обработки.")
        description.setWordWrap(True)

        self.docx_checkbox = QCheckBox("Word (.docx)")
        self.docx_checkbox.setChecked(export_preferences["docx"])
        self.pdf_checkbox = QCheckBox("PDF (.pdf)")
        self.pdf_checkbox.setChecked(export_preferences["pdf"])
        self.srt_checkbox = QCheckBox("SRT (.srt)")
        self.srt_checkbox.setChecked(export_preferences["srt"])
        self.txt_checkbox = QCheckBox("TXT (.txt)")
        self.txt_checkbox.setChecked(export_preferences["txt"])

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)

        layout.addWidget(description)
        layout.addWidget(self.docx_checkbox)
        layout.addWidget(self.pdf_checkbox)
        layout.addWidget(self.srt_checkbox)
        layout.addWidget(self.txt_checkbox)
        layout.addWidget(buttons)

    def get_preferences(self) -> dict[str, bool]:
        return {
            "docx": self.docx_checkbox.isChecked(),
            "pdf": self.pdf_checkbox.isChecked(),
            "srt": self.srt_checkbox.isChecked(),
            "txt": self.txt_checkbox.isChecked(),
        }


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.estimate_service = EstimateService()
        self.current_audio_info: Optional[AudioFileInfo] = None
        self.worker: Optional[ProcessingWorker] = None
        self.last_processing_result: Optional[ProcessingResult] = None
        self.export_preferences = {
            "docx": True,
            "pdf": False,
            "srt": False,
            "txt": False,
        }

        self.setWindowTitle(APP_NAME)
        self.resize(780, 620)
        self.setMinimumSize(720, 560)

        self._build_ui()
        self._apply_style()
        self._set_default_output_dir()
        self._update_quality_description()
        self._update_estimate_label()
        self._update_export_summary()

    def _build_ui(self) -> None:
        root = QWidget(self)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(14, 14, 14, 14)
        root_layout.setSpacing(10)

        title = QLabel("Переводчик Агатика")
        title.setObjectName("titleLabel")

        root_layout.addWidget(title)
        root_layout.addWidget(self._build_file_group())
        root_layout.addWidget(self._build_options_group())
        root_layout.addWidget(self._build_progress_group(), stretch=1)

        self.setCentralWidget(root)

    def _build_file_group(self) -> QGroupBox:
        group = QGroupBox("Файл и параметры")
        group.setObjectName("fileGroup")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        file_row = QHBoxLayout()
        self.file_path_edit = QLineEdit()
        self.file_path_edit.setObjectName("filePathEdit")
        self.file_path_edit.setReadOnly(True)
        self.file_path_edit.setPlaceholderText("Аудиофайл пока не выбран")
        self.select_file_button = QPushButton("Выбрать файл")
        self.select_file_button.setObjectName("primaryButton")
        self.select_file_button.clicked.connect(self._choose_input_file)
        file_row.addWidget(self.file_path_edit, stretch=1)
        file_row.addWidget(self.select_file_button)

        output_row = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        self.output_dir_edit.setObjectName("outputDirEdit")
        self.output_dir_edit.setReadOnly(True)
        self.output_dir_button = QPushButton("Папка сохранения")
        self.output_dir_button.setObjectName("secondaryButton")
        self.output_dir_button.clicked.connect(self._choose_output_dir)
        output_row.addWidget(self.output_dir_edit, stretch=1)
        output_row.addWidget(self.output_dir_button)

        layout.addLayout(file_row)
        layout.addLayout(output_row)
        return group

    def _build_options_group(self) -> QGroupBox:
        group = QGroupBox("Настройки обработки")
        group.setObjectName("optionsGroup")
        layout = QGridLayout(group)
        layout.setHorizontalSpacing(12)
        layout.setVerticalSpacing(8)

        self.quality_combo = QComboBox()
        self.quality_combo.setObjectName("qualityCombo")
        self.quality_combo.addItems(MODEL_PRESETS.keys())
        self.quality_combo.currentTextChanged.connect(self._handle_quality_changed)
        self.quality_description = QLabel("")
        self.quality_description.setWordWrap(True)
        self.quality_description.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)

        self.translate_checkbox = QCheckBox("Перевод на русский")
        self.translate_checkbox.setChecked(True)
        self.export_options_button = QPushButton("Форматы...")
        self.export_options_button.setObjectName("secondaryButton")
        self.export_options_button.clicked.connect(self._open_export_options_dialog)
        self.export_summary_label = QLabel("")
        self.export_summary_label.setObjectName("summaryLabel")
        self.export_summary_label.setWordWrap(True)

        self.estimate_value = QLabel("Ориентировочно: выберите файл")
        self.estimate_value.setObjectName("estimateLabel")

        layout.addWidget(QLabel("Качество распознавания:"), 0, 0)
        layout.addWidget(self.quality_combo, 0, 1)
        layout.addWidget(self.quality_description, 1, 0, 1, 2)
        layout.addWidget(self.translate_checkbox, 2, 0)
        layout.addWidget(self.export_options_button, 2, 1)
        layout.addWidget(QLabel("Форматы сохранения:"), 3, 0)
        layout.addWidget(self.export_summary_label, 3, 1)
        layout.addWidget(QLabel("Прогноз времени:"), 4, 0)
        layout.addWidget(self.estimate_value, 4, 1)

        return group

    def _build_progress_group(self) -> QGroupBox:
        group = QGroupBox("Ход выполнения")
        group.setObjectName("progressGroup")
        layout = QVBoxLayout(group)
        layout.setSpacing(8)

        controls_row = QHBoxLayout()
        self.start_button = QPushButton("Старт")
        self.start_button.setObjectName("primaryButton")
        self.start_button.clicked.connect(self._start_processing)
        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setObjectName("mutedButton")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self._cancel_processing)
        self.resave_button = QPushButton("Сохранить ещё раз")
        self.resave_button.setObjectName("secondaryButton")
        self.resave_button.setEnabled(False)
        self.resave_button.clicked.connect(self._resave_last_result)
        self.toggle_log_button = QPushButton("Журнал")
        self.toggle_log_button.setObjectName("secondaryButton")
        self.toggle_log_button.clicked.connect(self._toggle_log_visibility)
        controls_row.addWidget(self.start_button)
        controls_row.addWidget(self.cancel_button)
        controls_row.addWidget(self.resave_button)
        controls_row.addWidget(self.toggle_log_button)
        controls_row.addStretch(1)

        self.status_label = QLabel("Готово к запуску")
        self.progress_bar = QProgressBar()
        self.progress_bar.setObjectName("mainProgressBar")
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        self.log_output = QPlainTextEdit()
        self.log_output.setObjectName("logOutput")
        self.log_output.setReadOnly(True)
        self.log_output.setPlaceholderText("Здесь будет отображаться журнал выполнения.")
        self.log_output.setMaximumHeight(120)
        self.log_output.hide()

        layout.addLayout(controls_row)
        layout.addWidget(self.status_label)
        layout.addWidget(self.progress_bar)
        layout.addWidget(self.log_output, stretch=1)

        return group

    def _apply_style(self) -> None:
        styles_path = Path(__file__).with_name("main_window.qss")
        self.setStyleSheet(styles_path.read_text(encoding="utf-8"))

    def _set_default_output_dir(self) -> None:
        self.output_dir_edit.setText(str(DEFAULT_OUTPUT_DIR))

    def _open_export_options_dialog(self) -> None:
        dialog = ExportOptionsDialog(self.export_preferences, self)
        if dialog.exec():
            self.export_preferences = dialog.get_preferences()
            self._update_export_summary()

    def _update_export_summary(self) -> None:
        labels = []
        if self.export_preferences["docx"]:
            labels.append("Word")
        if self.export_preferences["pdf"]:
            labels.append("PDF")
        if self.export_preferences["srt"]:
            labels.append("SRT")
        if self.export_preferences["txt"]:
            labels.append("TXT")

        self.export_summary_label.setText(", ".join(labels) if labels else "Ничего не выбрано")

    def _toggle_log_visibility(self) -> None:
        is_visible = self.log_output.isVisible()
        self.log_output.setVisible(not is_visible)
        self.toggle_log_button.setText("Скрыть журнал" if not is_visible else "Журнал")

    def _show_message(self, level: str, title: str, text: str) -> None:
        icon_map = {
            "info": QMessageBox.Information,
            "warning": QMessageBox.Warning,
            "error": QMessageBox.Critical,
        }
        message_box = QMessageBox(self)
        message_box.setWindowTitle(title)
        message_box.setText(text)
        message_box.setIcon(icon_map[level])
        message_box.setStandardButtons(QMessageBox.Ok)
        message_box.setStyleSheet(
            """
            QMessageBox {
                background: #ffffff;
            }
            QMessageBox QLabel {
                color: #111827;
                min-width: 340px;
                font-size: 13px;
            }
            QMessageBox QPushButton {
                min-width: 88px;
                background: #0f172a;
                color: #ffffff;
                border: 1px solid #0f172a;
                border-radius: 10px;
                padding: 7px 14px;
            }
            """
        )
        message_box.exec()

    def _build_export_options(self, export_preferences: dict[str, bool]) -> ExportOptions:
        return ExportOptions(
            translate_to_ru=self.translate_checkbox.isChecked(),
            create_docx=export_preferences["docx"],
            save_pdf=export_preferences["pdf"],
            save_srt=export_preferences["srt"],
            save_txt=export_preferences["txt"],
        )

    def _choose_input_file(self) -> None:
        downloads_dir = Path.home() / "Downloads"
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Выберите аудиофайл",
            str(downloads_dir if downloads_dir.exists() else Path.home()),
            "Аудио и видео (*.mp3 *.m4a *.wav *.mp4 *.mov)",
        )
        if not file_path:
            return

        self.file_path_edit.setText(file_path)
        self._analyze_selected_file(Path(file_path))

    def _choose_output_dir(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self,
            "Выберите папку для сохранения",
            self.output_dir_edit.text() or str(DEFAULT_OUTPUT_DIR),
        )
        if folder:
            self.output_dir_edit.setText(folder)

    def _analyze_selected_file(self, path: Path) -> None:
        try:
            audio_info = AudioService.analyze_file(path)
        except Exception as exc:
            self._show_message("error", "Ошибка", str(exc))
            self.current_audio_info = None
            self._reset_audio_info()
            self._update_estimate_label()
            return

        self.current_audio_info = audio_info
        self._append_log(
            "Файл выбран: "
            f"{audio_info.file_name} | {format_bytes(audio_info.size_bytes)} | "
            f"{format_seconds_hhmmss(audio_info.duration_seconds)}"
        )
        if audio_info.analysis_note:
            self._append_log(audio_info.analysis_note)
        self._update_estimate_label()

    def _reset_audio_info(self) -> None:
        self.current_audio_info = None

    def _handle_quality_changed(self, _value: str) -> None:
        self._update_quality_description()
        self._update_estimate_label()

    def _update_quality_description(self) -> None:
        quality_label = self.quality_combo.currentText()
        description = MODEL_PRESETS[quality_label]["description"]
        self.quality_description.setText(description)

    def _update_estimate_label(self) -> None:
        if not self.current_audio_info:
            self.estimate_value.setText("Ориентировочно: выберите файл")
            return

        estimate_seconds = self.estimate_service.estimate_processing_seconds(
            audio_duration_seconds=self.current_audio_info.duration_seconds,
            quality_label=self.quality_combo.currentText(),
        )
        self.estimate_value.setText(format_estimate_window(estimate_seconds))

    def _start_processing(self) -> None:
        if self.worker and self.worker.isRunning():
            return

        input_path_text = self.file_path_edit.text().strip()
        if not input_path_text:
            self._show_message("warning", "Нет файла", "Сначала выберите аудиофайл.")
            return

        if not any(self.export_preferences.values()):
            self._show_message(
                "warning",
                "Нет форматов",
                "Выберите хотя бы один формат экспорта: Word, PDF, SRT или TXT.",
            )
            return

        request = ProcessingRequest(
            input_path=Path(input_path_text),
            output_dir=Path(self.output_dir_edit.text().strip() or str(DEFAULT_OUTPUT_DIR)),
            quality_label=self.quality_combo.currentText(),
            export_options=self._build_export_options(self.export_preferences),
        )

        self.log_output.clear()
        self.progress_bar.setValue(0)
        self.status_label.setText("Подготовка к запуску")
        self._append_log("Запуск обработки.")
        self._append_log(f"Папка сохранения: {request.output_dir}")
        self._append_log(f"Режим качества: {request.quality_label}")

        self.worker = ProcessingWorker(request)
        self.worker.progress_changed.connect(self.progress_bar.setValue)
        self.worker.status_changed.connect(self.status_label.setText)
        self.worker.log_message.connect(self._append_log)
        self.worker.completed.connect(self._handle_completed)
        self.worker.failed.connect(self._handle_failed)
        self.worker.cancelled.connect(self._handle_cancelled)

        self._set_running_state(True)
        self.worker.start()

    def _cancel_processing(self) -> None:
        if self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.cancel_button.setEnabled(False)
            self._append_log("Запрошена отмена. Ожидаю завершения текущего шага.")

    def _handle_completed(self, result: ProcessingResult) -> None:
        self.last_processing_result = result
        self._set_running_state(False)
        self.progress_bar.setValue(100)
        self.status_label.setText("Готово" if not result.warnings else "Готово с предупреждениями")
        self._append_log("Все файлы успешно сохранены.")

        generated_files = "\n".join(str(path) for path in result.generated_files)
        message = "Обработка завершена.\n\nСозданы файлы:\n" + generated_files
        if result.warnings:
            warnings_text = "\n".join(f"- {warning}" for warning in result.warnings)
            message += "\n\nПредупреждения:\n" + warnings_text
            if not self.log_output.isVisible():
                self._toggle_log_visibility()
        self._show_message("info", "Готово", message)
        self._update_estimate_label()

    def _resave_last_result(self) -> None:
        if not self.last_processing_result or not self.last_processing_result.audio_info:
            self._show_message(
                "warning",
                "Нет результата",
                "Сначала выполните распознавание, чтобы затем сохранять готовый результат повторно.",
            )
            return

        dialog = ExportOptionsDialog(self.export_preferences, self)
        if not dialog.exec():
            return

        export_preferences = dialog.get_preferences()
        if not any(export_preferences.values()):
            self._show_message(
                "warning",
                "Нет форматов",
                "Выберите хотя бы один формат: Word, PDF, SRT или TXT.",
            )
            return

        output_dir = Path(self.output_dir_edit.text().strip() or str(DEFAULT_OUTPUT_DIR))
        self.export_preferences = export_preferences
        self._update_export_summary()

        result = self.last_processing_result
        export_options = self._build_export_options(export_preferences)
        generated_files = ExportService.export_outputs(
            output_dir=output_dir,
            audio_info=result.audio_info,
            segments=result.segments,
            model_name=result.model_name,
            export_options=export_options,
        )

        self._append_log(
            f"Готовый результат повторно сохранён в папку: {output_dir}"
        )
        self._append_log(
            "Файлы перезаписаны: " + ", ".join(path.name for path in generated_files)
        )
        self._show_message(
            "info",
            "Сохранено",
            "Готовый результат сохранён повторно в уже выбранную папку.\n"
            "Если файлы с таким именем уже существовали, они были перезаписаны.\n\n"
            "Файлы:\n"
            + "\n".join(str(path) for path in generated_files),
        )

    def _handle_failed(self, message: str) -> None:
        self._set_running_state(False)
        self.status_label.setText("Ошибка")
        if not self.log_output.isVisible():
            self._toggle_log_visibility()
        self._append_log(message)
        self._show_message("error", "Ошибка", message)

    def _handle_cancelled(self, message: str) -> None:
        self._set_running_state(False)
        self.status_label.setText("Отменено")
        self._append_log(message)
        self._show_message("info", "Отмена", message)

    def _set_running_state(self, is_running: bool) -> None:
        self.select_file_button.setEnabled(not is_running)
        self.output_dir_button.setEnabled(not is_running)
        self.quality_combo.setEnabled(not is_running)
        self.translate_checkbox.setEnabled(not is_running)
        self.export_options_button.setEnabled(not is_running)
        self.start_button.setEnabled(not is_running)
        self.cancel_button.setEnabled(is_running)
        self.resave_button.setEnabled((not is_running) and self.last_processing_result is not None)
        self.toggle_log_button.setEnabled(not is_running or self.log_output.isVisible())

    def _append_log(self, message: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_output.appendPlainText(f"[{timestamp}] {message}")
