#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для генерації тестових даних.
"""

import sqlite3
from datetime import datetime, timedelta
import random
from .db_manager import create_connection, create_tables

def generate_test_data():
    """Генерує тестові дані для бази даних."""
    conn = create_connection()
    if not conn:
        print("Помилка підключення до бази даних")
        return

    try:
        cur = conn.cursor()
        
        # 1. Створюємо тестових користувачів
        users = [
            ("admin", "admin", "admin", "Адміністратор системи"),
            ("user", "user", "user", "Звичайний користувач")
        ]
        
        cur.executemany(
            "INSERT INTO users (username, password, role, full_name) VALUES (?, ?, ?, ?)",
            users
        )
        conn.commit()

        # 2. Створюємо базові категорії
        categories = [
            ("Зброя та боєприпаси", "Вогнепальна зброя, боєприпаси та супутнє спорядження"),
            ("Медичне забезпечення", "Медикаменти, перев'язувальні матеріали та медичне обладнання"),
            ("Спорядження", "Військова форма, бронежилети, каски та інше індивідуальне спорядження"),
            ("Зв'язок", "Засоби зв'язку, рації, антени та акумулятори"),
            ("Транспорт", "Транспортні засоби та запчастини")
        ]
        
        cur.executemany(
            "INSERT INTO categories (name, description) VALUES (?, ?)",
            categories
        )
        conn.commit()

        # Отримуємо ID категорій
        cur.execute("SELECT id, name FROM categories")
        category_ids = {name: id for id, name in cur.fetchall()}

        # 3. Створюємо тестові ресурси
        resources = [
            # Зброя та боєприпаси
            (category_ids["Зброя та боєприпаси"], "АК-74", 15, "шт.", "5.45-мм автомат Калашникова", 
             "ДП «Зброя України»", "+380501234567", "Україна", "2023-01-15", 25000, None, 5),
            (category_ids["Зброя та боєприпаси"], "Набої 5.45x39", 2000, "шт.", "Набої для АК-74", 
             "ДП «Боєприпаси»", "+380507654321", "Україна", "2023-02-20", 15, "2025-02-20", 500),
            
            # Медичне забезпечення
            (category_ids["Медичне забезпечення"], "Аптечка IFAK", 50, "шт.", "Індивідуальна аптечка першої допомоги", 
             "МедТех", "+380509876543", "США", "2023-03-10", 2500, "2025-03-10", 20),
            (category_ids["Медичне забезпечення"], "Джгут CAT", 100, "шт.", "Турнікет Combat Application Tourniquet", 
             "NAR", "+380506789012", "США", "2023-03-15", 750, "2025-03-15", 30),
            
            # Спорядження
            (category_ids["Спорядження"], "Бронежилет Корсар", 30, "шт.", "Бронежилет 4 класу захисту", 
             "ТОВ «Захист»", "+380503456789", "Україна", "2023-04-01", 30000, None, 10),
            (category_ids["Спорядження"], "Каска КП-3", 40, "шт.", "Кевларова каска", 
             "ТОВ «Захист»", "+380503456789", "Україна", "2023-04-05", 8000, None, 15),
            
            # Зв'язок
            (category_ids["Зв'язок"], "Рація Motorola", 25, "шт.", "Професійна рація", 
             "Motorola", "+380504567890", "США", "2023-05-01", 12000, None, 8),
            (category_ids["Зв'язок"], "Антена AT-1", 15, "шт.", "Антена для рацій", 
             "РадіоТех", "+380505678901", "Україна", "2023-05-05", 2000, None, 5),
            
            # Транспорт
            (category_ids["Транспорт"], "Шини R16", 16, "шт.", "Всесезонні шини", 
             "АвтоПром", "+380506789012", "Україна", "2023-06-01", 3500, None, 8),
            (category_ids["Транспорт"], "Акумулятор 12В", 10, "шт.", "Автомобільний акумулятор", 
             "АвтоПром", "+380506789012", "Україна", "2023-06-05", 4500, "2025-06-05", 4)
        ]

        cur.executemany("""
            INSERT INTO resources (
                category_id, name, quantity, unit_of_measure, description,
                supplier, phone, origin, arrival_date, cost,
                expiration_date, low_stock_threshold
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, resources)
        conn.commit()

        # 4. Створюємо тестові заявки
        departments = ["1-й батальйон", "2-й батальйон", "Медична рота", "Розвідрота", "Штаб"]
        urgencies = ["планова", "термінова", "критична"]
        statuses = ["нова", "на розгляді", "схвалено", "відхилено", "частково виконано", "виконано"]

        # Генеруємо 20 заявок за останні 3 місяці
        for i in range(20):
            days_ago = random.randint(0, 90)
            creation_date = datetime.now() - timedelta(days=days_ago)
            
            cur.execute("""
                INSERT INTO requisitions (
                    requisition_number, created_by_user_id, department_requesting,
                    creation_date, status, urgency, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                f"REQ-{creation_date.strftime('%Y%m')}-{i+1:04d}",
                random.randint(1, 2),  # ID користувачів (1 - admin, 2 - user)
                random.choice(departments),
                creation_date.strftime("%Y-%m-%d %H:%M:%S"),
                random.choice(statuses),
                random.choice(urgencies),
                f"Тестова заявка #{i+1}"
            ))
            conn.commit()
            
            requisition_id = cur.lastrowid
            
            # Додаємо 1-4 позиції до кожної заявки
            for _ in range(random.randint(1, 4)):
                cur.execute("SELECT id FROM resources ORDER BY RANDOM() LIMIT 1")
                resource = cur.fetchone()
                
                cur.execute("""
                    INSERT INTO requisition_items (
                        requisition_id, resource_id, requested_resource_name,
                        quantity_requested, quantity_executed, status, notes
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    requisition_id,
                    resource['id'],
                    f"Ресурс #{resource['id']}",
                    random.randint(1, 10),
                    random.randint(0, 5),
                    random.choice(["очікує", "частково виконано", "виконано"]),
                    f"Позиція заявки #{requisition_id}"
                ))
            conn.commit()

        # 5. Генеруємо тестові транзакції
        transaction_types = ["надходження", "видача"]
        
        for _ in range(50):  # 50 транзакцій
            days_ago = random.randint(0, 90)
            transaction_date = datetime.now() - timedelta(days=days_ago)
            
            cur.execute("SELECT id FROM resources ORDER BY RANDOM() LIMIT 1")
            resource = cur.fetchone()
            
            cur.execute("""
                INSERT INTO transactions (
                    resource_id, transaction_type, quantity_changed,
                    transaction_date, issued_by_user_id, recipient_department,
                    notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                resource['id'],
                random.choice(transaction_types),
                random.randint(1, 10) * (1 if random.random() > 0.5 else -1),
                transaction_date.strftime("%Y-%m-%d %H:%M:%S"),
                random.randint(1, 2),  # ID користувачів (1 - admin, 2 - user)
                random.choice(departments) if random.random() > 0.5 else None,
                f"Тестова транзакція для ресурсу #{resource['id']}"
            ))
            conn.commit()

        print("Тестові дані успішно згенеровано")

    except sqlite3.Error as e:
        print(f"Помилка при генерації тестових даних: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == '__main__':
    generate_test_data() 