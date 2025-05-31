#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Функції для роботи з базою даних.
"""

import os
import sqlite3
from datetime import datetime

# Змінюємо шлях до бази даних на абсолютний
DB_PATH = os.path.abspath(os.path.join(os.path.dirname(os.path.dirname(__file__)), "resources.db"))

CATEGORIES = [
    "Продукти харчування",
    "Медикаменти",
    "Боєприпаси",
    "Форма",
    "ПММ",
    "Інженерне майно",
    "Засоби зв'язку",
    "Спорядження та захист",
    "Ремонтні засоби та запчастини"
]

def create_connection(db_file=DB_PATH):
    """Створює з'єднання з базою даних."""
    conn = None
    try:
        print(f"Спроба підключення до бази даних: {db_file}")
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        print("З'єднання успішно встановлено")
        return conn
    except sqlite3.Error as e:
        print(f"Помилка підключення до БД: {e}")
    except Exception as e:
        print(f"Неочікувана помилка: {e}")
    return conn

def create_tables(conn):
    """Створює необхідні таблиці в базі даних."""
    if conn is None:
        print("Немає з'єднання з БД")
        return

    try:
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
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
                FOREIGN KEY (category_id) REFERENCES categories (id)
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
                FOREIGN KEY (resource_id) REFERENCES resources (id),
                FOREIGN KEY (issued_by_user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS requisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_number TEXT UNIQUE NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                department_requesting TEXT,
                creation_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'нова' CHECK(status IN ('нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано')),
                urgency TEXT DEFAULT 'планова' CHECK(urgency IN ('планова', 'термінова', 'критична')),
                notes TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS requisition_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_id INTEGER NOT NULL,
                resource_id INTEGER,
                requested_resource_name TEXT NOT NULL,
                quantity_requested INTEGER NOT NULL,
                unit_of_measure TEXT,
                justification TEXT,
                item_status TEXT DEFAULT 'очікує' CHECK(item_status IN ('очікує', 'схвалено', 'замовлено', 'отримано', 'відхилено')),
                FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
                FOREIGN KEY (resource_id) REFERENCES resources (id)
            );
        """)
        conn.commit()
        print("Таблиці успішно створено/перевірено.")

        # Початкове заповнення категорій
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            for cat_name in CATEGORIES:
                cur.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
            conn.commit()
            print("Початкові категорії додано.")

        # Початкове заповнення користувачів
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO users(username, password, role) VALUES(?,?,?)",
                [("admin", "admin", "admin"), ("user", "user", "user")]
            )
            conn.commit()
            print("Початкових користувачів додано.")

    except sqlite3.Error as e:
        print(f"Помилка при створенні таблиць: {e}")

# Допоміжні функції для роботи з БД
def validate_user(conn, username, password):
    """
    Перевіряє облікові дані користувача.
    
    Returns:
        tuple: (role, user_id) або (None, None) якщо автентифікація не вдалася
    """
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT role, id FROM users WHERE username=? AND password=?",
            (username, password)
        ).fetchone()
        
        if row:
            return row['role'], row['id']
    except sqlite3.Error as e:
        print(f"Помилка при валідації користувача: {e}")
    
    return None, None

def fetch_resources(conn, category):
    """Отримує список ресурсів для вказаної категорії."""
    return conn.execute(
        """SELECT r.id, r.name, r.quantity, r.description, r.image_path, r.expiration_date,
                  r.category_id, r.unit_of_measure, r.supplier, r.phone, r.origin,
                  r.arrival_date, r.cost, r.low_stock_threshold
        FROM resources r 
        JOIN categories c ON r.category_id = c.id 
        WHERE c.name=?""", (category,)
    ).fetchall()

def add_resource(conn, name, quantity, description, image_path, category):
    """Додає новий ресурс."""
    cat_id = conn.execute(
        "SELECT id FROM categories WHERE name=?", (category,)
    ).fetchone()["id"]
    
    cur = conn.execute(
        """INSERT INTO resources(name,quantity,description,image_path,category_id) 
        VALUES(?,?,?,?,?)""",
        (name, quantity, description, image_path, cat_id)
    )
    conn.commit()
    return cur.lastrowid

def update_resource(conn, rid, name, quantity, description, image_path):
    """Оновлює існуючий ресурс."""
    conn.execute(
        """UPDATE resources 
        SET name=?,quantity=?,description=?,image_path=? 
        WHERE id=?""",
        (name, quantity, description, image_path, rid)
    )
    conn.commit()

def delete_resource(conn, rid):
    """Видаляє ресурс та пов'язані записи."""
    conn.execute("DELETE FROM resource_transactions WHERE resource_id=?", (rid,))
    conn.execute("DELETE FROM requisition_items WHERE resource_id=?", (rid,))
    conn.execute("DELETE FROM resources WHERE id=?", (rid,))
    conn.commit()

def add_transaction(conn, resource_id, transaction_type, quantity_changed, 
                   recipient_department, issued_by_user_id, notes=None):
    """Додає нову транзакцію."""
    conn.execute(
        """INSERT INTO resource_transactions(
            resource_id, transaction_type, quantity_changed,
            recipient_department, issued_by_user_id, transaction_date, notes
        ) VALUES(?,?,?,?,?,?,?)""",
        (resource_id, transaction_type, quantity_changed,
         recipient_department, issued_by_user_id,
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         notes)
    )
    conn.commit()

def insert_test_resources(conn):
    """Insert test resources into the resources table."""
    try:
        cur = conn.cursor()
        
        # Get category IDs
        cur.execute("SELECT id FROM categories WHERE name = 'Боєприпаси' LIMIT 1")
        ammo_cat_id = cur.fetchone()['id']
        cur.execute("SELECT id FROM categories WHERE name = 'Медикаменти' LIMIT 1")
        med_cat_id = cur.fetchone()['id']
        cur.execute("SELECT id FROM categories WHERE name = 'Спорядження та захист' LIMIT 1")
        equip_cat_id = cur.fetchone()['id']
        
        test_resources = [
            ('5.45x39 Ammunition', ammo_cat_id, 'rounds', 'Standard rifle ammunition'),
            ('IFAK Individual First Aid Kit', med_cat_id, 'kit', 'Individual first aid kit'),
            ('Kevlar Helmet', equip_cat_id, 'piece', 'Standard issue helmet'),
            ('Bulletproof Vest', equip_cat_id, 'piece', 'Level III protection'),
            ('Combat Boots', equip_cat_id, 'pair', 'All-weather tactical boots')
        ]
        
        cur.executemany("""
            INSERT OR IGNORE INTO resources (name, category_id, unit_of_measure, description)
            VALUES (?, ?, ?, ?)
        """, test_resources)
        conn.commit()
        print("Test resources added successfully")
    except sqlite3.Error as e:
        print(f"Error inserting test resources: {e}")

if __name__ == '__main__':
    conn = create_connection()
    if conn:
        create_tables(conn)
        insert_test_resources(conn)  # Add test resources
        conn.close() 