#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головний файл програми обліку військового майна.
"""

import os
import sys

# Додаємо шлях до батьківської директорії в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from PyQt6 import QtWidgets

from logic.db_manager import create_connection, create_tables
from ui.login_dialog import LoginDialog
from ui.main_window import MainWindow

def load_styles() -> str:
    """Завантаження стилів."""
    style_path = os.path.join("assets", "style.css")
    if not os.path.exists(style_path):
        return ""
        
    with open(style_path, "r", encoding="utf-8") as f:
        return f.read()

def main():
    """Головна функція програми."""
    # Створення програми
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")

    # Застосування стилів
    app.setStyleSheet(load_styles())

    # Показ діалогу входу
    login = LoginDialog()
    if login.exec() != QtWidgets.QDialog.DialogCode.Accepted:
        return 0

    # Створення та показ головного вікна
    window = MainWindow(login.conn, login.user_role, login.user_id)
    window.show()

    # Запуск циклу подій
    return app.exec()

if __name__ == "__main__":
    sys.exit(main()) 