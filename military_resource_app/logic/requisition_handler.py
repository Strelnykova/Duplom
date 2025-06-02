#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль для роботи з заявками в системі обліку військового майна.
"""

import sqlite3
from datetime import datetime, timedelta
import os
import sys

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from logic.db_manager import create_connection, create_tables

def create_requisition(conn: sqlite3.Connection, user_id: int, department: str,
                      urgency: str, notes: str | None = None) -> int | None:
    """
    Створює нову заявку.

    Args:
        conn: З'єднання з базою даних.
        user_id: ID користувача, що створює заявку.
        department: Відділення, що подає заявку.
        urgency: Терміновість заявки.
        notes: Додаткові примітки (опціонально).

    Returns:
        ID створеної заявки або None у разі помилки.
    """
    try:
        print(f"[DEBUG] Створення заявки для користувача {user_id}, відділ {department}")
        cur = conn.cursor()
        # Генеруємо номер заявки (можна модифікувати логіку за потреби)
        cur.execute("SELECT COUNT(*) + 1 as next_num FROM requisitions")
        next_num = cur.fetchone()['next_num']
        requisition_number = f"REQ-{datetime.now().strftime('%Y%m')}-{next_num:04d}"
        print(f"[DEBUG] Згенерований номер заявки: {requisition_number}")

        cur.execute("""
            INSERT INTO requisitions (
                requisition_number, created_by_user_id, department_requesting,
                creation_date, status, urgency, notes
            ) VALUES (?, ?, ?, datetime('now'), 'нова', ?, ?)
        """, (requisition_number, user_id, department, urgency, notes))
        
        new_id = cur.lastrowid
        print(f"[DEBUG] Заявка успішно створена з ID: {new_id}")
        conn.commit()
        return new_id
    except sqlite3.Error as e:
        print(f"[ERROR] Помилка створення заявки: {e}")
        print(f"[ERROR] SQL State: {e.sqlite_errorcode if hasattr(e, 'sqlite_errorcode') else 'Unknown'}")
        print(f"[ERROR] Extended Error Code: {e.sqlite_errorname if hasattr(e, 'sqlite_errorname') else 'Unknown'}")
        return None

def add_item_to_requisition(conn: sqlite3.Connection, requisition_id: int,
                          resource_id: int | None, resource_name: str,
                          quantity_requested: float, notes: str | None = None) -> bool:
    """
    Додає позицію до заявки.

    Args:
        conn: З'єднання з базою даних.
        requisition_id: ID заявки.
        resource_id: ID ресурсу (якщо вибрано з існуючих).
        resource_name: Назва ресурсу.
        quantity_requested: Запитувана кількість.
        notes: Додаткові примітки.

    Returns:
        True якщо успішно, False у разі помилки.
    """
    try:
        print(f"[DEBUG] Додавання позиції до заявки {requisition_id}:")
        print(f"[DEBUG] Ресурс: {resource_name} (ID: {resource_id})")
        print(f"[DEBUG] Кількість: {quantity_requested}")
        
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO requisition_items (
                requisition_id, resource_id, requested_resource_name,
                quantity_requested, item_status, justification
            ) VALUES (?, ?, ?, ?, 'очікує', ?)
        """, (requisition_id, resource_id, resource_name, quantity_requested, notes))
        
        conn.commit()
        print(f"[DEBUG] Позицію успішно додано")
        return True
        
    except sqlite3.Error as e:
        print(f"[ERROR] Помилка додавання позиції до заявки: {e}")
        print(f"[ERROR] SQL State: {e.sqlite_errorcode if hasattr(e, 'sqlite_errorcode') else 'Unknown'}")
        print(f"[ERROR] Extended Error Code: {e.sqlite_errorname if hasattr(e, 'sqlite_errorname') else 'Unknown'}")
        if conn:
            conn.rollback()
        return False
    except Exception as e:
        print(f"[ERROR] Неочікувана помилка: {e}")
        if conn:
            conn.rollback()
        return False

def get_requisition_details(conn: sqlite3.Connection, requisition_id: int) -> dict:
    """
    Отримує детальну інформацію про заявку.

    Args:
        conn: З'єднання з базою даних.
        requisition_id: ID заявки.

    Returns:
        Словник з даними заявки та її позиціями.
    """
    try:
        # Отримуємо основну інформацію про заявку
        cur = conn.cursor()
        cur.execute("""
            SELECT r.*, u.username as created_by_username
            FROM requisitions r
            LEFT JOIN users u ON r.created_by_user_id = u.id
            WHERE r.id = ?
        """, (requisition_id,))
        requisition = dict(cur.fetchone())

        # Отримуємо позиції заявки
        cur.execute("""
            SELECT ri.*, r.name as resource_name
            FROM requisition_items ri
            LEFT JOIN resources r ON ri.resource_id = r.id
            WHERE ri.requisition_id = ?
        """, (requisition_id,))
        items = [dict(row) for row in cur.fetchall()]

        return {
            'requisition': requisition,
            'items': items
        }
    except sqlite3.Error as e:
        print(f"Помилка отримання деталей заявки: {e}")
        return {'requisition': None, 'items': []}

def update_requisition_status(conn: sqlite3.Connection, requisition_id: int,
                            new_status: str, updated_by_user_id: int) -> bool:
    """
    Оновлює статус заявки.

    Args:
        conn: З'єднання з базою даних.
        requisition_id: ID заявки.
        new_status: Новий статус.
        updated_by_user_id: ID користувача, що оновлює статус.

    Returns:
        True якщо успішно, False у разі помилки.
    """
    try:
        conn.execute("""
            UPDATE requisitions
            SET status = ?,
                last_updated = datetime('now'),
                last_updated_by_user_id = ?
            WHERE id = ?
        """, (new_status, updated_by_user_id, requisition_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Помилка оновлення статусу заявки: {e}")
        return False

def process_requisition_item_execution(conn: sqlite3.Connection, item_id: int,
                                    quantity_executed: float,
                                    executed_by_user_id: int) -> bool:
    """
    Обробляє виконання позиції заявки.

    Args:
        conn: З'єднання з базою даних.
        item_id: ID позиції заявки.
        quantity_executed: Виконана кількість.
        executed_by_user_id: ID користувача, що виконує.

    Returns:
        True якщо успішно, False у разі помилки.
    """
    try:
        # Отримуємо інформацію про позицію
        cur = conn.cursor()
        cur.execute("""
            SELECT ri.*, r.quantity as available_quantity
            FROM requisition_items ri
            LEFT JOIN resources r ON ri.resource_id = r.id
            WHERE ri.id = ?
        """, (item_id,))
        item = cur.fetchone()

        if not item:
            print("Позицію не знайдено")
            return False

        # Перевіряємо наявність ресурсу
        if item['resource_id'] is not None:
            if item['available_quantity'] < quantity_executed:
                print("Недостатньо ресурсу для виконання")
                return False

            # Оновлюємо кількість ресурсу
            conn.execute("""
                UPDATE resources
                SET quantity = quantity - ?
                WHERE id = ?
            """, (quantity_executed, item['resource_id']))

        # Оновлюємо статус позиції
        new_status = 'виконано'

        conn.execute("""
            UPDATE requisition_items
            SET item_status = ?,
                last_executed = datetime('now'),
                last_executed_by_user_id = ?
            WHERE id = ?
        """, (new_status, executed_by_user_id, item_id))

        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Помилка обробки виконання позиції: {e}")
        return False

def check_and_update_overall_requisition_status(conn: sqlite3.Connection,
                                              requisition_id: int) -> bool:
    """
    Перевіряє та оновлює загальний статус заявки на основі статусів її позицій.

    Args:
        conn: З'єднання з базою даних.
        requisition_id: ID заявки.

    Returns:
        True якщо успішно, False у разі помилки.
    """
    try:
        cur = conn.cursor()
        # Отримуємо статуси всіх позицій
        cur.execute("""
            SELECT status
            FROM requisition_items
            WHERE requisition_id = ?
        """, (requisition_id,))
        statuses = [row['status'] for row in cur.fetchall()]

        if not statuses:
            return False

        # Визначаємо загальний статус
        if all(s == 'виконано' for s in statuses):
            new_status = 'виконано'
        elif any(s in ('виконано', 'частково виконано') for s in statuses):
            new_status = 'частково виконано'
        else:
            return True  # Залишаємо поточний статус

        # Оновлюємо статус заявки
        conn.execute("""
            UPDATE requisitions
            SET status = ?,
                last_updated = datetime('now')
            WHERE id = ?
        """, (new_status, requisition_id))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Помилка оновлення загального статусу заявки: {e}")
        return False

def get_requisitions(date_from: str | None = None, date_to: str | None = None,
                     status: str | None = None, urgency: str | None = None,
                     search_term: str | None = None,
                     created_by_user_id: int | None = None,
                     limit: int = 100, offset: int = 0) -> list:
    """
    Отримує список заявок з можливістю фільтрації.

    Args:
        date_from: Початкова дата (опціонально)
        date_to: Кінцева дата (опціонально)
        status: Статус заявки (опціонально)
        urgency: Терміновість (опціонально)
        search_term: Пошуковий запит (опціонально)
        created_by_user_id: ID користувача-створювача (опціонально)
        limit: Ліміт результатів
        offset: Зміщення для пагінації

    Returns:
        Список заявок, що відповідають критеріям
    """
    try:
        print(f"[DEBUG] Отримання заявок з параметрами:")
        print(f"[DEBUG] - created_by_user_id: {created_by_user_id}")
        print(f"[DEBUG] - status: {status}")
        print(f"[DEBUG] - date_from: {date_from}")
        print(f"[DEBUG] - date_to: {date_to}")
        print(f"[DEBUG] - urgency: {urgency}")
        print(f"[DEBUG] - search_term: {search_term}")

        conn = create_connection()
        if not conn:
            print("[ERROR] Не вдалося підключитися до бази даних")
            return []

        conditions = []
        params = []

        if created_by_user_id is not None:
            conditions.append("r.created_by_user_id = ?")
            params.append(created_by_user_id)
            print(f"[DEBUG] Додано фільтр по користувачу: {created_by_user_id}")

        if status:
            conditions.append("r.status = ?")
            params.append(status)

        if date_from:
            conditions.append("r.creation_date >= ?")
            params.append(date_from)

        if date_to:
            conditions.append("r.creation_date <= ?")
            params.append(date_to)

        if urgency:
            conditions.append("r.urgency = ?")
            params.append(urgency)

        if search_term:
            conditions.append("(r.requisition_number LIKE ? OR r.notes LIKE ?)")
            search_pattern = f"%{search_term}%"
            params.extend([search_pattern, search_pattern])

        where_clause = " AND ".join(conditions) if conditions else "1"
        query = f"""
            SELECT r.*, u.username as created_by_username,
                   u2.username as last_updated_by_username
            FROM requisitions r
            LEFT JOIN users u ON r.created_by_user_id = u.id
            LEFT JOIN users u2 ON r.last_updated_by_user_id = u2.id
            WHERE {where_clause}
            ORDER BY r.creation_date DESC
            LIMIT ? OFFSET ?
        """
        params.extend([limit, offset])
        
        print(f"[DEBUG] SQL Query: {query}")
        print(f"[DEBUG] Parameters: {params}")

        cur = conn.cursor()
        cur.execute(query, params)
        results = [dict(row) for row in cur.fetchall()]
        print(f"[DEBUG] Знайдено {len(results)} заявок")
        
        return results
    except sqlite3.Error as e:
        print(f"[ERROR] Помилка отримання заявок: {e}")
        print(f"[ERROR] SQL State: {e.sqlite_errorcode if hasattr(e, 'sqlite_errorcode') else 'Unknown'}")
        print(f"[ERROR] Extended Error Code: {e.sqlite_errorname if hasattr(e, 'sqlite_errorname') else 'Unknown'}")
        return []
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Тестування функцій
    conn = create_connection()
    if conn:
        print("\nТестування get_requisitions з фільтрами...")
        
        print("\nВсі заявки (перші 5):")
        for req in get_requisitions(limit=5):
            print(req)

        print("\nЗаявки зі статусом 'схвалено':")
        for req in get_requisitions(status='схвалено'):
            print(req)

        print("\nЗаявки з терміновістю 'термінова':")
        for req in get_requisitions(urgency='термінова'):
            print(req)
        
        today_str = datetime.now().strftime("%Y-%m-%d")
        one_month_ago_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

        print(f"\nЗаявки за останній місяць (від {one_month_ago_str} до {today_str}):")
        for req in get_requisitions(date_from=one_month_ago_str, date_to=today_str):
            print(req)

        print("\nЗаявки, що містять слово 'навчань':")
        for req in get_requisitions(search_term='навчань'):
            print(req)

        conn.close()

    # Initialize database and tables
    conn = create_connection()
    if conn:
        create_tables(conn)
        conn.close()
    else:
        print("Failed to connect to database")
        sys.exit(1)

    # Test user existence and create if needed
    conn = create_connection()
    if conn:
        try:
            cur = conn.cursor()
            # Check if test user exists
            cur.execute("SELECT id FROM users WHERE id = 1")
            user = cur.fetchone()
            
            if not user:
                # Create test user if doesn't exist
                cur.execute("""
                    INSERT INTO users (id, username, password, role)
                    VALUES (1, 'test_user', 'test_password', 'admin')
                """)
                conn.commit()
                print("Created test user with ID 1")
            else:
                print("Test user with ID 1 already exists")
                
        except sqlite3.Error as e:
            print(f"Database error: {e}")
        finally:
            conn.close()

    # Test requisition creation
    new_req_id = create_requisition(
        conn,
        created_by_user_id=1,
        department="Supply Department",
        urgency='urgent',
        notes="Test requisition for functionality verification"
    )

    if new_req_id:
        print(f"\nCreated test requisition with ID: {new_req_id}")

        # Test adding items to requisition
        test_items = [
            ("5.45x39 Ammunition", 500, "pcs", None, "Stock replenishment"),
            ("IFAK Individual First Aid Kit", 10, "set", None, "For new personnel"),
            ("Test Bandage", 20, "pcs", 1, "For medical unit")
        ]

        for item in test_items:
            name, qty, unit, res_id, justif = item
            success = add_item_to_requisition(
                conn,
                new_req_id,
                res_id,
                name,
                qty,
                justif
            )
            print(f"Added item {name}: {'Success' if success else 'Failed'}")

        # Test getting requisition details
        print("\nRequisition details:")
        details = get_requisition_details(conn, new_req_id)
        if details['requisition']:
            for key, value in details['requisition'].items():
                if key == 'items':
                    print("\nItems:")
                    for item in value:
                        print(f"  - {item}")
                else:
                    print(f"{key}: {value}")

        # Test status updates
        print("\nTesting status updates:")
        statuses_to_test = ['in_review', 'approved']
        for status in statuses_to_test:
            success = update_requisition_status(conn, new_req_id, status, 1)
            print(f"Updated status to '{status}': {'Success' if success else 'Failed'}")

        # Test requisition listing
        print("\nAll requisitions:")
        all_reqs = get_requisitions()
        for req in all_reqs:
            print(f"Requisition {req['requisition_number']}: {req['status']}")

        print("\nNew requisitions only:")
        new_reqs = get_requisitions(status='new')
        for req in new_reqs:
            print(f"Requisition {req['requisition_number']}: {req['status']}")

    else:
        print("Failed to create test requisition") 