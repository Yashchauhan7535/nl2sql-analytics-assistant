import argparse
import csv
import hashlib
import os
import random
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path

TABLE_SCHEMAS = {
    "customers": """
        CREATE TABLE IF NOT EXISTS customers (
            customer_id TEXT PRIMARY KEY,
            customer_unique_id TEXT,
            customer_zip_code_prefix INTEGER,
            customer_city TEXT,
            customer_state TEXT
        );
    """,
    "orders": """
        CREATE TABLE IF NOT EXISTS orders (
            order_id TEXT PRIMARY KEY,
            customer_id TEXT,
            order_status TEXT,
            order_purchase_timestamp TEXT,
            order_approved_at TEXT,
            order_delivered_carrier_date TEXT,
            order_delivered_customer_date TEXT,
            order_estimated_delivery_date TEXT,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id)
        );
    """,
    "order_items": """
        CREATE TABLE IF NOT EXISTS order_items (
            order_id TEXT,
            order_item_id INTEGER,
            product_id TEXT,
            seller_id TEXT,
            shipping_limit_date TEXT,
            price REAL,
            freight_value REAL,
            PRIMARY KEY (order_id, order_item_id),
            FOREIGN KEY (order_id) REFERENCES orders(order_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id),
            FOREIGN KEY (seller_id) REFERENCES sellers(seller_id)
        );
    """,
    "order_payments": """
        CREATE TABLE IF NOT EXISTS order_payments (
            order_id TEXT,
            payment_sequential INTEGER,
            payment_type TEXT,
            payment_installments INTEGER,
            payment_value REAL,
            PRIMARY KEY (order_id, payment_sequential),
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
    """,
    "order_reviews": """
        CREATE TABLE IF NOT EXISTS order_reviews (
            review_id TEXT,
            order_id TEXT,
            review_score INTEGER,
            review_comment_title TEXT,
            review_comment_message TEXT,
            review_creation_date TEXT,
            review_answer_timestamp TEXT,
            FOREIGN KEY (order_id) REFERENCES orders(order_id)
        );
    """,
    "products": """
        CREATE TABLE IF NOT EXISTS products (
            product_id TEXT PRIMARY KEY,
            product_category_name TEXT,
            product_name_lenght INTEGER,
            product_description_lenght INTEGER,
            product_photos_qty INTEGER,
            product_weight_g REAL,
            product_length_cm REAL,
            product_height_cm REAL,
            product_width_cm REAL
        );
    """,
    "sellers": """
        CREATE TABLE IF NOT EXISTS sellers (
            seller_id TEXT PRIMARY KEY,
            seller_zip_code_prefix INTEGER,
            seller_city TEXT,
            seller_state TEXT
        );
    """,
    "geolocation": """
        CREATE TABLE IF NOT EXISTS geolocation (
            geolocation_zip_code_prefix INTEGER,
            geolocation_lat REAL,
            geolocation_lng REAL,
            geolocation_city TEXT,
            geolocation_state TEXT
        );
    """,
    "product_category_name_translation": """
        CREATE TABLE IF NOT EXISTS product_category_name_translation (
            product_category_name TEXT PRIMARY KEY,
            product_category_name_english TEXT
        );
    """
}

INDEX_STATEMENTS = [
    "CREATE INDEX IF NOT EXISTS idx_orders_customer ON orders(customer_id);",
    "CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(order_status);",
    "CREATE INDEX IF NOT EXISTS idx_orders_purchase ON orders(order_purchase_timestamp);",
    "CREATE INDEX IF NOT EXISTS idx_order_items_order ON order_items(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_order_items_product ON order_items(product_id);",
    "CREATE INDEX IF NOT EXISTS idx_order_items_seller ON order_items(seller_id);",
    "CREATE INDEX IF NOT EXISTS idx_order_payments_order ON order_payments(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_order_reviews_order ON order_reviews(order_id);",
    "CREATE INDEX IF NOT EXISTS idx_products_category ON products(product_category_name);"
]

CSV_MAPPINGS = {
    "customers": "olist_customers_dataset.csv",
    "orders": "olist_orders_dataset.csv",
    "order_items": "olist_order_items_dataset.csv",
    "order_payments": "olist_order_payments_dataset.csv",
    "order_reviews": "olist_order_reviews_dataset.csv",
    "products": "olist_products_dataset.csv",
    "sellers": "olist_sellers_dataset.csv",
    "geolocation": "olist_geolocation_dataset.csv",
    "product_category_name_translation": "product_category_name_translation.csv"
}

CATEGORIES = [
    ("beleza_saude", "health_beauty"),
    ("cama_mesa_banho", "bed_bath_table"),
    ("esporte_lazer", "sports_leisure"),
    ("informatica_acessorios", "computers_accessories"),
    ("moveis_decoracao", "furniture_decor"),
    ("relogios_presentes", "watches_gifts"),
    ("telefonia", "telephony"),
    ("automotivo", "auto"),
    ("brinquedos", "toys"),
    ("utilidades_domesticas", "housewares")
]

LOCATIONS = [
    (1000, "sao paulo", "SP", -23.5505, -46.6333),
    (20000, "rio de janeiro", "RJ", -22.9068, -43.1729),
    (30000, "belo horizonte", "MG", -19.9167, -43.9345),
    (80000, "curitiba", "PR", -25.4284, -49.2733),
    (90000, "porto alegre", "RS", -30.0346, -51.2177),
    (40000, "salvador", "BA", -12.9777, -38.5016),
    (50000, "recife", "PE", -8.0476, -34.8770),
    (70000, "brasilia", "DF", -15.7975, -47.8919)
]

def make_id(prefix: str, idx: int) -> str:
    return hashlib.md5(f"{prefix}-{idx}".encode()).hexdigest()[:16]

def load_from_csv(conn: sqlite3.Connection, csv_dir: Path) -> bool:
    found_any = False
    for table, filename in CSV_MAPPINGS.items():
        file_path = csv_dir / filename
        if not file_path.exists():
            continue
        found_any = True
        with open(file_path, "r", encoding="utf-8-sig") as f:
            reader = csv.reader(f)
            headers = next(reader, None)
            if not headers:
                continue
            placeholders = ", ".join(["?"] * len(headers))
            cols = ", ".join(headers)
            cursor = conn.cursor()
            cursor.execute(f"DELETE FROM {table};")
            cursor.executemany(f"INSERT OR REPLACE INTO {table} ({cols}) VALUES ({placeholders});", reader)
    return found_any

def seed_synthetic_data(conn: sqlite3.Connection):
    cursor = conn.cursor()
    rng = random.Random(42)

    for cat_pt, cat_en in CATEGORIES:
        cursor.execute(
            "INSERT OR REPLACE INTO product_category_name_translation VALUES (?, ?);",
            (cat_pt, cat_en)
        )

    for zip_prefix, city, state, lat, lng in LOCATIONS:
        cursor.execute(
            "INSERT OR REPLACE INTO geolocation VALUES (?, ?, ?, ?, ?);",
            (zip_prefix, lat, lng, city, state)
        )

    products = []
    for i in range(120):
        pid = make_id("prod", i)
        cat_pt, _ = CATEGORIES[i % len(CATEGORIES)]
        products.append(pid)
        cursor.execute(
            """INSERT OR REPLACE INTO products VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                pid,
                cat_pt,
                30 + (i % 20),
                150 + (i % 300),
                1 + (i % 5),
                200.0 + (i * 15),
                15.0 + (i % 30),
                10.0 + (i % 20),
                12.0 + (i % 25)
            )
        )

    sellers = []
    for i in range(40):
        sid = make_id("seller", i)
        loc = LOCATIONS[i % len(LOCATIONS)]
        sellers.append(sid)
        cursor.execute(
            "INSERT OR REPLACE INTO sellers VALUES (?, ?, ?, ?);",
            (sid, loc[0], loc[1], loc[2])
        )

    customers = []
    for i in range(300):
        cid = make_id("cust", i)
        uid = make_id("user", i % 220)
        loc = LOCATIONS[i % len(LOCATIONS)]
        customers.append(cid)
        cursor.execute(
            "INSERT OR REPLACE INTO customers VALUES (?, ?, ?, ?, ?);",
            (cid, uid, loc[0], loc[1], loc[2])
        )

    start_date = datetime(2017, 1, 1, 9, 0, 0)
    statuses = ["delivered", "delivered", "delivered", "delivered", "delivered", "shipped", "canceled"]
    pay_types = ["credit_card", "credit_card", "boleto", "voucher", "debit_card"]

    review_titles = [
        "Otimo produto", "Muito bom", "Recomendo", "Chegou antes do prazo",
        "Pessimo", "Nao gostei", "Produto com defeito", "Excelente atendimento"
    ]

    for i in range(850):
        oid = make_id("order", i)
        cid = customers[i % len(customers)]
        status = statuses[i % len(statuses)]

        days_offset = (i * 1.8) % 650
        purchase_dt = start_date + timedelta(days=days_offset, hours=(i * 3) % 24, minutes=(i * 7) % 60)
        approved_dt = purchase_dt + timedelta(hours=2)
        carrier_dt = purchase_dt + timedelta(days=2) if status in ["delivered", "shipped"] else None
        delivered_dt = purchase_dt + timedelta(days=7 + (i % 10)) if status == "delivered" else None
        estimated_dt = purchase_dt + timedelta(days=15)

        cursor.execute(
            """INSERT OR REPLACE INTO orders VALUES (?, ?, ?, ?, ?, ?, ?, ?);""",
            (
                oid,
                cid,
                status,
                purchase_dt.strftime("%Y-%m-%d %H:%M:%S"),
                approved_dt.strftime("%Y-%m-%d %H:%M:%S") if approved_dt else None,
                carrier_dt.strftime("%Y-%m-%d %H:%M:%S") if carrier_dt else None,
                delivered_dt.strftime("%Y-%m-%d %H:%M:%S") if delivered_dt else None,
                estimated_dt.strftime("%Y-%m-%d %H:%M:%S")
            )
        )

        item_count = 1 if (i % 4 != 0) else (2 if (i % 8 != 0) else 3)
        order_total = 0.0

        for item_idx in range(1, item_count + 1):
            pid = products[(i + item_idx) % len(products)]
            sid = sellers[(i * 2 + item_idx) % len(sellers)]
            price = round(25.0 + ((i * 7 + item_idx * 13) % 450) + (i % 5) * 0.5, 2)
            freight = round(10.0 + ((i + item_idx) % 25) + 0.45, 2)
            shipping_limit = (purchase_dt + timedelta(days=5)).strftime("%Y-%m-%d %H:%M:%S")

            cursor.execute(
                """INSERT OR REPLACE INTO order_items VALUES (?, ?, ?, ?, ?, ?, ?);""",
                (oid, item_idx, pid, sid, shipping_limit, price, freight)
            )
            order_total += price + freight

        ptype = pay_types[i % len(pay_types)]
        installments = 1 if ptype != "credit_card" else ((i % 10) + 1)
        cursor.execute(
            """INSERT OR REPLACE INTO order_payments VALUES (?, ?, ?, ?, ?);""",
            (oid, 1, ptype, installments, round(order_total, 2))
        )

        if status == "delivered":
            rid = make_id("rev", i)
            score = 5 if (i % 5 == 0 or i % 3 == 0) else (4 if i % 2 == 0 else (1 if i % 7 == 0 else 3))
            rtitle = review_titles[i % len(review_titles)]
            rmsg = f"Feedback referente ao pedido {oid} recebido com sucesso."
            r_create = (delivered_dt + timedelta(days=1)).strftime("%Y-%m-%d %H:%M:%S")
            r_answer = (delivered_dt + timedelta(days=2)).strftime("%Y-%m-%d %H:%M:%S")
            cursor.execute(
                """INSERT OR REPLACE INTO order_reviews VALUES (?, ?, ?, ?, ?, ?, ?);""",
                (rid, oid, score, rtitle, rmsg, r_create, r_answer)
            )

def setup_database(db_path: str = "olist.db", csv_dir: str = None):
    db_file = Path(db_path)
    if db_file.exists():
        db_file.unlink()

    conn = sqlite3.connect(db_file)
    cursor = conn.cursor()

    for table_name, schema_sql in TABLE_SCHEMAS.items():
        cursor.execute(schema_sql)

    csv_loaded = False
    if csv_dir and Path(csv_dir).exists():
        csv_loaded = load_from_csv(conn, Path(csv_dir))

    if not csv_loaded:
        seed_synthetic_data(conn)

    for idx_sql in INDEX_STATEMENTS:
        cursor.execute(idx_sql)

    conn.commit()
    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--db-path", default="olist.db")
    parser.add_argument("--csv-dir", default=None)
    args = parser.parse_args()
    setup_database(db_path=args.db_path, csv_dir=args.csv_dir)
