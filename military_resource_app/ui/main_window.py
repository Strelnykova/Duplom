#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головне вікно програми.
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

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, conn, role, user_id):
        super().__init__()
        self.conn = conn
        self.current_user_role = role
        self.current_user_id = user_id
        self.setup_ui()
        self.load_data()
        self.check_alerts()
        self.update_ui_for_role()

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setWindowTitle("Облік військового майна")
        self.resize(1280, 720)

        # Центральний віджет з вкладками
        self.central_widget = QtWidgets.QWidget()
        self.setCentralWidget(self.central_widget)
        self.main_layout = QtWidgets.QVBoxLayout(self.central_widget)

        # Статусний рядок для відображення інформації про користувача
        self.status_label = QtWidgets.QLabel()
        self.main_layout.addWidget(self.status_label)

        # Створення QTabWidget
        self.tab_widget = QtWidgets.QTabWidget()
        self.main_layout.addWidget(self.tab_widget)

        # Вкладка "Ресурси"
        self.setup_resources_tab()

        # Вкладка "Заявки"
        self.setup_requisitions_tab()

        # Панель інструментів
        self.setup_toolbar()

        # Підключення обробника зміни вкладки
        self.tab_widget.currentChanged.connect(self.on_tab_changed)

    def setup_requisitions_tab(self):
        """Налаштування вкладки заявок."""
        self.requisitions_tab = QtWidgets.QWidget()
        self.requisitions_layout = QtWidgets.QVBoxLayout(self.requisitions_tab)

        # --- Секція фільтрів ---
        self.filters_group_box = QtWidgets.QGroupBox("Фільтри та пошук заявок")
        self.filters_layout = QtWidgets.QGridLayout()

        # Фільтр за датою
        self.filters_layout.addWidget(QtWidgets.QLabel("Дата створення від:"), 0, 0)
        self.date_from_edit = QtWidgets.QDateEdit(self)
        self.date_from_edit.setCalendarPopup(True)
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_from_edit.setDisplayFormat("yyyy-MM-dd")
        self.filters_layout.addWidget(self.date_from_edit, 0, 1)

        self.filters_layout.addWidget(QtWidgets.QLabel("Дата створення до:"), 0, 2)
        self.date_to_edit = QtWidgets.QDateEdit(self)
        self.date_to_edit.setCalendarPopup(True)
        self.date_to_edit.setDate(QDate.currentDate())
        self.date_to_edit.setDisplayFormat("yyyy-MM-dd")
        self.filters_layout.addWidget(self.date_to_edit, 0, 3)

        # Фільтр за статусом
        self.filters_layout.addWidget(QtWidgets.QLabel("Статус:"), 1, 0)
        self.status_filter_combo = QtWidgets.QComboBox(self)
        self.status_filter_combo.addItem("Всі статуси", None)
        self.valid_requisition_statuses = ['нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано']
        for status in self.valid_requisition_statuses:
            self.status_filter_combo.addItem(status.capitalize(), status)
        self.filters_layout.addWidget(self.status_filter_combo, 1, 1)

        # Фільтр за терміновістю
        self.filters_layout.addWidget(QtWidgets.QLabel("Терміновість:"), 1, 2)
        self.urgency_filter_combo = QtWidgets.QComboBox(self)
        self.urgency_filter_combo.addItem("Всі терміновості", None)
        self.valid_urgencies = ['планова', 'термінова', 'критична']
        for urgency in self.valid_urgencies:
            self.urgency_filter_combo.addItem(urgency.capitalize(), urgency)
        self.filters_layout.addWidget(self.urgency_filter_combo, 1, 3)

        # Пошук за номером/ключовим словом
        self.filters_layout.addWidget(QtWidgets.QLabel("Пошук (номер/опис):"), 2, 0)
        self.search_requisition_edit = QtWidgets.QLineEdit(self)
        self.search_requisition_edit.setPlaceholderText("Введіть номер заявки або ключове слово...")
        self.filters_layout.addWidget(self.search_requisition_edit, 2, 1, 1, 3)

        # Кнопки для фільтрів
        self.apply_filters_button = QtWidgets.QPushButton("Застосувати фільтри")
        self.apply_filters_button.clicked.connect(self.apply_requisition_filters)
        self.filters_layout.addWidget(self.apply_filters_button, 3, 0, 1, 2)

        self.reset_filters_button = QtWidgets.QPushButton("Скинути фільтри")
        self.reset_filters_button.clicked.connect(self.reset_requisition_filters)
        self.filters_layout.addWidget(self.reset_filters_button, 3, 2, 1, 2)

        self.filters_group_box.setLayout(self.filters_layout)
        self.requisitions_layout.addWidget(self.filters_group_box)

        # Таблиця для заявок
        self.requisitions_table = QtWidgets.QTableWidget(self.requisitions_tab)
        self.setup_requisitions_table()
        
        # Кнопка оновлення заявок
        self.refresh_requisitions_button = QtWidgets.QPushButton("Оновити список заявок")
        self.refresh_requisitions_button.clicked.connect(self.load_requisitions_data)
        
        self.requisitions_layout.addWidget(self.refresh_requisitions_button)
        self.requisitions_layout.addWidget(self.requisitions_table)

        self.tab_widget.addTab(self.requisitions_tab, "Заявки")

    def setup_resources_tab(self):
        """Налаштування вкладки ресурсів."""
        self.resources_tab = QtWidgets.QWidget()
        self.resources_layout = QtWidgets.QHBoxLayout(self.resources_tab)
        self.resources_layout.setContentsMargins(0, 0, 0, 0)

        # Стек для таблиць категорій
        self.stack = QtWidgets.QStackedWidget()
        self.resources_layout.addWidget(self.stack, 1)

        # Попередній перегляд
        self.preview = QtWidgets.QLabel("(Попередній перегляд)")
        self.preview.setObjectName("previewLabel")
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedWidth(320)
        self.resources_layout.addWidget(self.preview)

        self.tab_widget.addTab(self.resources_tab, "Ресурси")

        # Створення моделей та представлень для кожної категорії
        self.models = {}
        self.views = {}
        for cat in CATEGORIES:
            view = QtWidgets.QTableView()
            view.setAlternatingRowColors(True)
            view.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeMode.Stretch
            )
            view.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
            )
            view.setEditTriggers(
                QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers
            )
            view.doubleClicked.connect(self.show_info)

            model = QtGui.QStandardItemModel(0, 4)
            model.setHorizontalHeaderLabels(["ID", "Назва", "Кількість", "Опис"])
            view.setModel(model)
            view.selectionModel().selectionChanged.connect(self.update_preview)

            self.views[cat] = view
            self.models[cat] = model
            self.stack.addWidget(view)

    def setup_requisitions_table(self):
        """Налаштовує таблицю заявок."""
        headers = ["ID", "Номер заявки", "Дата створення", "Відділення", "Створив", "Статус", "Терміновість", "Примітки"]
        self.requisitions_table.setColumnCount(len(headers))
        self.requisitions_table.setHorizontalHeaderLabels(headers)
        
        header = self.requisitions_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # ID
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.Stretch)          # Номер
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Дата
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)          # Відділення
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Створив
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Статус
        header.setSectionResizeMode(6, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)  # Терміновість
        header.setSectionResizeMode(7, QtWidgets.QHeaderView.ResizeMode.Stretch)          # Примітки
        
        self.requisitions_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.requisitions_table.setSelectionMode(QtWidgets.QAbstractItemView.SelectionMode.SingleSelection)
        self.requisitions_table.doubleClicked.connect(self.on_requisition_double_clicked)

    def on_requisition_double_clicked(self, index):
        """Обробник подвійного кліку по заявці."""
        if not index.isValid():
            return
            
        row = index.row()
        requisition_id = int(self.requisitions_table.item(row, 0).text())
        
        if requisition_id is not None:
            dialog = RequisitionDialog(
                current_user_id=self.current_user_id,
                current_user_role=self.current_user_role,
                parent=self,
                requisition_id_to_view=requisition_id
            )
            # Підключаємося до сигналів для оновлення даних
            dialog.requisition_status_changed_signal.connect(self.handle_requisition_status_changed)
            dialog.requisition_item_executed_signal.connect(self.handle_requisition_item_executed)
            dialog.exec()
        else:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Не вдалося отримати ID заявки.")

    def handle_requisition_status_changed(self, requisition_id: int):
        """Обробляє сигнал про зміну статусу заявки та оновлює таблицю."""
        print(f"Статус заявки ID {requisition_id} було змінено. Оновлення списку...")
        self.load_requisitions_data()  # Оновлюємо всю таблицю

    def handle_requisition_item_executed(self, requisition_id: int):
        """Обробляє сигнал про виконання позиції заявки та оновлює список ресурсів."""
        print(f"Позицію в заявці ID {requisition_id} було виконано. Оновлення списку ресурсів...")
        self.load_data()  # Оновлюємо список ресурсів
        self.load_requisitions_data()  # Оновлюємо список заявок, бо загальний статус міг змінитися

    def on_tab_changed(self, index):
        """Обробник зміни активної вкладки."""
        if self.tab_widget.widget(index) == self.requisitions_tab:
            self.load_requisitions_data()
        elif self.tab_widget.widget(index) == self.resources_tab:
            self.load_data()

    def load_data(self):
        """Завантаження даних у таблиці."""
        for category in CATEGORIES:
            model = self.models[category]
            model.removeRows(0, model.rowCount())
            
            for resource in fetch_resources(self.conn, category):
                row = []
                for field in ["id", "name", "quantity", "description"]:
                    item = QtGui.QStandardItem(str(resource[field]))
                    row.append(item)
                model.appendRow(row)

    def filter_resources(self):
        """Фільтрація ресурсів за пошуковим запитом."""
        search_text = self.search.text().lower()
        view = self.views[self.current_category]
        model = self.models[self.current_category]

        for row in range(model.rowCount()):
            name = model.item(row, 1).text().lower()
            description = model.item(row, 3).text().lower()
            hidden = (search_text not in name and search_text not in description)
            view.setRowHidden(row, hidden)

    def change_category(self, index):
        """Зміна поточної категорії."""
        self.stack.setCurrentIndex(index)
        self.filter_resources()

    @property
    def current_category(self):
        """Поточна вибрана категорія."""
        return self.category.currentText()

    def get_selected_resource_id(self):
        """Отримання ID вибраного ресурсу."""
        view = self.views[self.current_category]
        selection = view.selectionModel().selectedRows()
        if not selection:
            return None
        return int(self.models[self.current_category].item(selection[0].row(), 0).text())

    def update_preview(self):
        """Оновлення попереднього перегляду."""
        rid = self.get_selected_resource_id()
        if not rid:
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText("(Попередній перегляд)")
            return

        path = self.conn.execute(
            "SELECT image_path FROM resources WHERE id=?", (rid,)
        ).fetchone()["image_path"]

        if path and os.path.exists(path):
            pixmap = QtGui.QPixmap(path).scaled(
                self.preview.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.preview.setPixmap(pixmap)
            self.preview.setText("")
        else:
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText("(Попередній перегляд)")

    def check_alerts(self):
        """Перевірка та відображення попереджень."""
        alerts = []
        tomorrow = date.today() + timedelta(days=1)

        for category in CATEGORIES:
            resources = self.conn.execute(
                """SELECT r.name, r.quantity, r.expiration_date, r.low_stock_threshold
                FROM resources r
                JOIN categories c ON r.category_id = c.id
                WHERE c.name = ?""",
                (category,)
            ).fetchall()

            for r in resources:
                if r["quantity"] < r["low_stock_threshold"]:
                    alerts.append(
                        f"Низький залишок (<{r['low_stock_threshold']}): "
                        f"{r['name']} ({r['quantity']})"
                    )
                
                if r["expiration_date"]:
                    try:
                        exp = datetime.strptime(r["expiration_date"], "%Y-%m-%d").date()
                        if exp == tomorrow:
                            alerts.append(
                                f"Завтра закінчується термін придатності: "
                                f"{r['name']} ({exp})"
                            )
                    except ValueError:
                        pass

        if alerts:
            QtWidgets.QMessageBox.warning(
                self,
                "Попередження",
                "\n".join(alerts)
            )

    def add_resource(self):
        """Додавання нового ресурсу."""
        from ui.resource_editor_dialog import ResourceEditor
        
        editor = ResourceEditor(self.conn, self.current_category)
        if editor.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            data = editor.get_data()
            
            # Отримання ID категорії
            cat_id = self.conn.execute(
                "SELECT id FROM categories WHERE name = ?",
                (self.current_category,)
            ).fetchone()["id"]
            
            try:
                # Додавання ресурсу
                cur = self.conn.execute(
                    """INSERT INTO resources (
                        name, category_id, quantity, unit_of_measure,
                        description, image_path, supplier, phone,
                        origin, arrival_date, cost, expiration_date,
                        low_stock_threshold
                    ) VALUES (
                        ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?
                    )""",
                    (
                        data["name"],
                        cat_id,
                        data["quantity"],
                        data["unit_of_measure"],
                        data["description"],
                        data["image_path"],
                        data["supplier"],
                        data["phone"],
                        data["origin"],
                        data["arrival_date"],
                        data["cost"],
                        data["expiration_date"],
                        data["low_stock_threshold"]
                    )
                )
                self.conn.commit()
                
                # Якщо вказана початкова кількість, створюємо транзакцію надходження
                if data["quantity"] > 0:
                    from logic.transaction_handler import TransactionHandler
                    handler = TransactionHandler(self.conn)
                    handler.add_transaction(
                        resource_id=cur.lastrowid,
                        transaction_type="надходження",
                        quantity_changed=data["quantity"],
                        issued_by_user_id=1,  # TODO: Отримати реальний ID користувача
                        notes="Початкове надходження"
                    )
                
                self.load_data()
                self.check_alerts()
                
            except sqlite3.Error as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Помилка",
                    f"Не вдалося додати ресурс: {str(e)}"
                )

    def edit_resource(self):
        """Редагування ресурсу."""
        rid = self.get_selected_resource_id()
        if rid is None:
            return

        # Отримання даних ресурсу
        resource = self.conn.execute(
            "SELECT * FROM resources WHERE id = ?",
            (rid,)
        ).fetchone()

        if not resource:
            return

        from ui.resource_editor_dialog import ResourceEditor
        
        editor = ResourceEditor(
            self.conn,
            self.current_category,
            dict(resource)
        )
        
        if editor.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            data = editor.get_data()
            
            try:
                # Оновлення ресурсу
                self.conn.execute(
                    """UPDATE resources SET
                        name = ?,
                        quantity = ?,
                        unit_of_measure = ?,
                        description = ?,
                        image_path = ?,
                        supplier = ?,
                        phone = ?,
                        origin = ?,
                        arrival_date = ?,
                        cost = ?,
                        expiration_date = ?,
                        low_stock_threshold = ?
                    WHERE id = ?""",
                    (
                        data["name"],
                        data["quantity"],
                        data["unit_of_measure"],
                        data["description"],
                        data["image_path"],
                        data["supplier"],
                        data["phone"],
                        data["origin"],
                        data["arrival_date"],
                        data["cost"],
                        data["expiration_date"],
                        data["low_stock_threshold"],
                        rid
                    )
                )
                self.conn.commit()
                
                # Якщо змінилася кількість, створюємо відповідну транзакцію
                if data["quantity"] != resource["quantity"]:
                    from logic.transaction_handler import TransactionHandler
                    handler = TransactionHandler(self.conn)
                    
                    diff = data["quantity"] - resource["quantity"]
                    if diff > 0:
                        transaction_type = "надходження"
                    else:
                        transaction_type = "списання"
                        diff = abs(diff)
                    
                    handler.add_transaction(
                        resource_id=rid,
                        transaction_type=transaction_type,
                        quantity_changed=diff,
                        issued_by_user_id=1,  # TODO: Отримати реальний ID користувача
                        notes="Коригування кількості при редагуванні"
                    )
                
                self.load_data()
                self.check_alerts()
                
            except sqlite3.Error as e:
                QtWidgets.QMessageBox.critical(
                    self,
                    "Помилка",
                    f"Не вдалося оновити ресурс: {str(e)}"
                )

    def delete_resource(self):
        """Видалення ресурсу."""
        rid = self.get_selected_resource_id()
        if rid is None:
            return

        reply = QtWidgets.QMessageBox.question(
            self,
            "Підтвердження",
            "Ви впевнені, що хочете видалити цей ресурс?",
            QtWidgets.QMessageBox.StandardButton.Yes |
            QtWidgets.QMessageBox.StandardButton.No
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.conn.execute("DELETE FROM resources WHERE id = ?", (rid,))
            self.conn.commit()
            self.load_data()
            self.check_alerts()

    def show_info(self):
        """Показ інформації про ресурс."""
        # TODO: Реалізувати після створення InfoDialog
        pass

    def export_report(self):
        """Експорт звіту про ресурс."""
        # TODO: Реалізувати після створення модуля звітів
        pass

    def show_quantity_analytics(self):
        """Показ аналітики по залишках."""
        # TODO: Реалізувати після створення модуля аналітики
        pass

    def show_cost_analytics(self):
        """Показ аналітики по витратах."""
        # TODO: Реалізувати після створення модуля аналітики
        pass

    def show_transaction_dialog(self):
        """Показ діалогу створення нової транзакції."""
        from ui.transaction_dialog import TransactionDialog
        
        rid = self.get_selected_resource_id()
        dialog = TransactionDialog(
            self.conn,
            self.current_user_id,  # Використовуємо ID поточного користувача
            resource_id=rid,
            category=self.current_category if not rid else None
        )
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_data()
            self.check_alerts()

    def logout(self):
        """Вихід з облікового запису."""
        self.hide()
        login = LoginDialog()
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.current_user_role = login.user_role
            self.current_user_id = login.user_id
            self.update_ui_for_role()
            self.show()
            self.check_alerts()
        else:
            QtWidgets.QApplication.instance().quit()

    def update_ui_for_role(self):
        """Оновлює UI відповідно до ролі користувача"""
        # Оновлюємо статусний рядок
        self.status_label.setText(f"Ласкаво просимо! Роль: {self.current_user_role}")
        
        # Оновлюємо доступність кнопок на панелі інструментів
        for action in self.toolbar.actions():
            if action.text() in ["Додати", "Редагувати", "Видалити"]:
                action.setVisible(self.current_user_role == "admin")

    def show_resource_editor(self):
        """Відкриває діалог редагування ресурсів"""
        if self.current_user_role == 'admin':
            dialog = ResourceEditor(self.conn, self.current_category)
            dialog.exec()

    def show_requisition_dialog(self):
        """Відкриває діалог створення нової заявки."""
        dialog = RequisitionDialog(
            current_user_id=self.current_user_id,
            current_user_role=self.current_user_role,
            parent=self
        )
        if dialog.exec():
            self.load_requisitions_data()  # Оновлюємо таблицю після створення

    def apply_requisition_filters(self):
        """Збирає дані з фільтрів та оновлює список заявок."""
        date_from = self.date_from_edit.date().toString("yyyy-MM-dd")
        date_to = self.date_to_edit.date().toString("yyyy-MM-dd")
        status = self.status_filter_combo.currentData()
        urgency = self.urgency_filter_combo.currentData()
        search_term = self.search_requisition_edit.text().strip()
        
        self.load_requisitions_data(
            date_from=date_from,
            date_to=date_to,
            status=status,
            urgency=urgency,
            search_term=search_term
        )

    def reset_requisition_filters(self):
        """Скидає фільтри до значень за замовчуванням та оновлює список."""
        self.date_from_edit.setDate(QDate.currentDate().addMonths(-1))
        self.date_to_edit.setDate(QDate.currentDate())
        self.status_filter_combo.setCurrentIndex(0)
        self.urgency_filter_combo.setCurrentIndex(0)
        self.search_requisition_edit.clear()
        
        self.load_requisitions_data()

    def load_requisitions_data(self, date_from=None, date_to=None, status=None, urgency=None, search_term=None):
        """Завантажує дані про заявки в таблицю з урахуванням фільтрів."""
        self.requisitions_table.setRowCount(0)
        
        try:
            # Отримуємо заявки через функцію з requisition_handler
            requisitions = get_requisitions(
                date_from=date_from,
                date_to=date_to,
                status=status,
                urgency=urgency,
                search_term=search_term,
                created_by_user_id=None if self.current_user_role == 'admin' else self.current_user_id
            )
            
            for req in requisitions:
                row = self.requisitions_table.rowCount()
                self.requisitions_table.insertRow(row)
                
                self.requisitions_table.setItem(row, 0, QtWidgets.QTableWidgetItem(str(req['id'])))
                self.requisitions_table.setItem(row, 1, QtWidgets.QTableWidgetItem(req['requisition_number']))
                self.requisitions_table.setItem(row, 2, QtWidgets.QTableWidgetItem(req['creation_date']))
                self.requisitions_table.setItem(row, 3, QtWidgets.QTableWidgetItem(req['department_requesting']))
                self.requisitions_table.setItem(row, 4, QtWidgets.QTableWidgetItem(req['created_by']))
                self.requisitions_table.setItem(row, 5, QtWidgets.QTableWidgetItem(req['status'].capitalize()))
                self.requisitions_table.setItem(row, 6, QtWidgets.QTableWidgetItem(req['urgency'].capitalize()))
                self.requisitions_table.setItem(row, 7, QtWidgets.QTableWidgetItem(req['notes'] or ''))
                
        except Exception as e:
            print(f"Помилка завантаження заявок: {e}")
            QtWidgets.QMessageBox.critical(
                self,
                "Помилка",
                f"Не вдалося завантажити список заявок: {str(e)}"
            )

    def setup_toolbar(self):
        """Налаштування панелі інструментів."""
        self.toolbar = QtWidgets.QToolBar()
        self.addToolBar(self.toolbar)

        # Пошук
        self.toolbar.addWidget(QtWidgets.QLabel("Пошук:"))
        self.search = QtWidgets.QLineEdit()
        self.search.textChanged.connect(self.filter_resources)
        self.toolbar.addWidget(self.search)
        self.toolbar.addSeparator()

        # Вибір категорії
        self.category = QtWidgets.QComboBox()
        self.category.addItems(CATEGORIES)
        self.category.currentIndexChanged.connect(self.change_category)
        self.toolbar.addWidget(self.category)

        # Кнопки для адміністратора
        if self.current_user_role == "admin":
            self.toolbar.addAction(
                QtGui.QAction("Додати", self, triggered=self.add_resource)
            )
            self.toolbar.addAction(
                QtGui.QAction("Редагувати", self, triggered=self.edit_resource)
            )
            self.toolbar.addAction(
                QtGui.QAction("Видалити", self, triggered=self.delete_resource)
            )

        # Загальні кнопки
        self.toolbar.addAction(
            QtGui.QAction("Інформація", self, triggered=self.show_info)
        )
        self.toolbar.addAction(
            QtGui.QAction("Нова транзакція", self, triggered=self.show_transaction_dialog)
        )
        self.toolbar.addAction(
            QtGui.QAction("Нова заявка", self, triggered=self.show_requisition_dialog)
        )
        self.toolbar.addAction(
            QtGui.QAction("Звіт", self, triggered=self.export_report)
        )
        self.toolbar.addAction(
            QtGui.QAction("Аналітика залишків", self, triggered=self.show_quantity_analytics)
        )
        self.toolbar.addAction(
            QtGui.QAction("Аналітика витрат", self, triggered=self.show_cost_analytics)
        )
        self.toolbar.addAction(
            QtGui.QAction("Вийти", self, triggered=self.logout)
        ) 