"""네이버 금융에서 코스피200 편입종목 상위 정보를 수집합니다."""
from __future__ import annotations

from typing import Any
from urllib.parse import parse_qs, urlencode, urlsplit, urlunsplit

import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHeaderView,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)


KOSPI200_URL = "https://finance.naver.com/sise/sise_index.naver?code=KPI200"
HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
}


def clean_text(element: Any) -> str:
    """HTML 요소의 텍스트에서 불필요한 공백을 제거합니다."""
    if element is None:
        return ""
    return " ".join(element.get_text(" ", strip=True).split())


def crawl_kospi200(
    url: str = KOSPI200_URL,
    limit: int | None = 200,
    timeout: int = 10,
) -> list[dict[str, str]]:
    """코스피200 편입종목 상위 표를 여러 페이지에서 수집합니다."""
    if limit is not None and limit <= 0:
        return []

    entry_url = _entry_url(url)
    rows: list[dict[str, str]] = []
    page = 1
    while True:
        response = requests.get(
            _page_url(entry_url, page), headers=HEADERS, timeout=timeout
        )
        response.raise_for_status()
        response.encoding = response.apparent_encoding or response.encoding

        soup = BeautifulSoup(response.text, "html.parser")
        table = soup.select_one("table.type_1")
        if table is None:
            if page == 1:
                raise RuntimeError(
                    "편입종목 표를 찾지 못했습니다. 네이버 페이지 구조를 확인하세요."
                )
            break

        page_rows = _parse_rows(table)
        if not page_rows:
            break

        rows.extend(page_rows)
        if limit is not None and len(rows) >= limit:
            return rows[:limit]
        page += 1

    return rows


def _parse_rows(table: Any) -> list[dict[str, str]]:
    """편입종목 표에서 종목 데이터 행을 추출합니다."""
    rows: list[dict[str, str]] = []
    for row in table.select("tr"):
        name_link = row.select_one("td.ctg a[href*='/item/main.naver?code=']")
        cells = row.select("td")
        if name_link is None or len(cells) < 7:
            continue

        change_cell = cells[2]
        direction_element = change_cell.select_one("span.blind")
        change_value = clean_text(change_cell.select_one("span.tah"))
        rows.append(
            {
                "종목코드": parse_qs(urlsplit(name_link["href"]).query).get(
                    "code", [""]
                )[0],
                "종목명": clean_text(name_link),
                "현재가": clean_text(cells[1]),
                "전일비": change_value,
                "등락구분": clean_text(direction_element),
                "등락률": clean_text(cells[3]),
                "거래량": clean_text(cells[4]),
                "거래대금(백만)": clean_text(cells[5]),
                "시가총액(억)": clean_text(cells[6]),
            }
        )
    return rows


def _entry_url(index_url: str) -> str:
    """시세 URL을 네이버 금융 구성종목 URL로 변환합니다."""
    parsed_url = urlsplit(index_url)
    query = parse_qs(parsed_url.query)
    if "code" in query and "type" not in query:
        query["type"] = query.pop("code")
    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path.replace("sise_index.naver", "entryJongmok.naver"),
            urlencode(query, doseq=True),
            parsed_url.fragment,
        )
    )


def _page_url(entry_url: str, page: int) -> str:
    """구성종목 URL에 원하는 페이지 번호를 설정합니다."""
    parsed_url = urlsplit(entry_url)
    query = parse_qs(parsed_url.query)
    query["page"] = [str(page)]
    return urlunsplit(
        (
            parsed_url.scheme,
            parsed_url.netloc,
            parsed_url.path,
            urlencode(query, doseq=True),
            parsed_url.fragment,
        )
    )


class CrawlWorker(QObject):
    """별도 스레드에서 코스피200 데이터를 수집합니다."""

    completed = pyqtSignal(list)
    failed = pyqtSignal(str)

    def run(self) -> None:
        try:
            self.completed.emit(crawl_kospi200())
        except Exception as error:
            self.failed.emit(str(error))


class Kospi200Window(QMainWindow):
    """코스피200 편입종목을 표로 보여주는 메인 창입니다."""

    COLUMNS = [
        "종목코드",
        "종목명",
        "현재가",
        "전일비",
        "등락구분",
        "등락률",
        "거래량",
        "거래대금(백만)",
        "시가총액(억)",
    ]

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("코스피200 편입종목 상위")
        self.resize(1_200, 700)
        self._thread: QThread | None = None
        self._worker: CrawlWorker | None = None

        self.status_label = QLabel("데이터를 불러오는 중...")
        self.refresh_button = QPushButton("새로고침")
        self.refresh_button.clicked.connect(self.load_data)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels(self.COLUMNS)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.table.setAlternatingRowColors(True)
        self.table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeMode.ResizeToContents
        )
        self.table.horizontalHeader().setStretchLastSection(True)

        layout = QVBoxLayout()
        layout.addWidget(self.status_label)
        layout.addWidget(self.refresh_button, alignment=Qt.AlignmentFlag.AlignRight)
        layout.addWidget(self.table)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)
        self.load_data()

    def load_data(self) -> None:
        """백그라운드 스레드에서 최신 데이터를 요청합니다."""
        if self._thread is not None and self._thread.isRunning():
            return

        self.refresh_button.setEnabled(False)
        self.status_label.setText("데이터를 불러오는 중...")
        self._thread = QThread(self)
        self._worker = CrawlWorker()
        self._worker.moveToThread(self._thread)
        self._thread.started.connect(self._worker.run)
        self._worker.completed.connect(self.show_rows)
        self._worker.failed.connect(self.show_error)
        self._worker.completed.connect(self._thread.quit)
        self._worker.failed.connect(self._thread.quit)
        self._worker.completed.connect(self._worker.deleteLater)
        self._worker.failed.connect(self._worker.deleteLater)
        self._thread.finished.connect(self._thread.deleteLater)
        self._thread.start()

    def show_rows(self, rows: list[dict[str, str]]) -> None:
        """수집한 종목 데이터를 QTableWidget에 표시합니다."""
        self.table.setRowCount(len(rows))
        for row_index, row in enumerate(rows):
            for column_index, column_name in enumerate(self.COLUMNS):
                item = QTableWidgetItem(row.get(column_name, ""))
                if column_name not in {"종목코드", "종목명", "등락구분"}:
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.table.setItem(row_index, column_index, item)

        self.status_label.setText(f"총 {len(rows)}개 종목")
        self.refresh_button.setEnabled(True)

    def show_error(self, message: str) -> None:
        """크롤링 오류를 상태 표시와 대화상자로 알립니다."""
        self.status_label.setText("데이터를 불러오지 못했습니다.")
        self.refresh_button.setEnabled(True)
        QMessageBox.critical(self, "크롤링 오류", message)


def main() -> None:
    """PyQt6 애플리케이션을 실행합니다."""
    app = QApplication([])
    window = Kospi200Window()
    window.show()
    app.exec()


if __name__ == "__main__":
    main()