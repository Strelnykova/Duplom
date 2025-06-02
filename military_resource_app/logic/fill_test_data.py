#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Скрипт для заповнення бази даних тестовими даними.
"""

import sys
import os
import sqlite3
import random
from datetime import datetime, timedelta

# Налаштування шляху для імпорту модулів
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, '..'))
DB_FILE = 'resources.db'  # Використовуємо відносний шлях

sys.path.append(PROJECT_ROOT)
from logic.db_manager import create_connection, create_tables

# Список категорій, які мають бути в БД
EXPECTED_CATEGORIES = [
    "Боєприпаси",
    "ПММ",  # Пально-мастильні матеріали
    "Продукти харчування",
    "Медикаменти",
    "Інженерне майно",
    "Засоби зв'язку",
    "Форма",
    "Спорядження та захист",  # Об'єднано для бронежилетів, касок, рюкзаків тощо
    "Ремонтні засоби та запчастини",
    "Інше"  # Загальна категорія
]

def clear_data_from_tables(conn, tables_to_clear):
    """Очищає дані з вказаних таблиць."""
    print(f"Очищення даних з таблиць: {', '.join(tables_to_clear)}...")
    try:
        cur = conn.cursor()
        for table_name in tables_to_clear:
            cur.execute(f"DELETE FROM {table_name};")
        conn.commit()
        print("Дані з таблиць успішно очищено.")
    except sqlite3.Error as e:
        print(f"Помилка під час очищення даних з таблиць: {e}")
        conn.rollback()

def get_category_id(conn, category_name: str) -> int | None:
    """Отримує ID категорії за її назвою."""
    cur = conn.cursor()
    cur.execute("SELECT id FROM categories WHERE name = ?", (category_name,))
    row = cur.fetchone()
    if not row:
        print(f"ПОПЕРЕДЖЕННЯ: Категорія '{category_name}' не знайдена в базі даних!")
        return None
    return row['id']

def add_all_resources(conn):
    """Додає всі типи ресурсів до бази даних."""
    print("Додавання всіх типів ресурсів...")
    cur = conn.cursor()

    # Отримуємо ID категорій один раз
    category_ids = {name: get_category_id(conn, name) for name in EXPECTED_CATEGORIES}
    category_ids = {k: v for k, v in category_ids.items() if v is not None}

    if not category_ids:
        print("ПОМИЛКА: Не знайдено жодної категорії в БД. Ресурси не будуть додані.")
        return

    # --- 1. Боєприпаси ---
    ammo_cat_id = category_ids.get("Боєприпаси")
    if ammo_cat_id:
        ammo_resources = [
            ("Патрони 5.45х39 мм (7Н6М)", ammo_cat_id, random.randint(5000, 20000), "шт", "2028-12-31", 1000, "Арсенал, Україна", "КНВО «Форт»", "0432-50-72-00", 8.50, "Склад боєприпасів №1"),
            ("Патрони 7.62х39 мм (57-Н-231)", ammo_cat_id, random.randint(5000, 15000), "шт", "2027-10-31", 800, "ЛПЗ, Україна", "ДП «ЛПЗ»", "0322-XX-XX-XX", 9.20, "Склад боєприпасів №1"),
            ("Патрони 5.56х45 мм (SS109/M855)", ammo_cat_id, random.randint(3000, 10000), "шт", "2029-05-01", 500, "Імпорт (НАТО)", "MESKO S.A.", "+48 XX XXX XX XX", 15.00, "Склад боєприпасів №2"),
            ("Патрони 7.62х54R мм (ЛПС)", ammo_cat_id, random.randint(2000, 8000), "шт", "2028-08-15", 300, "ЛПЗ, Україна", "ДП «ЛПЗ»", "0322-XX-XX-XX", 12.50, "Склад боєприпасів №1"),
            ("Патрони 12.7х108 мм (Б-32)", ammo_cat_id, random.randint(1000, 5000), "шт", "2030-01-01", 100, "Арсенал, Україна", "КНВО «Форт»", "0432-50-72-00", 75.00, "Склад боєприпасів №2"),
            ("Гранатні постріли ВОГ-25", ammo_cat_id, random.randint(200, 1000), "шт", "2029-06-30", 50, "Прогрес, Україна", "НВК «Прогрес»", "0462-XX-XX-XX", 350.00, "Склад боєприпасів №1"),
            ("Ручні гранати Ф-1", ammo_cat_id, random.randint(100, 500), "шт", "2032-03-01", 20, "Арсенал, Україна", "КНВО «Форт»", "0432-50-72-00", 180.00, "Склад боєприпасів №2"),
            ("Ручні гранати РГД-5", ammo_cat_id, random.randint(100, 500), "шт", "2032-03-01", 20, "Арсенал, Україна", "КНВО «Форт»", "0432-50-72-00", 170.00, "Склад боєприпасів №2"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in ammo_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(30, 365))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, image_path, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, ammo_cat_id, qty, unit, desc, None, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 2. Пально-мастильні матеріали (ПММ) ---
    pmm_cat_id = category_ids.get("ПММ")
    if pmm_cat_id:
        pmm_resources = [
            ("Дизельне паливо (літо)", pmm_cat_id, random.randint(5000, 20000), "л", None, 1000, "НПЗ Кременчук", "Укртатнафта", "0800-XXX-XXX", 50.50, "Резервуар №1"),
            ("Дизельне паливо (зима, арктичне)", pmm_cat_id, random.randint(3000, 10000), "л", None, 500, "Імпорт (Orlen)", "Orlen Lietuva", "N/A", 55.75, "Резервуар №2"),
            ("Бензин А-95 (Евро-5)", pmm_cat_id, random.randint(2000, 8000), "л", None, 300, "НПЗ Мозир (до 2022)", "Укрнафта", "0800-XXX-XXX", 53.20, "Резервуар №3"),
            ("Мастило моторне М-10Г2К", pmm_cat_id, random.randint(100, 500), "л", None, 20, "Азмол, Україна", "ТОВ АЗМОЛ БП", "0615-XX-XX-XX", 90.00, "Склад ПММ"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in pmm_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(15, 180))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, pmm_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 3. Продовольство та вода ---
    food_cat_id = category_ids.get("Продукти харчування")
    if food_cat_id:
        food_resources = [
            ("Індивідуальний раціон харчування (ІРП, 24 години, тип 1)", food_cat_id, random.randint(100, 500), "уп.", (datetime.now() + timedelta(days=random.randint(90, 360))).strftime('%Y-%m-%d'), 20, "Фабрика-кухня, Україна", "ТОВ 'СухпайЗСУ'", "050-XXX-XX-XX", 350.00, "Продовольчий склад"),
            ("Вода питна негазована, 1.5л", food_cat_id, random.randint(500, 2000), "пляшка", (datetime.now() + timedelta(days=180)).strftime('%Y-%m-%d'), 100, "Моршин, Україна", "IDS Borjomi Ukraine", "0800-XXX-XXX", 15.00, "Продовольчий склад"),
            ("Консерви 'Каша гречана з м'ясом', 340г", food_cat_id, random.randint(200, 1000), "банка", (datetime.now() + timedelta(days=700)).strftime('%Y-%m-%d'), 50, "Верес, Україна", "ГК 'Верес'", "044-XXX-XX-XX", 65.00, "Продовольчий склад"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in food_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(7, 90))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, food_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 4. Медичне забезпечення ---
    med_cat_id = category_ids.get("Медикаменти")
    if med_cat_id:
        med_resources = [
            ("Аптечка індивідуальна IFAK (стандарт НАТО)", med_cat_id, random.randint(50, 200), "компл.", (datetime.now() + timedelta(days=random.randint(180, 500))).strftime('%Y-%m-%d'), 10, "Імпорт (США/ЄС)", "North American Rescue", "N/A", 2500.00, "Медичний склад"),
            ("Джгут кровоспинний CAT Gen7", med_cat_id, random.randint(100, 400), "шт", (datetime.now() + timedelta(days=1000)).strftime('%Y-%m-%d'), 20, "Імпорт (США)", "NAR / C•A•T Resources", "N/A", 550.00, "Медичний склад"),
            ("Бинт еластичний компресійний (Ізраїльський бандаж)", med_cat_id, random.randint(80, 300), "шт", (datetime.now() + timedelta(days=800)).strftime('%Y-%m-%d'), 15, "Імпорт (Ізраїль)", "PerSys Medical", "N/A", 300.00, "Медичний склад"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in med_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(10, 120))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, med_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 5. Інженерне майно ---
    eng_cat_id = category_ids.get("Інженерне майно")
    if eng_cat_id:
        eng_resources = [
            ("Лопата мала піхотна (МПЛ-50)", eng_cat_id, random.randint(50,150), "шт", None, 10, "Україна", "Завод 'Арсенал'", "N/A", 250.00, "Склад інж. майна"),
            ("Мішки для піску (поліпропіленові)", eng_cat_id, random.randint(1000,5000), "шт", None, 200, "Україна", "ТОВ 'УкрПолімер'", "N/A", 5.00, "Склад інж. майна"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in eng_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(60, 200))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, eng_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 6. Засоби зв'язку ---
    com_cat_id = category_ids.get("Засоби зв'язку")
    if com_cat_id:
        com_resources = [
            ("Радіостанція портативна Motorola DP4400E (VHF)", com_cat_id, random.randint(20,80), "шт", None, 5, "Імпорт (Motorola)", "Motorola Solutions", "N/A", 18000.00, "Склад засобів зв'язку"),
            ("Акумуляторна батарея до Motorola DP4400E", com_cat_id, random.randint(40,160), "шт", None, 10, "Імпорт (Motorola)", "Motorola Solutions", "N/A", 2500.00, "Склад засобів зв'язку"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in com_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(30, 150))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, com_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    # --- 7. Обмундирування та спорядження ---
    form_cat_id = category_ids.get("Форма")
    equip_cat_id = category_ids.get("Спорядження та захист")

    if form_cat_id:
        form_resources = [
            ("Комплект польової форми ММ-14 (кітель, штани), розмір 50/4", form_cat_id, random.randint(30,100), "компл.", None, 5, "Україна", "ТОВ 'Текстиль-Контакт'", "N/A", 2800.00, "Речовий склад"),
            ("Берци тактичні зимові, розмір 43", form_cat_id, random.randint(20,80), "пара", None, 4, "Україна", "фабрика 'Талан'", "N/A", 3500.00, "Речовий склад"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in form_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(45, 250))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, form_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    if equip_cat_id:
        equip_resources = [
            ("Бронежилет 'Корсар М3с-1-4' (4 кл. захисту)", equip_cat_id, random.randint(20,70), "шт", None, 3, "Україна", "ТЕМП-3000", "044-XXX-XX-XX", 16000.00, "Склад ЗІЗ"),
            ("Шолом балістичний PASGT (M88) з кавером", equip_cat_id, random.randint(30,90), "шт", None, 5, "Імпорт/Україна", "Різні", "N/A", 6500.00, "Склад ЗІЗ"),
            ("Рюкзак тактичний рейдовий 80л, койот", equip_cat_id, random.randint(10,40), "шт", None, 2, "Імпорт", "Mil-Tec", "N/A", 4200.00, "Речовий склад"),
        ]
        for r_name, _, qty, unit, exp_date, low_thresh, origin, supplier, phone, cost, desc in equip_resources:
            arrival = (datetime.now() - timedelta(days=random.randint(45, 250))).strftime('%Y-%m-%d')
            cur.execute("""
                INSERT INTO resources (name, category_id, quantity, unit_of_measure, description, supplier, phone, origin, arrival_date, cost, expiration_date, low_stock_threshold)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (r_name, equip_cat_id, qty, unit, desc, supplier, phone, origin, arrival, cost, exp_date, low_thresh))

    try:
        conn.commit()
        print("Тестові ресурси успішно додані до бази даних.")
    except sqlite3.Error as e:
        print(f"Помилка при коміті ресурсів: {e}")
        conn.rollback()

def main():
    """Головна функція для заповнення бази даних тестовими даними."""
    print("Починаємо заповнення бази даних...")
    
    # Перевіряємо існування файлу бази даних
    if os.path.exists(DB_FILE):
        print(f"База даних знайдена: {DB_FILE}")
        print(f"Розмір файлу: {os.path.getsize(DB_FILE)} байт")
    else:
        print(f"УВАГА: Файл бази даних не існує: {DB_FILE}")
        print("Спробуємо створити нову базу даних...")
    
    try:
        print(f"Робоча директорія: {os.getcwd()}")
        print(f"Шлях до бази даних: {os.path.abspath(DB_FILE)}")
        
        # Змінюємо робочу директорію на PROJECT_ROOT
        os.chdir(PROJECT_ROOT)
        
        conn = create_connection(DB_FILE)
        if not conn:
            print("Не вдалося створити з'єднання з базою даних")
            return
            
        print("З'єднання з базою даних встановлено")
        
        # 1. Створюємо/перевіряємо таблиці
        print("Створення/перевірка таблиць...")
        create_tables(conn)

        # 2. Очищаємо таблиці для тестових даних
        tables_to_clear_for_test_data = ["resource_transactions", "requisition_items", "requisitions", "resources"]
        print(f"Очищення таблиць: {', '.join(tables_to_clear_for_test_data)}")
        clear_data_from_tables(conn, tables_to_clear_for_test_data)

        # 3. Додаємо всі ресурси
        print("Додавання ресурсів...")
        add_all_resources(conn)

        conn.close()
        print("\nЗаповнення бази даних тестовими ресурсами завершено.")
        
        # Перевіряємо результат
        if os.path.exists(DB_FILE):
            print(f"База даних існує після заповнення, розмір: {os.path.getsize(DB_FILE)} байт")
        else:
            print("ПОМИЛКА: Файл бази даних не знайдено після заповнення!")
            
    except Exception as e:
        print(f"Критична помилка: {str(e)}")
        print(f"Тип помилки: {type(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main() 