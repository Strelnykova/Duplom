#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для заповнення бази даних тестовими даними.
"""

import os
import sqlite3
import random
from datetime import datetime, timedelta

# Імпортуємо з правильного місця
from military_resource_app.logic.db_manager import create_connection, create_tables

# Використовуємо відносний шлях до бази даних
DB_PATH = "military_resource_app/resources.db"

def clear_specific_tables(conn):
    """Очищає дані з таблиць, залишаючи users та categories, якщо вони вже заповнені."""
    print("Очищення таблиць resource_transactions, requisition_items, requisitions, resources...")
    try:
        cur = conn.cursor()
        # Порядок важливий через foreign keys
        cur.execute("DELETE FROM resource_transactions;")
        cur.execute("DELETE FROM requisition_items;")
        cur.execute("DELETE FROM requisitions;")
        cur.execute("DELETE FROM resources;")
        conn.commit()
        print("Таблиці успішно очищено.")
    except sqlite3.Error as e:
        print(f"Помилка під час очищення таблиць: {e}")
        conn.rollback()

def get_category_id(conn, category_name):
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    row = cur.fetchone()
    return row['id'] if row else None

def get_user_id(conn, username):
    cur = conn.cursor()
    cur.execute("SELECT id FROM users WHERE username = ?", (username,))
    row = cur.fetchone()
    return row['id'] if row else None

def add_test_resources(conn):
    print("Додавання тестових ресурсів...")
    cur = conn.cursor()
    resources_data = [
        # Боєприпаси
        ("Патрони 5.45х39 мм (ПС)", "Боєприпаси", 15000, "шт", "2028-12-31", 1000, "Склад №1, м. Київ", "ПАТ 'Форт'", "+380441234567", 5.50),
        ("Патрони 7.62х39 мм (ПС)", "Боєприпаси", 12000, "шт", "2027-10-31", 800, "Склад №1, м. Київ", "ДП 'Арсенал'", "+380447654321", 6.20),
        ("Гранати Ф-1", "Боєприпаси", 500, "шт", "2030-01-01", 50, "Склад №2, м. Львів", "ВО 'Карпати'", "+380321112233", 150.00),
        ("Постріли ВОГ-25", "Боєприпаси", 800, "шт", "2029-06-30", 100, "Склад №2, м. Львів", "ВО 'Карпати'", "+380321112233", 250.00),

        # ПММ
        ("Дизельне паливо (зимове)", "ПММ", 5000, "л", None, 500, "АЗС 'WOG', м. Житомир", "ТОВ 'ВОГ РІТЕЙЛ'", "+380800300525", 48.50),
        ("Бензин А-95", "ПММ", 2000, "л", None, 200, "АЗС 'ОККО', м. Київ", "ТОВ 'ОККО-ДРАЙВ'", "+380800501101", 52.70),
        ("Мастило моторне 10W-40", "ПММ", 200, "л", None, 20, "Автомагазин 'АТЛ'", "ТОВ 'АТЛ'", "+380445020050", 120.00),

        # Продовольство та вода
        ("Сухий пайок (ІРП) - варіант 1", "Продукти харчування", 300, "уп", (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d'), 30, "Продбаза №3, м. Одеса", "ТОВ 'Їжа Воїна'", "+380487778899", 280.00),
        ("Вода питна бутильована 5л", "Продукти харчування", 1000, "бут", (datetime.now() + timedelta(days=365)).strftime('%Y-%m-%d'), 100, "Продбаза №3, м. Одеса", "ПрАТ 'Моршинська'", "+380800500000", 35.00),
        ("Консерви м'ясні (тушонка)", "Продукти харчування", 800, "банка", (datetime.now() + timedelta(days=730)).strftime('%Y-%m-%d'), 50, "Продбаза №4, м. Харків", "ТОВ 'М'ясний дар'", "+380571231234", 75.00),

        # Медикаменти
        ("Індивідуальна аптечка (IFAK)", "Медикаменти", 150, "компл", (datetime.now() + timedelta(days=300)).strftime('%Y-%m-%d'), 10, "Медсклад №1, м. Дніпро", "ТОВ 'Парамедик'", "+380567890011", 1200.00),
        ("Джгут-турнікет САТ", "Медикаменти", 400, "шт", (datetime.now() + timedelta(days=1000)).strftime('%Y-%m-%d'), 20, "Медсклад №1, м. Дніпро", "ТОВ 'Січ-Турнікет'", "+380671234500", 450.00),
        ("Знеболююче (таблетки)", "Медикаменти", 2000, "уп", (datetime.now() + timedelta(days=90)).strftime('%Y-%m-%d'), 100, "Аптека 'Подорожник'", "ТОВ 'Подорожник'", "+380800300100", 50.00),
        ("Бинт стерильний 7х14", "Медикаменти", 50, "шт", (datetime.now() - timedelta(days=10)).strftime('%Y-%m-%d'), 5, "Старий запас", "Невідомо", "N/A", 10.00), # Прострочений
        ("Антисептик для рук", "Медикаменти", 8, "флакон", (datetime.now() + timedelta(days=370)).strftime('%Y-%m-%d'), 2, "Аптека 'Подорожник'", "ТОВ 'Подорожник'", "+380800300100", 30.00), # Мало

        # Форма та спорядження
        ("Комплект форми (літо, MTP)", "Форма", 200, "компл", None, 20, "Склад одягу №5", "ТОВ 'УкрЛегПром'", "+380445556677", 2500.00),
        ("Бронежилет 'Корсар М3с'", "Спорядження та захист", 80, "шт", None, 5, "Склад ЗІЗ №1", "ТОВ 'Темп-3000'", "+380442000300", 15000.00),
        ("Шолом балістичний 'КАСКА 1М'", "Спорядження та захист", 120, "шт", None, 10, "Склад ЗІЗ №1", "ТОВ 'Темп-3000'", "+380442000300", 7000.00),
        ("Рюкзак тактичний 60л", "Спорядження та захист", 50, "шт", None, 5, "Магазин 'Мілітарист'", "ФОП Петренко", "+380971234567", 3500.00),
    ]
    try:
        for r_name, cat_name, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost in resources_data:
            cat_id = get_category_id(conn, cat_name)
            if cat_id:
                cur.execute("""
                    INSERT INTO resources (name, category_id, quantity, unit_of_measure, expiration_date,
                                           low_stock_threshold, origin, supplier, phone, cost, arrival_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (r_name, cat_id, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, datetime.now().strftime('%Y-%m-%d')))
            else:
                print(f"ПОПЕРЕДЖЕННЯ: Категорія '{cat_name}' не знайдена для ресурсу '{r_name}'. Ресурс не додано.")
        conn.commit()
        print(f"Додано {len(resources_data)} тестових ресурсів.")
    except sqlite3.Error as e:
        print(f"Помилка при додаванні тестових ресурсів: {e}")
        conn.rollback()

def add_test_requisitions_and_items(conn):
    print("Додавання тестових заявок та позицій...")
    cur = conn.cursor()
    admin_id = get_user_id(conn, "admin")
    user_id = get_user_id(conn, "user")

    print(f"Знайдено ID користувачів: admin={admin_id}, user={user_id}")

    if not admin_id or not user_id:
        print("ПОМИЛКА: Тестові користувачі 'admin' або 'user' не знайдені. Заявки не будуть додані.")
        return

    requisitions_data = [
        (user_id, "Відділення Альфа", "планова", "Планове поповнення БК та медикаментів", [
            ("Патрони 5.45х39 мм (ПС)", 2000, "шт", "Для навчань", 'схвалено'),
            ("Джгут-турнікет САТ", 10, "шт", "Поповнення аптечок", 'схвалено'),
            ("Сухий пайок (ІРП) - варіант 1", 50, "уп", "На 5 днів", 'очікує'),
        ], 'схвалено'),
        (user_id, "Відділення Бета", "термінова", "Терміново потрібні ПММ для виїзду", [
            ("Дизельне паливо (зимове)", 500, "л", "Для БТР та вантажівки", 'схвалено'),
            ("Мастило моторне 10W-40", 20, "л", "Доливка", 'відхилено'),
        ], 'частково виконано'),
        (admin_id, "Ремонтна майстерня", "планова", "Запчастини для ремонту техніки", [
            ("Фільтр масляний MANN W712", 5, "шт", "Для УАЗ", 'очікує'),
            ("Колодки гальмівні передні TRW", 2, "компл", "Для Renault Duster", 'очікує'),
        ], 'нова'),
        (user_id, "Відділення Гамма", "критична", "Засоби індивідуального захисту терміново!", [
            ("Бронежилет 'Корсар М3с'", 5, "шт", "Для нових бійців", 'замовлено'),
            ("Шолом балістичний 'КАСКА 1М'", 5, "шт", "Для нових бійців", 'отримано'),
        ], 'схвалено'),
    ]

    try:
        for cr_by_id, dep, urg, notes, items, req_status_overall in requisitions_data:
            req_num = f"REQ-TEST-{datetime.now().strftime('%Y%m%d%H%M%S%f')[:-3]}"
            cr_date = (datetime.now() - timedelta(days=random.randint(1, 60))).strftime("%Y-%m-%d %H:%M:%S")

            print(f"\nДодавання заявки: {req_num}")
            print(f"Дані заявки: відділ={dep}, статус={req_status_overall}, терміновість={urg}")

            try:
                cur.execute("""
                    INSERT INTO requisitions (requisition_number, created_by_user_id, department_requesting,
                                              creation_date, status, urgency, notes)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (req_num, cr_by_id, dep, cr_date, req_status_overall, urg, notes))
                requisition_id = cur.lastrowid
                print(f"Заявку додано, ID={requisition_id}")

                for item_name, qty_req, unit, just, item_stat in items:
                    print(f"  Додавання позиції: {item_name}, кількість={qty_req} {unit}")
                    cur.execute("SELECT id FROM resources WHERE name = ?", (item_name,))
                    res_row = cur.fetchone()
                    res_id = res_row['id'] if res_row else None
                    print(f"  Знайдено resource_id={res_id}")

                    try:
                        cur.execute("""
                            INSERT INTO requisition_items (requisition_id, resource_id, requested_resource_name,
                                                           quantity_requested, unit_of_measure, justification, item_status)
                            VALUES (?, ?, ?, ?, ?, ?, ?)
                        """, (requisition_id, res_id, item_name, qty_req, unit, just, item_stat))
                        print(f"  Позицію додано успішно")
                    except sqlite3.Error as e:
                        print(f"  ПОМИЛКА при додаванні позиції: {e}")
                        raise

            except sqlite3.Error as e:
                print(f"ПОМИЛКА при додаванні заявки: {e}")
                raise

            conn.commit()
            print(f"Заявку {req_num} збережено")

        print(f"Додано {len(requisitions_data)} тестових заявок з позиціями.")
    except sqlite3.Error as e:
        print(f"Помилка при додаванні тестових заявок: {e}")
        conn.rollback()

def add_test_transactions(conn):
    print("Додавання тестових транзакцій...")
    cur = conn.cursor()
    admin_id = get_user_id(conn, "admin")
    user_id = get_user_id(conn, "user") # Може бути інший користувач

    if not admin_id:
        print("ПОМИЛКА: Тестовий користувач 'admin' не знайдений. Транзакції не будуть додані.")
        return

    # Отримаємо деякі ресурси для транзакцій
    cur.execute("SELECT id, name, quantity FROM resources WHERE name LIKE 'Патрони 5.45х39 мм (ПС)' OR name LIKE 'Дизельне паливо (зимове)' OR name LIKE 'Індивідуальна аптечка (IFAK)'")
    resources_for_transactions = cur.fetchall()

    if not resources_for_transactions:
        print("Не знайдено ресурсів для створення тестових транзакцій.")
        return

    transactions_data = []
    for res in resources_for_transactions:
        res_id = res['id']
        res_name = res['name']
        current_qty = res['quantity']

        # Надходження
        qty_added = random.randint(50, 200)
        transactions_data.append((res_id, 'надходження', qty_added, (datetime.now() - timedelta(days=random.randint(10, 20))).strftime("%Y-%m-%d %H:%M:%S"), None, admin_id, f"Планове поповнення {res_name}"))
        new_qty_after_add = current_qty + qty_added
        cur.execute("UPDATE resources SET quantity = ? WHERE id = ?", (new_qty_after_add, res_id))


        # Видача (якщо достатньо)
        if new_qty_after_add > 20:
            qty_issued = random.randint(10, min(50, new_qty_after_add - 10)) # Видаємо не більше ніж є, залишаючи трохи
            transactions_data.append((res_id, 'видача', qty_issued, (datetime.now() - timedelta(days=random.randint(1, 9))).strftime("%Y-%m-%d %H:%M:%S"), "Відділення Альфа (тест)", admin_id, f"Видача {res_name} для потреб"))
            new_qty_after_issue = new_qty_after_add - qty_issued
            cur.execute("UPDATE resources SET quantity = ? WHERE id = ?", (new_qty_after_issue, res_id))

        # Списання (невелика кількість)
        if new_qty_after_add > 5: # Використовуємо new_qty_after_add для розрахунку від початкового додавання
            qty_written_off = random.randint(1, 5)
            if new_qty_after_add - qty_issued > qty_written_off : # Перевіряємо актуальний залишок
                 transactions_data.append((res_id, 'списання', qty_written_off, (datetime.now() - timedelta(days=random.randint(0, 5))).strftime("%Y-%m-%d %H:%M:%S"), None, admin_id, f"Списання пошкодженого {res_name}"))
                 current_qty_for_write_off = cur.execute("SELECT quantity FROM resources WHERE id = ?", (res_id,)).fetchone()['quantity']
                 cur.execute("UPDATE resources SET quantity = ? WHERE id = ?", (current_qty_for_write_off - qty_written_off, res_id))


    try:
        cur.executemany("""
            INSERT INTO resource_transactions
            (resource_id, transaction_type, quantity_changed, transaction_date,
             recipient_department, issued_by_user_id, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, transactions_data)
        conn.commit()
        print(f"Додано {len(transactions_data)} тестових транзакцій та оновлено залишки ресурсів.")
    except sqlite3.Error as e:
        print(f"Помилка при додаванні тестових транзакцій: {e}")
        conn.rollback()

def main():
    print("Запуск скрипта заповнення бази даних...")
    conn = create_connection(DB_PATH)
    if conn:
        print(f"З'єднання з базою даних встановлено: {DB_PATH}")
        
        # 1. Створюємо таблиці (якщо їх немає), це також додасть категорії та користувачів
        print("\nСтворення таблиць...")
        create_tables(conn)

        # 2. Очищаємо дані з таблиць, які будемо заповнювати (щоб уникнути дублів при повторному запуску)
        #    УВАГА: Це видалить всі існуючі ресурси, заявки, транзакції!
        #    Закоментуйте, якщо хочете додавати дані до існуючих.
        print("\nОчищення існуючих даних...")
        clear_specific_tables(conn)

        # 3. Додаємо тестові ресурси
        print("\nДодавання тестових ресурсів...")
        add_test_resources(conn)

        # 4. Додаємо тестові заявки та їх позиції
        print("\nДодавання тестових заявок...")
        add_test_requisitions_and_items(conn)

        # 5. Додаємо тестові транзакції (і оновлюємо залишки)
        print("\nДодавання тестових транзакцій...")
        add_test_transactions(conn)

        conn.close()
        print("\nЗаповнення бази даних тестовими даними завершено.")
    else:
        print("Не вдалося підключитися до бази даних.")

if __name__ == "__main__":
    main() 