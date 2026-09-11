"""Crawl news search results from Naver with requests and BeautifulSoup."""
from __future__ import annotations

from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urljoin, urlparse

from openpyxl import Workbook
import requests
from bs4 import BeautifulSoup
from PyQt6.QtCore import QObject, QThread, Qt, pyqtSignal
from PyQt6.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

NAVER_NEWS_URL = (
    "https://search.naver.com/search.naver?"
    "where=nexearch&sm=top_hty&fbm=0&ie=utf8&"
    "query=%ED%8E%84%EC%96%B4%EB%B9%84%EC%8A%A4+%EC%A3%BC%EA%B0%80&"
    "ackey=w50sezjl"
)
GOOGLE_SEARCH_URL = (
    "https://www.google.com/search?q=%ED%8E%84%EC%96%B4%EB%B9%84%EC%8A%A4+%EC%A3%BC%EA%B0%80&"
    "oq=%ED%8E%84%EC%96%B4%EB%B9%84%EC%8A%A4+%EC%A3%BC%EA%B0%80&"
    "gs_lcrp=EgZjaHJvbWUqDQgAEAAYgwEYsQMYgAQyDQgAEAAYgwEYsQMYgAQyBwgBEAAYgAQy"
    "BwgCEAAYgAQyBwgDEAAYgAQyBwgEEAAYgAQyBwgFEAAYgAQyBwgGEAAYgAQyBwgHEAAYgAQy"
    "BwgIEAAYgAQyDQgJEC4YrwEYxwEYgATSAQgzNzExajBqN6gCALACAA&"
    "sourceid=chrome&source=chrome.ob&ie=UTF-8"
)

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/130.0.0.0 Safari/537.36"
    )
}
RESULT_FILE = Path(__file__).with_name("naverResult.xlsx")


def clean_text(element: Any) -> str:
    """Return an element's readable text without extra whitespace."""
    if element is None:
        return ""
    text = element.get_text(" ", strip=True).replace("새 창 열림", "")
    return " ".join(text.split())


def crawl_naver_news(
    url: str = NAVER_NEWS_URL,
    limit: int = 10,
    timeout: int = 10,
) -> list[dict[str, str]]:
    """Return news titles, links, publishers, summaries, and article bodies."""
    if limit <= 0:
        return []

    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    response.encoding = response.apparent_encoding or response.encoding

    soup = BeautifulSoup(response.text, "html.parser")
    articles: list[dict[str, str]] = []
    seen_links: set[str] = set()

    for news_item in soup.select(
        ".fds-news-item-list-desk > div.sds-comps-vertical-layout"
    ):
        article_links = [
            link_element
            for link_element in news_item.select("a[href]")
            if link_element["href"].startswith(("http://", "https://"))
            and "media.naver.com" not in link_element["href"]
            and "n.news.naver.com" not in link_element["href"]
            and "keep.naver.com" not in link_element["href"]
            and "news.naver.com/main/static" not in link_element["href"]
            and clean_text(link_element) not in {"", "새 창 열림"}
            and len(clean_text(link_element)) > 10
        ]
        if not article_links:
            continue

        title_link = article_links[0]
        link = urljoin(response.url, title_link["href"])
        title = clean_text(title_link)
        if not link or not title or link in seen_links:
            continue

        summary = clean_text(article_links[1]) if len(article_links) > 1 else ""

        articles.append(
            {
                "title": title,
                "link": link,
                "publisher": clean_text(
                    news_item.select_one(".sds-comps-profile-info-title-text")
                ),
                "summary": summary,
                "content": crawl_article_content(link, timeout=timeout),
            }
        )
        seen_links.add(link)
        if len(articles) >= limit:
            break

    return articles


def crawl_google_news(
    url: str = GOOGLE_SEARCH_URL,
    limit: int = 10,
    timeout: int = 10,
) -> list[dict[str, str]]:
    """Return article data from Google search results."""
    if limit <= 0:
        return []

    response = requests.get(url, headers=HEADERS, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    articles: list[dict[str, str]] = []
    seen_links: set[str] = set()

    for title_element in soup.select("h3"):
        title = clean_text(title_element)
        title_link = title_element.find_parent("a", href=True)
        if title_link is None or not title:
            continue

        link = google_result_url(title_link["href"], response.url)
        if not link or link in seen_links or not is_article_url(link):
            continue

        result_box = title_element.find_parent(
            lambda tag: tag.name == "div"
            and any(
                class_name in ("MjjYud", "SoaBEf", "g")
                for class_name in (tag.get("class") or [])
            )
        )
        result_text = clean_text(result_box)
        summary = result_text.removeprefix(title).strip()
        articles.append(
            {
                "title": title,
                "link": link,
                "publisher": "",
                "summary": summary,
                "content": crawl_article_content(link, timeout=timeout),
            }
        )
        seen_links.add(link)
        if len(articles) >= limit:
            break

    return articles


def google_result_url(href: str, base_url: str) -> str:
    """Resolve Google's direct and /url?q= result links."""
    absolute_url = urljoin(base_url, href)
    parsed_url = urlparse(absolute_url)
    if parsed_url.path == "/url":
        return unquote(parse_qs(parsed_url.query).get("q", [""])[0])
    return absolute_url


def is_article_url(url: str) -> bool:
    """Exclude Google navigation links from search results."""
    parsed_url = urlparse(url)
    return bool(parsed_url.netloc) and "google." not in parsed_url.netloc


def crawl_article_content(url: str, timeout: int = 10) -> str:
    """Best-effort extraction of an article body from a publisher page."""
    try:
        response = requests.get(url, headers=HEADERS, timeout=timeout)
        response.raise_for_status()
    except requests.RequestException:
        return ""

    soup = BeautifulSoup(response.text, "html.parser")
    selectors = (
        "#dic_area",
        ".article_body",
        ".article-body",
        ".article_view",
        ".news_body",
        "article",
    )
    for selector in selectors:
        content = clean_text(soup.select_one(selector))
        if content:
            return content
    return ""


def save_articles_to_excel(
    articles: list[dict[str, str]],
    file_path: Path = RESULT_FILE,
) -> None:
    """Save crawled news articles to an Excel workbook."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Naver News"
    worksheet.append(["제목", "언론사", "링크", "요약", "본문"])

    for article in articles:
        worksheet.append(
            [
                article.get("title", ""),
                article.get("publisher", ""),
                article.get("link", ""),
                article.get("summary", ""),
                article.get("content", "")[:32767],
            ]
        )

    worksheet.freeze_panes = "A2"
    worksheet.auto_filter.ref = worksheet.dimensions
    column_widths = {"A": 42, "B": 18, "C": 55, "D": 60, "E": 100}
    for column, width in column_widths.items():
        worksheet.column_dimensions[column].width = width
    workbook.save(file_path)


class CrawlWorker(QObject):
    """Run network crawling outside the GUI thread."""

    finished = pyqtSignal(list)
    failed = pyqtSignal(str)

    def __init__(self, url: str, limit: int) -> None:
        super().__init__()
        self.url = url
        self.limit = limit

    def run(self) -> None:
        try:
            self.finished.emit(crawl_naver_news(self.url, self.limit))
        except requests.RequestException as error:
            self.failed.emit(f"네이버 요청 중 오류가 발생했습니다.\n{error}")
        except Exception as error:
            self.failed.emit(f"크롤링 중 오류가 발생했습니다.\n{error}")


class NewsWindow(QWidget):
    """PyQt6 window for crawling Naver news and exporting results."""

    def __init__(self) -> None:
        super().__init__()
        self.articles: list[dict[str, str]] = []
        self.thread: QThread | None = None
        self.worker: CrawlWorker | None = None
        self.setWindowTitle("네이버 뉴스 크롤러")
        self.resize(1100, 650)
        self.build_ui()

    def build_ui(self) -> None:
        self.url_input = QLineEdit(NAVER_NEWS_URL)
        self.url_input.setPlaceholderText("네이버 검색 URL")

        self.limit_input = QSpinBox()
        self.limit_input.setRange(1, 50)
        self.limit_input.setValue(10)

        self.crawl_button = QPushButton("뉴스 크롤링")
        self.crawl_button.clicked.connect(self.start_crawling)
        self.save_button = QPushButton("Excel 저장")
        self.save_button.setEnabled(False)
        self.save_button.clicked.connect(self.save_excel)

        control_layout = QHBoxLayout()
        control_layout.addWidget(QLabel("검색 URL"))
        control_layout.addWidget(self.url_input, 1)
        control_layout.addWidget(QLabel("개수"))
        control_layout.addWidget(self.limit_input)
        control_layout.addWidget(self.crawl_button)
        control_layout.addWidget(self.save_button)

        self.status_label = QLabel("검색 URL을 확인한 후 크롤링을 시작하세요.")
        self.status_label.setStyleSheet("color: #475569; padding: 5px;")

        self.result_table = QTableWidget(0, 5)
        self.result_table.setHorizontalHeaderLabels(
            ["제목", "언론사", "링크", "요약", "본문"]
        )
        self.result_table.setSelectionBehavior(
            QAbstractItemView.SelectionBehavior.SelectRows
        )
        self.result_table.setEditTriggers(
            QAbstractItemView.EditTrigger.NoEditTriggers
        )
        self.result_table.setWordWrap(True)
        self.result_table.horizontalHeader().setStretchLastSection(True)
        self.result_table.setColumnWidth(0, 260)
        self.result_table.setColumnWidth(1, 120)
        self.result_table.setColumnWidth(2, 280)
        self.result_table.setColumnWidth(3, 300)

        layout = QVBoxLayout(self)
        layout.addLayout(control_layout)
        layout.addWidget(self.status_label)
        layout.addWidget(self.result_table)

    def start_crawling(self) -> None:
        if self.thread is not None:
            return

        url = self.url_input.text().strip()
        if not url.startswith(("http://", "https://")):
            QMessageBox.warning(self, "URL 확인", "올바른 URL을 입력하세요.")
            return

        self.crawl_button.setEnabled(False)
        self.save_button.setEnabled(False)
        self.status_label.setText("크롤링 중입니다. 잠시 기다려 주세요...")
        self.thread = QThread()
        self.worker = CrawlWorker(url, self.limit_input.value())
        self.worker.moveToThread(self.thread)
        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.crawling_finished)
        self.worker.failed.connect(self.crawling_failed)
        self.worker.finished.connect(self.thread.quit)
        self.worker.failed.connect(self.thread.quit)
        self.thread.finished.connect(self.thread.deleteLater)
        self.thread.finished.connect(self.clear_thread)
        self.thread.start()

    def crawling_finished(self, articles: list[dict[str, str]]) -> None:
        self.articles = articles
        self.result_table.setRowCount(0)
        for row, article in enumerate(articles):
            self.result_table.insertRow(row)
            values = (
                article.get("title", ""),
                article.get("publisher", ""),
                article.get("link", ""),
                article.get("summary", ""),
                article.get("content", ""),
            )
            for column, value in enumerate(values):
                self.result_table.setItem(row, column, QTableWidgetItem(value))
            self.result_table.setRowHeight(row, 90)

        self.crawl_button.setEnabled(True)
        self.save_button.setEnabled(bool(articles))
        self.status_label.setText(f"{len(articles)}건을 수집했습니다.")
        if not articles:
            QMessageBox.information(self, "검색 결과", "수집된 뉴스가 없습니다.")

    def crawling_failed(self, message: str) -> None:
        self.crawl_button.setEnabled(True)
        self.status_label.setText("크롤링에 실패했습니다.")
        QMessageBox.critical(self, "크롤링 오류", message)

    def save_excel(self) -> None:
        try:
            save_articles_to_excel(self.articles)
        except OSError as error:
            QMessageBox.critical(self, "저장 오류", str(error))
            return
        self.status_label.setText(f"저장 완료: {RESULT_FILE}")
        QMessageBox.information(self, "저장 완료", f"저장했습니다.\n{RESULT_FILE}")

    def clear_thread(self) -> None:
        self.thread = None
        self.worker = None


def main() -> None:
    """Start the PyQt6 news crawler window."""
    application = QApplication([])
    window = NewsWindow()
    window.show()
    application.exec()


if __name__ == "__main__":
    main()
