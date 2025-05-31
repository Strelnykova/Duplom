#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Діалог авторизації користувача.
"""

from PyQt6 import QtCore, QtWidgets
from logic.db_manager import validate_user

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setup_ui()
        self.role = None

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
        self.role = validate_user(self.conn, self.user.text(), self.pwd.text())
        if self.role:
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Невірний логін або пароль") 