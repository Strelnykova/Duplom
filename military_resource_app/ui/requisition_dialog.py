from PyQt6 import QtCore, QtGui, QtWidgets
from datetime import datetime
import sqlite3
# Налаштування шляхів для імпорту, якщо потрібно
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))) # Додаємо корінь проєкту
from logic.db_manager import create_connection # Для завантаження списку ресурсів
from logic.requisition_handler import (create_requisition, add_item_to_requisition,
                                       get_requisition_details, update_requisition_status,
                                       process_requisition_item_execution)

class RequisitionDialog(QtWidgets.QDialog):
    # Сигнал, який може бути використаний для оновлення даних у головному вікні
    requisition_status_changed_signal = QtCore.pyqtSignal(int)
    requisition_item_executed_signal = QtCore.pyqtSignal(int)

    def __init__(self, current_user_id: int, current_user_role: str,
                 parent=None, requisition_id_to_view: int | None = None):
        super().__init__(parent)
        self.current_user_id = current_user_id
        self.current_user_role = current_user_role
        self.requisition_id_to_view = requisition_id_to_view
        self.new_requisition_id = None
        self.successfully_saved_status = False
        self.details_data = None

        self.valid_statuses = ['нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано']

        self.layout = QtWidgets.QVBoxLayout(self)

        # --- Секція загальної інформації про заявку ---
        self.requisition_group_box = QtWidgets.QGroupBox("Загальна інформація про заявку")
        self.requisition_form_layout = QtWidgets.QFormLayout()

        self.department_edit = QtWidgets.QLineEdit(self)
        self.requisition_form_layout.addRow("Відділення, що подає заявку:", self.department_edit)

        self.urgency_combo = QtWidgets.QComboBox(self)
        self.urgency_combo.addItems(['планова', 'термінова', 'критична'])
        self.requisition_form_layout.addRow("Терміновість:", self.urgency_combo)

        self.purpose_description_edit = QtWidgets.QTextEdit(self)
        self.purpose_description_edit.setFixedHeight(60)
        self.requisition_form_layout.addRow("Опис призначення:", self.purpose_description_edit)

        self.requisition_group_box.setLayout(self.requisition_form_layout)
        self.layout.addWidget(self.requisition_group_box)

        # --- Елементи для зміни статусу (в режимі перегляду) ---
        self.status_management_group_box = QtWidgets.QGroupBox("Управління статусом")
        self.status_management_layout = QtWidgets.QFormLayout()
        
        self.current_status_label = QtWidgets.QLabel("Поточний статус:")
        self.status_value_label = QtWidgets.QLabel()
        self.status_management_layout.addRow(self.current_status_label, self.status_value_label)

        self.status_combo_label = QtWidgets.QLabel("Змінити статус на:")
        self.status_combo = QtWidgets.QComboBox(self)
        self.status_combo.addItems(self.valid_statuses)
        self.status_management_layout.addRow(self.status_combo_label, self.status_combo)

        self.save_status_button = QtWidgets.QPushButton("Зберегти статус", self)
        self.save_status_button.clicked.connect(self.save_new_status)
        status_button_layout = QtWidgets.QHBoxLayout()
        status_button_layout.addStretch()
        status_button_layout.addWidget(self.save_status_button)
        self.status_management_layout.addRow(status_button_layout)

        self.status_management_group_box.setLayout(self.status_management_layout)
        self.layout.addWidget(self.status_management_group_box)
        self.status_management_group_box.setVisible(False)

        # --- Секція позицій заявки ---
        self.items_group_box = QtWidgets.QGroupBox("Позиції заявки")
        self.items_layout = QtWidgets.QVBoxLayout()

        # Таблиця для відображення доданих позицій
        self.items_table = QtWidgets.QTableWidget(self)
        self.items_table.setColumnCount(7)
        self.items_table.setHorizontalHeaderLabels(["Назва ресурсу", "Заявл. к-сть", "Од.вим.", "Обґрунтування", "Статус позиції", "Дії"])
        self.items_table.setColumnHidden(6, True)
        header = self.items_table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(2, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(3, QtWidgets.QHeaderView.ResizeMode.Stretch)
        header.setSectionResizeMode(4, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(5, QtWidgets.QHeaderView.ResizeMode.ResizeToContents)
        self.items_table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows)
        self.items_layout.addWidget(self.items_table)

        # Форма для додавання нової позиції
        self.add_item_form_widget = QtWidgets.QWidget()
        self.add_item_form_layout = QtWidgets.QFormLayout(self.add_item_form_widget)
        self.resource_search_combo = QtWidgets.QComboBox(self)
        self.resource_search_combo.setEditable(True)
        self.resource_search_combo.setInsertPolicy(QtWidgets.QComboBox.InsertPolicy.NoInsert)
        self.resource_search_combo.completer().setCompletionMode(QtWidgets.QCompleter.CompletionMode.PopupCompletion)
        self.load_resources_for_combo()
        self.resource_search_combo.currentTextChanged.connect(self.on_resource_combo_changed)

        self.add_item_form_layout.addRow("Пошук/Назва ресурсу:", self.resource_search_combo)

        self.quantity_requested_spinbox = QtWidgets.QSpinBox(self)
        self.quantity_requested_spinbox.setRange(1, 100000)
        self.add_item_form_layout.addRow("Кількість:", self.quantity_requested_spinbox)

        self.unit_of_measure_edit = QtWidgets.QLineEdit(self)
        self.unit_of_measure_edit.setPlaceholderText("напр., шт, кг, л, комплект")
        self.add_item_form_layout.addRow("Одиниця виміру:", self.unit_of_measure_edit)

        self.justification_edit = QtWidgets.QLineEdit(self)
        self.add_item_form_layout.addRow("Обґрунтування:", self.justification_edit)

        self.add_item_button = QtWidgets.QPushButton("Додати позицію до заявки", self)
        self.add_item_button.clicked.connect(self.add_item_to_table)

        self.items_layout.addWidget(self.add_item_form_widget)
        self.items_layout.addWidget(self.add_item_button)
        self.items_group_box.setLayout(self.items_layout)
        self.layout.addWidget(self.items_group_box)

        # Кнопки OK (Створити заявку) та Скасувати
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )

        if self.requisition_id_to_view:
            self.setWindowTitle(f"Деталі заявки") # Заголовок буде оновлено після завантаження даних
            self.load_data_for_view()
            self.setup_view_mode()
        else:
            self.setWindowTitle("Створення нової заявки")
            self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setText("Створити заявку")
            self.button_box.accepted.connect(self.accept_requisition)

        self.button_box.rejected.connect(self.reject)
        self.layout.addWidget(self.button_box)

    def on_resource_combo_changed(self, text):
        """Коли текст в комбо-боксі пошуку змінюється, оновлюємо unit_of_measure, якщо ресурс вибрано."""
        selected_data = self.resource_search_combo.currentData()
        if selected_data: # Якщо вибрано існуючий ресурс
            self.unit_of_measure_edit.setText(selected_data.get('unit_of_measure', ''))
            self.unit_of_measure_edit.setReadOnly(True) # Блокуємо редагування, якщо з довідника
        else:
            # Якщо користувач вводить текст, який не відповідає жодному ресурсу
            self.unit_of_measure_edit.clear()
            self.unit_of_measure_edit.setReadOnly(False)


    def load_resources_for_combo(self):
        """Завантажує список ресурсів у QComboBox для пошуку."""
        self.resource_search_combo.clear()
        self.resource_search_combo.addItem("", None) # Порожній елемент для можливості ввести нову назву

        conn = create_connection()
        if not conn: return
        try:
            cur = conn.cursor()
            cur.execute("SELECT id, name, unit_of_measure FROM resources ORDER BY name")
            resources = cur.fetchall()
            for resource in resources:
                # Зберігаємо id та unit_of_measure в userData
                self.resource_search_combo.addItem(
                    f"{resource['name']} (од: {resource['unit_of_measure'] or 'не вказано'})",
                    {'id': resource['id'], 'name': resource['name'], 'unit_of_measure': resource['unit_of_measure']}
                )
        except sqlite3.Error as e:
            print(f"Помилка завантаження ресурсів для комбо-боксу: {e}")
        finally:
            if conn: conn.close()


    def add_item_to_table(self):
        """Додає введену позицію до таблиці позицій заявки."""
        resource_data = self.resource_search_combo.currentData()
        resource_id_linked = None
        resource_name = self.resource_search_combo.currentText().strip() # Беремо текст з комбо-боксу

        if resource_data: # Якщо вибрано існуючий ресурс
            resource_id_linked = resource_data.get('id')
            resource_name = resource_data.get('name', resource_name) # Використовуємо точну назву з БД
            unit_of_measure = resource_data.get('unit_of_measure', self.unit_of_measure_edit.text().strip())
        else: # Якщо введено нову назву
             # Перевіряємо, чи назва не порожня, якщо не вибрано з довідника
            if not resource_name:
                QtWidgets.QMessageBox.warning(self, "Помилка вводу", "Будь ласка, вкажіть назву ресурсу або оберіть існуючий.")
                return
            unit_of_measure = self.unit_of_measure_edit.text().strip()


        quantity = self.quantity_requested_spinbox.value()
        justification = self.justification_edit.text().strip()

        if quantity <= 0:
            QtWidgets.QMessageBox.warning(self, "Помилка вводу", "Кількість повинна бути більшою за нуль.")
            return
        if not unit_of_measure:
            QtWidgets.QMessageBox.warning(self, "Помилка вводу", "Будь ласка, вкажіть одиницю виміру.")
            return

        row_position = self.items_table.rowCount()
        self.items_table.insertRow(row_position)

        item_obj_data = {
            'name': resource_name,
            'id_linked': resource_id_linked,
            'unit': unit_of_measure,
            'qty': quantity,
            'just': justification,
            'item_id': None,
            'item_status': 'очікує'
        }

        name_item = QtWidgets.QTableWidgetItem(resource_name)
        name_item.setData(QtCore.Qt.ItemDataRole.UserRole, item_obj_data)
        self.items_table.setItem(row_position, 0, name_item)
        self.items_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(quantity)))
        self.items_table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(unit_of_measure))
        self.items_table.setItem(row_position, 3, QtWidgets.QTableWidgetItem(justification))
        self.items_table.setItem(row_position, 4, QtWidgets.QTableWidgetItem(item_obj_data['item_status']))

        remove_button = QtWidgets.QPushButton("Видалити")
        remove_button.clicked.connect(lambda _, r=row_position: self.items_table.removeRow(r))
        self.items_table.setCellWidget(row_position, 5, remove_button)

        # Очищення полів форми додавання позиції
        self.resource_search_combo.setCurrentIndex(0) # Скидаємо вибір
        self.quantity_requested_spinbox.setValue(1)
        self.unit_of_measure_edit.clear()
        self.justification_edit.clear()
        self.unit_of_measure_edit.setReadOnly(False) # Розблоковуємо, якщо було заблоковано


    def accept_requisition(self):
        """Створює нову заявку з введеними даними."""
        try:
            # Перевірка введених даних
            department = self.department_edit.text().strip()
            if not department:
                QtWidgets.QMessageBox.warning(self, "Помилка валідації",
                                            "Будь ласка, вкажіть відділення")
                return

            if self.items_table.rowCount() == 0:
                QtWidgets.QMessageBox.warning(self, "Помилка валідації",
                                            "Додайте хоча б одну позицію до заявки")
                return

            # Створюємо з'єднання з БД
            conn = create_connection()
            if not conn:
                QtWidgets.QMessageBox.critical(self, "Помилка з'єднання",
                                             "Не вдалося підключитися до бази даних")
                return

            try:
                # Створюємо заявку
                requisition_id = create_requisition(
                    conn=conn,
                    user_id=self.current_user_id,
                    department=department,
                    urgency=self.urgency_combo.currentText(),
                    purpose_description=self.purpose_description_edit.toPlainText().strip()
                )

                if not requisition_id:
                    QtWidgets.QMessageBox.critical(self, "Помилка створення",
                                                 "Не вдалося створити заявку")
                    return

                # Додаємо позиції до заявки
                for row in range(self.items_table.rowCount()):
                    # Отримуємо дані з UserRole першої колонки
                    item_data = self.items_table.item(row, 0).data(QtCore.Qt.ItemDataRole.UserRole)
                    if not item_data:
                        raise Exception(f"Помилка отримання даних для позиції {row + 1}")

                    print(f"[DEBUG] Дані позиції для додавання:")
                    print(f"[DEBUG] {item_data}")

                    success = add_item_to_requisition(
                        conn=conn,
                        requisition_id=requisition_id,
                        resource_id=item_data['id_linked'],
                        resource_name=item_data['name'],
                        quantity_requested=item_data['qty'],
                        notes=item_data['just']
                    )

                    if not success:
                        raise Exception(f"Не вдалося додати позицію '{item_data['name']}' до заявки")

                conn.commit()
                self.new_requisition_id = requisition_id
                self.successfully_saved_status = True
                QtWidgets.QMessageBox.information(self, "Успіх", 
                                                f"Заявку успішно створено (ID: {requisition_id})")
                super().accept()  # Закриваємо діалог тільки після успішного збереження

            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Помилка",
                                             f"Помилка при створенні заявки: {str(e)}")
                if conn:
                    conn.rollback()
                return
            finally:
                if conn:
                    conn.close()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Помилка",
                                         f"Неочікувана помилка: {str(e)}")
            return

    def load_data_for_view(self):
        """Завантажує дані заявки для режиму перегляду."""
        if not self.requisition_id_to_view:
            return

        self.details_data = get_requisition_details(self.requisition_id_to_view)
        if not self.details_data:
            QtWidgets.QMessageBox.critical(self, "Помилка", f"Не вдалося завантажити деталі заявки ID: {self.requisition_id_to_view}")
            self.close() # Закриваємо діалог, якщо даних немає
            return

        self.setWindowTitle(f"Деталі заявки № {self.details_data.get('requisition_number', self.requisition_id_to_view)}")

        # Заповнення загальної інформації
        self.department_edit.setText(self.details_data.get('department_requesting', ''))
        urgency_index = self.urgency_combo.findText(self.details_data.get('urgency', 'планова'), QtCore.Qt.MatchFlag.MatchFixedString)
        if urgency_index >= 0:
            self.urgency_combo.setCurrentIndex(urgency_index)
        self.purpose_description_edit.setPlainText(self.details_data.get('purpose_description', ''))

        # Відображення поточного статусу та налаштування комбо-боксу для зміни
        current_status = self.details_data.get('status', 'нова')
        self.status_value_label.setText(f"<b>{current_status.capitalize()}</b>")
        status_idx = self.status_combo.findText(current_status, QtCore.Qt.MatchFlag.MatchFixedString)
        if status_idx >= 0:
            self.status_combo.setCurrentIndex(status_idx)

        # Заповнення таблиці позицій
        self.items_table.setRowCount(0) # Очищаємо таблицю перед заповненням
        for item_data in self.details_data.get('items', []):
            row_position = self.items_table.rowCount()
            self.items_table.insertRow(row_position)

            resource_display_name = item_data.get('requested_resource_name', '')
            name_item = QtWidgets.QTableWidgetItem(resource_display_name)
            name_item.setData(QtCore.Qt.ItemDataRole.UserRole, item_data)
            self.items_table.setItem(row_position, 0, name_item)
            self.items_table.setItem(row_position, 1, QtWidgets.QTableWidgetItem(str(item_data.get('quantity_requested', ''))))
            self.items_table.setItem(row_position, 2, QtWidgets.QTableWidgetItem(item_data.get('unit_of_measure', '')))
            self.items_table.setItem(row_position, 3, QtWidgets.QTableWidgetItem(item_data.get('justification', '')))
            self.items_table.setItem(row_position, 4, QtWidgets.QTableWidgetItem(item_data.get('item_status', '')))
            self.items_table.setItem(row_position, 6, QtWidgets.QTableWidgetItem(str(item_data.get('id'))))

            if (self.current_user_role == 'admin' and
                item_data.get('item_status') in ['схвалено', 'частково виконано'] and
                item_data.get('resource_id') is not None):
                execute_button = QtWidgets.QPushButton("Виконати")
                execute_button.clicked.connect(
                    lambda _, r_item_id=item_data.get('id'), req_qty=item_data.get('quantity_requested'):
                        self.execute_requisition_item_prompt(r_item_id, req_qty)
                )
                self.items_table.setCellWidget(row_position, 5, execute_button)
            else:
                self.items_table.setCellWidget(row_position, 5, None)

    def setup_view_mode(self):
        """Налаштовує діалог для режиму 'тільки для читання'."""
        # Загальна інформація
        self.department_edit.setReadOnly(True)
        self.urgency_combo.setEnabled(False)
        self.purpose_description_edit.setReadOnly(True)

        # Секція додавання позицій
        self.items_group_box.setTitle("Перелік позицій у заявці")
        self.add_item_form_widget.setVisible(False)
        self.add_item_button.setVisible(False)
        self.items_table.setColumnHidden(6, True)

        # Показуємо секцію управління статусом та робимо її активною для адміна
        if self.current_user_role == 'admin':
            self.status_management_group_box.setVisible(True)
        else:
            self.status_management_group_box.setVisible(False)

        # Основні кнопки діалогу
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Ok).setVisible(False)
        self.button_box.button(QtWidgets.QDialogButtonBox.StandardButton.Cancel).setText("Закрити")

    def execute_requisition_item_prompt(self, requisition_item_id: int, requested_quantity: int):
        if not self.details_data: return

        default_qty = requested_quantity

        quantity_to_issue, ok = QtWidgets.QInputDialog.getInt(
            self, "Кількість до видачі",
            f"Вкажіть кількість для видачі (макс: {default_qty}):",
            value=default_qty, min=1, max=default_qty
        )

        if ok and quantity_to_issue > 0:
            recipient = self.details_data.get('department_requesting', 'Не вказано')
            success, message = process_requisition_item_execution(
                requisition_item_id=requisition_item_id,
                quantity_to_issue=quantity_to_issue,
                issued_by_user_id=self.current_user_id,
                recipient_department=recipient
            )
            if success:
                QtWidgets.QMessageBox.information(self, "Успіх", message)
                self.load_data_for_view()
                self.requisition_status_changed_signal.emit(self.requisition_id_to_view)
                self.requisition_item_executed_signal.emit(self.requisition_id_to_view)
            else:
                QtWidgets.QMessageBox.warning(self, "Помилка виконання", message)
        else:
            print("Видачу скасовано користувачем або введено невірне значення.")

    def save_new_status(self):
        if not self.requisition_id_to_view:
            return

        new_status = self.status_combo.currentText()
        success = update_requisition_status(
            requisition_id=self.requisition_id_to_view,
            new_status=new_status,
            updated_by_user_id=self.current_user_id
        )

        if success:
            QtWidgets.QMessageBox.information(self, "Успіх", f"Статус заявки оновлено на '{new_status}'.")
            self.status_value_label.setText(f"<b>{new_status.capitalize()}</b>")
            self.successfully_saved_status = True
            self.requisition_status_changed_signal.emit(self.requisition_id_to_view)
            if new_status == "схвалено":
                self.load_data_for_view()
        else:
            QtWidgets.QMessageBox.critical(self, "Помилка", "Не вдалося оновити статус заявки.")

# --- Приклад використання (для тестування цього діалогу окремо) ---
if __name__ == '__main__':
    app = QtWidgets.QApplication(sys.argv)
    # Переконайтеся, що БД ініціалізована (запустіть db_manager.py)
    # та є користувач з ID 1 (або змініть)
    dialog = RequisitionDialog(current_user_id=1, current_user_role='admin')
    if dialog.exec():
        print(f"Діалог успішно завершено, створено заявку ID: {dialog.new_requisition_id}")
    else:
        print("Діалог скасовано")
    sys.exit(app.exec()) 