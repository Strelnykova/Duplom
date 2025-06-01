#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головне вікно програми обліку військового майна.
"""

import sys
import os
import sqlite3
from PyQt6 import QtCore, QtGui, QtWidgets

# Налаштування шляху для імпорту модулів
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from logic.db_manager import create_connection
from logic.requisition_handler import get_requisitions
from .requisition_dialog import RequisitionDialog
from .transaction_dialog import TransactionDialog

class MainWindow(QtWidgets.QMainWindow):
    # Сигнал для виходу з системи
    logout_requested_signal = QtCore.pyqtSignal()

    def __init__(self, role, user_id, user_details, parent=None):
        super().__init__(parent)
        self.role = role
        self.user_id = user_id
        self.user_details = user_details
        self.resources_table_model = None

        self.setWindowTitle("Облік військового майна")
        self.resize(1100, 650)
        self.apply_styles()

        # Створюємо дії
        self._create_actions()
        
        # Головний вертикальний layout для всього вікна
        self.main_widget = QtWidgets.QWidget()
        self.main_vertical_layout = QtWidgets.QVBoxLayout(self.main_widget)
        self.main_vertical_layout.setContentsMargins(0, 0, 0, 0)
        self.main_vertical_layout.setSpacing(0)

        self._setup_header_and_tabs_by_role()
        self.setCentralWidget(self.main_widget)

        self.load_initial_data_for_current_tab()
        if self.tab_widget.count() > 0:
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
        
        self._setup_statusbar()

    def apply_styles(self):
        """Застосовує стилі до головного вікна та всіх елементів."""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ECEFF1;
            }
            QWidget#HeaderBar {
                background-color: #37474F;
                padding: 8px 15px;
                border-bottom: 2px solid #263238;
            }
            QLabel#HeaderLabel {
                color: #FFFFFF;
                font-size: 12pt;
                font-weight: bold;
            }
            QPushButton#ActionButton {
                color: #FFFFFF;
                background-color: transparent;
                border: none;
                padding: 8px 12px;
                font-size: 10pt;
                font-weight: bold;
                text-align: center;
            }
            QPushButton#ActionButton:hover {
                background-color: #455A64;
                border-radius: 4px;
            }
            QPushButton#ActionButton:pressed {
                background-color: #263238;
                border-radius: 4px;
            }
            QTabWidget::pane {
                border-top: 3px solid #78909C;
                background-color: #FFFFFF;
            }
            QTabBar::tab {
                background: #B0BEC5;
                color: #37474F;
                border: 1px solid #90A4AE;
                border-bottom: none;
                border-top-left-radius: 5px;
                border-top-right-radius: 5px;
                min-width: 120px;
                padding: 10px;
                font-size: 10pt;
                font-weight: 500;
            }
            QTabBar::tab:selected {
                background: #FFFFFF;
                color: #263238;
                border-color: #78909C;
                border-bottom: 1px solid #FFFFFF;
            }
            QTabBar::tab:!selected:hover {
                background: #90A4AE;
                color: #FFFFFF;
            }
            QStatusBar {
                background-color: #CFD8DC;
                font-size: 9pt;
                color: #37474F;
            }
            QGroupBox {
                font-weight: bold;
                font-size: 11pt;
                margin-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top left;
                padding: 0 5px 0 5px;
                left: 10px;
            }
            QLabel, QLineEdit, QComboBox, QDateEdit, QTextEdit, QSpinBox {
                font-size: 10pt;
                padding: 3px;
            }
            QPushButton {
                font-size: 10pt;
                padding: 6px 12px;
            }
            QTableView {
                border: 1px solid #B0BEC5;
                gridline-color: #CFD8DC;
                selection-background-color: #90A4AE;
                selection-color: #FFFFFF;
            }
            QHeaderView::section {
                background-color: #CFD8DC;
                padding: 5px;
                border: 1px solid #B0BEC5;
                font-weight: bold;
            }
            QComboBox {
                border: 1px solid #B0BEC5;
                border-radius: 3px;
                padding: 5px;
                min-width: 6em;
            }
            QComboBox:hover {
                border-color: #78909C;
            }
            QComboBox::drop-down {
                border: none;
                width: 20px;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
            }
        """)

    def _create_actions(self):
        """Створює QAction для логіки програми."""
        self.exit_action = QtGui.QAction("Вийти з системи", self)
        self.exit_action.setToolTip("Повернутися до вікна входу")
        self.exit_action.triggered.connect(self.handle_logout)

        self.create_requisition_action = QtGui.QAction("Створити заявку", self)
        self.create_requisition_action.setToolTip("Створити нову заявку на ресурси")
        if hasattr(self, 'show_requisition_dialog'):
            self.create_requisition_action.triggered.connect(self.show_requisition_dialog)
        else:
            self.create_requisition_action.setEnabled(False)

        self.add_transaction_action = QtGui.QAction("Нова транзакція", self)
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', 'transaction_icon.png')
        if os.path.exists(icon_path):
            self.add_transaction_action.setIcon(QtGui.QIcon(icon_path))
        self.add_transaction_action.setToolTip("Зареєструвати надходження, видачу або списання ресурсу")
        if hasattr(self, 'show_transaction_dialog'):
            self.add_transaction_action.triggered.connect(self.show_transaction_dialog)
        else:
            self.add_transaction_action.setEnabled(False)
            print("УВАГА: Метод show_transaction_dialog не реалізовано в MainWindow!")

    def _setup_header_and_tabs_by_role(self):
        """Налаштовує хедер (панель дій) та вкладки відповідно до ролі."""
        # Хедер / Панель дій
        header_bar = QtWidgets.QWidget(self)
        header_bar.setObjectName("HeaderBar")
        header_layout = QtWidgets.QHBoxLayout(header_bar)
        header_layout.setContentsMargins(10, 5, 10, 5)
        header_layout.setSpacing(15)

        if self.role == 'user':
            create_req_button = QtWidgets.QPushButton("Створити заявку")
            create_req_button.setObjectName("ActionButton")
            if hasattr(self, 'show_requisition_dialog'):
                create_req_button.clicked.connect(self.show_requisition_dialog)
            else:
                create_req_button.setEnabled(False)
            header_layout.addWidget(create_req_button)
            
            header_layout.addStretch(1)
            
            logout_button = QtWidgets.QPushButton("Вийти з системи")
            logout_button.setObjectName("ActionButton")
            logout_button.clicked.connect(self.handle_logout)
            header_layout.addWidget(logout_button)
        elif self.role == 'admin':
            admin_create_req_button = QtWidgets.QPushButton("Створити заявку")
            admin_create_req_button.setObjectName("ActionButton")
            if hasattr(self, 'show_requisition_dialog'):
                admin_create_req_button.clicked.connect(self.show_requisition_dialog)
            header_layout.addWidget(admin_create_req_button)

            admin_add_trans_button = QtWidgets.QPushButton("Нова транзакція")
            admin_add_trans_button.setObjectName("ActionButton")
            if hasattr(self, 'show_transaction_dialog'):
                admin_add_trans_button.clicked.connect(self.show_transaction_dialog)
            header_layout.addWidget(admin_add_trans_button)
            
            header_layout.addStretch(1)
            
            admin_logout_button = QtWidgets.QPushButton("Вийти з системи")
            admin_logout_button.setObjectName("ActionButton")
            admin_logout_button.clicked.connect(self.handle_logout)
            header_layout.addWidget(admin_logout_button)

        self.main_vertical_layout.addWidget(header_bar)

        # Прибираємо рядок меню
        self.setMenuBar(None)

        # Вкладки
        self.tab_widget = QtWidgets.QTabWidget()
        
        self.resources_tab = QtWidgets.QWidget()
        self.resources_layout = QtWidgets.QVBoxLayout(self.resources_tab)
        self.setup_resources_tab()
        self.tab_widget.addTab(self.resources_tab, "Ресурси")

        self.requisitions_tab = QtWidgets.QWidget()
        self.requisitions_layout = QtWidgets.QVBoxLayout(self.requisitions_tab)
        self.setup_requisitions_tab()
        self.tab_widget.addTab(self.requisitions_tab, "Заявки")

        if self.role == 'admin':
            self.reports_tab = QtWidgets.QWidget()
            self.reports_layout = QtWidgets.QVBoxLayout(self.reports_tab)
            self.setup_reports_tab()
            self.tab_widget.addTab(self.reports_tab, "Звіти")

            self.analytics_tab = QtWidgets.QWidget()
            self.analytics_layout = QtWidgets.QVBoxLayout(self.analytics_tab)
            self.setup_analytics_tab()
            self.tab_widget.addTab(self.analytics_tab, "Аналітика")
        
        self.main_vertical_layout.addWidget(self.tab_widget)

    def _setup_statusbar(self):
        """Налаштовує статус-бар з інформацією про користувача."""
        status_bar_message = f"Роль: {self.role.capitalize()}"
        if self.user_details:
            user_name_display = self.user_details.get('last_name', '')
            fn_initial = self.user_details.get('first_name', '')
            mn_initial = self.user_details.get('middle_name', '')
            if fn_initial:
                user_name_display += f" {fn_initial[0]}."
            if mn_initial:
                user_name_display += f"{mn_initial[0]}."
            
            full_title_parts = []
            if self.user_details.get('rank'):
                full_title_parts.append(self.user_details.get('rank'))
            if self.user_details.get('position'):
                full_title_parts.append(self.user_details.get('position'))
            full_title = " ".join(full_title_parts)
            
            if user_name_display.strip():
                status_bar_message += f" | {full_title} {user_name_display.strip()}" if full_title else f" | {user_name_display.strip()}"
            else:
                status_bar_message += f" | Користувач: {self.user_details.get('username', self.user_id)}"
        else:
            status_bar_message += f" | Користувач ID: {self.user_id}"
        
        self.statusBar().showMessage(status_bar_message)

    def handle_logout(self):
        """Обробляє вихід з системи."""
        print("Ініційовано вихід з системи (logout)...")
        self._is_logging_out = True
        self.logout_requested_signal.emit()
        self.close()

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Обробляє подію закриття вікна."""
        if hasattr(self, '_is_logging_out') and self._is_logging_out:
            self._is_logging_out = False
            event.accept()
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            'Завершення роботи',
            "Ви впевнені, що хочете повністю вийти з програми?",
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            QtWidgets.QApplication.instance().quit()
            event.accept()
        else:
            event.ignore()

    def setup_resources_tab(self):
        """Налаштування вкладки ресурсів."""
        # Група фільтрів
        filters_group = QtWidgets.QGroupBox("Фільтри")
        filters_layout = QtWidgets.QHBoxLayout()
        
        # Фільтр за категорією
        self.category_filter = QtWidgets.QComboBox()
        self.category_filter.addItem("Всі категорії")
        self.category_filter.currentTextChanged.connect(self.on_resource_category_changed)
        filters_layout.addWidget(QtWidgets.QLabel("Категорія:"))
        filters_layout.addWidget(self.category_filter)
        
        # Фільтр за наявністю
        self.stock_filter = QtWidgets.QComboBox()
        self.stock_filter.addItems(["Всі", "В наявності", "Закінчується", "Відсутні"])
        self.stock_filter.currentTextChanged.connect(self.on_stock_filter_changed)
        filters_layout.addWidget(QtWidgets.QLabel("Наявність:"))
        filters_layout.addWidget(self.stock_filter)
        
        filters_group.setLayout(filters_layout)
        self.resources_layout.addWidget(filters_group)

        # Таблиця ресурсів
        self.resources_table = QtWidgets.QTableView()
        self.resources_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.resources_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        
        # Створюємо та налаштовуємо модель даних
        self.resources_table_model = QtGui.QStandardItemModel(self)
        self.resources_table_model.setHorizontalHeaderLabels([
            "ID", "Назва", "Категорія", "Кількість", "Од.вим.", 
            "Мін.залишок", "Постачальник", "Примітки"
        ])
        self.resources_table.setModel(self.resources_table_model)
        
        # Налаштовуємо розміри стовпців
        self.resources_table.setColumnWidth(0, 50)  # ID
        self.resources_table.setColumnWidth(1, 200) # Назва
        self.resources_table.setColumnWidth(2, 150) # Категорія
        self.resources_table.setColumnWidth(3, 100) # Кількість
        self.resources_table.setColumnWidth(4, 80)  # Од.вим.
        self.resources_table.setColumnWidth(5, 100) # Мін.залишок
        self.resources_table.setColumnWidth(6, 150) # Постачальник
        self.resources_table.setColumnWidth(7, 200) # Примітки
        
        self.resources_layout.addWidget(self.resources_table)

        # Заповнюємо комбо-бокс категорій
        self.populate_resource_categories()

    def populate_resource_categories(self):
        """Заповнює комбо-бокс категоріями ресурсів з бази даних."""
        self.category_filter.clear()
        self.category_filter.addItem("Всі категорії", None)
        
        conn = None
        try:
            conn = create_connection()
            if conn:
                cur = conn.cursor()
                cur.execute("SELECT id, name FROM categories ORDER BY name")
                categories = cur.fetchall()
                for category in categories:
                    self.category_filter.addItem(category['name'], category['id'])
        except sqlite3.Error as e:
            print(f"Помилка завантаження категорій: {e}")
        finally:
            if conn:
                conn.close()

    def on_resource_category_changed(self, selected_category: str):
        """Обробник зміни вибраної категорії ресурсів."""
        category_id = self.category_filter.currentData()
        stock_status = self.stock_filter.currentText()
        self.load_resources_data(category_id, stock_status)

    def on_stock_filter_changed(self, selected_status: str):
        """Обробник зміни фільтру за наявністю."""
        category_id = self.category_filter.currentData()
        self.load_resources_data(category_id, selected_status)

    def load_resources_data(self, category_id=None, stock_status="Всі"):
        """Завантажує дані про ресурси з урахуванням фільтрів."""
        print(f"Завантаження ресурсів для категорії ID: {category_id}, статус: {stock_status}")
        
        # Очищаємо модель перед завантаженням нових даних
        self.resources_table_model.setRowCount(0)
        
        conn = None
        try:
            conn = create_connection()
            if not conn:
                return

            query = """
                SELECT r.id, r.name, c.name as category_name, r.quantity, 
                       r.unit_of_measure, r.low_stock_threshold, r.supplier, 
                       r.description
                FROM resources r
                JOIN categories c ON r.category_id = c.id
                WHERE 1=1
            """
            params = []

            if category_id is not None:
                query += " AND r.category_id = ?"
                params.append(category_id)

            if stock_status == "В наявності":
                query += " AND r.quantity > r.low_stock_threshold"
            elif stock_status == "Закінчується":
                query += " AND r.quantity <= r.low_stock_threshold AND r.quantity > 0"
            elif stock_status == "Відсутні":
                query += " AND r.quantity = 0"

            query += " ORDER BY c.name, r.name"

            cur = conn.cursor()
            cur.execute(query, params)
            resources = cur.fetchall()

            for resource in resources:
                row_items = [
                    QtGui.QStandardItem(str(resource['id'])),
                    QtGui.QStandardItem(resource['name']),
                    QtGui.QStandardItem(resource['category_name']),
                    QtGui.QStandardItem(str(resource['quantity'])),
                    QtGui.QStandardItem(resource['unit_of_measure'] or ''),
                    QtGui.QStandardItem(str(resource['low_stock_threshold'])),
                    QtGui.QStandardItem(resource['supplier'] or ''),
                    QtGui.QStandardItem(resource['description'] or '')
                ]
                self.resources_table_model.appendRow(row_items)

        except sqlite3.Error as e:
            print(f"Помилка завантаження ресурсів: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Не вдалося завантажити дані ресурсів: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def setup_requisitions_tab(self):
        """Налаштування вкладки заявок."""
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

    def setup_reports_tab(self):
        """Налаштування вкладки звітів."""
        reports_group = QtWidgets.QGroupBox("Доступні звіти")
        reports_buttons_layout = QtWidgets.QVBoxLayout()
        
        stock_report_btn = QtWidgets.QPushButton("Звіт по залишках")
        if hasattr(self, 'generate_stock_report'):
            stock_report_btn.clicked.connect(self.generate_stock_report)
        reports_buttons_layout.addWidget(stock_report_btn)
        
        transactions_report_btn = QtWidgets.QPushButton("Звіт по транзакціях")
        if hasattr(self, 'generate_transactions_report'):
            transactions_report_btn.clicked.connect(self.generate_transactions_report)
        reports_buttons_layout.addWidget(transactions_report_btn)
        
        reports_group.setLayout(reports_buttons_layout)
        self.reports_layout.addWidget(reports_group)

    def setup_analytics_tab(self):
        """Налаштування вкладки аналітики."""
        analytics_group = QtWidgets.QGroupBox("Аналітичні інструменти")
        analytics_buttons_layout = QtWidgets.QVBoxLayout()
        
        usage_analytics_btn = QtWidgets.QPushButton("Аналіз використання ресурсів")
        if hasattr(self, 'show_usage_analytics'):
            usage_analytics_btn.clicked.connect(self.show_usage_analytics)
        analytics_buttons_layout.addWidget(usage_analytics_btn)
        
        trends_analytics_btn = QtWidgets.QPushButton("Аналіз трендів")
        if hasattr(self, 'show_trends_analytics'):
            trends_analytics_btn.clicked.connect(self.show_trends_analytics)
        analytics_buttons_layout.addWidget(trends_analytics_btn)
        
        analytics_group.setLayout(analytics_buttons_layout)
        self.analytics_layout.addWidget(analytics_group)

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
            # Оновлюємо дані ресурсів при переході на вкладку
            category_id = self.category_filter.currentData()
            stock_status = self.stock_filter.currentText()
            self.load_resources_data(category_id, stock_status)
        elif widget == self.requisitions_tab:
            self.load_requisitions_data()
        elif self.role == 'admin':
            if widget == self.reports_tab:
                self.load_reports_data()
            elif widget == self.analytics_tab:
                self.load_analytics_data()

    def show_requisition_dialog(self):
        """Показує діалог створення нової заявки."""
        dialog = RequisitionDialog(self.user_id, self.role)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_requisitions_data()

    def show_requisition_details(self, requisition_id: int):
        """Показує діалог перегляду деталей заявки."""
        dialog = RequisitionDialog(
            current_user_id=self.user_id,
            current_user_role=self.role,
            requisition_id_to_view=requisition_id
        )
        # Підключаємо сигнал оновлення статусу
        dialog.requisition_status_changed_signal.connect(lambda: self.load_requisitions_data())
        dialog.exec()

    def show_transaction_dialog(self):
        """Показує діалог створення нової транзакції."""
        if self.role != 'admin':
            QtWidgets.QMessageBox.warning(
                self,
                "Обмежений доступ",
                "Тільки адміністратор може створювати транзакції"
            )
            return
            
        try:
            dialog = TransactionDialog(self.user_id, parent=self)
            if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
                print("Транзакція успішно створена")
                # Оновлюємо дані на активній вкладці
                current_widget = self.tab_widget.currentWidget()
                if current_widget == self.resources_tab:
                    category_id = self.category_filter.currentData()
                    stock_status = self.stock_filter.currentText()
                    self.load_resources_data(category_id, stock_status)
                elif current_widget == self.analytics_tab:
                    self.load_analytics_data()
                elif current_widget == self.reports_tab:
                    self.load_reports_data()
            else:
                print("Діалог транзакції скасовано або закрито")
        except Exception as e:
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Не вдалося створити транзакцію: {str(e)}"
            )
            print(f"Помилка при створенні транзакції: {e}")

    # Методи для завантаження даних
    def load_requisitions_data(self):
        """Завантажує дані про заявки."""
        print("Завантаження даних заявок...")
        
        # Створюємо модель для таблиці, якщо її ще немає
        if not hasattr(self, 'requisitions_model'):
            self.requisitions_model = QtGui.QStandardItemModel(self)
            self.requisitions_model.setHorizontalHeaderLabels([
                "ID", "Номер", "Відділення", "Дата створення", 
                "Статус", "Терміновість", "Примітки"
            ])
            self.requisitions_table.setModel(self.requisitions_model)
            
            # Налаштовуємо розміри стовпців
            self.requisitions_table.setColumnWidth(0, 50)   # ID
            self.requisitions_table.setColumnWidth(1, 120)  # Номер
            self.requisitions_table.setColumnWidth(2, 150)  # Відділення
            self.requisitions_table.setColumnWidth(3, 120)  # Дата
            self.requisitions_table.setColumnWidth(4, 100)  # Статус
            self.requisitions_table.setColumnWidth(5, 100)  # Терміновість
            self.requisitions_table.setColumnWidth(6, 200)  # Примітки

            # Підключаємо подвійний клік для перегляду деталей
            self.requisitions_table.doubleClicked.connect(self.on_requisition_double_clicked)

        # Очищаємо модель перед завантаженням нових даних
        self.requisitions_model.setRowCount(0)

        # Отримуємо фільтри
        status_filter = self.status_filter.currentText()
        if status_filter == "Всі статуси":
            status_filter = None

        # Отримуємо дані заявок
        conn = create_connection()
        if not conn:
            return

        try:
            cur = conn.cursor()
            query = """
                SELECT r.id, r.requisition_number, r.department_requesting,
                       r.creation_date, r.status, r.urgency, r.notes
                FROM requisitions r
                WHERE 1=1
            """
            params = []

            if status_filter:
                query += " AND r.status = ?"
                params.append(status_filter.lower())

            if self.role != 'admin':
                query += " AND r.created_by_user_id = ?"
                params.append(self.user_id)

            query += " ORDER BY r.creation_date DESC"

            cur.execute(query, params)
            requisitions = cur.fetchall()

            for req in requisitions:
                row_items = [
                    QtGui.QStandardItem(str(req['id'])),
                    QtGui.QStandardItem(req['requisition_number']),
                    QtGui.QStandardItem(req['department_requesting']),
                    QtGui.QStandardItem(req['creation_date']),
                    QtGui.QStandardItem(req['status'].capitalize()),
                    QtGui.QStandardItem(req['urgency'].capitalize()),
                    QtGui.QStandardItem(req['notes'] or '')
                ]
                self.requisitions_model.appendRow(row_items)

        except sqlite3.Error as e:
            print(f"Помилка завантаження заявок: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Не вдалося завантажити дані заявок: {str(e)}"
            )
        finally:
            if conn:
                conn.close()

    def on_requisition_double_clicked(self, index):
        """Обробник подвійного кліку по заявці."""
        # Отримуємо ID заявки з першої колонки
        requisition_id = int(self.requisitions_model.data(
            self.requisitions_model.index(index.row(), 0)
        ))
        self.show_requisition_details(requisition_id)

    def load_reports_data(self):
        """Завантажує дані для звітів."""
        print("Завантаження даних звітів...")
        # TODO: Реалізувати завантаження даних

    def load_analytics_data(self):
        """Завантажує дані для аналітики."""
        print("Завантаження даних аналітики...")
        # TODO: Реалізувати завантаження даних 