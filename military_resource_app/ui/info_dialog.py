#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог перегляду інформації про ресурс.
"""

import os
from datetime import datetime
from PyQt6 import QtCore, QtGui, QtWidgets

class InfoDialog(QtWidgets.QDialog):
    def __init__(self, conn, resource_id: int):
        super().__init__()
        self.conn = conn
        self.resource_id = resource_id
        self.data = self.load_resource_data()
        self.setup_ui()
        self.load_data()

    def load_resource_data(self):
        """Завантаження даних про ресурс."""
        return dict(self.conn.execute("""
            SELECT r.*, c.name as category_name
            FROM resources r
            JOIN categories c ON r.category_id = c.id
            WHERE r.id = ?
        """, (self.resource_id,)).fetchone())

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setWindowTitle(f"Інформація про ресурс: {self.data['name']}")
        self.setMinimumWidth(800)

        layout = QtWidgets.QHBoxLayout(self)

        # Ліва частина - основна інформація
        left_widget = QtWidgets.QWidget()
        left_layout = QtWidgets.QVBoxLayout(left_widget)

        # Основні дані
        info_group = QtWidgets.QGroupBox("Основна інформація")
        info_layout = QtWidgets.QFormLayout(info_group)
        
        self.labels = {}
        for field, label in [
            ("name", "Назва"),
            ("category_name", "Категорія"),
            ("quantity", "Кількість"),
            ("unit_of_measure", "Одиниця виміру"),
            ("description", "Опис"),
            ("supplier", "Постачальник"),
            ("phone", "Телефон"),
            ("origin", "Походження"),
            ("arrival_date", "Дата надходження"),
            ("expiration_date", "Термін придатності"),
            ("cost", "Вартість"),
            ("low_stock_threshold", "Поріг сповіщення")
        ]:
            self.labels[field] = QtWidgets.QLabel()
            info_layout.addRow(f"{label}:", self.labels[field])

        left_layout.addWidget(info_group)

        # Історія транзакцій
        history_group = QtWidgets.QGroupBox("Історія транзакцій")
        history_layout = QtWidgets.QVBoxLayout(history_group)
        
        self.history_table = QtWidgets.QTableWidget()
        self.history_table.setColumnCount(5)
        self.history_table.setHorizontalHeaderLabels([
            "Дата", "Тип", "Кількість", "Отримувач", "Примітки"
        ])
        self.history_table.horizontalHeader().setSectionResizeMode(
            QtWidgets.QHeaderView.ResizeMode.Stretch
        )
        history_layout.addWidget(self.history_table)
        
        left_layout.addWidget(history_group)
        layout.addWidget(left_widget)

        # Права частина - фото та графіки
        right_widget = QtWidgets.QWidget()
        right_layout = QtWidgets.QVBoxLayout(right_widget)

        # Фото
        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(300, 300)
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("border: 2px solid #FFD700;")
        right_layout.addWidget(self.preview)

        # Графік руху
        chart_group = QtWidgets.QGroupBox("Графік руху")
        chart_layout = QtWidgets.QVBoxLayout(chart_group)
        self.chart_view = QtWidgets.QLabel("Графік руху ресурсу")
        self.chart_view.setFixedSize(300, 200)
        self.chart_view.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.chart_view.setStyleSheet("border: 1px solid #FFD700;")
        chart_layout.addWidget(self.chart_view)
        right_layout.addWidget(chart_group)

        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Close
        )
        buttons.rejected.connect(self.reject)
        right_layout.addWidget(buttons)

        layout.addWidget(right_widget)

    def load_data(self):
        """Завантаження даних у форму."""
        # Основна інформація
        self.labels["name"].setText(self.data["name"])
        self.labels["category_name"].setText(self.data["category_name"])
        self.labels["quantity"].setText(str(self.data["quantity"]))
        self.labels["unit_of_measure"].setText(self.data.get("unit_of_measure", "шт"))
        self.labels["description"].setText(self.data.get("description", ""))
        self.labels["supplier"].setText(self.data.get("supplier", ""))
        self.labels["phone"].setText(self.data.get("phone", ""))
        self.labels["origin"].setText(self.data.get("origin", ""))
        self.labels["arrival_date"].setText(self.data.get("arrival_date", ""))
        self.labels["expiration_date"].setText(
            self.data.get("expiration_date", "Безстроково")
        )
        self.labels["cost"].setText(
            f"{self.data.get('cost', 0):.2f} грн" if self.data.get("cost") else "-"
        )
        self.labels["low_stock_threshold"].setText(
            str(self.data.get("low_stock_threshold", 10))
        )

        # Фото
        if self.data.get("image_path") and os.path.exists(self.data["image_path"]):
            pixmap = QtGui.QPixmap(self.data["image_path"])
            scaled = pixmap.scaled(
                self.preview.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.preview.setPixmap(scaled)
        else:
            self.preview.setText("Фото відсутнє")

        # Історія транзакцій
        transactions = self.conn.execute("""
            SELECT t.transaction_date, t.transaction_type,
                   t.quantity_changed, t.recipient_department,
                   t.notes, u.username as issued_by
            FROM resource_transactions t
            LEFT JOIN users u ON t.issued_by_user_id = u.id
            WHERE t.resource_id = ?
            ORDER BY t.transaction_date DESC
        """, (self.resource_id,)).fetchall()

        self.history_table.setRowCount(len(transactions))
        for row, t in enumerate(transactions):
            self.history_table.setItem(
                row, 0,
                QtWidgets.QTableWidgetItem(
                    datetime.strptime(t["transaction_date"], "%Y-%m-%d %H:%M:%S")
                    .strftime("%d.%m.%Y %H:%M")
                )
            )
            self.history_table.setItem(
                row, 1,
                QtWidgets.QTableWidgetItem(t["transaction_type"])
            )
            self.history_table.setItem(
                row, 2,
                QtWidgets.QTableWidgetItem(str(t["quantity_changed"]))
            )
            self.history_table.setItem(
                row, 3,
                QtWidgets.QTableWidgetItem(t["recipient_department"] or "-")
            )
            notes = []
            if t["notes"]:
                notes.append(t["notes"])
            if t["issued_by"]:
                notes.append(f"Виконав: {t['issued_by']}")
            self.history_table.setItem(
                row, 4,
                QtWidgets.QTableWidgetItem(" | ".join(notes) if notes else "-")
            ) 