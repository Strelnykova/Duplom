#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головне вікно програми обліку військового майна.
"""

import os
from datetime import datetime, date, timedelta
from PyQt6 import QtCore, QtGui, QtWidgets
from PyQt6.QtCore import QDate
import sqlite3

from logic.db_manager import CATEGORIES, fetch_resources, create_connection
from logic.requisition_handler import get_requisitions
from ui.login_dialog import LoginDialog
from ui.resource_editor_dialog import ResourceEditor
from ui.requisition_dialog import RequisitionDialog
from .transaction_dialog import TransactionDialog

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, conn, role, user_id, parent=None):
        super().__init__(parent)
        self.conn = conn
        self.role = role
        self.user_id = user_id
        
        # Отримуємо деталі користувача
        self.user_details = self.get_user_details()
        
        # Налаштування вікна
        self.setWindowTitle("Система обліку військового майна")
        self.setMinimumSize(800, 600)
        
        self.setup_ui_by_role()

    def get_user_details(self):
        """Отримує деталі про користувача з бази даних."""
        try:
            cursor = self.conn.cursor()
            user = cursor.execute(
                "SELECT * FROM users WHERE id = ?",
                (self.user_id,)
            ).fetchone()
            return dict(user) if user else {}
        except Exception as e:
            print(f"Помилка отримання даних користувача: {e}")
            return {}

    def setup_ui_by_role(self):
        """Налаштовує елементи UI залежно від ролі."""
        # Створення QTabWidget
        self.tab_widget = QtWidgets.QTabWidget()
        self.setCentralWidget(self.tab_widget)

        # Вкладка "Ресурси" (доступна всім)
        self.setup_resources_tab()
        
        # Вкладка "Заявки" (доступна всім)
        self.setup_requisitions_tab()

        # Вкладки тільки для Адміністратора
        if self.role == 'admin':
            self.setup_admin_tabs()

        self.setup_menus_and_toolbar_by_role()
        self.load_initial_data_for_current_tab()
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def setup_resources_tab(self):
        """Налаштування вкладки ресурсів."""
        self.resources_tab = QtWidgets.QWidget()
        self.resources_layout = QtWidgets.QVBoxLayout(self.resources_tab)

        # Група фільтрів
        filters_group = QtWidgets.QGroupBox("Фільтри")
        filters_layout = QtWidgets.QHBoxLayout()
        
        # Фільтр за категорією
        self.category_filter = QtWidgets.QComboBox()
        self.category_filter.addItem("Всі категорії")
        self.load_categories()
        filters_layout.addWidget(QtWidgets.QLabel("Категорія:"))
        filters_layout.addWidget(self.category_filter)
        
        # Фільтр за наявністю
        self.stock_filter = QtWidgets.QComboBox()
        self.stock_filter.addItems(["Всі", "В наявності", "Закінчується", "Відсутні"])
        filters_layout.addWidget(QtWidgets.QLabel("Наявність:"))
        filters_layout.addWidget(self.stock_filter)
        
        filters_group.setLayout(filters_layout)
        self.resources_layout.addWidget(filters_group)

        # Таблиця ресурсів
        self.resources_table = QtWidgets.QTableView()
        self.resources_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.resources_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.resources_layout.addWidget(self.resources_table)

        self.tab_widget.addTab(self.resources_tab, "Ресурси")

    def setup_requisitions_tab(self):
        """Налаштування вкладки заявок."""
        self.requisitions_tab = QtWidgets.QWidget()
        self.requisitions_layout = QtWidgets.QVBoxLayout(self.requisitions_tab)

        # Група фільтрів
        filters_group = QtWidgets.QGroupBox("Фільтри заявок")
        filters_layout = QtWidgets.QHBoxLayout()
        
        # Фільтр за статусом
        self.status_filter = QtWidgets.QComboBox()
        self.status_filter.addItems(["Всі статуси", "Нові", "В обробці", "Виконані", "Відхилені"])
        filters_layout.addWidget(QtWidgets.QLabel("Статус:"))
        filters_layout.addWidget(self.status_filter)
        
        # Фільтр за датою
        self.date_filter = QtWidgets.QComboBox()
        self.date_filter.addItems(["Всі дати", "Сьогодні", "Цей тиждень", "Цей місяць"])
        filters_layout.addWidget(QtWidgets.QLabel("Період:"))
        filters_layout.addWidget(self.date_filter)
        
        filters_group.setLayout(filters_layout)
        self.requisitions_layout.addWidget(filters_group)

        # Таблиця заявок
        self.requisitions_table = QtWidgets.QTableView()
        self.requisitions_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.requisitions_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.requisitions_layout.addWidget(self.requisitions_table)

        self.tab_widget.addTab(self.requisitions_tab, "Заявки")

    def setup_admin_tabs(self):
        """Налаштування вкладок для адміністратора."""
        # Вкладка "Звіти"
        self.reports_tab = QtWidgets.QWidget()
        self.reports_layout = QtWidgets.QVBoxLayout(self.reports_tab)
        
        reports_group = QtWidgets.QGroupBox("Доступні звіти")
        reports_buttons_layout = QtWidgets.QVBoxLayout()
        
        # Кнопки для різних типів звітів
        stock_report_btn = QtWidgets.QPushButton("Звіт по залишках")
        stock_report_btn.clicked.connect(self.generate_stock_report)
        reports_buttons_layout.addWidget(stock_report_btn)
        
        transactions_report_btn = QtWidgets.QPushButton("Звіт по транзакціях")
        transactions_report_btn.clicked.connect(self.generate_transactions_report)
        reports_buttons_layout.addWidget(transactions_report_btn)
        
        reports_group.setLayout(reports_buttons_layout)
        self.reports_layout.addWidget(reports_group)
        
        self.tab_widget.addTab(self.reports_tab, "Звіти")

        # Вкладка "Аналітика"
        self.analytics_tab = QtWidgets.QWidget()
        self.analytics_layout = QtWidgets.QVBoxLayout(self.analytics_tab)
        
        analytics_group = QtWidgets.QGroupBox("Аналітичні інструменти")
        analytics_buttons_layout = QtWidgets.QVBoxLayout()
        
        usage_analytics_btn = QtWidgets.QPushButton("Аналіз використання ресурсів")
        usage_analytics_btn.clicked.connect(self.show_usage_analytics)
        analytics_buttons_layout.addWidget(usage_analytics_btn)
        
        trends_analytics_btn = QtWidgets.QPushButton("Аналіз трендів")
        trends_analytics_btn.clicked.connect(self.show_trends_analytics)
        analytics_buttons_layout.addWidget(trends_analytics_btn)
        
        analytics_group.setLayout(analytics_buttons_layout)
        self.analytics_layout.addWidget(analytics_group)
        
        self.tab_widget.addTab(self.analytics_tab, "Аналітика")

    def setup_menus_and_toolbar_by_role(self):
        """Налаштовує меню та панель інструментів залежно від ролі користувача."""
        self.toolbar = self.addToolBar("Основні дії")
        menubar = self.menuBar()

        # Меню "Файл"
        file_menu = menubar.addMenu("&Файл")
        
        logout_action = QtGui.QAction("Вийти з системи", self)
        logout_action.triggered.connect(self.logout_user)
        file_menu.addAction(logout_action)
        
        file_menu.addSeparator()
        
        exit_action = QtGui.QAction("Вихід", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню "Дії"
        actions_menu = menubar.addMenu("&Дії")

        create_requisition_action = QtGui.QAction("Створити нову заявку", self)
        create_requisition_action.triggered.connect(self.show_requisition_dialog)
        self.toolbar.addAction(create_requisition_action)
        actions_menu.addAction(create_requisition_action)

        if self.role == 'admin':
            add_transaction_action = QtGui.QAction("Зареєструвати транзакцію", self)
            add_transaction_action.triggered.connect(self.show_transaction_dialog)
            self.toolbar.addAction(add_transaction_action)
            actions_menu.addAction(add_transaction_action)

            reports_menu = menubar.addMenu("&Звіти")
            stock_report_action = QtGui.QAction("Звіт по залишках", self)
            stock_report_action.triggered.connect(self.generate_stock_report)
            reports_menu.addAction(stock_report_action)

            analytics_menu = menubar.addMenu("&Аналітика")
            usage_analytics_action = QtGui.QAction("Аналіз використання", self)
            usage_analytics_action.triggered.connect(self.show_usage_analytics)
            analytics_menu.addAction(usage_analytics_action)

        # Привітання в статус-барі
        welcome_text = f"Ласкаво просимо, {self.user_details.get('full_name', '')}! Роль: {self.role.capitalize()}"
        self.statusBar().showMessage(welcome_text)

    def load_initial_data_for_current_tab(self):
        """Завантажує початкові дані для активної вкладки."""
        if self.tab_widget.count() > 0:
            self.on_tab_changed(self.tab_widget.currentIndex())

    def on_tab_changed(self, index):
        """Обробник зміни активної вкладки."""
        if index < 0 or index >= self.tab_widget.count():
            return
            
        widget = self.tab_widget.widget(index)
        if widget == self.resources_tab:
            self.load_resources_data()
        elif widget == self.requisitions_tab:
            self.load_requisitions_data()
        elif self.role == 'admin':
            if hasattr(self, 'reports_tab') and widget == self.reports_tab:
                self.load_reports_data()
            elif hasattr(self, 'analytics_tab') and widget == self.analytics_tab:
                self.load_analytics_data()

    def load_categories(self):
        """Завантажує категорії ресурсів."""
        try:
            cursor = self.conn.cursor()
            categories = cursor.execute("SELECT name FROM categories ORDER BY name").fetchall()
            for category in categories:
                self.category_filter.addItem(category['name'])
        except Exception as e:
            print(f"Помилка завантаження категорій: {e}")

    def load_resources_data(self):
        """Завантажує дані про ресурси."""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT r.*, c.name as category_name
                FROM resources r
                JOIN categories c ON r.category_id = c.id
                ORDER BY c.name, r.name
            """
            resources = cursor.execute(query).fetchall()
            # TODO: Відобразити дані в таблиці
            print(f"Завантажено {len(resources)} ресурсів")
        except Exception as e:
            print(f"Помилка завантаження ресурсів: {e}")

    def load_requisitions_data(self):
        """Завантажує дані про заявки."""
        try:
            cursor = self.conn.cursor()
            query = """
                SELECT r.*, u.full_name as created_by
                FROM requisitions r
                JOIN users u ON r.created_by_user_id = u.id
                ORDER BY r.creation_date DESC
            """
            requisitions = cursor.execute(query).fetchall()
            # TODO: Відобразити дані в таблиці
            print(f"Завантажено {len(requisitions)} заявок")
        except Exception as e:
            print(f"Помилка завантаження заявок: {e}")

    def show_requisition_dialog(self):
        """Показує діалог створення нової заявки."""
        dialog = RequisitionDialog(self.conn, self.user_id)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_requisitions_data()

    def show_transaction_dialog(self):
        """Показує діалог створення нової транзакції."""
        if self.role != 'admin':
            QtWidgets.QMessageBox.warning(
                self,
                "Обмежений доступ",
                "Тільки адміністратор може створювати транзакції"
            )
            return
            
        dialog = TransactionDialog(self.conn, self.user_id)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_resources_data()

    def generate_stock_report(self):
        """Генерує звіт по залишках."""
        print("Генерація звіту по залишках...")
        # TODO: Реалізувати генерацію звіту

    def generate_transactions_report(self):
        """Генерує звіт по транзакціях."""
        print("Генерація звіту по транзакціях...")
        # TODO: Реалізувати генерацію звіту

    def show_usage_analytics(self):
        """Показує аналітику використання ресурсів."""
        print("Відображення аналітики використання...")
        # TODO: Реалізувати відображення аналітики

    def show_trends_analytics(self):
        """Показує аналітику трендів."""
        print("Відображення аналітики трендів...")
        # TODO: Реалізувати відображення трендів

    def logout_user(self):
        """Виходить з облікового запису користувача."""
        reply = QtWidgets.QMessageBox.question(
            self,
            'Підтвердження',
            'Ви дійсно хочете вийти з системи?',
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.close()
            # TODO: Реалізувати перезапуск програми з вікном входу 