# Система обліку військового майна

## 📋 Опис проекту
Система для обліку та управління військовим майном з функціями створення заявок, відстеження ресурсів та генерації звітів.

## 🏗️ Архітектура

### Структура проекту
```
military_resource_app/
├── logic/           # Бізнес-логіка
│   ├── db_manager.py     # Управління базою даних
│   └── requisition_handler.py  # Обробка заявок
├── ui/             # Інтерфейс користувача
│   ├── login_dialog.py   # Вікно входу
│   ├── main_window.py    # Головне вікно
│   └── requisition_dialog.py  # Вікно заявок
└── assets/         # Ресурси
    └── style.css   # Стилі
```

### Компоненти системи
- **База даних**: SQLite
- **Інтерфейс**: PyQt6
- **Бізнес-логіка**: Python 3.x

## 🔄 Основні процеси
1. Авторизація користувачів
2. Управління ресурсами (додавання, редагування, видалення)
3. Створення та обробка заявок
4. Генерація звітів
5. Відстеження залишків та термінів придатності

## 👥 Ролі користувачів
- **Адміністратор**: Повний доступ до системи
- **Користувач**: Обмежений доступ (створення заявок, перегляд ресурсів)

## 📊 Діаграма бази даних
```mermaid
erDiagram
    users ||--o{ requisitions : creates
    users {
        int id PK
        string username
        string password
        string role
        string rank
        string last_name
        string first_name
        string middle_name
        string position
    }
    categories ||--o{ resources : contains
    categories {
        int id PK
        string name
        int parent_id FK
    }
    resources ||--o{ resource_transactions : has
    resources ||--o{ requisition_items : requested_in
    resources {
        int id PK
        string name
        int category_id FK
        int quantity
        string unit_of_measure
        string description
        string image_path
        string supplier
        string phone
        string origin
        date arrival_date
        float cost
        date expiration_date
        int low_stock_threshold
    }
    requisitions ||--o{ requisition_items : contains
    requisitions {
        int id PK
        string requisition_number
        int created_by_user_id FK
        string department_requesting
        datetime creation_date
        string status
        string urgency
        string purpose_description
        string requisition_type
        string author_manual_rank
        string author_manual_lastname
        string author_manual_initials
    }
    requisition_items {
        int id PK
        int requisition_id FK
        int resource_id FK
        string requested_resource_name
        int quantity_requested
        string unit_of_measure
        string justification
        string item_status
    }
    resource_transactions {
        int id PK
        int resource_id FK
        string transaction_type
        int quantity_changed
        datetime transaction_date
        string recipient_department
        int issued_by_user_id FK
        string notes
    }
```

## 🔒 Безпека
- Хешування паролів
- Контроль доступу на основі ролей
- Логування важливих операцій

## 📈 Масштабування
- Можливість додавання нових типів ресурсів
- Розширення функціоналу звітності
- Інтеграція з іншими системами 