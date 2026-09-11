"""SQLite CRUD example for product data."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Optional

from openpyxl import Workbook
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
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

DB_PATH = Path(__file__).with_name("products.db")
Product = tuple[int, str, int]


@contextmanager
def get_connection(db_path: Path = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Return a SQLite connection with the Products table ready to use."""
    connection = sqlite3.connect(db_path)
    try:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS Products (
                productID INTEGER PRIMARY KEY AUTOINCREMENT,
                productName TEXT NOT NULL,
                productPrice INTEGER NOT NULL CHECK (productPrice >= 0)
            )
            """
        )
        connection.commit()
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()


def add_product(product_name: str, product_price: int, db_path: Path = DB_PATH) -> int:
    """Insert a product and return its automatically generated ID."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "INSERT INTO Products (productName, productPrice) VALUES (?, ?)",
            (product_name, product_price),
        )
        return int(cursor.lastrowid)


def update_product(
    product_id: int,
    product_name: str,
    product_price: int,
    db_path: Path = DB_PATH,
) -> bool:
    """Update a product and return whether a row was changed."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            """
            UPDATE Products
            SET productName = ?, productPrice = ?
            WHERE productID = ?
            """,
            (product_name, product_price, product_id),
        )
        return cursor.rowcount > 0


def delete_product(product_id: int, db_path: Path = DB_PATH) -> bool:
    """Delete a product and return whether a row was deleted."""
    with get_connection(db_path) as connection:
        cursor = connection.execute(
            "DELETE FROM Products WHERE productID = ?",
            (product_id,),
        )
        return cursor.rowcount > 0


def get_product(product_id: int, db_path: Path = DB_PATH) -> Optional[Product]:
    """Find one product by ID."""
    with get_connection(db_path) as connection:
        row = connection.execute(
            """
            SELECT productID, productName, productPrice
            FROM Products
            WHERE productID = ?
            """,
            (product_id,),
        ).fetchone()
    return row if row is None else (int(row[0]), str(row[1]), int(row[2]))


def get_products(keyword: Optional[str] = None, db_path: Path = DB_PATH) -> list[Product]:
    """Return all products, or products whose names contain keyword."""
    with get_connection(db_path) as connection:
        if keyword:
            rows = connection.execute(
                """
                SELECT productID, productName, productPrice
                FROM Products
                WHERE productName LIKE ?
                ORDER BY productID
                """,
                (f"%{keyword}%",),
            ).fetchall()
        else:
            rows = connection.execute(
                """
                SELECT productID, productName, productPrice
                FROM Products
                ORDER BY productID
                """
            ).fetchall()
    return [(int(row[0]), str(row[1]), int(row[2])) for row in rows]


def export_products_to_excel(products: list[Product], file_path: str) -> None:
    """Save the supplied products to an Excel workbook."""
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Products"
    worksheet.append(["productID", "productName", "productPrice"])
    for product in products:
        worksheet.append(list(product))
    worksheet.column_dimensions["A"].width = 12
    worksheet.column_dimensions["B"].width = 24
    worksheet.column_dimensions["C"].width = 16
    workbook.save(file_path)


class ProductWindow(QWidget):
    """GUI for managing products and exporting the visible list."""

    def __init__(self) -> None:
        super().__init__()
        self.selected_product_id: Optional[int] = None
        self.setWindowTitle("PRODUCTS / 제품 관리")
        self.resize(820, 620)
        self.setStyleSheet(
            """
            QWidget {
                background-color: #111827;
                color: #f8fafc;
                font-family: 'Malgun Gothic';
                font-size: 13px;
            }
            QLabel {
                color: #9ca3af;
                font-weight: bold;
            }
            QLineEdit, QSpinBox {
                background-color: #1f2937;
                border: 1px solid #374151;
                border-radius: 8px;
                padding: 11px 13px;
                color: #f8fafc;
                selection-background-color: #14b8a6;
            }
            QLineEdit:focus, QSpinBox:focus {
                border: 2px solid #2dd4bf;
                padding: 10px 12px;
            }
            QPushButton {
                background-color: #263244;
                border: 1px solid #3b4a60;
                border-radius: 8px;
                padding: 10px 16px;
                color: #e5e7eb;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #334155;
                border-color: #5eead4;
            }
            QPushButton:pressed {
                background-color: #0f766e;
            }
            QTableWidget {
                background-color: #172033;
                alternate-background-color: #1b2639;
                border: 1px solid #334155;
                border-radius: 10px;
                gridline-color: #2c3a50;
                padding: 5px;
                selection-background-color: #115e59;
                selection-color: #ecfeff;
            }
            QHeaderView::section {
                background-color: #0f766e;
                color: #ecfeff;
                border: none;
                padding: 11px 8px;
                font-weight: bold;
            }
            QTableWidget::item {
                padding: 7px;
                border-bottom: 1px solid #263449;
            }
            QScrollBar:vertical {
                background: #172033;
                width: 12px;
                margin: 2px;
            }
            QScrollBar::handle:vertical {
                background: #3b4a60;
                border-radius: 5px;
                min-height: 24px;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QMessageBox {
                background-color: #111827;
            }
            """
        )
        self.build_ui()
        self.refresh_table()

    def build_ui(self) -> None:
        title = QLabel("PRODUCT INVENTORY")
        title.setStyleSheet("color: #5eead4; font-size: 25px; font-weight: 900; letter-spacing: 1px;")
        subtitle = QLabel("SQLite DATA CONTROL  /  제품 데이터 관리")
        subtitle.setStyleSheet("color: #64748b; font-size: 11px; letter-spacing: 1px;")

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("제품명을 입력하세요")
        self.price_input = QSpinBox()
        self.price_input.setRange(0, 2_147_483_647)
        self.price_input.setSuffix(" 원")

        form = QFormLayout()
        form.addRow("제품명", self.name_input)
        form.addRow("제품 가격", self.price_input)

        add_button = QPushButton("입력")
        add_button.clicked.connect(self.add_product_from_form)
        update_button = QPushButton("수정")
        update_button.clicked.connect(self.update_selected_product)
        delete_button = QPushButton("삭제")
        delete_button.clicked.connect(self.delete_selected_product)
        clear_button = QPushButton("입력 초기화")
        clear_button.clicked.connect(self.clear_form)

        action_layout = QHBoxLayout()
        for button in (add_button, update_button, delete_button, clear_button):
            action_layout.addWidget(button)

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("제품명 검색")
        search_button = QPushButton("검색")
        search_button.clicked.connect(self.search_products)
        all_button = QPushButton("전체 조회")
        all_button.clicked.connect(self.refresh_table)
        excel_button = QPushButton("엑셀 저장")
        excel_button.setStyleSheet(
            "QPushButton { background-color: #f97316; border-color: #fb923c; color: white; }"
            "QPushButton:hover { background-color: #ea580c; }"
        )
        excel_button.clicked.connect(self.save_excel)

        search_layout = QHBoxLayout()
        search_layout.addWidget(QLabel("검색"))
        search_layout.addWidget(self.search_input)
        search_layout.addWidget(search_button)
        search_layout.addWidget(all_button)
        search_layout.addWidget(excel_button)

        self.product_table = QTableWidget(0, 3)
        self.product_table.setHorizontalHeaderLabels(["ID", "제품명", "가격"])
        self.product_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.product_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.product_table.horizontalHeader().setStretchLastSection(True)
        self.product_table.cellClicked.connect(self.select_product)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(28, 24, 28, 28)
        layout.setSpacing(14)
        layout.addWidget(title)
        layout.addWidget(subtitle)
        layout.addLayout(form)
        layout.addLayout(action_layout)
        layout.addLayout(search_layout)
        layout.addWidget(self.product_table)

    def refresh_table(self, products: Optional[list[Product]] = None) -> None:
        products = get_products() if products is None else products
        self.product_table.setRowCount(0)
        for row, product in enumerate(products):
            self.product_table.insertRow(row)
            for column, value in enumerate(product):
                item = QTableWidgetItem(str(value))
                if column in (0, 2):
                    item.setTextAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
                self.product_table.setItem(row, column, item)

    def read_form(self) -> Optional[tuple[str, int]]:
        product_name = self.name_input.text().strip()
        if not product_name:
            QMessageBox.warning(self, "입력 확인", "제품명을 입력하세요.")
            self.name_input.setFocus()
            return None
        return product_name, self.price_input.value()

    def add_product_from_form(self) -> None:
        product = self.read_form()
        if product is None:
            return
        add_product(*product)
        self.refresh_table()
        self.clear_form()

    def update_selected_product(self) -> None:
        if self.selected_product_id is None:
            QMessageBox.information(self, "제품 선택", "수정할 제품을 목록에서 선택하세요.")
            return
        product = self.read_form()
        if product is None:
            return
        update_product(self.selected_product_id, *product)
        self.refresh_table()
        self.clear_form()

    def delete_selected_product(self) -> None:
        if self.selected_product_id is None:
            QMessageBox.information(self, "제품 선택", "삭제할 제품을 목록에서 선택하세요.")
            return
        answer = QMessageBox.question(self, "삭제 확인", "선택한 제품을 삭제하시겠습니까?")
        if answer == QMessageBox.StandardButton.Yes:
            delete_product(self.selected_product_id)
            self.refresh_table()
            self.clear_form()

    def search_products(self) -> None:
        self.refresh_table(get_products(self.search_input.text().strip() or None))

    def select_product(self, row: int, _column: int) -> None:
        self.selected_product_id = int(self.product_table.item(row, 0).text())
        self.name_input.setText(self.product_table.item(row, 1).text())
        self.price_input.setValue(int(self.product_table.item(row, 2).text()))

    def clear_form(self) -> None:
        self.selected_product_id = None
        self.name_input.clear()
        self.price_input.setValue(0)
        self.product_table.clearSelection()

    def save_excel(self) -> None:
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "엑셀 파일 저장",
            str(Path.home() / "products.xlsx"),
            "Excel 파일 (*.xlsx)",
        )
        if not file_path:
            return
        try:
            export_products_to_excel(get_products(self.search_input.text().strip() or None), file_path)
        except OSError as error:
            QMessageBox.critical(self, "저장 실패", f"엑셀 파일을 저장할 수 없습니다.\n{error}")
            return
        QMessageBox.information(self, "저장 완료", f"엑셀 파일을 저장했습니다.\n{file_path}")


def main() -> None:
    """Start the PyQt6 product management window."""
    application = QApplication([])
    window = ProductWindow()
    window.show()
    application.exec()


if __name__ == "__main__":
    main()
