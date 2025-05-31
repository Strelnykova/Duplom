#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головне вікно програми.
"""

import os
from datetime import datetime, date, timedelta
from PyQt6 import QtCore, QtGui, QtWidgets
import sqlite3

from logic.db_manager import CATEGORIES, fetch_resources
from ui.login_dialog import LoginDialog

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, conn, role):
        super().__init__()
        self.conn = conn
        self.role = role
        self.setup_ui()
        self.load_data()
        self.check_alerts()

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setWindowTitle("Облік військового майна")
        self.resize(1280, 720)

        # Центральний віджет
        central = QtWidgets.QWidget()
        layout = QtWidgets.QHBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)

        # Стек для таблиць категорій
        self.stack = QtWidgets.QStackedWidget()
        layout.addWidget(self.stack, 1)

        # Попередній перегляд
        self.preview = QtWidgets.QLabel("(Попередній перегляд)")
        self.preview.setObjectName("previewLabel")
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedWidth(320)
        layout.addWidget(self.preview)

        self.setCentralWidget(central)

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

        # Панель інструментів
        self.setup_toolbar()

    def setup_toolbar(self):
        """Налаштування панелі інструментів."""
        toolbar = QtWidgets.QToolBar()
        self.addToolBar(toolbar)

        # Пошук
        toolbar.addWidget(QtWidgets.QLabel("Пошук:"))
        self.search = QtWidgets.QLineEdit()
        self.search.textChanged.connect(self.filter_resources)
        toolbar.addWidget(self.search)
        toolbar.addSeparator()

        # Вибір категорії
        self.category = QtWidgets.QComboBox()
        self.category.addItems(CATEGORIES)
        self.category.currentIndexChanged.connect(self.change_category)
        toolbar.addWidget(self.category)

        # Кнопки для адміністратора
        if self.role == "admin":
            toolbar.addAction(
                QtGui.QAction("Додати", self, triggered=self.add_resource)
            )

        # Загальні кнопки
        for text, slot in [
            ("Інформація", self.show_info),
            ("Редагувати", self.edit_resource),
            ("Видалити", self.delete_resource),
            ("Нова транзакція", self.show_transaction_dialog),
            ("Звіт", self.export_report),
            ("Аналітика залишків", self.show_quantity_analytics),
            ("Аналітика витрат", self.show_cost_analytics),
            ("Вийти", self.logout)
        ]:
            action = QtGui.QAction(text, self)
            action.triggered.connect(slot)
            toolbar.addAction(action)

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
            1,  # TODO: Отримати реальний ID користувача
            resource_id=rid,
            category=self.current_category if not rid else None
        )
        
        if dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.load_data()
            self.check_alerts()

    def logout(self):
        """Вихід з облікового запису."""
        self.hide()
        login = LoginDialog(self.conn)
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.role = login.role
            self.show()
            self.check_alerts()
        else:
            QtWidgets.QApplication.instance().quit() 