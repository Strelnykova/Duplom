#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для ініціалізації бази даних.
"""

import sqlite3
import os
from datetime import datetime, timedelta
import random

DB_FILENAME = "resources.db"
# Визначаємо шлях до папки military_resource_app відносно поточного файлу скрипта
# Припускаємо, що initialize_database.py знаходиться в корені проєкту,
# а папка military_resource_app - на тому ж рівні.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_FOLDER_PATH = os.path.join(BASE_DIR, 'military_resource_app')
DB_PATH = os.path.join(DB_FOLDER_PATH, DB_FILENAME)

EXPECTED_CATEGORIES = [
    "Боєприпаси", "ПММ", "Продукти харчування", "Медикаменти",
    "Інженерне майно", "Засоби зв'язку", "Форма",
    "Спорядження та захист", "Ремонтні засоби та запчастини", "Інше"
]

VALID_REQUISITION_TYPES = [
    "Забезпечення БК", "Забезпечення ПММ", "Медичне забезпечення",
    "Форма та спорядження", "Продовольче забезпечення", "МТЗ", "Інше"
]

def create_connection(db_file_path=DB_PATH):
    """ Створює з'єднання з базою даних SQLite. Створює директорію, якщо її немає. """
    conn = None
    try:
        # Створюємо директорію для БД, якщо вона не існує
        os.makedirs(os.path.dirname(db_file_path), exist_ok=True)
        conn = sqlite3.connect(db_file_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        print(f"З'єднання з БД '{db_file_path}' успішно встановлено/створено.")
        return conn
    except sqlite3.Error as e:
        print(f"Помилка підключення до БД '{db_file_path}': {e}")
    return conn

def create_defined_tables(conn):
    """ Створює всі таблиці з визначеною структурою, використовуючи IF NOT EXISTS. """
    if not conn:
        return False
    print("Перевірка/створення таблиць з визначеною структурою...")
    try:
        cur = conn.cursor()
        # Використовуємо CREATE TABLE IF NOT EXISTS для всіх таблиць
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user')),
                rank TEXT,
                last_name TEXT,
                first_name TEXT,
                middle_name TEXT,
                position TEXT
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES categories (id)
            );

            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit_of_measure TEXT,
                description TEXT,
                image_path TEXT,
                supplier TEXT,
                phone TEXT,
                origin TEXT,
                arrival_date TEXT,
                cost REAL,
                expiration_date TEXT,
                low_stock_threshold INTEGER DEFAULT 10,
                FOREIGN KEY (category_id) REFERENCES categories (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS requisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_number TEXT UNIQUE NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                department_requesting TEXT,
                creation_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'нова' CHECK(status IN ('нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано')),
                urgency TEXT DEFAULT 'планова' CHECK(urgency IN ('планова', 'термінова', 'критична')),
                purpose_description TEXT,
                requisition_type TEXT CHECK(requisition_type IN ('Забезпечення БК', 'Забезпечення ПММ', 'Медичне забезпечення', 'Форма та спорядження', 'Продовольче забезпечення', 'МТЗ', 'Інше')),
                author_manual_rank TEXT,
                author_manual_lastname TEXT,
                author_manual_initials TEXT,
                notes TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS requisition_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_id INTEGER NOT NULL,
                resource_id INTEGER,
                requested_resource_name TEXT NOT NULL,
                quantity_requested INTEGER NOT NULL,
                unit_of_measure TEXT,
                justification TEXT,
                item_status TEXT DEFAULT 'очікує' CHECK(item_status IN ('очікує', 'схвалено', 'замовлено', 'отримано', 'відхилено', 'виконано', 'частково виконано')),
                FOREIGN KEY (requisition_id) REFERENCES requisitions (id) ON DELETE CASCADE,
                FOREIGN KEY (resource_id) REFERENCES resources (id) ON DELETE SET NULL
            );

            CREATE TABLE IF NOT EXISTS resource_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('надходження', 'видача', 'списання', 'повернення')),
                quantity_changed INTEGER NOT NULL,
                transaction_date TEXT NOT NULL,
                recipient_department TEXT,
                issued_by_user_id INTEGER,
                notes TEXT,
                requisition_item_id INTEGER,
                FOREIGN KEY (resource_id) REFERENCES resources (id) ON DELETE CASCADE,
                FOREIGN KEY (issued_by_user_id) REFERENCES users (id) ON DELETE SET NULL,
                FOREIGN KEY (requisition_item_id) REFERENCES requisition_items (id) ON DELETE SET NULL
            );
        """)
        conn.commit()
        print("Структуру таблиць перевірено/створено.")
        return True
    except sqlite3.Error as e:
        print(f"Помилка при створенні таблиць: {e}")
        conn.rollback()
        return False

def populate_initial_data(conn):
    """ Заповнює таблиці categories та users початковими даними, ЯКЩО ВОНИ ПОРОЖНІ. """
    if not conn:
        return
    print("Перевірка/заповнення початковими даними (категорії, користувачі)...")
    cur = conn.cursor()
    try:
        # Категорії
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            for cat_name in EXPECTED_CATEGORIES:
                cur.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
            print(f"Додано {len(EXPECTED_CATEGORIES)} категорій.")
        else:
            print("Категорії вже існують або таблиця не порожня.")

        # Користувачі
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            users_data = [
                ("admin", "admin_password", "admin", "Полковник", "Адміністраторенко", "Адмін", "Адмінович", "Начальник служби забезпечення"),
                ("user1", "user1_password", "user", "Сержант", "Користувацький", "Іван", "Іванович", "Командир 1-го відділення"),
                ("user2", "user2_password", "user", "Солдат", "Тестовий", "Петро", "Петрович", "Стрілець 2-го відділення")
            ]
            cur.executemany(
                "INSERT INTO users(username, password, role, rank, last_name, first_name, middle_name, position) VALUES(?,?,?,?,?,?,?,?)",
                users_data
            )
            print(f"Додано {len(users_data)} тестових користувачів.")
        else:
            print("Користувачі вже існують або таблиця не порожня.")
        conn.commit()
    except sqlite3.Error as e:
        print(f"Помилка при заповненні початковими даними: {e}")
        conn.rollback()

def main_initialize_or_create():
    """
    Головна функція для ініціалізації БД:
    1. Створює з'єднання (і файл БД, якщо його немає).
    2. Створює таблиці, якщо вони не існують.
    3. Заповнює категорії та користувачів, якщо їх таблиці порожні.
    Цей скрипт НЕ видаляє існуючий файл БД автоматично.
    """
    print(f"Ініціалізація бази даних за шляхом: {DB_PATH}")
    conn = create_connection()
    if conn:
        if create_defined_tables(conn): # Якщо таблиці успішно створені (або вже існували)
            populate_initial_data(conn)
        conn.close()
        print(f"\nІніціалізацію бази даних '{DB_PATH}' завершено.")
    else:
        print("Ініціалізація бази даних не вдалася: не вдалося встановити з'єднання.")

if __name__ == "__main__":
    main_initialize_or_create()
    print("\n--- Перевірка ---")
    print("Якщо ви бачите повідомлення про створення таблиць та додавання категорій/користувачів,")
    print("це означає, що база даних була порожньою або не існувала і була створена з нуля.")
    print("Якщо ви бачите повідомлення 'Категорії вже існують' та 'Користувачі вже існують',")
    print("це означає, що скрипт успішно підключився до існуючої бази даних і не перезаписував ці дані.")
    print("ВАЖЛИВО: Цей скрипт НЕ виправляє структуру існуючих таблиць, якщо вона НЕПРАВИЛЬНА.")
    print("Якщо у вас помилки 'no such column', вам потрібно видалити старий файл resources.db вручну,")
    print(f"який знаходиться тут: {DB_PATH}")
    print("і потім запустити цей скрипт initialize_database.py знову, щоб створити БД з правильною структурою.") 