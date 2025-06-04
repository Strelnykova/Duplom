from military_resource_app.logic.db_manager import create_connection, create_tables

def main():
    print("Створення бази даних...")
    conn = create_connection()
    if conn:
        print("З'єднання з базою даних встановлено")
        create_tables(conn)
        print("Таблиці створено")
        conn.close()
    else:
        print("Помилка з'єднання з базою даних")

if __name__ == "__main__":
    main() 