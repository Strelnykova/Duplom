#!/usr/bin/env python
# -*- coding: utf-8 -*-

from logic.test_data_generator import generate_test_data
from logic.db_manager import create_connection, create_tables

if __name__ == '__main__':
    # Створюємо з'єднання та таблиці
    conn = create_connection()
    if conn:
        create_tables(conn)
        conn.close()
        print("Таблиці створено")
        
        # Генеруємо тестові дані
        generate_test_data()
    else:
        print("Помилка підключення до бази даних") 