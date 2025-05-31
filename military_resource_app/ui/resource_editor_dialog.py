#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог редагування/створення ресурсу.
"""

import os
import shutil
import time
from datetime import datetime
from typing import Dict, Any, Optional

from PyQt6 import QtCore, QtGui, QtWidgets

class ResourceEditor(QtWidgets.QDialog):
    def __init__(self, conn, category: str, data: Optional[Dict[str, Any]] = None):
        super().__init__()
        self.conn = conn
        self.category = category
        self.data = data or {}
        self.image_path = self.data.get("image_path", "")
        
        self.setup_ui()
        self.load_data()

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setWindowTitle("Редагування ресурсу" if self.data else "Новий ресурс")
        self.setMinimumWidth(500)

        layout = QtWidgets.QVBoxLayout(self)

        # Основна форма
        form = QtWidgets.QFormLayout()
        
        # Назва
        self.name = QtWidgets.QLineEdit()
        form.addRow("Назва:", self.name)

        # Кількість та одиниця виміру
        qty_layout = QtWidgets.QHBoxLayout()
        self.quantity = QtWidgets.QSpinBox()
        self.quantity.setRange(0, 1_000_000)
        self.unit = QtWidgets.QComboBox()
        self.unit.setEditable(True)
        self.unit.addItems(["шт", "кг", "л", "м", "уп", "компл"])
        qty_layout.addWidget(self.quantity)
        qty_layout.addWidget(self.unit)
        form.addRow("Кількість:", qty_layout)

        # Опис
        self.description = QtWidgets.QTextEdit()
        self.description.setMaximumHeight(100)
        form.addRow("Опис:", self.description)

        # Постачальник
        self.supplier = QtWidgets.QLineEdit()
        form.addRow("Постачальник:", self.supplier)

        # Телефон
        self.phone = QtWidgets.QLineEdit()
        self.phone.setInputMask("+38(999)999-99-99")
        form.addRow("Телефон:", self.phone)

        # Походження
        self.origin = QtWidgets.QLineEdit()
        form.addRow("Походження:", self.origin)

        # Дата надходження
        self.arrival_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.arrival_date.setCalendarPopup(True)
        form.addRow("Дата надходження:", self.arrival_date)

        # Термін придатності
        self.expiration_date = QtWidgets.QDateEdit(QtCore.QDate.currentDate())
        self.expiration_date.setCalendarPopup(True)
        exp_layout = QtWidgets.QHBoxLayout()
        exp_layout.addWidget(self.expiration_date)
        self.no_expiration = QtWidgets.QCheckBox("Безстроково")
        self.no_expiration.toggled.connect(
            lambda checked: self.expiration_date.setEnabled(not checked)
        )
        exp_layout.addWidget(self.no_expiration)
        form.addRow("Термін придатності:", exp_layout)

        # Вартість
        self.cost = QtWidgets.QDoubleSpinBox()
        self.cost.setRange(0, 1_000_000)
        self.cost.setDecimals(2)
        self.cost.setSuffix(" грн")
        form.addRow("Вартість:", self.cost)

        # Поріг для сповіщень
        self.threshold = QtWidgets.QSpinBox()
        self.threshold.setRange(0, 1_000)
        self.threshold.setValue(10)
        form.addRow("Поріг сповіщення:", self.threshold)

        layout.addLayout(form)

        # Фото
        photo_layout = QtWidgets.QHBoxLayout()
        
        self.preview = QtWidgets.QLabel()
        self.preview.setFixedSize(200, 200)
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setStyleSheet("border: 2px dashed #FFD700;")
        photo_layout.addWidget(self.preview)

        photo_buttons = QtWidgets.QVBoxLayout()
        select_btn = QtWidgets.QPushButton("Обрати фото")
        select_btn.clicked.connect(self.select_image)
        clear_btn = QtWidgets.QPushButton("Очистити")
        clear_btn.clicked.connect(self.clear_image)
        photo_buttons.addWidget(select_btn)
        photo_buttons.addWidget(clear_btn)
        photo_buttons.addStretch()
        photo_layout.addLayout(photo_buttons)

        layout.addLayout(photo_layout)

        # Кнопки
        buttons = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        buttons.accepted.connect(self.validate_and_accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def load_data(self):
        """Завантаження даних для редагування."""
        if not self.data:
            return

        self.name.setText(self.data.get("name", ""))
        self.quantity.setValue(int(self.data.get("quantity", 0)))
        self.description.setText(self.data.get("description", ""))
        self.supplier.setText(self.data.get("supplier", ""))
        self.phone.setText(self.data.get("phone", ""))
        self.origin.setText(self.data.get("origin", ""))
        self.unit.setCurrentText(self.data.get("unit_of_measure", "шт"))
        
        if self.data.get("arrival_date"):
            self.arrival_date.setDate(
                QtCore.QDate.fromString(self.data["arrival_date"], "yyyy-MM-dd")
            )
            
        if self.data.get("expiration_date"):
            self.expiration_date.setDate(
                QtCore.QDate.fromString(self.data["expiration_date"], "yyyy-MM-dd")
            )
        else:
            self.no_expiration.setChecked(True)
            
        self.cost.setValue(float(self.data.get("cost", 0)))
        self.threshold.setValue(int(self.data.get("low_stock_threshold", 10)))
        
        # Завантаження фото
        if self.image_path and os.path.exists(self.image_path):
            self.update_preview()

    def select_image(self):
        """Вибір зображення."""
        file_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self,
            "Обрати фото",
            "",
            "Зображення (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        
        if file_path:
            # Створення директорії для зображень
            os.makedirs("assets/images", exist_ok=True)
            
            # Генерація нового імені файлу
            ext = os.path.splitext(file_path)[1]
            new_name = f"img_{int(time.time())}{ext}"
            new_path = os.path.join("assets/images", new_name)
            
            # Копіювання файлу
            shutil.copy2(file_path, new_path)
            self.image_path = new_path
            self.update_preview()

    def clear_image(self):
        """Очищення зображення."""
        self.image_path = ""
        self.preview.setPixmap(QtGui.QPixmap())
        self.preview.setText("Немає фото")

    def update_preview(self):
        """Оновлення попереднього перегляду."""
        if not self.image_path or not os.path.exists(self.image_path):
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText("Немає фото")
            return

        pixmap = QtGui.QPixmap(self.image_path)
        scaled = pixmap.scaled(
            self.preview.size(),
            QtCore.Qt.AspectRatioMode.KeepAspectRatio,
            QtCore.Qt.TransformationMode.SmoothTransformation
        )
        self.preview.setPixmap(scaled)

    def validate_and_accept(self):
        """Перевірка та прийняття даних."""
        name = self.name.text().strip()
        if not name:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Введіть назву ресурсу")
            return

        if self.quantity.value() < 0:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Кількість не може бути від'ємною")
            return

        self.accept()

    def get_data(self) -> Dict[str, Any]:
        """Отримання даних з форми."""
        return {
            "name": self.name.text().strip(),
            "quantity": self.quantity.value(),
            "unit_of_measure": self.unit.currentText(),
            "description": self.description.toPlainText().strip(),
            "supplier": self.supplier.text().strip(),
            "phone": self.phone.text().strip(),
            "origin": self.origin.text().strip(),
            "arrival_date": self.arrival_date.date().toString("yyyy-MM-dd"),
            "expiration_date": (
                None if self.no_expiration.isChecked()
                else self.expiration_date.date().toString("yyyy-MM-dd")
            ),
            "cost": self.cost.value(),
            "low_stock_threshold": self.threshold.value(),
            "image_path": self.image_path
        } 