"""
Модальное окно справки по G-кодам.
Загружает документацию из gcode.md в корне проекта.
"""
from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QColor, QTextCharFormat, QTextCursor, QTextDocument
from PyQt6.QtWidgets import (
    QDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTextBrowser,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from app.utils.logger import get_logger

logger = get_logger()

_LOAD_ERROR_MESSAGE = "Не удалось загрузить документацию G-code"


def get_gcode_doc_path() -> Path:
    """Путь к gcode.md: корень проекта относительно модуля или текущая рабочая директория."""
    project_root = Path(__file__).resolve().parents[2]
    candidates = [
        project_root / "gcode.md",
        Path.cwd() / "gcode.md",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return candidates[0]


class HelpDialog(QDialog):
    """Диалог справки с Markdown-документацией и поиском по тексту."""

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.setObjectName("HelpDialog")
        self.setWindowTitle("Помощь — G-коды")
        self.setMinimumSize(700, 500)
        self.resize(900, 650)

        self._search_positions: List[QTextCursor] = []
        self._current_match_index = -1

        self._init_ui()
        self._load_documentation()

    def _init_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)

        header = QHBoxLayout()
        title = QLabel("Документация по G-кодам")
        title.setObjectName("HelpDialogTitle")
        header.addWidget(title)
        header.addStretch()

        close_btn = QPushButton("×")
        close_btn.setObjectName("HelpDialogCloseButton")
        close_btn.setFixedSize(32, 32)
        close_btn.setToolTip("Закрыть")
        close_btn.clicked.connect(self.accept)
        header.addWidget(close_btn)
        layout.addLayout(header)

        search_row = QHBoxLayout()
        search_row.setSpacing(6)
        search_label = QLabel("Поиск:")
        self.search_field = QLineEdit()
        self.search_field.setObjectName("HelpDialogSearchField")
        self.search_field.setPlaceholderText("Введите текст для поиска…")
        self.search_field.setClearButtonEnabled(True)
        self.search_field.textChanged.connect(self._on_search_changed)
        self.search_field.returnPressed.connect(self._find_next)

        self.search_status = QLabel("")
        self.search_status.setObjectName("HelpDialogSearchStatus")
        self.search_status.setMinimumWidth(80)

        self.prev_btn = QPushButton("◀")
        self.prev_btn.setObjectName("HelpDialogNavButton")
        self.prev_btn.setFixedWidth(36)
        self.prev_btn.setToolTip("Предыдущее совпадение")
        self.prev_btn.clicked.connect(self._find_prev)

        self.next_btn = QPushButton("▶")
        self.next_btn.setObjectName("HelpDialogNavButton")
        self.next_btn.setFixedWidth(36)
        self.next_btn.setToolTip("Следующее совпадение")
        self.next_btn.clicked.connect(self._find_next)

        search_row.addWidget(search_label)
        search_row.addWidget(self.search_field, 1)
        search_row.addWidget(self.search_status)
        search_row.addWidget(self.prev_btn)
        search_row.addWidget(self.next_btn)
        layout.addLayout(search_row)

        self.content_browser = QTextBrowser()
        self.content_browser.setObjectName("HelpDialogContent")
        self.content_browser.setOpenExternalLinks(False)
        self.content_browser.setLineWrapMode(QTextEdit.LineWrapMode.WidgetWidth)
        layout.addWidget(self.content_browser, 1)

    def _load_documentation(self) -> None:
        path = get_gcode_doc_path()
        try:
            if not path.is_file():
                raise FileNotFoundError(f"Файл не найден: {path}")
            markdown_text = path.read_text(encoding="utf-8")
            self.content_browser.setMarkdown(markdown_text)
            logger.info("Справка загружена из %s", path)
        except Exception as exc:
            logger.error("Не удалось загрузить gcode.md: %s", exc)
            self.content_browser.setPlainText(_LOAD_ERROR_MESSAGE)

    def _on_search_changed(self, text: str) -> None:
        query = text.strip()
        self._search_positions.clear()
        self._current_match_index = -1
        self.content_browser.setExtraSelections([])

        if not query:
            self.search_status.setText("")
            self.prev_btn.setEnabled(False)
            self.next_btn.setEnabled(False)
            return

        doc = self.content_browser.document()
        cursor = QTextCursor(doc)
        cursor.movePosition(QTextCursor.MoveOperation.Start)

        highlight_fmt = QTextCharFormat()
        highlight_fmt.setBackground(QColor("#fff3cd"))

        extra_selections: List[QTextEdit.ExtraSelection] = []
        flags = QTextDocument.FindFlag(0)

        while True:
            found = doc.find(query, cursor, flags)
            if found.isNull():
                break
            selection = QTextEdit.ExtraSelection()
            selection.format = highlight_fmt
            selection.cursor = found
            extra_selections.append(selection)
            self._search_positions.append(QTextCursor(found))
            cursor = found

        count = len(extra_selections)
        if count:
            self.search_status.setText(f"{count} совпад.")
            self._current_match_index = 0
            self._apply_current_match_highlight(extra_selections)
            self._scroll_to_match(self._current_match_index)
        else:
            self.search_status.setText("не найдено")

        self.content_browser.setExtraSelections(extra_selections)
        self.prev_btn.setEnabled(count > 1)
        self.next_btn.setEnabled(count > 1)

    def _apply_current_match_highlight(
        self, extra_selections: List[QTextEdit.ExtraSelection]
    ) -> None:
        if self._current_match_index < 0 or self._current_match_index >= len(extra_selections):
            return
        current_fmt = QTextCharFormat()
        current_fmt.setBackground(QColor("#ffc107"))
        extra_selections[self._current_match_index].format = current_fmt

    def _scroll_to_match(self, index: int) -> None:
        if index < 0 or index >= len(self._search_positions):
            return
        cursor = self._search_positions[index]
        self.content_browser.setTextCursor(cursor)
        self.content_browser.ensureCursorVisible()

    def _find_next(self) -> None:
        if not self._search_positions:
            return
        self._current_match_index = (self._current_match_index + 1) % len(self._search_positions)
        self._refresh_match_highlight()
        self._scroll_to_match(self._current_match_index)
        self.search_status.setText(
            f"{self._current_match_index + 1} из {len(self._search_positions)}"
        )

    def _find_prev(self) -> None:
        if not self._search_positions:
            return
        self._current_match_index = (self._current_match_index - 1) % len(self._search_positions)
        self._refresh_match_highlight()
        self._scroll_to_match(self._current_match_index)
        self.search_status.setText(
            f"{self._current_match_index + 1} из {len(self._search_positions)}"
        )

    def _refresh_match_highlight(self) -> None:
        extra_selections = self.content_browser.extraSelections()
        if not extra_selections:
            return
        highlight_fmt = QTextCharFormat()
        highlight_fmt.setBackground(QColor("#fff3cd"))
        for selection in extra_selections:
            selection.format = highlight_fmt
        self._apply_current_match_highlight(extra_selections)
        self.content_browser.setExtraSelections(extra_selections)
