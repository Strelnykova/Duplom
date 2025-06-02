#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для перевірки даних в базі даних.
"""

import os
import sys
import sqlite3

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DB_FILE = os.path.join(PROJECT_ROOT, 'resources.db')

def check_database():
    """Перевіряє вміст бази даних."""
    try:
        conn = sqlite3.connect(DB_FILE)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Перевірка категорій
        print("\nКатегорії:")
        print("-" * 50)
        categories = cur.execute("SELECT * FROM categories").fetchall()
        for cat in categories:
            print(f"ID: {cat['id']}, Назва: {cat['name']}")

        # Перевірка ресурсів
        print("\nРесурси (перші 5 для кожної категорії):")
        print("-" * 50)
        for cat in categories:
            print(f"\nКатегорія: {cat['name']}")
            resources = cur.execute("""
                SELECT * FROM resources 
                WHERE category_id = ? 
                LIMIT 5""", (cat['id'],)).fetchall()
            for res in resources:
                print(f"- {res['name']}: {res['quantity']} {res['unit_of_measure']}")

        # Статистика
        print("\nСтатистика:")
        print("-" * 50)
        stats = {
            'categories': cur.execute("SELECT COUNT(*) FROM categories").fetchone()[0],
            'resources': cur.execute("SELECT COUNT(*) FROM resources").fetchone()[0],
            'transactions': cur.execute("SELECT COUNT(*) FROM resource_transactions").fetchone()[0],
            'requisitions': cur.execute("SELECT COUNT(*) FROM requisitions").fetchone()[0],
        }
        for name, count in stats.items():
            print(f"{name.capitalize()}: {count}")

    except sqlite3.Error as e:
        print(f"Помилка при роботі з базою даних: {e}")
    except Exception as e:
        print(f"Неочікувана помилка: {e}")
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    check_database() 