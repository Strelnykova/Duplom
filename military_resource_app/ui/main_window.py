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
        self.resize(1100, 700)
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QToolBar {
                background-color: #e0e0e0;
                border: none;
                padding: 5px;
                spacing: 10px;
            }
            QToolButton {
                background-color: #c7ddf5;
                border: 1px solid #a0a0a0;
                border-radius: 4px;
                padding: 6px 12px;
                font-size: 10pt;
            }
            QToolButton:hover {
                background-color: #d8e6f8;
            }
            QToolButton:pressed {
                background-color: #b8cde8;
            }
            QTabWidget::pane {
                border-top: 2px solid #c2c7cb;
            }
            QTabBar::tab {
                background: #e0e0e0;
                border: 1px solid #c4c4c3;
                border-bottom-color: #c2c7cb;
                border-top-left-radius: 4px;
                border-top-right-radius: 4px;
                min-width: 100px;
                padding: 8px;
                font-size: 10pt;
            }
            QTabBar::tab:selected {
                background: #f0f0f0;
                border-color: #9B9B9B;
                border-bottom-color: #f0f0f0;
            }
            QTabBar::tab:!selected:hover {
                background: #d4d4d4;
            }
            QStatusBar {
                background-color: #e0e0e0;
                font-size: 9pt;
            }
        """)

        self._create_actions()
        self._setup_ui_elements()
        self._apply_role_restrictions_and_layout()

        self.load_initial_data_for_current_tab()
        if self.tab_widget.count() > 0:
            self.tab_widget.currentChanged.connect(self.on_tab_changed)
        else:
            no_tabs_label = QtWidgets.QLabel("Немає доступних розділів.")
            no_tabs_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
            self.setCentralWidget(no_tabs_label)

    def _get_icon(self, icon_name: str, theme_name: str = None) -> QtGui.QIcon:
        """
        Отримує іконку за вказаним ім'ям файлу.
        
        Args:
            icon_name (str): Ім'я файлу іконки (наприклад, 'logout_icon.png')
            theme_name (str, optional): Ім'я системної іконки як запасний варіант
        
        Returns:
            QIcon: Об'єкт іконки
        """
        icon_path = os.path.join(os.path.dirname(__file__), '..', 'assets', 'icons', icon_name)
        if os.path.exists(icon_path):
            return QtGui.QIcon(icon_path)
        elif theme_name:
            theme_icon = QtGui.QIcon.fromTheme(theme_name)
            if not theme_icon.isNull():
                return theme_icon
            print(f"ПОПЕРЕДЖЕННЯ: Ні файл іконки '{icon_name}', ні системна іконка '{theme_name}' не знайдені.")
        else:
            print(f"ПОПЕРЕДЖЕННЯ: Іконка не знайдена за шляхом: {icon_path}")
        return QtGui.QIcon()  # Повертаємо порожню іконку як запасний варіант

    def _create_actions(self):
        """Створює всі можливі QAction для меню та панелі інструментів."""
        # Дія "Вийти"
        self.logout_action = QtGui.QAction(
            self._get_icon('logout_icon.png', 'system-log-out'),
            "Вийти",
            self
        )
        self.logout_action.triggered.connect(self.handle_logout)

        # Дія для повного виходу з програми
        self.quit_application_action = QtGui.QAction(
            self._get_icon('exit_icon.png', 'application-exit'),
            "Завершити роботу",
            self
        )
        self.quit_application_action.triggered.connect(QtWidgets.QApplication.instance().quit)

        # Створити нову заявку
        self.create_requisition_action = QtGui.QAction(
            self._get_icon('new_requisition.png', 'document-new'),
            "Створити заявку",
            self
        )
        if hasattr(self, 'show_requisition_dialog'):
            self.create_requisition_action.triggered.connect(self.show_requisition_dialog)
        else:
            self.create_requisition_action.setEnabled(False)

        # Адміністративні дії
        self.add_transaction_action = QtGui.QAction(
            self._get_icon('transaction.png', 'document-edit'),
            "Нова транзакція",
            self
        )
        if hasattr(self, 'show_transaction_dialog'):
            self.add_transaction_action.triggered.connect(self.show_transaction_dialog)
        else:
            self.add_transaction_action.setEnabled(False)

        self.stock_report_action = QtGui.QAction(
            self._get_icon('report.png', 'document-properties'),
            "Звіт по залишках",
            self
        )
        if hasattr(self, 'generate_stock_report'):
            self.stock_report_action.triggered.connect(self.generate_stock_report)

        self.requisition_analytics_action = QtGui.QAction(
            self._get_icon('analytics.png', 'view-statistics'),
            "Аналітика заявок",
            self
        )
        if hasattr(self, 'show_requisition_analytics'):
            self.requisition_analytics_action.triggered.connect(self.show_requisition_analytics)

    def _setup_ui_elements(self):
        """Створює основні віджети UI."""
        # Меню
        menubar = self.menuBar()
        self.file_menu = menubar.addMenu("&Файл")
        self.actions_menu = menubar.addMenu("&Дії")
        self.reports_menu = menubar.addMenu("&Звіти")
        self.analytics_menu = menubar.addMenu("&Аналітика")

        # Панель інструментів
        self.toolbar = self.addToolBar("Основні дії")

        # Вкладки
        self.tab_widget = QtWidgets.QTabWidget()

        # Вкладка "Ресурси"
        self.resources_tab = QtWidgets.QWidget()
        self.resources_layout = QtWidgets.QVBoxLayout(self.resources_tab)
        self.setup_resources_tab()

        # Вкладка "Заявки"
        self.requisitions_tab = QtWidgets.QWidget()
        self.requisitions_layout = QtWidgets.QVBoxLayout(self.requisitions_tab)
        self.setup_requisitions_tab()
        
        # Вкладки для адміністратора
        self.reports_tab = QtWidgets.QWidget()
        self.reports_layout = QtWidgets.QVBoxLayout(self.reports_tab)
        self.setup_reports_tab()

        self.analytics_tab = QtWidgets.QWidget()
        self.analytics_layout = QtWidgets.QVBoxLayout(self.analytics_tab)
        self.setup_analytics_tab()

    def _apply_role_restrictions_and_layout(self):
        """Налаштовує панель інструментів, меню та вкладки відповідно до ролі."""
        
        # --- Налаштування панелі інструментів ---
        self.toolbar.clear()
        
        if hasattr(self, 'create_requisition_action') and self.create_requisition_action.isEnabled():
             self.toolbar.addAction(self.create_requisition_action)

        if self.role == 'admin':
            self.toolbar.addSeparator()
            if hasattr(self, 'add_transaction_action') and self.add_transaction_action.isEnabled():
                self.toolbar.addAction(self.add_transaction_action)
        
        spacer = QtWidgets.QWidget()
        spacer.setSizePolicy(QtWidgets.QSizePolicy.Policy.Expanding, QtWidgets.QSizePolicy.Policy.Expanding)
        self.toolbar.addWidget(spacer)
        
        logout_tool_button = QtWidgets.QToolButton()
        logout_tool_button.setDefaultAction(self.logout_action)
        logout_tool_button.setToolButtonStyle(QtCore.Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
        logout_tool_button.setIconSize(QtCore.QSize(20, 20))
        self.toolbar.addWidget(logout_tool_button)

        # --- Налаштування Меню ---
        menubar = self.menuBar()
        menubar.clear()  # Очищаємо всі попередні меню ПЕРЕД будь-якими умовами

        if self.role == 'admin':
            # Для адміна створюємо повний набір меню
            self.file_menu = menubar.addMenu("&Файл")
            self.file_menu.addAction(self.logout_action)  # "Вийти"
            self.file_menu.addSeparator()
            self.file_menu.addAction(self.quit_application_action)  # "Завершити роботу"

            self.actions_menu = menubar.addMenu("&Дії")
            if hasattr(self, 'create_requisition_action'):
                self.actions_menu.addAction(self.create_requisition_action)
            if hasattr(self, 'add_transaction_action'):
                self.actions_menu.addAction(self.add_transaction_action)

            if hasattr(self, 'reports_menu'):
                self.reports_menu = menubar.addMenu("&Звіти")
                if hasattr(self, 'stock_report_action'):
                    self.reports_menu.addAction(self.stock_report_action)

            if hasattr(self, 'analytics_menu'):
                self.analytics_menu = menubar.addMenu("&Аналітика")
                if hasattr(self, 'requisition_analytics_action'):
                    self.analytics_menu.addAction(self.requisition_analytics_action)
        # Для користувача не створюємо меню, оскільки всі дії доступні на панелі інструментів

        # --- Налаштування видимості Вкладок ---
        while self.tab_widget.count() > 0:
            self.tab_widget.removeTab(0)

        # Базові вкладки для всіх користувачів
        self.tab_widget.addTab(self.resources_tab, "Ресурси")
        self.tab_widget.addTab(self.requisitions_tab, "Заявки")

        # Додаткові вкладки для адміністратора
        if self.role == 'admin':
            if hasattr(self, 'reports_tab'):
                self.tab_widget.addTab(self.reports_tab, "Звіти")
            if hasattr(self, 'analytics_tab'):
                self.tab_widget.addTab(self.analytics_tab, "Аналітика")

        self.setCentralWidget(self.tab_widget)

        # --- Статус-бар ---
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

    def show_transaction_dialog(self):
        """Показує діалог створення нової транзакції."""
        if self.role != 'admin':
            QtWidgets.QMessageBox.warning(
                self,
                "Обмежений доступ",
                "Тільки адміністратор може створювати транзакції"
            )
            return
            
        dialog = TransactionDialog(self.user_id)
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_resources_data()

    # Методи для завантаження даних
    def load_requisitions_data(self):
        """Завантажує дані про заявки."""
        print("Завантаження даних заявок...")
        # TODO: Реалізувати завантаження даних

    def load_reports_data(self):
        """Завантажує дані для звітів."""
        print("Завантаження даних звітів...")
        # TODO: Реалізувати завантаження даних

    def load_analytics_data(self):
        """Завантажує дані для аналітики."""
        print("Завантаження даних аналітики...")
        # TODO: Реалізувати завантаження даних 

    def handle_logout(self):
        """Обробляє вихід з системи (повернення до вікна входу)."""
        print("Ініційовано вихід з системи (logout)...")
        self._is_logging_out = True  # Встановлюємо прапорець
        self.logout_requested_signal.emit()  # Сигнал для main.py
        self.close()  # Це викличе closeEvent

    def closeEvent(self, event: QtGui.QCloseEvent):
        """Обробляє подію закриття вікна."""
        if hasattr(self, '_is_logging_out') and self._is_logging_out:
            # Якщо це вихід з системи (logout), просто приймаємо закриття вікна
            self._is_logging_out = False  # Скидаємо прапорець
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
            print("Повне закриття програми через closeEvent.")
            QtWidgets.QApplication.instance().quit()  # Закриваємо всю програму
            event.accept()
        else:
            event.ignore() 