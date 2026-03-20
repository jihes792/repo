import os
import sqlite3
from datetime import datetime

APP_NAME = "OrderingSystem"


def app_dir():
    if os.name == "nt":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
        p = os.path.join(base, APP_NAME)
    else:
        p = os.path.join(os.path.expanduser("~"), f".{APP_NAME.lower()}")
    os.makedirs(p, exist_ok=True)
    return p


def db_path():
    return os.path.join(app_dir(), "app.db")


def connect():
    con = sqlite3.connect(db_path())
    con.row_factory = sqlite3.Row
    return con


def init_db():
    con = connect()
    cur = con.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS products(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        sku TEXT,
        price REAL NOT NULL DEFAULT 0,
        stock INTEGER NOT NULL DEFAULT 0,
        active INTEGER NOT NULL DEFAULT 1
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS customers(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        phone TEXT,
        address TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS orders(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        customer_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'Draft',
        total REAL NOT NULL DEFAULT 0,
        FOREIGN KEY(customer_id) REFERENCES customers(id)
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS order_items(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        order_id INTEGER NOT NULL,
        product_id INTEGER NOT NULL,
        product_name TEXT NOT NULL,
        sku TEXT,
        qty INTEGER NOT NULL,
        unit_price REAL NOT NULL,
        line_total REAL NOT NULL,
        FOREIGN KEY(order_id) REFERENCES orders(id),
        FOREIGN KEY(product_id) REFERENCES products(id)
    )
    """)

    con.commit()
    con.close()


# ---- Products ----
def list_products():
    con = connect()
    rows = con.execute("SELECT * FROM products WHERE active=1 ORDER BY id DESC").fetchall()
    con.close()
    return rows


def add_product(name, sku, price, stock):
    con = connect()
    con.execute(
        "INSERT INTO products(name, sku, price, stock) VALUES(?,?,?,?)",
        (name, sku, price, stock),
    )
    con.commit()
    con.close()


def update_product(pid, name, sku, price, stock):
    con = connect()
    con.execute(
        "UPDATE products SET name=?, sku=?, price=?, stock=? WHERE id=?",
        (name, sku, price, stock, pid),
    )
    con.commit()
    con.close()


def delete_product(pid):
    con = connect()
    con.execute("UPDATE products SET active=0 WHERE id=?", (pid,))
    con.commit()
    con.close()


# ---- Customers ----
def list_customers():
    con = connect()
    rows = con.execute("SELECT * FROM customers ORDER BY id DESC").fetchall()
    con.close()
    return rows


def add_customer(name, phone, address):
    con = connect()
    con.execute(
        "INSERT INTO customers(name, phone, address) VALUES(?,?,?)",
        (name, phone, address),
    )
    con.commit()
    con.close()


def update_customer(cid, name, phone, address):
    con = connect()
    con.execute(
        "UPDATE customers SET name=?, phone=?, address=? WHERE id=?",
        (name, phone, address, cid),
    )
    con.commit()
    con.close()


def delete_customer(cid):
    con = connect()
    con.execute("DELETE FROM customers WHERE id=?", (cid,))
    con.commit()
    con.close()


# ---- Orders ----
def create_order(customer_id, items, status="Confirmed"):
    """
    items: list of dict {product_id, product_name, sku, qty, unit_price}
    """
    created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    total = 0.0
    normalized = []
    for it in items:
        qty = int(it["qty"])
        unit_price = float(it["unit_price"])
        line_total = qty * unit_price
        total += line_total
        normalized.append({**it, "qty": qty, "unit_price": unit_price, "line_total": line_total})

    con = connect()
    cur = con.cursor()
    cur.execute(
        "INSERT INTO orders(customer_id, created_at, status, total) VALUES(?,?,?,?)",
        (customer_id, created_at, status, total),
    )
    order_id = cur.lastrowid

    for it in normalized:
        cur.execute("""
            INSERT INTO order_items(order_id, product_id, product_name, sku, qty, unit_price, line_total)
            VALUES(?,?,?,?,?,?,?)
        """, (order_id, it["product_id"], it["product_name"], it.get("sku",""), it["qty"], it["unit_price"], it["line_total"]))

        # 扣库存（不想扣也可以删掉这段）
        cur.execute("UPDATE products SET stock = stock - ? WHERE id=?", (it["qty"], it["product_id"]))

    con.commit()
    con.close()
    return order_id


def list_orders():
    con = connect()
    rows = con.execute("""
        SELECT o.*, c.name AS customer_name
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        ORDER BY o.id DESC
    """).fetchall()
    con.close()
    return rows


def get_order_items(order_id):
    con = connect()
    rows = con.execute("SELECT * FROM order_items WHERE order_id=? ORDER BY id ASC", (order_id,)).fetchall()
    con.close()
    return rows


def get_order(order_id):
    con = connect()
    row = con.execute("""
        SELECT o.*, c.name AS customer_name, c.phone AS customer_phone, c.address AS customer_address
        FROM orders o
        JOIN customers c ON c.id = o.customer_id
        WHERE o.id=?
    """, (order_id,)).fetchone()
    con.close()
    return row
