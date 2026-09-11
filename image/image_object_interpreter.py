import base64
import mimetypes
import os
import sys
from pathlib import Path

from openai import OpenAI
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtGui import QPixmap
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QSplitter,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

def load_environment_file(path: Path) -> None:
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        os.environ.setdefault(name.strip(), value.strip().strip('"\''))


load_environment_file(Path(__file__).resolve().parent / ".env")


class AnalysisWorker(QObject):
    completed = pyqtSignal(str)
    failed = pyqtSignal(str)

    def __init__(self, image_path: Path, api_key: str, model: str) -> None:
        super().__init__()
        self.image_path = image_path
        self.api_key = api_key
        self.model = model

    def run(self) -> None:
        try:
            mime_type = mimetypes.guess_type(self.image_path.name)[0] or "image/jpeg"
            image_data = base64.b64encode(self.image_path.read_bytes()).decode("ascii")
            image_url = f"data:{mime_type};base64,{image_data}"
            client = OpenAI(api_key=self.api_key)
            response = client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "사진 속 사물을 한국어로 정확하고 이해하기 쉽게 설명하세요. "
                            "주요 사물, 관찰 가능한 특징, 장면과 불확실한 부분을 구분해서 답하세요."
                        ),
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": "이 사진에 있는 사물을 해석해 주세요."},
                            {"type": "image_url", "image_url": {"url": image_url}},
                        ],
                    },
                ],
                max_tokens=700,
            )
            result = response.choices[0].message.content or "분석 결과가 비어 있습니다."
            self.completed.emit(result)
        except Exception as exc:
            self.failed.emit(str(exc))


class ImageObjectInterpreter(QMainWindow):
    supported_extensions = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".gif"}

    def __init__(self) -> None:
        super().__init__()
        self.image_directory = Path(__file__).resolve().parent
        self.current_image: Path | None = None
        self.worker_thread: QThread | None = None
        self.worker: AnalysisWorker | None = None
        self.setWindowTitle("사진 속 사물 해석기")
        self.resize(1100, 720)
        self._build_ui()
        self._load_images()

    def _build_ui(self) -> None:
        self.setStyleSheet(
            """
            QMainWindow, QWidget {
                background: #f6f8fb;
                color: #172033;
                font-family: 'Malgun Gothic';
                font-size: 10pt;
            }
            QSplitter::handle {
                background: #e4e9f1;
                width: 1px;
            }
            QLabel#appTitle {
                color: #172033;
                font-size: 18pt;
                font-weight: 700;
            }
            QLabel#sectionTitle {
                color: #697386;
                font-size: 9pt;
                font-weight: 700;
            }
            QLabel#hint {
                color: #7b8494;
                font-size: 9pt;
            }
            QListWidget, QTextEdit, QLineEdit {
                background: #ffffff;
                border: 1px solid #d9e0ea;
                border-radius: 8px;
                padding: 8px;
                selection-background-color: #dcecff;
                selection-color: #172033;
            }
            QListWidget {
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px 8px;
                border-radius: 6px;
            }
            QListWidget::item:selected {
                background: #dcecff;
                color: #1557a6;
                font-weight: 700;
            }
            QLineEdit:focus, QTextEdit:focus {
                border: 1px solid #4d8fe8;
            }
            QPushButton {
                background: #ffffff;
                border: 1px solid #cfd8e6;
                border-radius: 8px;
                color: #26344d;
                padding: 10px 14px;
                font-weight: 600;
            }
            QPushButton:hover {
                background: #edf5ff;
                border-color: #8ab7ef;
            }
            QPushButton:pressed {
                background: #dcecff;
            }
            QPushButton#analyzeButton {
                background: #2369c8;
                border: 1px solid #2369c8;
                color: #ffffff;
                padding: 12px;
                font-size: 10.5pt;
            }
            QPushButton#analyzeButton:hover {
                background: #1b56a5;
            }
            QPushButton#analyzeButton:disabled {
                background: #9dbce4;
                border-color: #9dbce4;
            }
            QLabel#preview {
                background: #ffffff;
                border: 1px solid #d9e0ea;
                border-radius: 10px;
                color: #8a94a5;
            }
            QTextEdit {
                line-height: 1.4em;
            }
            """
        )
        self.image_list = QListWidget()
        self.image_list.currentTextChanged.connect(self._select_image)

        self.preview = QLabel("이미지를 선택하세요")
        self.preview.setObjectName("preview")
        self.preview.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview.setMinimumSize(420, 360)

        self.api_key_input = QLineEdit(os.getenv("OPENAI_API_KEY", ""))
        self.api_key_input.setPlaceholderText("OPENAI_API_KEY 또는 여기에 API 키 입력")
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)

        self.analyze_button = QPushButton("선택한 이미지 분석")
        self.analyze_button.setObjectName("analyzeButton")
        self.analyze_button.clicked.connect(self._analyze_image)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText("분석 결과가 여기에 표시됩니다.")

        left_panel = QWidget()
        left_layout = QVBoxLayout(left_panel)
        left_layout.setContentsMargins(20, 22, 14, 20)
        left_layout.setSpacing(12)
        image_title = QLabel("이미지 라이브러리")
        image_title.setObjectName("appTitle")
        left_layout.addWidget(image_title)
        image_hint = QLabel("분석할 사진을 선택하세요")
        image_hint.setObjectName("hint")
        left_layout.addWidget(image_hint)
        left_layout.addWidget(self.image_list)
        open_button = QPushButton("이미지 폴더 열기")
        open_button.clicked.connect(self._choose_image_directory)
        left_layout.addWidget(open_button)

        right_panel = QWidget()
        right_layout = QVBoxLayout(right_panel)
        right_layout.setContentsMargins(20, 22, 20, 20)
        right_layout.setSpacing(10)
        page_title = QLabel("사진 속 사물 해석")
        page_title.setObjectName("appTitle")
        right_layout.addWidget(page_title)
        page_hint = QLabel("선택한 이미지를 OpenAI Vision으로 분석합니다")
        page_hint.setObjectName("hint")
        right_layout.addWidget(page_hint)
        right_layout.addWidget(self.preview, 2)
        key_label = QLabel("OPENAI API 키")
        key_label.setObjectName("sectionTitle")
        right_layout.addWidget(key_label)
        right_layout.addWidget(self.api_key_input)
        right_layout.addWidget(self.analyze_button)
        result_label = QLabel("ANALYSIS RESULT")
        result_label.setObjectName("sectionTitle")
        right_layout.addWidget(result_label)
        right_layout.addWidget(self.result_text, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.addWidget(left_panel)
        splitter.addWidget(right_panel)
        splitter.setSizes([260, 840])
        self.setCentralWidget(splitter)

    def _load_images(self) -> None:
        self.image_list.clear()
        if not self.image_directory.is_dir():
            self.result_text.setPlainText(f"폴더를 찾을 수 없습니다: {self.image_directory}")
            return
        image_paths = sorted(
            path
            for path in self.image_directory.iterdir()
            if path.is_file() and path.suffix.lower() in self.supported_extensions
        )
        self.image_list.addItems([path.name for path in image_paths])
        if image_paths:
            self.image_list.setCurrentRow(0)
        else:
            self.result_text.setPlainText("image 폴더에 지원되는 이미지가 없습니다.")

    def _select_image(self, filename: str) -> None:
        if not filename:
            return
        image_path = self.image_directory / filename
        if not image_path.is_file():
            return
        self.current_image = image_path
        pixmap = QPixmap(str(image_path))
        if pixmap.isNull():
            self.preview.setText("이미지를 표시할 수 없습니다.")
            return
        self._update_preview(pixmap)
        self.result_text.clear()

    def _update_preview(self, pixmap: QPixmap) -> None:
        self.preview.setPixmap(
            pixmap.scaled(
                self.preview.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )

    def resizeEvent(self, event) -> None:
        super().resizeEvent(event)
        if self.current_image:
            self._update_preview(QPixmap(str(self.current_image)))

    def _choose_image_directory(self) -> None:
        selected_directory = QFileDialog.getExistingDirectory(
            self, "이미지 폴더 선택", str(self.image_directory)
        )
        if selected_directory:
            self.image_directory = Path(selected_directory)
            self._load_images()

    def _analyze_image(self) -> None:
        if self.current_image is None:
            QMessageBox.warning(self, "이미지 없음", "먼저 분석할 이미지를 선택하세요.")
            return
        api_key = self.api_key_input.text().strip()
        if not api_key or api_key.lower() in {"your-api-key", "your_api_key", "여기에-api-키-입력"}:
            QMessageBox.warning(
                self,
                "API 키 없음",
                "실제 OpenAI API 키를 입력하세요. 예시 문자열은 사용할 수 없습니다.",
            )
            return

        self.analyze_button.setEnabled(False)
        self.result_text.setPlainText("이미지를 분석하고 있습니다...")
        self.worker_thread = QThread(self)
        self.worker = AnalysisWorker(self.current_image, api_key, "gpt-4o-mini")
        self.worker.moveToThread(self.worker_thread)
        self.worker_thread.started.connect(self.worker.run)
        self.worker.completed.connect(self._show_result)
        self.worker.failed.connect(self._show_error)
        self.worker.completed.connect(self.worker_thread.quit)
        self.worker.failed.connect(self.worker_thread.quit)
        self.worker_thread.finished.connect(self._analysis_finished)
        self.worker_thread.finished.connect(self.worker.deleteLater)
        self.worker_thread.finished.connect(self.worker_thread.deleteLater)
        self.worker_thread.start()

    def _show_result(self, result: str) -> None:
        self.result_text.setPlainText(result)

    def _show_error(self, message: str) -> None:
        if "insufficient_quota" in message or "credit_balance_exhausted" in message:
            message = (
                "OpenAI API 크레딧이 모두 사용되었습니다.\n"
                "OpenAI 결제 및 사용량 페이지에서 크레딧을 충전한 뒤 다시 시도하세요.\n\n"
                "https://platform.openai.com/settings/organization/billing/"
            )
        self.result_text.setPlainText(f"분석 중 오류가 발생했습니다.\n\n{message}")

    def _analysis_finished(self) -> None:
        self.analyze_button.setEnabled(True)
        self.worker = None
        self.worker_thread = None


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ImageObjectInterpreter()
    window.show()
    sys.exit(app.exec())