#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Модуль для роботи з транзакціями ресурсів.
"""

import sqlite3
from datetime import datetime
from typing import Dict, List, Optional, Tuple, Union

class TransactionError(Exception):
    """Базовий клас для помилок транзакцій."""
    pass

class InsufficientQuantityError(TransactionError):
    """Помилка: недостатня кількість ресурсу."""
    pass

class InvalidTransactionTypeError(TransactionError):
    """Помилка: неправильний тип транзакції."""
    pass

class TransactionHandler:
    """Обробник транзакцій ресурсів."""

    VALID_TRANSACTION_TYPES = {
        'надходження': 1,    # Збільшує кількість
        'видача': -1,        # Зменшує кількість
        'списання': -1,      # Зменшує кількість
        'повернення': 1      # Збільшує кількість
    }

    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn

    def add_transaction(
        self,
        resource_id: int,
        transaction_type: str,
        quantity_changed: int,
        issued_by_user_id: int,
        recipient_department: Optional[str] = None,
        notes: Optional[str] = None,
        transaction_date: Optional[str] = None
    ) -> Tuple[bool, str]:
        """
        Додає нову транзакцію та оновлює кількість ресурсу.

        Args:
            resource_id: ID ресурсу
            transaction_type: Тип транзакції ('надходження', 'видача', 'списання', 'повернення')
            quantity_changed: Кількість ресурсу в транзакції (завжди додатнє число)
            issued_by_user_id: ID користувача, що виконує транзакцію
            recipient_department: Підрозділ-отримувач (для видачі)
            notes: Додаткові примітки
            transaction_date: Дата транзакції (якщо None, використовується поточна дата/час)

        Returns:
            Tuple[bool, str]: (успіх, повідомлення)

        Raises:
            InsufficientQuantityError: якщо недостатньо ресурсу для видачі/списання
            InvalidTransactionTypeError: якщо вказано неправильний тип транзакції
        """
        if transaction_type not in self.VALID_TRANSACTION_TYPES:
            raise InvalidTransactionTypeError(
                f"Неправильний тип транзакції. Допустимі типи: {', '.join(self.VALID_TRANSACTION_TYPES.keys())}"
            )

        if quantity_changed <= 0:
            return False, "Кількість повинна бути більше 0"

        # Застосування множника відповідно до типу транзакції
        actual_change = quantity_changed * self.VALID_TRANSACTION_TYPES[transaction_type]

        try:
            # Перевірка наявності достатньої кількості ресурсу
            current_quantity = self.conn.execute(
                "SELECT quantity FROM resources WHERE id = ?",
                (resource_id,)
            ).fetchone()

            if not current_quantity:
                return False, "Ресурс не знайдено"

            new_quantity = current_quantity["quantity"] + actual_change

            if new_quantity < 0:
                raise InsufficientQuantityError(
                    f"Недостатньо ресурсу. Наявно: {current_quantity['quantity']}"
                )

            # Початок транзакції
            self.conn.execute("BEGIN TRANSACTION")

            # Оновлення кількості ресурсу
            self.conn.execute(
                "UPDATE resources SET quantity = ? WHERE id = ?",
                (new_quantity, resource_id)
            )

            # Додавання запису про транзакцію
            self.conn.execute(
                """INSERT INTO resource_transactions (
                    resource_id, transaction_type, quantity_changed,
                    transaction_date, recipient_department,
                    issued_by_user_id, notes
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                (
                    resource_id,
                    transaction_type,
                    quantity_changed,  # Зберігаємо оригінальну (додатню) кількість
                    transaction_date or datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    recipient_department,
                    issued_by_user_id,
                    notes
                )
            )

            self.conn.commit()
            return True, "Транзакцію успішно виконано"

        except sqlite3.Error as e:
            self.conn.rollback()
            return False, f"Помилка бази даних: {str(e)}"
        except TransactionError as e:
            self.conn.rollback()
            return False, str(e)

    def get_resource_transactions(
        self,
        resource_id: int,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Отримує історію транзакцій для конкретного ресурсу.

        Args:
            resource_id: ID ресурсу
            start_date: Початкова дата у форматі 'YYYY-MM-DD'
            end_date: Кінцева дата у форматі 'YYYY-MM-DD'

        Returns:
            List[Dict]: Список транзакцій
        """
        query = """
            SELECT 
                t.*,
                u.username as issued_by_username,
                r.name as resource_name,
                r.unit_of_measure
            FROM resource_transactions t
            JOIN resources r ON t.resource_id = r.id
            LEFT JOIN users u ON t.issued_by_user_id = u.id
            WHERE t.resource_id = ?
        """
        params = [resource_id]

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")

        query += " ORDER BY t.transaction_date DESC"

        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_department_transactions(
        self,
        department: str,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Отримує історію транзакцій для конкретного підрозділу.

        Args:
            department: Назва підрозділу
            start_date: Початкова дата у форматі 'YYYY-MM-DD'
            end_date: Кінцева дата у форматі 'YYYY-MM-DD'

        Returns:
            List[Dict]: Список транзакцій
        """
        query = """
            SELECT 
                t.*,
                u.username as issued_by_username,
                r.name as resource_name,
                r.unit_of_measure,
                c.name as category_name
            FROM resource_transactions t
            JOIN resources r ON t.resource_id = r.id
            JOIN categories c ON r.category_id = c.id
            LEFT JOIN users u ON t.issued_by_user_id = u.id
            WHERE t.recipient_department = ?
        """
        params = [department]

        if start_date:
            query += " AND t.transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND t.transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")

        query += " ORDER BY t.transaction_date DESC"

        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_recent_transactions(
        self,
        limit: int = 50,
        transaction_type: Optional[str] = None
    ) -> List[Dict[str, Union[str, int]]]:
        """
        Отримує останні транзакції.

        Args:
            limit: Максимальна кількість транзакцій
            transaction_type: Тип транзакції для фільтрації

        Returns:
            List[Dict]: Список транзакцій
        """
        query = """
            SELECT 
                t.*,
                u.username as issued_by_username,
                r.name as resource_name,
                r.unit_of_measure,
                c.name as category_name
            FROM resource_transactions t
            JOIN resources r ON t.resource_id = r.id
            JOIN categories c ON r.category_id = c.id
            LEFT JOIN users u ON t.issued_by_user_id = u.id
        """
        params = []

        if transaction_type:
            query += " WHERE t.transaction_type = ?"
            params.append(transaction_type)

        query += " ORDER BY t.transaction_date DESC LIMIT ?"
        params.append(limit)

        return [dict(row) for row in self.conn.execute(query, params).fetchall()]

    def get_transaction_summary(
        self,
        resource_id: Optional[int] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> Dict[str, int]:
        """
        Отримує зведену інформацію про транзакції.

        Args:
            resource_id: ID ресурсу (якщо None, для всіх ресурсів)
            start_date: Початкова дата у форматі 'YYYY-MM-DD'
            end_date: Кінцева дата у форматі 'YYYY-MM-DD'

        Returns:
            Dict[str, int]: Словник з кількістю транзакцій кожного типу
        """
        query = """
            SELECT 
                transaction_type,
                COUNT(*) as count,
                SUM(quantity_changed) as total_quantity
            FROM resource_transactions
            WHERE 1=1
        """
        params = []

        if resource_id:
            query += " AND resource_id = ?"
            params.append(resource_id)
        if start_date:
            query += " AND transaction_date >= ?"
            params.append(f"{start_date} 00:00:00")
        if end_date:
            query += " AND transaction_date <= ?"
            params.append(f"{end_date} 23:59:59")

        query += " GROUP BY transaction_type"

        return {
            row["transaction_type"]: {
                "count": row["count"],
                "total_quantity": row["total_quantity"]
            }
            for row in self.conn.execute(query, params).fetchall()
        } 