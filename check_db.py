#!/usr/bin/env python
# -*- coding: utf-8 -*-

import sqlite3

def check_db():
    conn = sqlite3.connect('military_resource_app/resources.db')
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # Перевіряємо структуру таблиць
    print("\nСтруктура таблиць:")
    tables = cur.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    for table in tables:
        table_name = table['name']
        print(f"\nТаблиця {table_name}:")
        schema = cur.execute(f"PRAGMA table_info({table_name})").fetchall()
        for col in schema:
            print(f"  {col['name']} ({col['type']})")

    # Перевіряємо дані в таблицях
    print("\nКількість записів у таблицях:")
    for table in tables:
        table_name = table['name']
        count = cur.execute(f"SELECT COUNT(*) as count FROM {table_name}").fetchone()['count']
        print(f"{table_name}: {count} записів")

    conn.close()

if __name__ == '__main__':
    check_db() 