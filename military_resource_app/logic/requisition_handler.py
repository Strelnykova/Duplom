import sqlite3
from datetime import datetime
import os
import sys

# Add parent directory to Python path for imports
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from logic.db_manager import create_connection, create_tables

def create_requisition(created_by_user_id: int, department_requesting: str,
                       urgency: str = 'routine', notes: str | None = None) -> int | None:
    """
    Creates a new requisition.

    Args:
        created_by_user_id: ID of the user creating the requisition.
        department_requesting: Department submitting the requisition.
        urgency: Requisition urgency ('routine', 'urgent', 'critical').
        notes: Notes for the requisition.

    Returns:
        ID of the newly created requisition if successful, None otherwise.
    """
    conn = create_connection()
    if not conn:
        return None

    requisition_number = f"REQ-{datetime.now().strftime('%Y%m%d%H%M%S')}-{created_by_user_id}" # Example number generation
    creation_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = 'new' # Initial status

    try:
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO requisitions
            (requisition_number, created_by_user_id, department_requesting,
             creation_date, status, urgency, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (requisition_number, created_by_user_id, department_requesting,
              creation_date, status, urgency, notes))
        conn.commit()
        new_requisition_id = cur.lastrowid
        print(f"Created new requisition ID: {new_requisition_id}, Number: {requisition_number}")
        return new_requisition_id
    except sqlite3.Error as e:
        print(f"Database error while creating requisition: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()

def add_item_to_requisition(requisition_id: int, requested_resource_name: str,
                            quantity_requested: int, unit_of_measure: str | None = None,
                            resource_id: int | None = None, justification: str | None = None) -> bool:
    """
    Adds an item to an existing requisition.

    Args:
        requisition_id: ID of the requisition to add the item to.
        requested_resource_name: Name of the requested resource.
        quantity_requested: Requested quantity.
        unit_of_measure: Unit of measure.
        resource_id: Resource ID from the catalog (if known).
        justification: Need justification.

    Returns:
        True if item was successfully added, False otherwise.
    """
    if quantity_requested <= 0:
        print("Error: Quantity for requisition item must be greater than zero.")
        return False

    conn = create_connection()
    if not conn:
        return False

    item_status = 'pending' # Initial item status

    try:
        cur = conn.cursor()
        # Check if requisition exists (optional but useful)
        cur.execute("SELECT id FROM requisitions WHERE id = ?", (requisition_id,))
        if not cur.fetchone():
            print(f"Error: Requisition with ID {requisition_id} not found.")
            return False

        cur.execute("""
            INSERT INTO requisition_items
            (requisition_id, resource_id, requested_resource_name,
             quantity_requested, unit_of_measure, justification, item_status)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (requisition_id, resource_id, requested_resource_name,
              quantity_requested, unit_of_measure, justification, item_status))
        conn.commit()
        print(f"Added item '{requested_resource_name}' to requisition ID: {requisition_id}")
        return True
    except sqlite3.Error as e:
        print(f"Database error while adding item to requisition: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def get_requisitions(status: str | None = None, limit: int = 100, offset: int = 0) -> list:
    """
    Gets a list of requisitions with optional status filtering and pagination.

    Args:
        status: Requisition status to filter by (e.g., 'new', 'approved').
        limit: Maximum number of requisitions to return.
        offset: Offset for pagination.

    Returns:
        List of dictionaries containing requisition data.
    """
    conn = create_connection()
    if not conn:
        return []

    query = """
        SELECT r.id, r.requisition_number, u.username as created_by, r.department_requesting,
               r.creation_date, r.status, r.urgency, r.notes
        FROM requisitions r
        LEFT JOIN users u ON r.created_by_user_id = u.id
    """
    params = []

    if status:
        query += " WHERE r.status = ?"
        params.append(status)

    query += " ORDER BY r.creation_date DESC LIMIT ? OFFSET ?"
    params.extend([limit, offset])

    try:
        cur = conn.cursor()
        cur.execute(query, tuple(params))
        requisitions = cur.fetchall()
        return [dict(row) for row in requisitions]
    except sqlite3.Error as e:
        print(f"Database error while getting requisitions list: {e}")
        return []
    finally:
        if conn:
            conn.close()

def get_requisition_details(requisition_id: int) -> dict | None:
    """
    Gets details of a specific requisition, including its items.

    Returns:
        Dictionary with requisition data and list of its items, or None if requisition not found.
    """
    requisition_data = None
    items_data = []
    conn = create_connection()
    if not conn:
        return None

    try:
        cur = conn.cursor()
        # Get main requisition information
        cur.execute("""
            SELECT r.id, r.requisition_number, r.created_by_user_id, u.username as created_by_username,
                   r.department_requesting, r.creation_date, r.status, r.urgency, r.notes
            FROM requisitions r
            LEFT JOIN users u ON r.created_by_user_id = u.id
            WHERE r.id = ?
        """, (requisition_id,))
        requisition_info = cur.fetchone()

        if not requisition_info:
            print(f"Requisition with ID {requisition_id} not found.")
            return None
        
        requisition_data = dict(requisition_info)

        # Get requisition items
        cur.execute("""
            SELECT ri.id, ri.resource_id, res.name as resource_name_from_db,
                   ri.requested_resource_name, ri.quantity_requested,
                   ri.unit_of_measure, ri.justification, ri.item_status
            FROM requisition_items ri
            LEFT JOIN resources res ON ri.resource_id = res.id
            WHERE ri.requisition_id = ?
            ORDER BY ri.id
        """, (requisition_id,))
        items = cur.fetchall()
        items_data = [dict(item) for item in items]

        requisition_data['items'] = items_data
        return requisition_data

    except sqlite3.Error as e:
        print(f"Database error while getting requisition details for ID {requisition_id}: {e}")
        return None
    finally:
        if conn:
            conn.close()

def update_requisition_status(requisition_id: int, new_status: str, updated_by_user_id: int | None = None) -> bool:
    """
    Updates requisition status.

    Args:
        requisition_id: ID of the requisition to update.
        new_status: New requisition status.
        updated_by_user_id: ID of the user updating the status (for logging if needed).

    Returns:
        True if status was successfully updated, False otherwise.
    """
    # Список допустимих статусів українською
    valid_statuses = ['нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано']
    if new_status not in valid_statuses:
        print(f"Error: Invalid new requisition status '{new_status}'.")
        return False

    conn = create_connection()
    if not conn:
        return False

    try:
        cur = conn.cursor()
        cur.execute("UPDATE requisitions SET status = ? WHERE id = ?", (new_status, requisition_id))
        if cur.rowcount == 0:
            print(f"Error: Requisition with ID {requisition_id} not found for status update.")
            return False
        conn.commit()
        print(f"Updated requisition ID {requisition_id} status to '{new_status}'.")
        # Can add status change logging here if there's a corresponding table
        return True
    except sqlite3.Error as e:
        print(f"Database error while updating requisition status: {e}")
        if conn:
            conn.rollback()
        return False
    finally:
        if conn:
            conn.close()

def process_requisition_item_execution(requisition_item_id: int,
                                       quantity_to_issue: int,
                                       issued_by_user_id: int,
                                       recipient_department: str) -> tuple[bool, str]:
    """
    Обробляє виконання однієї позиції заявки.
    Створює транзакцію видачі та оновлює статус позиції.

    Args:
        requisition_item_id: ID позиції заявки для виконання.
        quantity_to_issue: Кількість, яку потрібно видати.
        issued_by_user_id: ID користувача, що здійснює видачу.
        recipient_department: Відділення, якому видається ресурс.

    Returns:
        Кортеж (success: bool, message: str)
    """
    conn = create_connection()
    if not conn:
        return False, "Не вдалося підключитися до бази даних."

    try:
        cur = conn.cursor()

        # 1. Отримати деталі позиції заявки
        cur.execute("""
            SELECT ri.id, ri.requisition_id, ri.resource_id, ri.requested_resource_name,
                   ri.quantity_requested, ri.item_status, r.quantity as current_stock, r.name as stock_resource_name
            FROM requisition_items ri
            LEFT JOIN resources r ON ri.resource_id = r.id
            WHERE ri.id = ?
        """, (requisition_item_id,))
        item = cur.fetchone()

        if not item:
            return False, f"Позицію заявки з ID {requisition_item_id} не знайдено."

        if item['item_status'] == 'виконано':
            return False, f"Позиція '{item['requested_resource_name']}' вже виконана."
        
        # Перевіряємо, чи позиція прив'язана до конкретного ресурсу на складі
        if not item['resource_id']:
            return False, (f"Неможливо автоматично видати '{item['requested_resource_name']}', "
                           f"оскільки позиція не пов'язана з конкретним ресурсом на складі (resource_id відсутній). "
                           f"Спочатку додайте цей ресурс на склад та прив'яжіть до позиції заявки, або оприбуткуйте його.")

        if quantity_to_issue <= 0:
            return False, "Кількість для видачі повинна бути більшою за нуль."

        if quantity_to_issue > item['quantity_requested'] and item['item_status'] != 'частково виконано':
             print(f"Увага: видається ({quantity_to_issue}) більше, ніж запитано ({item['quantity_requested']}) для '{item['stock_resource_name']}'")

        if item['current_stock'] is None or item['current_stock'] < quantity_to_issue:
            return False, (f"Недостатньо ресурсу '{item['stock_resource_name']}' на складі. "
                           f"В наявності: {item['current_stock'] or 0}, потрібно: {quantity_to_issue}.")

        # 3. Зареєструвати транзакцію видачі
        transaction_notes = f"Видача по заявці ID: {item['requisition_id']}, позиція ID: {requisition_item_id}"
        
        from .transaction_handler import TransactionHandler
        transaction_handler = TransactionHandler(conn)
        transaction_success, transaction_message = transaction_handler.add_transaction(
            resource_id=item['resource_id'],
            transaction_type='видача',
            quantity_changed=quantity_to_issue,
            recipient_department=recipient_department,
            issued_by_user_id=issued_by_user_id,
            notes=transaction_notes
        )

        if not transaction_success:
            return False, f"Не вдалося зареєструвати транзакцію видачі: {transaction_message}"

        # 4. Оновити статус позиції заявки
        new_item_status = 'виконано'
        cur.execute("UPDATE requisition_items SET item_status = ? WHERE id = ?", (new_item_status, requisition_item_id))
        
        # 5. Перевірити і оновити загальний статус заявки
        check_and_update_overall_requisition_status(item['requisition_id'], conn)
        
        conn.commit()
        return True, f"Позицію '{item['stock_resource_name']}' (кількість: {quantity_to_issue}) успішно видано."

    except sqlite3.Error as e:
        print(f"Помилка бази даних при виконанні позиції заявки: {e}")
        if conn:
            conn.rollback()
        return False, f"Помилка бази даних: {e}"
    finally:
        if conn:
            conn.close()

def check_and_update_overall_requisition_status(requisition_id: int, db_connection: sqlite3.Connection):
    """
    Перевіряє статуси всіх позицій заявки та оновлює загальний статус заявки.
    Ця функція повинна викликатися всередині транзакції або з переданим активним з'єднанням.
    """
    cur = db_connection.cursor()
    cur.execute("""
        SELECT COUNT(*) as total_items,
               SUM(CASE WHEN item_status = 'виконано' THEN 1 ELSE 0 END) as completed_items,
               SUM(CASE WHEN item_status = 'частково виконано' THEN 1 ELSE 0 END) as partially_completed_items,
               SUM(CASE WHEN item_status = 'відхилено' THEN 1 ELSE 0 END) as rejected_items
        FROM requisition_items
        WHERE requisition_id = ?
    """, (requisition_id,))
    status_summary = cur.fetchone()

    if not status_summary or status_summary['total_items'] == 0:
        return # Немає позицій або помилка

    new_overall_status = None
    if status_summary['completed_items'] == status_summary['total_items']:
        new_overall_status = 'виконано'
    elif (status_summary['completed_items'] + status_summary['partially_completed_items'] + status_summary['rejected_items']) == status_summary['total_items'] and \
         (status_summary['completed_items'] > 0 or status_summary['partially_completed_items'] > 0):
        new_overall_status = 'частково виконано'
    elif (status_summary['completed_items'] + status_summary['rejected_items']) == status_summary['total_items']:
         if status_summary['completed_items'] > 0:
             new_overall_status = 'частково виконано'
         else:
             new_overall_status = 'відхилено'

    if new_overall_status:
        cur.execute("UPDATE requisitions SET status = ? WHERE id = ?", (new_overall_status, requisition_id))

if __name__ == '__main__':
    print("Testing requisition handling functionality...")
    
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
        created_by_user_id=1,
        department_requesting="Supply Department",
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
                new_req_id, name, qty, unit,
                resource_id=res_id,
                justification=justif
            )
            print(f"Added item {name}: {'Success' if success else 'Failed'}")

        # Test getting requisition details
        print("\nRequisition details:")
        details = get_requisition_details(new_req_id)
        if details:
            for key, value in details.items():
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
            success = update_requisition_status(new_req_id, status)
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