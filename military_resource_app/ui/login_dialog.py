#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог авторизації користувача.
"""

from PyQt6 import QtCore, QtWidgets
from logic.db_manager import validate_user, create_connection, create_tables

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.conn = create_connection()
        if self.conn:
            create_tables(self.conn)
        else:
            QtWidgets.QMessageBox.critical(self, "Помилка", "Не вдалося підключитися до бази даних")
            self.reject()
        self.setup_ui()
        self.user_role = None
        self.user_id = None

    def setup_ui(self):
        """Налаштування інтерфейсу."""
        self.setFixedSize(330, 200)
        self.setWindowTitle("Авторизація")
        
        layout = QtWidgets.QVBoxLayout(self)
        
        # Заголовок
        title = QtWidgets.QLabel("Авторизація")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:18pt; font-weight:bold;")
        layout.addWidget(title)

        # Форма
        form = QtWidgets.QFormLayout()
        self.user = QtWidgets.QLineEdit()
        self.pwd = QtWidgets.QLineEdit()
        self.pwd.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        form.addRow("Логін:", self.user)
        form.addRow("Пароль:", self.pwd)
        layout.addLayout(form)

        # Кнопка входу
        btn = QtWidgets.QPushButton("Увійти")
        btn.clicked.connect(self.try_login)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)

    def try_login(self):
        """Спроба авторизації."""
        if not self.conn:
            QtWidgets.QMessageBox.critical(self, "Помилка", "Відсутнє з'єднання з базою даних")
            return

        username = self.user.text().strip()
        password = self.pwd.text().strip()

        if not username or not password:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Введіть логін та пароль")
            return

        self.user_role, self.user_id = validate_user(self.conn, username, password)
        if self.user_role:
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Невірний логін або пароль")
            
    def get_user_id(self):
        """Повертає ID авторизованого користувача."""
        return self.user_id 