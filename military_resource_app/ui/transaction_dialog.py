#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог для створення та редагування транзакцій ресурсів.
"""

import sys
import os
from datetime import datetime
from PyQt6 import QtCore, QtGui, QtWidgets
import sqlite3

# Налаштування шляху для імпорту модулів
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.db_manager import create_connection

class TransactionDialog(QtWidgets.QDialog):
    def __init__(self, current_user_id: int, parent=None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.setWindowTitle("Реєстрація транзакції")
        self.setModal(True)
        self.resize(500, 400)
        
        self._setup_ui()
        self._load_resources_data()
        self._setup_connections()

    def _setup_ui(self):
        """Налаштовує інтерфейс користувача."""
        layout = QtWidgets.QVBoxLayout(self)
        
        # Група для типу транзакції
        transaction_type_group = QtWidgets.QGroupBox("Тип транзакції")
        transaction_type_layout = QtWidgets.QHBoxLayout()
        
        self.transaction_type_combo = QtWidgets.QComboBox()
        self.transaction_type_combo.addItems(["Надходження", "Видача", "Списання"])
        transaction_type_layout.addWidget(QtWidgets.QLabel("Тип:"))
        transaction_type_layout.addWidget(self.transaction_type_combo)
        transaction_type_group.setLayout(transaction_type_layout)
        layout.addWidget(transaction_type_group)

        # Група для вибору ресурсу
        resource_group = QtWidgets.QGroupBox("Ресурс")
        resource_layout = QtWidgets.QGridLayout()
        
        # Комбо-бокс для категорій
        self.category_combo = QtWidgets.QComboBox()
        resource_layout.addWidget(QtWidgets.QLabel("Категорія:"), 0, 0)
        resource_layout.addWidget(self.category_combo, 0, 1)
        
        # Комбо-бокс для ресурсів
        self.resource_combo = QtWidgets.QComboBox()
        resource_layout.addWidget(QtWidgets.QLabel("Ресурс:"), 1, 0)
        resource_layout.addWidget(self.resource_combo, 1, 1)
        
        # Поле для кількості
        self.quantity_spin = QtWidgets.QSpinBox()
        self.quantity_spin.setMinimum(1)
        self.quantity_spin.setMaximum(9999)
        resource_layout.addWidget(QtWidgets.QLabel("Кількість:"), 2, 0)
        resource_layout.addWidget(self.quantity_spin, 2, 1)
        
        resource_group.setLayout(resource_layout)
        layout.addWidget(resource_group)

        # Група для додаткової інформації
        details_group = QtWidgets.QGroupBox("Додаткова інформація")
        details_layout = QtWidgets.QGridLayout()
        
        # Поле для відділу/отримувача
        self.department_edit = QtWidgets.QLineEdit()
        details_layout.addWidget(QtWidgets.QLabel("Відділ/Отримувач:"), 0, 0)
        details_layout.addWidget(self.department_edit, 0, 1)
        
        # Поле для документа-підстави
        self.document_edit = QtWidgets.QLineEdit()
        details_layout.addWidget(QtWidgets.QLabel("Документ-підстава:"), 1, 0)
        details_layout.addWidget(self.document_edit, 1, 1)
        
        # Поле для приміток
        self.notes_edit = QtWidgets.QTextEdit()
        self.notes_edit.setMaximumHeight(60)
        details_layout.addWidget(QtWidgets.QLabel("Примітки:"), 2, 0)
        details_layout.addWidget(self.notes_edit, 2, 1)
        
        details_group.setLayout(details_layout)
        layout.addWidget(details_group)

        # Кнопки
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok | 
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)

    def _setup_connections(self):
        """Налаштовує з'єднання сигналів і слотів."""
        self.category_combo.currentIndexChanged.connect(self._on_category_changed)
        self.transaction_type_combo.currentIndexChanged.connect(self._on_transaction_type_changed)

    def _load_resources_data(self):
        """Завантажує дані про категорії та ресурси."""
        conn = None
        try:
            conn = create_connection()
            if conn:
                # Завантаження категорій
                cur = conn.cursor()
                cur.execute("SELECT id, name FROM categories ORDER BY name")
                categories = cur.fetchall()
                
                self.category_combo.clear()
                self.category_combo.addItem("Оберіть категорію", None)
                for category in categories:
                    self.category_combo.addItem(category['name'], category['id'])
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Помилка завантаження даних: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def _on_category_changed(self, index):
        """Обробник зміни вибраної категорії."""
        category_id = self.category_combo.currentData()
        self._load_resources_for_category(category_id)

    def _load_resources_for_category(self, category_id):
        """Завантажує ресурси для вибраної категорії."""
        if not category_id:
            self.resource_combo.clear()
            return

        conn = None
        try:
            conn = create_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("""
                    SELECT id, name, quantity, unit_of_measure 
                    FROM resources 
                    WHERE category_id = ?
                    ORDER BY name
                """, (category_id,))
                resources = cur.fetchall()
                
                self.resource_combo.clear()
                self.resource_combo.addItem("Оберіть ресурс", None)
                for resource in resources:
                    display_text = f"{resource['name']} ({resource['quantity']} {resource['unit_of_measure']})"
                    self.resource_combo.addItem(display_text, resource['id'])
                
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Помилка завантаження ресурсів: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def _on_transaction_type_changed(self, index):
        """Обробник зміни типу транзакції."""
        transaction_type = self.transaction_type_combo.currentText()
        
        # Налаштування полів відповідно до типу транзакції
        if transaction_type == "Надходження":
            self.department_edit.setPlaceholderText("Постачальник")
            self.document_edit.setPlaceholderText("Номер накладної")
        elif transaction_type == "Видача":
            self.department_edit.setPlaceholderText("Відділ/Отримувач")
            self.document_edit.setPlaceholderText("Номер вимоги")
        else:  # Списання
            self.department_edit.setPlaceholderText("Підрозділ")
            self.document_edit.setPlaceholderText("Номер акту списання")

    def accept(self):
        """Обробляє підтвердження діалогу."""
        try:
            # Перевірка введених даних
            if not self._validate_input():
                return
            
            # Збереження транзакції
            if self._save_transaction():
                super().accept()  # Закриваємо діалог тільки після успішного збереження
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Неочікувана помилка при створенні транзакції: {str(e)}"
            )
            return

    def _validate_input(self) -> bool:
        """Перевіряє коректність введених даних."""
        if not self.resource_combo.currentData():
            QtWidgets.QMessageBox.warning(
                self,
                "Помилка валідації",
                "Будь ласка, оберіть ресурс"
            )
            return False
            
        if not self.department_edit.text().strip():
            QtWidgets.QMessageBox.warning(
                self,
                "Помилка валідації",
                "Будь ласка, вкажіть відділ/отримувача"
            )
            return False
            
        if not self.document_edit.text().strip():
            QtWidgets.QMessageBox.warning(
                self,
                "Помилка валідації",
                "Будь ласка, вкажіть документ-підставу"
            )
            return False
            
        return True

    def _save_transaction(self) -> bool:
        """Зберігає транзакцію в базу даних."""
        conn = None
        try:
            conn = create_connection()
            if not conn:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Помилка з'єднання",
                    "Не вдалося підключитися до бази даних"
                )
                return False

            cur = conn.cursor()
            
            # Отримуємо дані для транзакції
            resource_id = self.resource_combo.currentData()
            quantity = self.quantity_spin.value()
            transaction_type = self.transaction_type_combo.currentText().lower()
            
            # Перевіряємо наявність достатньої кількості ресурсу для видачі/списання
            if transaction_type in ['видача', 'списання']:
                cur.execute("SELECT quantity FROM resources WHERE id = ?", (resource_id,))
                current_quantity = cur.fetchone()['quantity']
                if current_quantity < quantity:
                    QtWidgets.QMessageBox.warning(
                        self,
                        "Помилка",
                        f"Недостатньо ресурсу. Доступно: {current_quantity}"
                    )
                    return False

            try:
                # Зберігаємо транзакцію
                cur.execute("""
                    INSERT INTO resource_transactions (
                        resource_id, transaction_type, quantity_changed, 
                        transaction_date, recipient_department, issued_by_user_id,
                        notes
                    ) VALUES (?, ?, ?, datetime('now'), ?, ?, ?)
                """, (
                    resource_id,
                    transaction_type,
                    quantity if transaction_type == 'надходження' else -quantity,
                    self.department_edit.text().strip(),
                    self.current_user_id,
                    f"{self.document_edit.text().strip()} - {self.notes_edit.toPlainText().strip()}"
                ))
                
                # Оновлюємо кількість ресурсу
                if transaction_type == 'надходження':
                    cur.execute("""
                        UPDATE resources 
                        SET quantity = quantity + ? 
                        WHERE id = ?
                    """, (quantity, resource_id))
                else:  # видача або списання
                    cur.execute("""
                        UPDATE resources 
                        SET quantity = quantity - ? 
                        WHERE id = ?
                    """, (quantity, resource_id))
                
                conn.commit()
                QtWidgets.QMessageBox.information(
                    self,
                    "Успіх",
                    "Транзакцію успішно створено"
                )
                return True
                
            except sqlite3.Error as e:
                if conn:
                    conn.rollback()
                QtWidgets.QMessageBox.critical(
                    self,
                    "Помилка бази даних",
                    f"Помилка при збереженні транзакції: {str(e)}"
                )
                return False
                
        except Exception as e:
            if conn:
                conn.rollback()
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Неочікувана помилка: {str(e)}"
            )
            return False
            
        finally:
            if conn:
                conn.close()
            
        return False 