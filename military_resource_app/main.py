#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Головний файл програми обліку військового майна.
"""

import os
import sys
import sqlite3
from PyQt6 import QtWidgets

# Додаємо шлях до батьківської директорії в PYTHONPATH
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

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

def get_user_details(conn, user_id):
    """Отримує деталі користувача з бази даних."""
    try:
        cursor = conn.cursor()
        user = cursor.execute("""
            SELECT username, rank, last_name, first_name, middle_name, position, role
            FROM users 
            WHERE id = ?
        """, (user_id,)).fetchone()
        return dict(user) if user else {}
    except Exception as e:
        print(f"Помилка отримання даних користувача: {e}")
        return {}

def run_application():
    """Головна функція запуску програми."""
    app = QtWidgets.QApplication(sys.argv)
    app.setStyle("Fusion")
    app.setStyleSheet(load_styles())

    # Ініціалізація бази даних
    conn_init = create_connection()
    if conn_init:
        create_tables(conn_init)
        conn_init.close()
    else:
        QtWidgets.QMessageBox.critical(
            None, 
            "Помилка Бази Даних",
            "Не вдалося підключитися до бази даних. Програма не може продовжити роботу."
        )
        return -1

    current_main_window = None

    while True:  # Головний цикл: логін -> головне вікно -> логін ...
        login_dialog = LoginDialog()
        
        if login_dialog.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            # Отримуємо дані автентифікації
            user_role = login_dialog.user_role
            user_id = login_dialog.user_id
            
            if not user_id or not user_role:
                print("Помилка: не вдалося отримати дані автентифікації.")
                break
            
            # Отримуємо повні дані користувача
            conn_main = create_connection()
            current_user_details = None
            if conn_main and user_id:
                current_user_details = get_user_details(conn_main, user_id)
                conn_main.close()
            
            # Видаляємо попереднє головне вікно, якщо воно існує
            if current_main_window:
                current_main_window.deleteLater()

            # Створюємо нове головне вікно
            current_main_window = MainWindow(
                role=user_role,
                user_id=user_id,
                user_details=current_user_details
            )
            current_main_window.show()
            
            # Запускаємо цикл обробки подій
            app.exec()
            
            # Перевіряємо стан вікна після завершення циклу
            if current_main_window and not current_main_window.isVisible():
                # Це був logout (бо closeEvent закрив би програму)
                print("Повернення до вікна входу...")
                continue
            else:
                # Вікно було закрито повністю
                print("Завершення головного циклу програми.")
                break
        else:
            # Користувач закрив діалог входу
            print("Користувач скасував вхід. Завершення програми.")
            break

    return 0

if __name__ == '__main__':
    sys.exit(run_application()) 