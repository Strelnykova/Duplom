#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Resource Management App (olive‑yellow UI) + звіти, повернення в логін,
та pop‑up попередження (кількість <10 або строк придатності завтра).
"""

import os
import sys
import sqlite3
import shutil
import time
from datetime import datetime, date, timedelta
from typing import Dict, Any

from PIL import Image, ImageQt   # резерв
from PyQt6 import QtCore, QtGui, QtWidgets

# =============================================================
# --------------------------- STYLE ---------------------------
# =============================================================

STYLE_SHEET = """
* { font-family:"Segoe UI",Arial,sans-serif; }

QMainWindow,QDialog { background:#3B5323; color:#FFD700; }
QToolBar,QMenuBar,QStatusBar { background:#3B5323; spacing:8px; }
QLabel { color:#FFD700; }

QPushButton,QToolButton {
    background:#FFD700; color:#000;
    border:1px solid #302B00; border-radius:4px; padding:4px 12px; }
QPushButton:hover,QToolButton:hover  { background:#FFE54A; }
QPushButton:pressed,QToolButton:pressed { background:#FFC107; }

QLineEdit,QSpinBox,QComboBox {
    background:#FFFFFF; color:#000;
    border:1px solid #A0A0A0; border-radius:4px; padding:2px 4px; }

QHeaderView::section {
    background:#556B2F; color:#FFD700; font-weight:bold; border:none; padding:4px; }

QTableView { background:#FFFFFF; alternate-background-color:#F7F7F7; gridline-color:#BFBFBF; }
QTableView::item:selected { background:#B8C65E; color:#000; }

#previewLabel { background:#3B5323; border:2px dashed #FFD700; color:#FFD700; }
"""

# =============================================================
# ------------------------ DATABASE ---------------------------
# =============================================================

DB_NAME = "military_resources.db"

CATEGORIES = [
    "Продукти харчування",
    "Медикаменти",
    "Боєприпаси",
    "Форма",
    "ПММ",
    "Інженерне майно",
    "Засоби зв'язку",
    "Спорядження та захист",
    "Ремонтні засоби та запчастини"
]

def create_connection(db_file=DB_NAME):
    conn = None
    try:
        conn = sqlite3.connect(db_file)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn
    except sqlite3.Error as e:
        print(f"Помилка підключення до БД: {e}")
    return conn

def create_tables(conn):
    if conn is None:
        print("Немає з'єднання з БД")
        return

    try:
        cur = conn.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                role TEXT NOT NULL CHECK(role IN ('admin', 'user'))
            );

            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                parent_id INTEGER,
                FOREIGN KEY (parent_id) REFERENCES categories (id)
            );

            CREATE TABLE IF NOT EXISTS resources (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                category_id INTEGER NOT NULL,
                quantity INTEGER NOT NULL DEFAULT 0,
                unit_of_measure TEXT,
                description TEXT,
                image_path TEXT,
                supplier TEXT,
                phone TEXT,
                origin TEXT,
                arrival_date TEXT,
                cost REAL,
                expiration_date TEXT,
                low_stock_threshold INTEGER DEFAULT 10,
                FOREIGN KEY (category_id) REFERENCES categories (id)
            );

            CREATE TABLE IF NOT EXISTS resource_transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                resource_id INTEGER NOT NULL,
                transaction_type TEXT NOT NULL CHECK(transaction_type IN ('надходження', 'видача', 'списання', 'повернення')),
                quantity_changed INTEGER NOT NULL,
                transaction_date TEXT NOT NULL,
                recipient_department TEXT,
                issued_by_user_id INTEGER,
                notes TEXT,
                FOREIGN KEY (resource_id) REFERENCES resources (id),
                FOREIGN KEY (issued_by_user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS requisitions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_number TEXT UNIQUE NOT NULL,
                created_by_user_id INTEGER NOT NULL,
                department_requesting TEXT,
                creation_date TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'нова' CHECK(status IN ('нова', 'на розгляді', 'схвалено', 'відхилено', 'частково виконано', 'виконано')),
                urgency TEXT DEFAULT 'планова' CHECK(urgency IN ('планова', 'термінова', 'критична')),
                notes TEXT,
                FOREIGN KEY (created_by_user_id) REFERENCES users (id)
            );

            CREATE TABLE IF NOT EXISTS requisition_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requisition_id INTEGER NOT NULL,
                resource_id INTEGER,
                requested_resource_name TEXT NOT NULL,
                quantity_requested INTEGER NOT NULL,
                unit_of_measure TEXT,
                justification TEXT,
                item_status TEXT DEFAULT 'очікує' CHECK(item_status IN ('очікує', 'схвалено', 'замовлено', 'отримано', 'відхилено')),
                FOREIGN KEY (requisition_id) REFERENCES requisitions (id),
                FOREIGN KEY (resource_id) REFERENCES resources (id)
            );
        """)
        conn.commit()
        print("Таблиці успішно створено/перевірено.")

        # Початкове заповнення категорій
        cur.execute("SELECT COUNT(*) FROM categories")
        if cur.fetchone()[0] == 0:
            for cat_name in CATEGORIES:
                cur.execute("INSERT INTO categories (name) VALUES (?)", (cat_name,))
            conn.commit()
            print("Початкові категорії додано.")

        # Початкове заповнення користувачів
        cur.execute("SELECT COUNT(*) FROM users")
        if cur.fetchone()[0] == 0:
            cur.executemany(
                "INSERT INTO users(username, password, role) VALUES(?,?,?)",
                [("admin", "admin", "admin"), ("user", "user", "user")]
            )
            conn.commit()
            print("Початкових користувачів додано.")

    except sqlite3.Error as e:
        print(f"Помилка при створенні таблиць: {e}")

# ---------------- helpers ----------------
validate_user = lambda c,u,p: (
    c.execute(
        "SELECT role FROM users WHERE username=? AND password=?", (u,p)
    ).fetchone() or [None]
)[0]

fetch_resources = lambda c,cat: c.execute(
    """SELECT r.id, r.name, r.quantity, r.description, r.image_path, r.expiration_date 
    FROM resources r 
    JOIN categories c ON r.category_id = c.id 
    WHERE c.name=?""", (cat,)
).fetchall()

def add_resource_db(c,n,q,d,img,cat):
    cat_id = c.execute("SELECT id FROM categories WHERE name=?", (cat,)).fetchone()["id"]
    cur = c.execute(
        """INSERT INTO resources(name,quantity,description,image_path,category_id) 
        VALUES(?,?,?,?,?)""",
        (n,q,d,img,cat_id)
    )
    c.commit()
    return cur.lastrowid

def update_resource_db(c,rid,n,q,d,img):
    c.execute(
        """UPDATE resources 
        SET name=?,quantity=?,description=?,image_path=? 
        WHERE id=?""",
        (n,q,d,img,rid)
    )
    c.commit()

def delete_resource_db(c,rid):
    c.execute("DELETE FROM resource_transactions WHERE resource_id=?", (rid,))
    c.execute("DELETE FROM requisition_items WHERE resource_id=?", (rid,))
    c.execute("DELETE FROM resources WHERE id=?", (rid,))
    c.commit()

def add_purchase_db(c, *t):
    c.execute(
        """INSERT INTO resource_transactions(
            resource_id,transaction_type,quantity_changed,
            recipient_department,issued_by_user_id,transaction_date,notes
        ) VALUES(?,?,?,?,?,?,?)""",
        (t[0], "надходження", t[3], t[1], t[2], 
         datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
         f"Постачальник: {t[1]}, Телефон: {t[2]}, Походження: {t[4]}, Вартість: {t[5]}")
    )
    c.commit()

# =============================================================
# --------------------------- DIALOGS -------------------------
# =============================================================

class LoginDialog(QtWidgets.QDialog):
    def __init__(self, conn):
        super().__init__()
        self.conn = conn
        self.setFixedSize(330, 200)
        self.setWindowTitle("Авторизація")
        layout = QtWidgets.QVBoxLayout(self)
        title = QtWidgets.QLabel("Авторизація")
        title.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        title.setStyleSheet("font-size:18pt; font-weight:bold;")
        layout.addWidget(title)

        form = QtWidgets.QFormLayout()
        self.user = QtWidgets.QLineEdit()
        self.pwd = QtWidgets.QLineEdit()
        self.pwd.setEchoMode(QtWidgets.QLineEdit.EchoMode.Password)
        form.addRow("Логін:", self.user)
        form.addRow("Пароль:", self.pwd)
        layout.addLayout(form)

        btn = QtWidgets.QPushButton("Увійти")
        btn.clicked.connect(self.try_login)
        layout.addWidget(btn, alignment=QtCore.Qt.AlignmentFlag.AlignCenter)
        self.role = None

    def try_login(self):
        self.role = validate_user(self.conn, self.user.text(), self.pwd.text())
        if self.role:
            self.accept()
        else:
            QtWidgets.QMessageBox.warning(self, "Помилка", "Невірний логін або пароль")

class ResourceEditor(QtWidgets.QDialog):
    def __init__(self, conn, cat, data: Dict[str, Any] | None = None):
        super().__init__()
        self.conn, self.cat = conn, cat
        self.data = data or {}
        self.setMinimumWidth(380)
        self.setWindowTitle("Редагувати" if data else "Додати ресурс")
        self.img = self.data.get("image_path", "")

        form = QtWidgets.QFormLayout(self)
        self.name = QtWidgets.QLineEdit(self.data.get("name", ""))
        self.qty = QtWidgets.QSpinBox()
        self.qty.setRange(0, 1_000_000)
        self.qty.setValue(int(self.data.get("quantity", 0)))
        self.desc = QtWidgets.QLineEdit(self.data.get("description", ""))
        img_btn = QtWidgets.QPushButton("Фото")
        img_btn.clicked.connect(self.pick_img)

        form.addRow("Назва:", self.name)
        form.addRow("Кількість:", self.qty)
        form.addRow("Опис:", self.desc)
        form.addRow(img_btn)

        bb = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Ok |
            QtWidgets.QDialogButtonBox.StandardButton.Cancel
        )
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def pick_img(self):
        p, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, "Фото", "", "Images (*.png *.jpg *.jpeg *.bmp *.gif)"
        )
        if p:
            os.makedirs("images", exist_ok=True)
            dst = os.path.join("images", f"img_{int(time.time())}{os.path.splitext(p)[1]}")
            shutil.copy2(p, dst)
            self.img = dst
            QtWidgets.QMessageBox.information(self, "Фото", f"Збережено: {dst}")

    def get(self):
        return {
            "name": self.name.text().strip(),
            "quantity": self.qty.value(),
            "description": self.desc.text().strip(),
            "image_path": self.img
        }

class InfoDialog(QtWidgets.QDialog):
    """Показує та дозволяє редагувати деталі вибраного ресурсу."""
    def __init__(self, conn, rid):
        super().__init__()
        self.conn = conn
        self.rid = rid
        self.setWindowTitle("Деталі ресурсу")
        self.setMinimumWidth(400)

        cur = conn.execute(
            "SELECT supplier,phone,origin,arrival_date,cost,expiration_date "
            "FROM resources WHERE id=?", (rid,)
        )
        row = cur.fetchone()

        form = QtWidgets.QFormLayout(self)
        labels = ["Постачальник", "Телефон", "Звідки", "Дата приходу", "Вартість", "Термін придатності"]
        fields = ['supplier', 'phone', 'origin', 'arrival_date', 'cost', 'expiration_date']
        self.edits: Dict[str, QtWidgets.QLineEdit] = {}
        self.old_values: Dict[str, str] = {}

        for field, lbl in zip(fields, labels):
            val = row[field] if row and row[field] is not None else ""
            edit = QtWidgets.QLineEdit(str(val))
            form.addRow(lbl + ":", edit)
            self.edits[field] = edit
            self.old_values[field] = str(val)

        bb = QtWidgets.QDialogButtonBox()
        save_btn = QtWidgets.QPushButton("Зберегти")
        cancel_btn = QtWidgets.QPushButton("Скасувати")
        bb.addButton(save_btn, QtWidgets.QDialogButtonBox.ButtonRole.AcceptRole)
        bb.addButton(cancel_btn, QtWidgets.QDialogButtonBox.ButtonRole.RejectRole)
        bb.accepted.connect(self.accept)
        bb.rejected.connect(self.reject)
        form.addRow(bb)

    def accept(self):
        sup = self.edits['supplier'].text().strip()
        phone = self.edits['phone'].text().strip()
        origin = self.edits['origin'].text().strip()
        arrival = self.edits['arrival_date'].text().strip()
        cost_str = self.edits['cost'].text().strip()
        exp = self.edits['expiration_date'].text().strip()

        if cost_str:
            try:
                cost_val = float(cost_str)
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'Помилка', 'Вартість повинна бути числом.')
                return
        else:
            cost_val = None

        if arrival:
            try:
                datetime.strptime(arrival, '%Y-%m-%d')
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'Помилка', 'Дата приходу повинна бути у форматі YYYY-MM-DD.')
                return

        if exp:
            try:
                datetime.strptime(exp, '%Y-%m-%d')
            except ValueError:
                QtWidgets.QMessageBox.warning(self, 'Помилка', 'Термін придатності повинен бути у форматі YYYY-MM-DD.')
                return

        self.conn.execute(
            "UPDATE resources SET supplier=?, phone=?, origin=?, arrival_date=?, cost=?, expiration_date=? WHERE id=?",
            (sup, phone, origin,
             arrival if arrival else None,
             cost_val if cost_val is not None else None,
             exp if exp else None,
             self.rid)
        )
        self.conn.commit()

        old_cost_str = self.old_values.get('cost', '')
        old_arrival = self.old_values.get('arrival_date', '')
        try:
            old_cost_val = float(old_cost_str) if old_cost_str != '' else None
        except ValueError:
            old_cost_val = None

        if cost_val is not None and (
            old_cost_val is None or
            abs(cost_val - old_cost_val) > 1e-9 or
            (arrival and arrival != old_arrival)
        ):
            add_purchase_db(self.conn, self.rid, sup, phone, origin, cost_val)

        super().accept()

# =============================================================
# --------------------------- MAIN UI -------------------------
# =============================================================

def row_items(r):
    return [QtGui.QStandardItem(str(r[f])) for f in ("id", "name", "quantity", "description")]

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, conn, role):
        super().__init__()
        self.conn, self.role = conn, role
        self.setWindowTitle("Облік ресурсів")
        self.resize(1280, 720)

        central = QtWidgets.QWidget()
        h = QtWidgets.QHBoxLayout(central)
        h.setContentsMargins(0,0,0,0)
        self.stack = QtWidgets.QStackedWidget()
        h.addWidget(self.stack, 1)

        self.preview = QtWidgets.QLabel("(Попередній)")
        self.preview.setObjectName("previewLabel")
        self.preview.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.preview.setFixedWidth(320)
        h.addWidget(self.preview)
        self.setCentralWidget(central)

        self.models, self.views = {}, {}
        for cat in CATEGORIES:
            view = QtWidgets.QTableView()
            view.setAlternatingRowColors(True)
            view.horizontalHeader().setSectionResizeMode(
                QtWidgets.QHeaderView.ResizeMode.Stretch
            )
            view.setSelectionBehavior(
                QtWidgets.QAbstractItemView.SelectionBehavior.SelectRows
            )
            # Вимикаємо редагування в таблиці:
            view.setEditTriggers(QtWidgets.QAbstractItemView.EditTrigger.NoEditTriggers)

            view.doubleClicked.connect(self.open_info)
            model = QtGui.QStandardItemModel(0, 4)
            model.setHorizontalHeaderLabels(["ID","NAME","QUANTITY","DESCRIPTION"])
            view.setModel(model)
            view.selectionModel().selectionChanged.connect(self.update_preview)

            self.views[cat] = view
            self.models[cat] = model
            self.stack.addWidget(view)

        tb = QtWidgets.QToolBar()
        self.addToolBar(tb)
        tb.addWidget(QtWidgets.QLabel("Пошук:"))
        self.search = QtWidgets.QLineEdit()
        self.search.textChanged.connect(self.filter)
        tb.addWidget(self.search)
        tb.addSeparator()

        self.cat = QtWidgets.QComboBox()
        self.cat.addItems(CATEGORIES)
        self.cat.currentIndexChanged.connect(self.change_cat)
        tb.addWidget(self.cat)

        if role == "admin":
            for txt, slot in [("Фото", self.add), ("Додати", self.add)]:
                act = QtGui.QAction(txt, self)
                act.triggered.connect(slot)
                tb.addAction(act)

        tb.addSeparator()
        info_act = QtGui.QAction("Інфо", self)
        info_act.triggered.connect(self.open_info)
        tb.addAction(info_act)

        for txt, slot in [
            ("Редагувати", self.edit),
            ("Видалити", self.delete),
            ("Звіт", self.export_report),
            ("Аналітика Залишків", self.qty),
            ("Аналітика Витрат", self.cost),
        ]:
            act = QtGui.QAction(txt, self)
            act.triggered.connect(slot)
            tb.addAction(act)

        tb.addSeparator()
        tb.addAction(QtGui.QAction("Вийти", self, triggered=self.logout))

        self.load_all()
        self.change_cat(0)
        self.check_alerts()

    # ---------- data helpers ----------
    def cur_cat(self): return self.cat.currentText()
    def view_model(self):
        return self.views[self.cur_cat()], self.models[self.cur_cat()]

    def load_all(self):
        for c in CATEGORIES:
            m = self.models[c]
            m.removeRows(0, m.rowCount())
            for r in fetch_resources(self.conn, c):
                m.appendRow(row_items(r))

    # ---------- ui slots ----------
    def change_cat(self, _):
        self.stack.setCurrentIndex(self.cat.currentIndex())
        self.filter()

    def filter(self):
        txt = self.search.text().lower()
        view, model = self.view_model()
        for i in range(model.rowCount()):
            hidden = txt not in model.item(i,1).text().lower()
            view.setRowHidden(i, hidden)

    def selected_id(self):
        view, model = self.view_model()
        sel = view.selectionModel().selectedRows()
        if not sel: return None
        return int(model.item(sel[0].row(), 0).text())

    def update_preview(self, *args):
        rid = self.selected_id()
        if not rid:
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText("(Попередній)")
            return
        path = self.conn.execute(
            "SELECT image_path FROM resources WHERE id=?", (rid,)
        ).fetchone()["image_path"]
        if path and os.path.exists(path):
            pix = QtGui.QPixmap(path).scaled(
                self.preview.size(),
                QtCore.Qt.AspectRatioMode.KeepAspectRatio,
                QtCore.Qt.TransformationMode.SmoothTransformation
            )
            self.preview.setPixmap(pix)
            self.preview.setText("")
        else:
            self.preview.setPixmap(QtGui.QPixmap())
            self.preview.setText("(Попередній)")

    # --------- CRUD ------------
    def add(self):
        dlg = ResourceEditor(self.conn, self.cur_cat())
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            d = dlg.get()
            add_resource_db(
                self.conn, d["name"], d["quantity"],
                d["description"], d["image_path"], self.cur_cat()
            )
            self.load_all()
            self.check_alerts()

    def edit(self):
        rid = self.selected_id()
        if rid is None: return
        data = dict(self.conn.execute(
            "SELECT * FROM resources WHERE id=?", (rid,)
        ).fetchone())
        dlg = ResourceEditor(self.conn, data["category"], data)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            d = dlg.get()
            update_resource_db(
                self.conn, rid, d["name"], d["quantity"],
                d["description"], d["image_path"]
            )
            self.load_all()
            self.check_alerts()

    def delete(self):
        rid = self.selected_id()
        if rid is None: return
        if QtWidgets.QMessageBox.question(
            self, "Підтвердження", "Видалити ресурс?"
        ) == QtWidgets.QMessageBox.StandardButton.Yes:
            delete_resource_db(self.conn, rid)
            self.load_all()
            self.check_alerts()

    def open_info(self, *args):
        rid = self.selected_id()
        if rid is None:
            return
        dlg = InfoDialog(self.conn, rid)
        if dlg.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.check_alerts()

    # -------- reporting ----------
    def export_report(self):
        rid = self.selected_id()
        if rid is None:
            QtWidgets.QMessageBox.information(self, "Звіт", "Оберіть ресурс.")
            return
        row = self.conn.execute(
            "SELECT * FROM resources WHERE id=?", (rid,)
        ).fetchone()
        os.makedirs("reports", exist_ok=True)
        fname = os.path.join("reports", f"report_{row['name']}_{int(time.time())}.txt")
        with open(fname, "w", encoding="utf-8") as f:
            for k in row.keys():
                f.write(f"{k}: {row[k]}\n")
        QtWidgets.QMessageBox.information(self, "Звіт", f"Збережено: {fname}")

    # ------- analytics ----------
    def qty(self):
        rows = fetch_resources(self.conn, self.cur_cat())
        text = "\n".join(f"{r['name']}: {r['quantity']}" for r in rows) or "Немає даних"
        QtWidgets.QMessageBox.information(self, "Аналітика залишків", text)

    def cost(self):
        cur = self.conn.execute(
            "SELECT p.cost,p.date FROM purchases p "
            "JOIN resources r ON p.resource_id=r.id WHERE r.category=?",
            (self.cur_cat(),)
        )
        today = date.today()
        week_ago = today - timedelta(days=6)
        sums = {"day":0.0, "week":0.0, "month":0.0}
        for cost, dt in cur.fetchall():
            d = datetime.strptime(dt, "%Y-%m-%d %H:%M:%S").date()
            if d == today: sums["day"] += cost
            if week_ago <= d <= today: sums["week"] += cost
            if d.year == today.year and d.month == today.month: sums["month"] += cost
        QtWidgets.QMessageBox.information(
            self, "Аналітика витрат",
            f"Сьогодні: {sums['day']:.2f} грн\n"
            f"Тиждень: {sums['week']:.2f} грн\n"
            f"Місяць: {sums['month']:.2f} грн"
        )

    # -------- alerts -----------
    def check_alerts(self):
        alerts = []
        tomorrow = date.today() + timedelta(days=1)
        for cat in CATEGORIES:
            for r in self.conn.execute(
                """SELECT r.name, r.quantity, r.expiration_date 
                FROM resources r 
                JOIN categories c ON r.category_id = c.id 
                WHERE c.name = ?""", (cat,)
            ).fetchall():
                if r["quantity"] is not None and r["quantity"] < 10:
                    alerts.append(f"Мало залишилось (<10): {r['name']} ({r['quantity']})")
                if r["expiration_date"]:
                    try:
                        exp = datetime.strptime(r["expiration_date"], "%Y-%m-%d").date()
                        if exp == tomorrow:
                            alerts.append(f"Завтра спливає строк: {r['name']} ({exp})")
                    except ValueError:
                        pass
        if alerts:
            QtWidgets.QMessageBox.warning(self, "Попередження", "\n".join(alerts))

    # ------- logout ----------
    def logout(self):
        self.hide()
        login = LoginDialog(self.conn)
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            self.show()
            self.check_alerts()
        else:
            QtWidgets.QApplication.instance().quit()

# =============================================================
# --------------------------- ENTRY ---------------------------
# =============================================================

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setStyleSheet(STYLE_SHEET)
    conn = create_connection()
    create_tables(conn)
    while True:
        login = LoginDialog(conn)
        if login.exec() == QtWidgets.QDialog.DialogCode.Accepted:
            win = MainWindow(conn, login.role)
            win.show()
            app.exec()
            if not win.isVisible():
                break
        else:
            break

if __name__ == "__main__":
    main()
