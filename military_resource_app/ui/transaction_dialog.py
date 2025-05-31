#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог для створення нової транзакції.
"""

from datetime import datetime
from typing import Dict, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

from logic.db_manager import CATEGORIES
from logic.transaction_handler import TransactionHandler, TransactionError

class TransactionDialog(QtWidgets.QDialog):
    def __init__(
        self,
        conn,
        user_id: int,
        resource_id: Optional[int] = None,
        category: Optional[str] = None
    ):
        super().__init__()
        self.conn = conn
        self.user_id = user_id
        self.resource_id = resource_id
        self.category = category
        self.transaction_handler = TransactionHandler(conn)
        
        self.setup_ui()
        if resource_id:
            self.load_resource_data()

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setWindowTitle("Нова транзакція")
        self.setMinimumWidth(400)

        layout = QtWidgets.QVBoxLayout(self)

        # Форма
        form = QtWidgets.QFormLayout()

        # Категорія
        self.category_combo = QtWidgets.QComboBox()
        self.category_combo.addItems(CATEGORIES)
        if self.category:
            self.category_combo.setCurrentText(self.category)
        self.category_combo.currentIndexChanged.connect(self.load_resources)
        form.addRow("Категорія:", self.category_combo)

        # Ресурс
        self.resource_combo = QtWidgets.QComboBox()
        form.addRow("Ресурс:", self.resource_combo)

        # Тип транзакції
        self.type_combo = QtWidgets.QComboBox()
        self.type_combo.addItems(TransactionHandler.VALID_TRANSACTION_TYPES.keys())
        self.type_combo.currentTextChanged.connect(self.on_type_changed)
        form.addRow("Тип:", self.type_combo)

        # Кількість
        self.quantity = QtWidgets.QSpinBox()
        self.quantity.setRange(1, 1_000_000)
        self.quantity.setValue(1)
        form.addRow("Кількість:", self.quantity)

        # Підрозділ-отримувач
        self.department = QtWidgets.QComboBox()
        self.department.setEditable(True)
        self.department.addItems(self.load_departments())
        form.addRow("Підрозділ:", self.department)

        # Дата
        self.date = QtWidgets.QDateTimeEdit(QtCore.QDateTime.currentDateTime())
        self.date.setCalendarPopup(True)
        form.addRow("Дата:", self.date)

        # Примітки
        self.notes = QtWidgets.QTextEdit()
        self.notes.setMaximumHeight(100)
        form.addRow("Примітки:", self.notes)

        layout.addLayout(form)

        # Інформація про наявність
        self.info_label = QtWidgets.QLabel()
        self.info_label.setStyleSheet("color: #FFD700;")
        layout.addWidget(self.info_label)

        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        # Завантаження ресурсів
        self.load_resources()

    def load_departments(self) -> list:
        """Завантаження списку підрозділів з історії транзакцій."""
        departments = self.conn.execute("""
            SELECT DISTINCT recipient_department
            FROM resource_transactions
            WHERE recipient_department IS NOT NULL
            ORDER BY recipient_department
        """).fetchall()
        return [d["recipient_department"] for d in departments]

    def load_resources(self):
        """Завантаження списку ресурсів для вибраної категорії."""
        self.resource_combo.clear()
        
        category = self.category_combo.currentText()
        resources = self.conn.execute("""
            SELECT r.id, r.name, r.quantity, r.unit_of_measure
            FROM resources r
            JOIN categories c ON r.category_id = c.id
            WHERE c.name = ?
            ORDER BY r.name
        """, (category,)).fetchall()

        for r in resources:
            self.resource_combo.addItem(
                f"{r['name']} ({r['quantity']} {r['unit_of_measure']})",
                r["id"]
            )

        if self.resource_id:
            index = self.resource_combo.findData(self.resource_id)
            if index >= 0:
                self.resource_combo.setCurrentIndex(index)

        self.update_info_label()
        
    def load_resource_data(self):
        """Завантаження даних про конкретний ресурс."""
        resource = self.conn.execute("""
            SELECT r.*, c.name as category_name
            FROM resources r
            JOIN categories c ON r.category_id = c.id
            WHERE r.id = ?
        """, (self.resource_id,)).fetchone()

        if resource:
            index = self.category_combo.findText(resource["category_name"])
            if index >= 0:
                self.category_combo.setCurrentIndex(index)
                self.load_resources()

    def on_type_changed(self, transaction_type: str):
        """Обробка зміни типу транзакції."""
        # Показуємо/приховуємо поле підрозділу
        show_department = transaction_type in ('видача', 'повернення')
        self.department.setEnabled(show_department)
        self.department.setVisible(show_department)
        self.layout().labelForField(self.department).setVisible(show_department)

    def update_info_label(self):
        """Оновлення інформації про наявність ресурсу."""
        resource_id = self.resource_combo.currentData()
        if not resource_id:
            self.info_label.clear()
            return

        resource = self.conn.execute("""
            SELECT name, quantity, unit_of_measure, low_stock_threshold
            FROM resources
            WHERE id = ?
        """, (resource_id,)).fetchone()

        if resource:
            status = (
                "Критично мало"
                if resource["quantity"] < resource["low_stock_threshold"]
                else "Достатньо"
            )
            self.info_label.setText(
                f"В наявності: {resource['quantity']} {resource['unit_of_measure']} "
                f"({status})"
            )

    def validate_and_accept(self):
        """Перевірка та збереження транзакції."""
        resource_id = self.resource_combo.currentData()
        if not resource_id:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Виберіть ресурс")
            return

        transaction_type = self.type_combo.currentText()
        if transaction_type in ('видача', 'повернення'):
            department = self.department.currentText().strip()
            if not department:
                QtWidgets.QMessageBox.warning(
                    self,
                    "Помилка",
                    "Вкажіть підрозділ"
                )
                return
        else:
            department = None

        try:
            success, message = self.transaction_handler.add_transaction(
                resource_id=resource_id,
                transaction_type=transaction_type,
                quantity_changed=self.quantity.value(),
                issued_by_user_id=self.user_id,
                recipient_department=department,
                notes=self.notes.toPlainText().strip() or None,
                transaction_date=self.date.dateTime().toString("yyyy-MM-dd HH:mm:ss")
            )

            if success:
                self.accept()
            else:
                QtWidgets.QMessageBox.warning(self, "Помилка", message)

        except TransactionError as e:
            QtWidgets.QMessageBox.warning(self, "Помилка", str(e))

    def get_data(self) -> Dict:
        """Отримання даних транзакції."""
        return {
            "resource_id": self.resource_combo.currentData(),
            "resource_name": self.resource_combo.currentText().split(" (")[0],
            "transaction_type": self.type_combo.currentText(),
            "quantity": self.quantity.value(),
            "department": (
                self.department.currentText().strip()
                if self.department.isEnabled()
                else None
            ),
            "date": self.date.dateTime().toString("yyyy-MM-dd HH:mm:ss"),
            "notes": self.notes.toPlainText().strip() or None
        } 