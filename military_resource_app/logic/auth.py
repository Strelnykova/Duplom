#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Логіка автентифікації та управління користувачами.
"""

import hashlib
import sqlite3
from typing import Optional, Tuple

def hash_password(password: str) -> str:
    """Хешує пароль користувача."""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(stored_hash: str, password: str) -> bool:
    """Перевіряє відповідність пароля хешу."""
    return stored_hash == hash_password(password)

class AuthManager:
    def __init__(self, conn: sqlite3.Connection):
        self.conn = conn
        self._current_user = None
        self._current_role = None

    @property
    def current_user(self) -> Optional[str]:
        """Повертає ім'я поточного користувача."""
        return self._current_user

    @property
    def current_role(self) -> Optional[str]:
        """Повертає роль поточного користувача."""
        return self._current_role

    def login(self, username: str, password: str) -> Tuple[bool, str]:
        """
        Спроба входу користувача.
        
        Returns:
            Tuple[bool, str]: (успіх, повідомлення про помилку)
        """
        try:
            user = self.conn.execute(
                "SELECT username, password, role FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if not user:
                return False, "Користувача не знайдено"

            if not verify_password(user['password'], password):
                return False, "Невірний пароль"

            self._current_user = user['username']
            self._current_role = user['role']
            return True, ""

        except sqlite3.Error as e:
            return False, f"Помилка бази даних: {str(e)}"

    def logout(self):
        """Вихід користувача."""
        self._current_user = None
        self._current_role = None

    def change_password(self, username: str, old_password: str, new_password: str) -> Tuple[bool, str]:
        """
        Зміна пароля користувача.
        
        Returns:
            Tuple[bool, str]: (успіх, повідомлення про помилку)
        """
        try:
            user = self.conn.execute(
                "SELECT password FROM users WHERE username = ?",
                (username,)
            ).fetchone()

            if not user:
                return False, "Користувача не знайдено"

            if not verify_password(user['password'], old_password):
                return False, "Невірний поточний пароль"

            self.conn.execute(
                "UPDATE users SET password = ? WHERE username = ?",
                (hash_password(new_password), username)
            )
            self.conn.commit()
            return True, "Пароль успішно змінено"

        except sqlite3.Error as e:
            return False, f"Помилка бази даних: {str(e)}"

    def create_user(self, username: str, password: str, role: str = 'user') -> Tuple[bool, str]:
        """
        Створення нового користувача.
        
        Args:
            username: Ім'я користувача
            password: Пароль
            role: Роль (за замовчуванням 'user')
            
        Returns:
            Tuple[bool, str]: (успіх, повідомлення)
        """
        if role not in ('admin', 'user'):
            return False, "Недопустима роль"

        try:
            self.conn.execute(
                "INSERT INTO users (username, password, role) VALUES (?, ?, ?)",
                (username, hash_password(password), role)
            )
            self.conn.commit()
            return True, "Користувача успішно створено"

        except sqlite3.IntegrityError:
            return False, "Користувач з таким іменем вже існує"
        except sqlite3.Error as e:
            return False, f"Помилка бази даних: {str(e)}"

    def delete_user(self, username: str) -> Tuple[bool, str]:
        """
        Видалення користувача.
        
        Returns:
            Tuple[bool, str]: (успіх, повідомлення)
        """
        if username == 'admin':
            return False, "Неможливо видалити адміністратора"

        try:
            cur = self.conn.execute("DELETE FROM users WHERE username = ?", (username,))
            self.conn.commit()
            
            if cur.rowcount == 0:
                return False, "Користувача не знайдено"
                
            return True, "Користувача успішно видалено"

        except sqlite3.Error as e:
            return False, f"Помилка бази даних: {str(e)}"

    def list_users(self) -> list:
        """Повертає список всіх користувачів."""
        return [
            dict(row) for row in 
            self.conn.execute("SELECT username, role FROM users").fetchall()
        ] 