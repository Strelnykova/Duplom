#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль для генерації звітів в системі обліку військового майна.
"""

import sqlite3
from datetime import datetime, timedelta
from .db_manager import create_connection

def get_current_resource_stock_report(category_id: int | None = None) -> list:
    """
    Отримує дані для звіту про поточні залишки ресурсів.

    Args:
        category_id: ID категорії для фільтрації (якщо None, то всі категорії).

    Returns:
        Список словників, де кожен словник представляє ресурс та його залишки.
    """
    conn = create_connection()
    if not conn:
        return []

    query = """
        SELECT
            r.id as resource_id,
            r.name as resource_name,
            c.name as category_name,
            r.quantity,
            r.unit_of_measure,
            r.expiration_date,
            r.low_stock_threshold,
            r.cost,
            r.supplier,
            r.arrival_date,
            (SELECT COUNT(*) FROM transactions t 
             WHERE t.resource_id = r.id AND t.transaction_type = 'видача') as total_issues,
            (SELECT COUNT(*) FROM requisition_items ri 
             WHERE ri.resource_id = r.id AND ri.status != 'виконано') as pending_requests
        FROM resources r
        JOIN categories c ON r.category_id = c.id
    """
    params = []

    if category_id is not None:
        query += " WHERE r.category_id = ?"
        params.append(category_id)

    query += " ORDER BY c.name, r.name"

    try:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        report_data = cur.fetchall()
        
        # Додаємо додаткові розрахункові поля
        result = []
        for row in report_data:
            row_dict = dict(row)
            # Розрахунок вартості залишків
            row_dict['total_value'] = row_dict['quantity'] * (row_dict['cost'] or 0)
            # Статус запасів
            if row_dict['quantity'] <= 0:
                row_dict['stock_status'] = 'відсутній'
            elif row_dict['quantity'] <= row_dict['low_stock_threshold']:
                row_dict['stock_status'] = 'критичний'
            elif row_dict['quantity'] <= row_dict['low_stock_threshold'] * 2:
                row_dict['stock_status'] = 'низький'
            else:
                row_dict['stock_status'] = 'достатній'
            result.append(row_dict)
        
        return result
    except sqlite3.Error as e:
        print(f"Помилка бази даних при формуванні звіту про залишки: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_requisition_summary_report(date_from: str | None = None,
                                 date_to: str | None = None,
                                 status: str | None = None,
                                 department: str | None = None) -> list:
    """
    Отримує дані для звіту про виконання заявок за період.

    Args:
        date_from: Дата створення заявки "від" (формат YYYY-MM-DD).
        date_to: Дата створення заявки "до" (формат YYYY-MM-DD).
        status: Статус заявки для фільтрації.
        department: Відділення, що подало заявку, для фільтрації.

    Returns:
        Список словників, де кожен словник представляє заявку.
    """
    conn = create_connection()
    if not conn:
        return []

    query = """
        SELECT
            req.id as requisition_id,
            req.requisition_number,
            req.creation_date,
            req.department_requesting,
            u_created.username as created_by_username,
            req.status,
            req.urgency,
            req.last_updated,
            u_updated.username as last_updated_by_username,
            (SELECT COUNT(*) FROM requisition_items ri WHERE ri.requisition_id = req.id) as total_items,
            (SELECT COUNT(*) FROM requisition_items ri 
             WHERE ri.requisition_id = req.id AND ri.status = 'виконано') as completed_items,
            (SELECT GROUP_CONCAT(DISTINCT ri.status) 
             FROM requisition_items ri 
             WHERE ri.requisition_id = req.id) as item_statuses
        FROM requisitions req
        LEFT JOIN users u_created ON req.created_by_user_id = u_created.id
        LEFT JOIN users u_updated ON req.last_updated_by_user_id = u_updated.id
    """
    conditions = []
    params = []

    if date_from:
        conditions.append("DATE(req.creation_date) >= DATE(?)")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(req.creation_date) <= DATE(?)")
        params.append(date_to)
    if status:
        conditions.append("req.status = ?")
        params.append(status)
    if department:
        conditions.append("req.department_requesting LIKE ?")
        params.append(f"%{department}%")

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY req.creation_date DESC"

    try:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        report_data = cur.fetchall()
        
        # Додаємо додаткові розрахункові поля та деталі позицій
        result = []
        for row in report_data:
            row_dict = dict(row)
            
            # Отримуємо деталі позицій заявки
            cur.execute("""
                SELECT ri.*, r.name as resource_name, r.unit_of_measure
                FROM requisition_items ri
                LEFT JOIN resources r ON ri.resource_id = r.id
                WHERE ri.requisition_id = ?
            """, (row_dict['requisition_id'],))
            items = [dict(item) for item in cur.fetchall()]
            row_dict['items'] = items
            
            # Розрахунок відсотка виконання
            row_dict['completion_percentage'] = (
                (row_dict['completed_items'] / row_dict['total_items'] * 100)
                if row_dict['total_items'] > 0 else 0
            )
            
            # Розрахунок часу обробки
            if row_dict['last_updated']:
                creation_date = datetime.strptime(row_dict['creation_date'], "%Y-%m-%d %H:%M:%S")
                last_updated = datetime.strptime(row_dict['last_updated'], "%Y-%m-%d %H:%M:%S")
                processing_time = last_updated - creation_date
                row_dict['processing_time_hours'] = processing_time.total_seconds() / 3600
            else:
                row_dict['processing_time_hours'] = None
            
            result.append(row_dict)
        
        return result
    except sqlite3.Error as e:
        print(f"Помилка бази даних при формуванні звіту по заявках: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_resource_movement_report(resource_id: int | None = None,
                               date_from: str | None = None,
                               date_to: str | None = None) -> list:
    """
    Отримує дані для звіту про рух ресурсів (надходження та видача).

    Args:
        resource_id: ID ресурсу для фільтрації (якщо None, то всі ресурси).
        date_from: Дата транзакції "від" (формат YYYY-MM-DD).
        date_to: Дата транзакції "до" (формат YYYY-MM-DD).

    Returns:
        Список словників з інформацією про рух ресурсів.
    """
    conn = create_connection()
    if not conn:
        return []

    query = """
        SELECT
            t.id as transaction_id,
            t.transaction_date,
            r.id as resource_id,
            r.name as resource_name,
            c.name as category_name,
            t.transaction_type,
            t.quantity_changed,
            r.unit_of_measure,
            t.recipient_department,
            u.username as issued_by_username,
            t.notes,
            req.requisition_number
        FROM transactions t
        JOIN resources r ON t.resource_id = r.id
        JOIN categories c ON r.category_id = c.id
        LEFT JOIN users u ON t.issued_by_user_id = u.id
        LEFT JOIN requisitions req ON t.requisition_id = req.id
    """
    conditions = []
    params = []

    if resource_id is not None:
        conditions.append("t.resource_id = ?")
        params.append(resource_id)
    if date_from:
        conditions.append("DATE(t.transaction_date) >= DATE(?)")
        params.append(date_from)
    if date_to:
        conditions.append("DATE(t.transaction_date) <= DATE(?)")
        params.append(date_to)

    if conditions:
        query += " WHERE " + " AND ".join(conditions)

    query += " ORDER BY t.transaction_date DESC"

    try:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        transactions = cur.fetchall()
        
        # Додаємо підсумкову статистику
        result = {
            'transactions': [dict(t) for t in transactions],
            'summary': {
                'total_incoming': sum(t['quantity_changed'] for t in transactions 
                                   if t['transaction_type'] == 'надходження'),
                'total_outgoing': sum(abs(t['quantity_changed']) for t in transactions 
                                   if t['transaction_type'] == 'видача'),
                'departments_served': len(set(t['recipient_department'] for t in transactions 
                                           if t['recipient_department'])),
                'unique_resources': len(set(t['resource_id'] for t in transactions))
            }
        }
        
        return result
    except sqlite3.Error as e:
        print(f"Помилка бази даних при формуванні звіту про рух ресурсів: {e}")
        return {'transactions': [], 'summary': {}}
    finally:
        if conn:
            conn.close()

if __name__ == '__main__':
    # Тестування функцій звітності
    print("\n=== Тестування функцій звітності ===")
    
    print("\n--- Звіт про поточні залишки ресурсів ---")
    stock_report = get_current_resource_stock_report()
    if stock_report:
        for item in stock_report:
            print(f"\nРесурс: {item['resource_name']}")
            print(f"Категорія: {item['category_name']}")
            print(f"Кількість: {item['quantity']} {item['unit_of_measure'] or ''}")
            print(f"Статус запасів: {item['stock_status']}")
            print(f"Термін придатності: {item['expiration_date'] or 'N/A'}")
            print(f"Вартість залишків: {item['total_value']:.2f}")
            print(f"Активних заявок: {item['pending_requests']}")
    else:
        print("Немає даних для звіту про залишки.")

    print("\n--- Звіт по заявках за останній місяць ---")
    today_str = datetime.now().strftime("%Y-%m-%d")
    one_month_ago_str = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")

    requisition_report = get_requisition_summary_report(
        date_from=one_month_ago_str,
        date_to=today_str
    )
    if requisition_report:
        for req in requisition_report:
            print(f"\nЗаявка №{req['requisition_number']}")
            print(f"Створено: {req['creation_date']}")
            print(f"Статус: {req['status']}")
            print(f"Відділення: {req['department_requesting']}")
            print(f"Виконано: {req['completion_percentage']:.1f}%")
            if req['processing_time_hours']:
                print(f"Час обробки: {req['processing_time_hours']:.1f} годин")
            print("\nПозиції:")
            for item in req['items']:
                print(f"- {item['requested_resource_name']}: "
                      f"{item['quantity_requested']} {item['unit_of_measure'] or ''} "
                      f"({item['status']})")
    else:
        print("Немає даних для звіту по заявках.")

    print("\n--- Звіт про рух ресурсів за останній місяць ---")
    movement_report = get_resource_movement_report(
        date_from=one_month_ago_str,
        date_to=today_str
    )
    if movement_report['transactions']:
        print("\nСтатистика:")
        print(f"Всього надходжень: {movement_report['summary']['total_incoming']}")
        print(f"Всього видач: {movement_report['summary']['total_outgoing']}")
        print(f"Обслуговано відділень: {movement_report['summary']['departments_served']}")
        print(f"Унікальних ресурсів: {movement_report['summary']['unique_resources']}")
        
        print("\nОстанні транзакції:")
        for t in movement_report['transactions'][:5]:  # Показуємо тільки 5 останніх
            print(f"\n{t['transaction_date']} - {t['resource_name']}")
            print(f"Тип: {t['transaction_type']}")
            print(f"Кількість: {abs(t['quantity_changed'])} {t['unit_of_measure'] or ''}")
            if t['recipient_department']:
                print(f"Відділення: {t['recipient_department']}")
            if t['requisition_number']:
                print(f"Заявка: {t['requisition_number']}")
    else:
        print("Немає даних про рух ресурсів.") 