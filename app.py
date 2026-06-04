import os
import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, date

import pandas as pd
import streamlit as st
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


st.set_page_config(
    page_title="Fabrika Satınalma Sistemi",
    layout="wide"
)

st.title("Fabrika Satınalma Talep ve Onay Yönetim Sistemi")


# PostgreSQL bağlantısı
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)


APPROVAL_STEPS = [
    "Departman Yöneticisi",
    "Satınalma",
    "Finans",
    "Genel Müdür / Yönetim"
]
ALL_MENUS = [
    "Talep Oluştur",
    "Talep Listesi",
    "Onay Ekranı",
    "Teklif Girişi",
    "Siparişe Dönüştür",
    "Mal Kabul",
    "Fatura Kontrolü",
    "Dashboard",
    "Admin Paneli"
]

DEFAULT_OPEN_MENUS = [
    "Talep Oluştur",
    "Talep Listesi"
]

def ensure_tables():
    create_purchase_requests_table = """
    CREATE TABLE IF NOT EXISTS purchase_requests (
        request_id SERIAL PRIMARY KEY,

        department VARCHAR(100) NOT NULL,
        requester_name VARCHAR(100) NOT NULL,
        item_name VARCHAR(150) NOT NULL,
        category VARCHAR(100) NOT NULL,

        quantity NUMERIC(12,2) NOT NULL,
        unit VARCHAR(50) NOT NULL,

        estimated_unit_price NUMERIC(12,2) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        exchange_rate NUMERIC(12,4) NOT NULL,

        total_amount_original NUMERIC(14,2) NOT NULL,
        total_amount_tl NUMERIC(14,2) NOT NULL,

        urgency VARCHAR(50) NOT NULL,
        priority VARCHAR(50) NOT NULL,

        approval_flow TEXT NOT NULL,
        required_approval_count INTEGER NOT NULL,
        current_approval_step INTEGER NOT NULL,
        next_approval_role VARCHAR(100),

        sla_due_at TIMESTAMP NOT NULL,
        required_date DATE NOT NULL,

        status VARCHAR(100) NOT NULL,
        description TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_goods_receipts_table = """
    CREATE TABLE IF NOT EXISTS goods_receipts (
        receipt_id SERIAL PRIMARY KEY,

        order_id INTEGER NOT NULL REFERENCES purchase_orders(order_id),
        request_id INTEGER NOT NULL REFERENCES purchase_requests(request_id),

        supplier_name VARCHAR(150) NOT NULL,
        item_name VARCHAR(150) NOT NULL,

        ordered_quantity NUMERIC(12,2) NOT NULL,
        received_quantity NUMERIC(12,2) NOT NULL,
        unit VARCHAR(50) NOT NULL,

        receipt_status VARCHAR(100) NOT NULL,
        warehouse_user VARCHAR(100) NOT NULL,
        receipt_note TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_invoice_controls_table = """
    CREATE TABLE IF NOT EXISTS invoice_controls (
        invoice_control_id SERIAL PRIMARY KEY,

        request_id INTEGER NOT NULL REFERENCES purchase_requests(request_id),
        order_id INTEGER NOT NULL REFERENCES purchase_orders(order_id),

        invoice_no VARCHAR(100) NOT NULL,
        invoice_date DATE NOT NULL,

        invoice_amount_original NUMERIC(14,2) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        exchange_rate NUMERIC(12,4) NOT NULL,
        invoice_amount_tl NUMERIC(14,2) NOT NULL,

        order_amount_tl NUMERIC(14,2) NOT NULL,
        amount_difference NUMERIC(14,2) NOT NULL,

        decision VARCHAR(50) NOT NULL,
        accountant_name VARCHAR(100) NOT NULL,
        invoice_note TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_app_users_table = """
    CREATE TABLE IF NOT EXISTS app_users (
        user_id SERIAL PRIMARY KEY,

        username VARCHAR(50),
        password_salt TEXT,
        password_hash TEXT,

        full_name VARCHAR(100) NOT NULL,
        email VARCHAR(150),
        department VARCHAR(100),
        role VARCHAR(100) DEFAULT 'Talep Eden Kullanıcı',

        is_admin BOOLEAN DEFAULT FALSE,
        is_active BOOLEAN DEFAULT TRUE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    alter_app_users_table = """
    ALTER TABLE app_users
        ADD COLUMN IF NOT EXISTS username VARCHAR(50),
        ADD COLUMN IF NOT EXISTS password_salt TEXT,
        ADD COLUMN IF NOT EXISTS password_hash TEXT,
        ADD COLUMN IF NOT EXISTS is_admin BOOLEAN DEFAULT FALSE;
    """

    create_unique_username_index = """
    CREATE UNIQUE INDEX IF NOT EXISTS idx_app_users_username
    ON app_users(username)
    WHERE username IS NOT NULL;
    """

    create_user_permissions_table = """
    CREATE TABLE IF NOT EXISTS user_permissions (
        permission_id SERIAL PRIMARY KEY,

        user_id INTEGER NOT NULL REFERENCES app_users(user_id) ON DELETE CASCADE,
        menu_name VARCHAR(100) NOT NULL,
        can_access BOOLEAN DEFAULT TRUE,

        UNIQUE(user_id, menu_name)
    );
    """
    create_approval_history_table = """
    CREATE TABLE IF NOT EXISTS approval_history (
        approval_id SERIAL PRIMARY KEY,

        request_id INTEGER NOT NULL REFERENCES purchase_requests(request_id),

        approval_step INTEGER NOT NULL,
        approval_role VARCHAR(100) NOT NULL,
        approver_name VARCHAR(100) NOT NULL,

        decision VARCHAR(50) NOT NULL,
        comment TEXT,

        approved_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_supplier_offers_table = """
    CREATE TABLE IF NOT EXISTS supplier_offers (
        offer_id SERIAL PRIMARY KEY,

        request_id INTEGER NOT NULL REFERENCES purchase_requests(request_id),

        supplier_name VARCHAR(150) NOT NULL,
        supplier_contact VARCHAR(150),

        offer_unit_price NUMERIC(14,2) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        exchange_rate NUMERIC(12,4) NOT NULL,

        offer_total_original NUMERIC(14,2) NOT NULL,
        offer_total_tl NUMERIC(14,2) NOT NULL,

        delivery_days INTEGER NOT NULL,
        payment_term VARCHAR(100),
        offer_note TEXT,

        is_selected BOOLEAN DEFAULT FALSE,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    create_purchase_orders_table = """
    CREATE TABLE IF NOT EXISTS purchase_orders (
        order_id SERIAL PRIMARY KEY,

        request_id INTEGER NOT NULL REFERENCES purchase_requests(request_id),
        offer_id INTEGER NOT NULL REFERENCES supplier_offers(offer_id),

        supplier_name VARCHAR(150) NOT NULL,
        item_name VARCHAR(150) NOT NULL,

        quantity NUMERIC(12,2) NOT NULL,
        unit VARCHAR(50) NOT NULL,

        order_amount_original NUMERIC(14,2) NOT NULL,
        currency VARCHAR(10) NOT NULL,
        order_amount_tl NUMERIC(14,2) NOT NULL,

        delivery_days INTEGER NOT NULL,
        expected_delivery_date DATE NOT NULL,

        order_status VARCHAR(100) NOT NULL,
        order_note TEXT,

        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    with engine.begin() as connection:
        connection.execute(text(create_purchase_requests_table))
        connection.execute(text(create_approval_history_table))
        connection.execute(text(create_supplier_offers_table))
        connection.execute(text(create_purchase_orders_table))
        connection.execute(text(create_goods_receipts_table))
        connection.execute(text(create_invoice_controls_table))

        connection.execute(text(create_app_users_table))
        connection.execute(text(alter_app_users_table))
        connection.execute(text(create_unique_username_index))
        connection.execute(text(create_user_permissions_table))

def hash_password(password, salt=None):
    if salt is None:
        salt = secrets.token_hex(16)

    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        100000
    ).hex()

    return salt, password_hash


def verify_password(password, salt, stored_hash):
    if not salt or not stored_hash:
        return False

    _, password_hash = hash_password(password, salt)

    return hmac.compare_digest(password_hash, stored_hash)


def seed_admin_user():
    admin_username = "itadmin"
    admin_password = "Admin123!"

    check_query = """
    SELECT COUNT(*)
    FROM app_users
    WHERE username = :username;
    """

    insert_query = """
    INSERT INTO app_users (
        username,
        password_salt,
        password_hash,
        full_name,
        email,
        department,
        role,
        is_admin,
        is_active
    )
    VALUES (
        :username,
        :password_salt,
        :password_hash,
        :full_name,
        :email,
        :department,
        :role,
        :is_admin,
        :is_active
    );
    """

    salt, password_hash = hash_password(admin_password)

    admin_data = {
        "username": admin_username,
        "password_salt": salt,
        "password_hash": password_hash,
        "full_name": "IT Admin",
        "email": "itadmin@firma.com",
        "department": "Bilgi İşlem",
        "role": "Admin",
        "is_admin": True,
        "is_active": True
    }

    with engine.begin() as connection:
        result = connection.execute(
            text(check_query),
            {"username": admin_username}
        )

        admin_exists = result.scalar()

        if admin_exists == 0:
            connection.execute(text(insert_query), admin_data)


def get_user_by_username(username):
    query = """
    SELECT
        user_id,
        username,
        password_salt,
        password_hash,
        full_name,
        email,
        department,
        role,
        is_admin,
        is_active
    FROM app_users
    WHERE username = :username;
    """

    with engine.begin() as connection:
        row = connection.execute(
            text(query),
            {"username": username}
        ).mappings().first()

    if row:
        return dict(row)

    return None


def load_all_users_from_db():
    query = """
    SELECT
        user_id,
        username,
        full_name,
        email,
        department,
        role,
        is_admin,
        is_active,
        created_at
    FROM app_users
    ORDER BY user_id DESC;
    """

    return pd.read_sql(text(query), engine)


def set_user_permissions(connection, user_id, selected_menus):
    delete_query = """
    DELETE FROM user_permissions
    WHERE user_id = :user_id;
    """

    insert_permission_query = """
    INSERT INTO user_permissions (
        user_id,
        menu_name,
        can_access
    )
    VALUES (
        :user_id,
        :menu_name,
        TRUE
    )
    ON CONFLICT (user_id, menu_name)
    DO UPDATE SET can_access = TRUE;
    """

    connection.execute(
        text(delete_query),
        {"user_id": user_id}
    )

    for menu_name in selected_menus:
        connection.execute(
            text(insert_permission_query),
            {
                "user_id": user_id,
                "menu_name": menu_name
            }
        )


def insert_app_user_to_db(data, selected_menus):
    salt, password_hash = hash_password(data["password"])

    insert_user_query = """
    INSERT INTO app_users (
        username,
        password_salt,
        password_hash,
        full_name,
        email,
        department,
        role,
        is_admin,
        is_active
    )
    VALUES (
        :username,
        :password_salt,
        :password_hash,
        :full_name,
        :email,
        :department,
        :role,
        :is_admin,
        :is_active
    )
    RETURNING user_id;
    """

    user_data = {
        "username": data["username"],
        "password_salt": salt,
        "password_hash": password_hash,
        "full_name": data["full_name"],
        "email": data["email"],
        "department": data["department"],
        "role": data["role"],
        "is_admin": data["is_admin"],
        "is_active": data["is_active"]
    }

    with engine.begin() as connection:
        result = connection.execute(text(insert_user_query), user_data)
        new_user_id = result.scalar()

        set_user_permissions(connection, new_user_id, selected_menus)


def update_user_permissions(user_id, selected_menus):
    with engine.begin() as connection:
        set_user_permissions(connection, user_id, selected_menus)


def load_user_permissions(user_id):
    query = """
    SELECT menu_name
    FROM user_permissions
    WHERE user_id = :user_id
      AND can_access = TRUE;
    """

    df = pd.read_sql(
        text(query),
        engine,
        params={"user_id": user_id}
    )

    if df.empty:
        return []

    return df["menu_name"].tolist()


def user_can_access_menu(user_id, is_admin, menu_name):
    if is_admin:
        return True

    if menu_name in DEFAULT_OPEN_MENUS:
        return True

    if menu_name == "Admin Paneli":
        return False

    query = """
    SELECT COUNT(*)
    FROM user_permissions
    WHERE user_id = :user_id
      AND menu_name = :menu_name
      AND can_access = TRUE;
    """

    with engine.begin() as connection:
        result = connection.execute(
            text(query),
            {
                "user_id": user_id,
                "menu_name": menu_name
            }
        )

        permission_count = result.scalar()

    return permission_count > 0


def calculate_approval_flow(total_amount_tl):
    if total_amount_tl <= 5000:
        required_approval_count = 1
        approval_level_text = "1 Seviye Onay - Departman Yöneticisi"

    elif total_amount_tl <= 25000:
        required_approval_count = 2
        approval_level_text = "2 Seviye Onay - Departman Yöneticisi + Satınalma"

    elif total_amount_tl <= 100000:
        required_approval_count = 3
        approval_level_text = "3 Seviye Onay - Departman Yöneticisi + Satınalma + Finans"

    else:
        required_approval_count = 4
        approval_level_text = "4 Seviye Onay - Departman Yöneticisi + Satınalma + Finans + Genel Müdür / Yönetim"

    return required_approval_count, approval_level_text


def calculate_priority_and_sla(urgency, category):
    if urgency == "Kritik":
        priority = "Kritik"
        sla_due_at = datetime.now() + timedelta(days=1)

    elif urgency == "Yüksek":
        priority = "Yüksek"
        sla_due_at = datetime.now() + timedelta(days=3)

    elif category in ["Hammadde", "Yedek Parça"]:
        priority = "Yüksek"
        sla_due_at = datetime.now() + timedelta(days=3)

    elif urgency == "Düşük":
        priority = "Düşük"
        sla_due_at = datetime.now() + timedelta(days=14)

    else:
        priority = "Normal"
        sla_due_at = datetime.now() + timedelta(days=7)

    return priority, sla_due_at


def insert_purchase_request_to_db(data):
    insert_query = """
    INSERT INTO purchase_requests (
        department,
        requester_name,
        item_name,
        category,
        quantity,
        unit,
        estimated_unit_price,
        currency,
        exchange_rate,
        total_amount_original,
        total_amount_tl,
        urgency,
        priority,
        approval_flow,
        required_approval_count,
        current_approval_step,
        next_approval_role,
        sla_due_at,
        required_date,
        status,
        description
    )
    VALUES (
        :department,
        :requester_name,
        :item_name,
        :category,
        :quantity,
        :unit,
        :estimated_unit_price,
        :currency,
        :exchange_rate,
        :total_amount_original,
        :total_amount_tl,
        :urgency,
        :priority,
        :approval_flow,
        :required_approval_count,
        :current_approval_step,
        :next_approval_role,
        :sla_due_at,
        :required_date,
        :status,
        :description
    );
    """

    with engine.begin() as connection:
        connection.execute(text(insert_query), data)


def load_purchase_requests_from_db():
    query = """
    SELECT
        request_id,
        department,
        requester_name,
        item_name,
        category,
        quantity,
        unit,
        estimated_unit_price,
        currency,
        exchange_rate,
        total_amount_original,
        total_amount_tl,
        urgency,
        priority,
        approval_flow,
        required_approval_count,
        current_approval_step,
        next_approval_role,
        sla_due_at,
        required_date,
        status,
        description,
        created_at,
        updated_at
    FROM purchase_requests
    ORDER BY request_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_waiting_approval_requests_from_db(current_user_role, current_user_department, is_admin):
    if is_admin:
        query = """
        SELECT
            request_id,
            department,
            requester_name,
            item_name,
            category,
            quantity,
            unit,
            total_amount_original,
            currency,
            total_amount_tl,
            urgency,
            priority,
            approval_flow,
            required_approval_count,
            current_approval_step,
            next_approval_role,
            sla_due_at,
            required_date,
            status,
            description,
            created_at
        FROM purchase_requests
        WHERE status LIKE :status_pattern
        ORDER BY request_id DESC;
        """

        params = {
            "status_pattern": "%Onayı Bekliyor"
        }

    elif current_user_role == "Departman Yöneticisi":
        query = """
        SELECT
            request_id,
            department,
            requester_name,
            item_name,
            category,
            quantity,
            unit,
            total_amount_original,
            currency,
            total_amount_tl,
            urgency,
            priority,
            approval_flow,
            required_approval_count,
            current_approval_step,
            next_approval_role,
            sla_due_at,
            required_date,
            status,
            description,
            created_at
        FROM purchase_requests
        WHERE next_approval_role = :current_user_role
          AND department = :current_user_department
          AND status LIKE :status_pattern
        ORDER BY request_id DESC;
        """

        params = {
            "current_user_role": current_user_role,
            "current_user_department": current_user_department,
            "status_pattern": "%Onayı Bekliyor"
        }

    else:
        query = """
        SELECT
            request_id,
            department,
            requester_name,
            item_name,
            category,
            quantity,
            unit,
            total_amount_original,
            currency,
            total_amount_tl,
            urgency,
            priority,
            approval_flow,
            required_approval_count,
            current_approval_step,
            next_approval_role,
            sla_due_at,
            required_date,
            status,
            description,
            created_at
        FROM purchase_requests
        WHERE next_approval_role = :current_user_role
          AND status LIKE :status_pattern
        ORDER BY request_id DESC;
        """

        params = {
            "current_user_role": current_user_role,
            "status_pattern": "%Onayı Bekliyor"
        }

    return pd.read_sql(
        text(query),
        engine,
        params=params
    )


def insert_approval_history_to_db(data):
    insert_query = """
    INSERT INTO approval_history (
        request_id,
        approval_step,
        approval_role,
        approver_name,
        decision,
        comment
    )
    VALUES (
        :request_id,
        :approval_step,
        :approval_role,
        :approver_name,
        :decision,
        :comment
    );
    """

    with engine.begin() as connection:
        connection.execute(text(insert_query), data)


def update_request_after_approval(request_id, current_step, required_count, decision):
    if decision == "Reddedildi":
        update_query = """
        UPDATE purchase_requests
        SET
            status = 'Reddedildi',
            next_approval_role = '-',
            updated_at = CURRENT_TIMESTAMP
        WHERE request_id = :request_id;
        """

        params = {
            "request_id": request_id
        }

    else:
        if current_step >= required_count:
            update_query = """
            UPDATE purchase_requests
            SET
                status = 'Teklif Toplanıyor',
                next_approval_role = '-',
                updated_at = CURRENT_TIMESTAMP
            WHERE request_id = :request_id;
            """

            params = {
                "request_id": request_id
            }

        else:
            next_step = current_step + 1
            next_role = APPROVAL_STEPS[next_step - 1]
            next_status = f"{next_role} Onayı Bekliyor"

            update_query = """
            UPDATE purchase_requests
            SET
                current_approval_step = :next_step,
                next_approval_role = :next_role,
                status = :next_status,
                updated_at = CURRENT_TIMESTAMP
            WHERE request_id = :request_id;
            """

            params = {
                "request_id": request_id,
                "next_step": next_step,
                "next_role": next_role,
                "next_status": next_status
            }

    with engine.begin() as connection:
        connection.execute(text(update_query), params)


def load_approval_history_from_db(request_id):
    query = """
    SELECT
        approval_step,
        approval_role,
        approver_name,
        decision,
        comment,
        approved_at
    FROM approval_history
    WHERE request_id = :request_id
    ORDER BY approval_step ASC, approved_at ASC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"request_id": request_id}
    )


def load_offer_ready_requests_from_db():
    query = """
    SELECT
        request_id,
        department,
        requester_name,
        item_name,
        category,
        quantity,
        unit,
        total_amount_original,
        currency,
        total_amount_tl,
        required_date,
        status
    FROM purchase_requests
    WHERE status = :status
    ORDER BY request_id DESC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"status": "Teklif Toplanıyor"}
    )


def insert_supplier_offer_to_db(data):
    insert_query = """
    INSERT INTO supplier_offers (
        request_id,
        supplier_name,
        supplier_contact,
        offer_unit_price,
        currency,
        exchange_rate,
        offer_total_original,
        offer_total_tl,
        delivery_days,
        payment_term,
        offer_note
    )
    VALUES (
        :request_id,
        :supplier_name,
        :supplier_contact,
        :offer_unit_price,
        :currency,
        :exchange_rate,
        :offer_total_original,
        :offer_total_tl,
        :delivery_days,
        :payment_term,
        :offer_note
    );
    """

    with engine.begin() as connection:
        connection.execute(text(insert_query), data)


def load_supplier_offers_by_request_id(request_id):
    query = """
    SELECT
        offer_id,
        request_id,
        supplier_name,
        supplier_contact,
        offer_unit_price,
        currency,
        exchange_rate,
        offer_total_original,
        offer_total_tl,
        delivery_days,
        payment_term,
        offer_note,
        is_selected,
        created_at
    FROM supplier_offers
    WHERE request_id = :request_id
    ORDER BY offer_total_tl ASC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"request_id": request_id}
    )


def load_requests_with_offers_from_db():
    query = """
    SELECT DISTINCT
        pr.request_id,
        pr.department,
        pr.requester_name,
        pr.item_name,
        pr.category,
        pr.quantity,
        pr.unit,
        pr.total_amount_tl,
        pr.status
    FROM purchase_requests pr
    INNER JOIN supplier_offers so
        ON pr.request_id = so.request_id
    WHERE pr.status = :status
    ORDER BY pr.request_id DESC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"status": "Teklif Toplanıyor"}
    )


def load_order_offers_by_request_id(request_id):
    query = """
    SELECT
        offer_id,
        request_id,
        supplier_name,
        supplier_contact,
        offer_unit_price,
        currency,
        exchange_rate,
        offer_total_original,
        offer_total_tl,
        delivery_days,
        payment_term,
        offer_note,
        is_selected,
        created_at
    FROM supplier_offers
    WHERE request_id = :request_id
    ORDER BY offer_total_tl ASC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"request_id": request_id}
    )


def create_purchase_order_from_offer(order_data):
    insert_order_query = """
    INSERT INTO purchase_orders (
        request_id,
        offer_id,
        supplier_name,
        item_name,
        quantity,
        unit,
        order_amount_original,
        currency,
        order_amount_tl,
        delivery_days,
        expected_delivery_date,
        order_status,
        order_note
    )
    VALUES (
        :request_id,
        :offer_id,
        :supplier_name,
        :item_name,
        :quantity,
        :unit,
        :order_amount_original,
        :currency,
        :order_amount_tl,
        :delivery_days,
        :expected_delivery_date,
        :order_status,
        :order_note
    );
    """

    reset_offers_query = """
    UPDATE supplier_offers
    SET is_selected = FALSE
    WHERE request_id = :request_id;
    """

    select_offer_query = """
    UPDATE supplier_offers
    SET is_selected = TRUE
    WHERE offer_id = :offer_id;
    """

    update_request_query = """
    UPDATE purchase_requests
    SET
        status = 'Mal Kabul Bekliyor',
        next_approval_role = '-',
        updated_at = CURRENT_TIMESTAMP
    WHERE request_id = :request_id;
    """

    with engine.begin() as connection:
        connection.execute(
            text(reset_offers_query),
            {"request_id": order_data["request_id"]}
        )

        connection.execute(
            text(select_offer_query),
            {"offer_id": order_data["offer_id"]}
        )

        connection.execute(
            text(insert_order_query),
            order_data
        )

        connection.execute(
            text(update_request_query),
            {"request_id": order_data["request_id"]}
        )


def load_purchase_orders_from_db():
    query = """
    SELECT
        order_id,
        request_id,
        offer_id,
        supplier_name,
        item_name,
        quantity,
        unit,
        order_amount_original,
        currency,
        order_amount_tl,
        delivery_days,
        expected_delivery_date,
        order_status,
        order_note,
        created_at
    FROM purchase_orders
    ORDER BY order_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_waiting_receipt_orders_from_db():
    query = """
    SELECT
        order_id,
        request_id,
        offer_id,
        supplier_name,
        item_name,
        quantity,
        unit,
        order_amount_original,
        currency,
        order_amount_tl,
        delivery_days,
        expected_delivery_date,
        order_status,
        order_note,
        created_at
    FROM purchase_orders
    WHERE order_status = :order_status
    ORDER BY order_id DESC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"order_status": "Mal Kabul Bekliyor"}
    )


def insert_goods_receipt_to_db(data):
    insert_query = """
    INSERT INTO goods_receipts (
        order_id,
        request_id,
        supplier_name,
        item_name,
        ordered_quantity,
        received_quantity,
        unit,
        receipt_status,
        warehouse_user,
        receipt_note
    )
    VALUES (
        :order_id,
        :request_id,
        :supplier_name,
        :item_name,
        :ordered_quantity,
        :received_quantity,
        :unit,
        :receipt_status,
        :warehouse_user,
        :receipt_note
    );
    """

    update_order_query = """
    UPDATE purchase_orders
    SET order_status = 'Mal Kabul Tamamlandı'
    WHERE order_id = :order_id;
    """

    update_request_query = """
    UPDATE purchase_requests
    SET
        status = 'Fatura Kontrolü Bekliyor',
        next_approval_role = 'Muhasebe / Finans',
        updated_at = CURRENT_TIMESTAMP
    WHERE request_id = :request_id;
    """

    with engine.begin() as connection:
        connection.execute(text(insert_query), data)

        connection.execute(
            text(update_order_query),
            {"order_id": data["order_id"]}
        )

        connection.execute(
            text(update_request_query),
            {"request_id": data["request_id"]}
        )


def load_goods_receipts_from_db():
    query = """
    SELECT
        receipt_id,
        order_id,
        request_id,
        supplier_name,
        item_name,
        ordered_quantity,
        received_quantity,
        unit,
        receipt_status,
        warehouse_user,
        receipt_note,
        created_at
    FROM goods_receipts
    ORDER BY receipt_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_waiting_invoice_requests_from_db():
    query = """
    SELECT
        pr.request_id,
        pr.department,
        pr.requester_name,
        pr.item_name,
        pr.category,
        pr.status,

        po.order_id,
        po.supplier_name,
        po.order_amount_original,
        po.currency AS order_currency,
        po.order_amount_tl,
        po.expected_delivery_date,
        po.order_status,

        gr.receipt_id,
        gr.received_quantity,
        gr.unit,
        gr.receipt_status,
        gr.created_at AS receipt_date
    FROM purchase_requests pr
    INNER JOIN purchase_orders po
        ON pr.request_id = po.request_id
    INNER JOIN goods_receipts gr
        ON po.order_id = gr.order_id
    WHERE pr.status = :status
    ORDER BY pr.request_id DESC;
    """

    return pd.read_sql(
        text(query),
        engine,
        params={"status": "Fatura Kontrolü Bekliyor"}
    )


def insert_invoice_control_to_db(data):
    insert_query = """
    INSERT INTO invoice_controls (
        request_id,
        order_id,
        invoice_no,
        invoice_date,
        invoice_amount_original,
        currency,
        exchange_rate,
        invoice_amount_tl,
        order_amount_tl,
        amount_difference,
        decision,
        accountant_name,
        invoice_note
    )
    VALUES (
        :request_id,
        :order_id,
        :invoice_no,
        :invoice_date,
        :invoice_amount_original,
        :currency,
        :exchange_rate,
        :invoice_amount_tl,
        :order_amount_tl,
        :amount_difference,
        :decision,
        :accountant_name,
        :invoice_note
    );
    """

    if data["decision"] == "Onaylandı":
        new_status = "Tamamlandı"
        next_approval_role = "-"
    else:
        new_status = "Fatura Reddedildi"
        next_approval_role = "Muhasebe / Satınalma İnceleme"

    update_request_query = """
    UPDATE purchase_requests
    SET
        status = :new_status,
        next_approval_role = :next_approval_role,
        updated_at = CURRENT_TIMESTAMP
    WHERE request_id = :request_id;
    """

    with engine.begin() as connection:
        connection.execute(text(insert_query), data)

        connection.execute(
            text(update_request_query),
            {
                "request_id": data["request_id"],
                "new_status": new_status,
                "next_approval_role": next_approval_role
            }
        )


def load_invoice_controls_from_db():
    query = """
    SELECT
        invoice_control_id,
        request_id,
        order_id,
        invoice_no,
        invoice_date,
        invoice_amount_original,
        currency,
        exchange_rate,
        invoice_amount_tl,
        order_amount_tl,
        amount_difference,
        decision,
        accountant_name,
        invoice_note,
        created_at
    FROM invoice_controls
    ORDER BY invoice_control_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_dashboard_requests_from_db():
    query = """
    SELECT
        request_id,
        department,
        requester_name,
        item_name,
        category,
        quantity,
        unit,
        total_amount_tl,
        urgency,
        priority,
        approval_flow,
        status,
        sla_due_at,
        created_at,
        updated_at,
        CASE
            WHEN status NOT IN ('Tamamlandı', 'Reddedildi', 'Fatura Reddedildi')
                 AND sla_due_at < CURRENT_TIMESTAMP
            THEN 'Gecikmiş'
            ELSE 'Zamanında'
        END AS sla_status
    FROM purchase_requests
    ORDER BY request_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_dashboard_orders_from_db():
    query = """
    SELECT
        order_id,
        request_id,
        supplier_name,
        item_name,
        quantity,
        unit,
        order_amount_tl,
        expected_delivery_date,
        order_status,
        created_at
    FROM purchase_orders
    ORDER BY order_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_dashboard_invoices_from_db():
    query = """
    SELECT
        invoice_control_id,
        request_id,
        order_id,
        invoice_no,
        invoice_amount_tl,
        order_amount_tl,
        amount_difference,
        decision,
        accountant_name,
        created_at
    FROM invoice_controls
    ORDER BY invoice_control_id DESC;
    """

    return pd.read_sql(text(query), engine)


def load_dashboard_offers_from_db():
    query = """
    SELECT
        offer_id,
        request_id,
        supplier_name,
        offer_total_tl,
        delivery_days,
        payment_term,
        is_selected,
        created_at
    FROM supplier_offers
    ORDER BY offer_id DESC;
    """

    return pd.read_sql(text(query), engine)

ensure_tables()
seed_admin_user()


if "auth_user" not in st.session_state:
    st.session_state.auth_user = None


st.sidebar.title("Giriş")

if st.session_state.auth_user is None:
    login_username = st.sidebar.text_input("Kullanıcı Adı")
    login_password = st.sidebar.text_input("Şifre", type="password")

    if st.sidebar.button("Giriş Yap"):
        user = get_user_by_username(login_username)

        if user and user["is_active"] and verify_password(
            login_password,
            user["password_salt"],
            user["password_hash"]
        ):
            st.session_state.auth_user = user
            st.rerun()
        else:
            st.sidebar.error("Kullanıcı adı veya şifre hatalı.")

    st.info(
        "İlk giriş için admin kullanıcı:\n\n"
        "Kullanıcı adı: itadmin\n\n"
        "Şifre: Admin123!"
    )

    st.stop()


current_user = st.session_state.auth_user

current_user_id = current_user["user_id"]
current_username = current_user["username"]
current_user_name = current_user["full_name"]
current_user_department = current_user["department"]
current_user_role = current_user["role"]
current_user_is_admin = current_user["is_admin"]


st.sidebar.success(f"Giriş yapan: {current_user_name}")
st.sidebar.caption(f"Rol: {current_user_role}")
st.sidebar.caption(f"Departman: {current_user_department}")

if st.sidebar.button("Çıkış Yap"):
    st.session_state.auth_user = None
    st.rerun()


st.sidebar.title("Menü")

menu = st.sidebar.radio(
    "Sayfa Seç",
    ALL_MENUS
)


if not user_can_access_menu(
    current_user_id,
    current_user_is_admin,
    menu
):
    st.warning("Bu sayfaya erişim yetkiniz bulunmuyor.")
    st.stop()


if menu == "Talep Oluştur":
    st.subheader("Satınalma Talebi Oluştur")

    col1, col2 = st.columns(2)

    with col1:
        department_options = [
            "Üretim",
            "Depo",
            "Muhasebe",
            "Satınalma",
            "Kalite",
            "Teknik Bakım",
            "İnsan Kaynakları",
            "Bilgi İşlem",
            "Yönetim"
        ]

        default_department_index = (
            department_options.index(current_user_department)
            if current_user_department in department_options
            else 0
        )

        if current_user_is_admin:
            department = st.selectbox(
                "Talep Eden Departman",
                department_options,
                index=default_department_index
            )
        else:
            department = st.selectbox(
                "Talep Eden Departman",
                department_options,
                index=default_department_index,
                disabled=True
            )
        requester_name = st.text_input(
            "Talep Eden Kişi",
            value=current_user_name
        )

        item_name = st.text_input("Ürün / Hizmet Adı")

        category = st.selectbox(
            "Kategori",
            [
                "Hammadde",
                "Ambalaj",
                "Yedek Parça",
                "Teknik Malzeme",
                "Ofis Malzemesi",
                "Temizlik Malzemesi",
                "IT Ekipmanı",
                "Hizmet Alımı"
            ]
        )

    with col2:
        quantity = st.number_input(
            "Miktar",
            min_value=0.0,
            step=1.0
        )

        unit = st.selectbox(
            "Birim",
            [
                "Adet",
                "Koli",
                "Kg",
                "Litre",
                "Metre",
                "Paket",
                "Hizmet"
            ]
        )

        estimated_unit_price = st.number_input(
            "Tahmini Birim Fiyat",
            min_value=0.0,
            step=100.0
        )

        currency = st.selectbox(
            "Para Birimi",
            [
                "TL",
                "USD"
            ]
        )

        exchange_rate = 1.0

        if currency == "USD":
            exchange_rate = st.number_input(
                "Dolar Kuru (TL)",
                min_value=0.01,
                value=40.00,
                step=0.10
            )

        urgency = st.selectbox(
            "Aciliyet",
            [
                "Düşük",
                "Normal",
                "Yüksek",
                "Kritik"
            ]
        )

        required_date = st.date_input(
            "İstenen Teslim Tarihi",
            value=date.today() + timedelta(days=7)
        )

    description = st.text_area("Açıklama")

    total_amount_original = quantity * estimated_unit_price

    if currency == "USD":
        total_amount_tl = total_amount_original * exchange_rate
    else:
        total_amount_tl = total_amount_original

    required_approval_count, approval_level = calculate_approval_flow(total_amount_tl)
    priority, sla_due_at = calculate_priority_and_sla(urgency, category)

    st.divider()

    st.subheader("Otomatik Hesaplanan Bilgiler")

    col3, col4, col5, col6 = st.columns(4)

    col3.metric("Toplam Tutar", f"{total_amount_original:,.2f} {currency}")
    col4.metric("TL Karşılığı", f"{total_amount_tl:,.2f} TL")
    col5.metric("Öncelik", priority)
    col6.metric("SLA Tarihi", sla_due_at.strftime("%d.%m.%Y %H:%M"))

    st.info(f"Onay Akışı: {approval_level}")

    if st.button("Talebi Kaydet", type="primary"):
        if not requester_name or not item_name or quantity <= 0 or estimated_unit_price <= 0:
            st.warning("Talep eden kişi, ürün/hizmet adı, miktar ve birim fiyat alanları zorunludur.")
        else:
            first_approval_role = APPROVAL_STEPS[0]

            request_data = {
                "department": department,
                "requester_name": requester_name,
                "item_name": item_name,
                "category": category,
                "quantity": quantity,
                "unit": unit,
                "estimated_unit_price": estimated_unit_price,
                "currency": currency,
                "exchange_rate": exchange_rate,
                "total_amount_original": total_amount_original,
                "total_amount_tl": total_amount_tl,
                "urgency": urgency,
                "priority": priority,
                "approval_flow": approval_level,
                "required_approval_count": required_approval_count,
                "current_approval_step": 1,
                "next_approval_role": first_approval_role,
                "sla_due_at": sla_due_at,
                "required_date": required_date,
                "status": f"{first_approval_role} Onayı Bekliyor",
                "description": description
            }

            insert_purchase_request_to_db(request_data)

            st.success("Talep PostgreSQL veritabanına başarıyla kaydedildi.")

            st.write("### Kaydedilen Talep Özeti")
            st.write({
                "Departman": department,
                "Talep Eden": requester_name,
                "Ürün / Hizmet": item_name,
                "Kategori": category,
                "Miktar": quantity,
                "Birim": unit,
                "Toplam Tutar": f"{total_amount_original:,.2f} {currency}",
                "TL Karşılığı": f"{total_amount_tl:,.2f} TL",
                "Aciliyet": urgency,
                "Öncelik": priority,
                "Onay Akışı": approval_level,
                "Durum": f"{first_approval_role} Onayı Bekliyor"
            })


elif menu == "Talep Listesi":
    st.subheader("Satınalma Talep Listesi")

    df = load_purchase_requests_from_db()

    if df.empty:
        st.info("Henüz kayıtlı satınalma talebi bulunmuyor.")
    else:
        df_display = df.rename(columns={
            "request_id": "Talep No",
            "department": "Departman",
            "requester_name": "Talep Eden",
            "item_name": "Ürün / Hizmet",
            "category": "Kategori",
            "quantity": "Miktar",
            "unit": "Birim",
            "estimated_unit_price": "Tahmini Birim Fiyat",
            "currency": "Para Birimi",
            "exchange_rate": "Döviz Kuru",
            "total_amount_original": "Toplam Tutar",
            "total_amount_tl": "Toplam TL Karşılığı",
            "urgency": "Aciliyet",
            "priority": "Otomatik Öncelik",
            "approval_flow": "Onay Akışı",
            "next_approval_role": "Sıradaki Onay",
            "status": "Durum",
            "created_at": "Oluşturulma Tarihi"
        })

        col1, col2, col3 = st.columns(3)

        selected_department = col1.selectbox(
            "Departmana Göre Filtrele",
            ["Tümü"] + sorted(df_display["Departman"].dropna().unique().tolist())
        )

        selected_category = col2.selectbox(
            "Kategoriye Göre Filtrele",
            ["Tümü"] + sorted(df_display["Kategori"].dropna().unique().tolist())
        )

        selected_status = col3.selectbox(
            "Duruma Göre Filtrele",
            ["Tümü"] + sorted(df_display["Durum"].dropna().unique().tolist())
        )

        filtered_df = df_display.copy()

        if selected_department != "Tümü":
            filtered_df = filtered_df[filtered_df["Departman"] == selected_department]

        if selected_category != "Tümü":
            filtered_df = filtered_df[filtered_df["Kategori"] == selected_category]

        if selected_status != "Tümü":
            filtered_df = filtered_df[filtered_df["Durum"] == selected_status]

        display_columns = [
            "Talep No",
            "Departman",
            "Talep Eden",
            "Ürün / Hizmet",
            "Kategori",
            "Miktar",
            "Birim",
            "Toplam Tutar",
            "Para Birimi",
            "Toplam TL Karşılığı",
            "Otomatik Öncelik",
            "Onay Akışı",
            "Sıradaki Onay",
            "Durum",
            "Oluşturulma Tarihi"
        ]

        st.dataframe(filtered_df[display_columns], use_container_width=True)

        st.write("### Özet Bilgiler")

        col4, col5, col6 = st.columns(3)

        col4.metric("Toplam Talep", len(df_display))
        col5.metric("Toplam TL Karşılığı", f"{df_display['Toplam TL Karşılığı'].sum():,.2f} TL")

        waiting_count = len(
            df_display[df_display["Durum"].str.contains("Onayı Bekliyor", na=False)]
        )

        col6.metric("Onay Bekleyen Talep", waiting_count)


elif menu == "Onay Ekranı":
    st.subheader("Satınalma Onay Ekranı")

    waiting_df = load_waiting_approval_requests_from_db(
    current_user_role,
    current_user_department,
    current_user_is_admin
    )

    if waiting_df.empty:
        st.info("Onay bekleyen satınalma talebi bulunmuyor.")
    else:
        request_options = []

        for _, row in waiting_df.iterrows():
            option_text = (
                f"{row['request_id']} | "
                f"{row['department']} | "
                f"{row['item_name']} | "
                f"{row['total_amount_tl']:,.2f} TL | "
                f"{row['next_approval_role']}"
            )
            request_options.append(option_text)

        selected_request_text = st.selectbox(
            "Onaylanacak Talep Seç",
            request_options
        )

        selected_request_id = int(selected_request_text.split("|")[0].strip())

        selected_row = waiting_df[
            waiting_df["request_id"] == selected_request_id
        ].iloc[0]

        st.write("### Talep Detayı")

        detail_col1, detail_col2 = st.columns(2)

        with detail_col1:
            st.write(f"**Talep No:** {selected_row['request_id']}")
            st.write(f"**Departman:** {selected_row['department']}")
            st.write(f"**Talep Eden:** {selected_row['requester_name']}")
            st.write(f"**Ürün / Hizmet:** {selected_row['item_name']}")
            st.write(f"**Kategori:** {selected_row['category']}")
            st.write(f"**Aciliyet:** {selected_row['urgency']}")

        with detail_col2:
            st.write(f"**Toplam Tutar:** {selected_row['total_amount_original']:,.2f} {selected_row['currency']}")
            st.write(f"**TL Karşılığı:** {selected_row['total_amount_tl']:,.2f} TL")
            st.write(f"**Onay Akışı:** {selected_row['approval_flow']}")
            st.write(f"**Sıradaki Onay:** {selected_row['next_approval_role']}")
            st.write(f"**Durum:** {selected_row['status']}")
            st.write(f"**SLA Tarihi:** {selected_row['sla_due_at']}")

        st.divider()

        st.write("### Onay İşlemi")

        approver_name = st.text_input(
            "Onaylayan Kişi",
            value=current_user_name
        )

        decision = st.radio(
            "Karar",
            ["Onaylandı", "Reddedildi"],
            horizontal=True
        )

        approval_comment = st.text_area("Onay Açıklaması / Not")

        if st.button("Kararı Kaydet", type="primary"):
            if not approver_name:
                st.warning("Onaylayan kişi alanı zorunludur.")
            else:
                current_step = int(selected_row["current_approval_step"])
                required_count = int(selected_row["required_approval_count"])
                current_role = selected_row["next_approval_role"]

                approval_data = {
                    "request_id": selected_request_id,
                    "approval_step": current_step,
                    "approval_role": current_role,
                    "approver_name": approver_name,
                    "decision": decision,
                    "comment": approval_comment
                }

                insert_approval_history_to_db(approval_data)

                update_request_after_approval(
                    request_id=selected_request_id,
                    current_step=current_step,
                    required_count=required_count,
                    decision=decision
                )

                st.success("Onay işlemi PostgreSQL veritabanına başarıyla kaydedildi.")
                st.rerun()

        st.divider()

        st.write("### Onay Geçmişi")

        approval_history_df = load_approval_history_from_db(selected_request_id)

        if approval_history_df.empty:
            st.info("Bu talep için henüz onay geçmişi bulunmuyor.")
        else:
            approval_history_df = approval_history_df.rename(columns={
                "approval_step": "Onay Adımı",
                "approval_role": "Onay Rolü",
                "approver_name": "Onaylayan",
                "decision": "Karar",
                "comment": "Açıklama",
                "approved_at": "Onay Tarihi"
            })

            st.dataframe(approval_history_df, use_container_width=True)

elif menu == "Teklif Girişi":
    st.subheader("Tedarikçi Teklif Girişi")

    offer_ready_df = load_offer_ready_requests_from_db()

    if offer_ready_df.empty:
        st.info("Teklif girilebilecek onaylanmış satınalma talebi bulunmuyor.")
    else:
        request_options = []

        for _, row in offer_ready_df.iterrows():
            option_text = (
                f"{row['request_id']} | "
                f"{row['department']} | "
                f"{row['item_name']} | "
                f"{row['total_amount_tl']:,.2f} TL"
            )
            request_options.append(option_text)

        selected_request_text = st.selectbox(
            "Teklif Girilecek Talep Seç",
            request_options
        )

        selected_request_id = int(selected_request_text.split("|")[0].strip())

        selected_row = offer_ready_df[
            offer_ready_df["request_id"] == selected_request_id
        ].iloc[0]

        st.write("### Talep Bilgisi")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Talep No:** {selected_row['request_id']}")
            st.write(f"**Departman:** {selected_row['department']}")
            st.write(f"**Talep Eden:** {selected_row['requester_name']}")
            st.write(f"**Ürün / Hizmet:** {selected_row['item_name']}")
            st.write(f"**Kategori:** {selected_row['category']}")

        with col2:
            st.write(f"**Talep Miktarı:** {selected_row['quantity']} {selected_row['unit']}")
            st.write(f"**Talep Tahmini Tutar:** {selected_row['total_amount_original']:,.2f} {selected_row['currency']}")
            st.write(f"**TL Karşılığı:** {selected_row['total_amount_tl']:,.2f} TL")
            st.write(f"**Durum:** {selected_row['status']}")
            st.write(f"**İstenen Teslim Tarihi:** {selected_row['required_date']}")

        st.divider()

        st.write("### Yeni Teklif Ekle")

        offer_col1, offer_col2 = st.columns(2)

        with offer_col1:
            supplier_name = st.text_input("Tedarikçi Adı")
            supplier_contact = st.text_input("Tedarikçi Yetkilisi / İletişim")

            offer_unit_price = st.number_input(
                "Teklif Birim Fiyat",
                min_value=0.0,
                step=100.0
            )

            offer_currency = st.selectbox(
                "Teklif Para Birimi",
                ["TL", "USD"]
            )

        with offer_col2:
            offer_exchange_rate = 1.0

            if offer_currency == "USD":
                offer_exchange_rate = st.number_input(
                    "Teklif Dolar Kuru (TL)",
                    min_value=0.01,
                    value=40.00,
                    step=0.10
                )

            delivery_days = st.number_input(
                "Teslim Süresi (Gün)",
                min_value=1,
                step=1
            )

            payment_term = st.selectbox(
                "Ödeme Şekli",
                [
                    "Peşin",
                    "30 Gün Vadeli",
                    "60 Gün Vadeli",
                    "90 Gün Vadeli"
                ]
            )

            offer_note = st.text_area("Teklif Notu")

        quantity = float(selected_row["quantity"])
        offer_total_original = quantity * offer_unit_price

        if offer_currency == "USD":
            offer_total_tl = offer_total_original * offer_exchange_rate
        else:
            offer_total_tl = offer_total_original

        st.info(f"Teklif Toplamı: {offer_total_original:,.2f} {offer_currency}")
        st.info(f"Teklif TL Karşılığı: {offer_total_tl:,.2f} TL")

        if st.button("Teklifi Kaydet", type="primary"):
            if not supplier_name or offer_unit_price <= 0:
                st.warning("Tedarikçi adı ve teklif birim fiyat alanları zorunludur.")
            else:
                offer_data = {
                    "request_id": selected_request_id,
                    "supplier_name": supplier_name,
                    "supplier_contact": supplier_contact,
                    "offer_unit_price": offer_unit_price,
                    "currency": offer_currency,
                    "exchange_rate": offer_exchange_rate,
                    "offer_total_original": offer_total_original,
                    "offer_total_tl": offer_total_tl,
                    "delivery_days": int(delivery_days),
                    "payment_term": payment_term,
                    "offer_note": offer_note
                }

                insert_supplier_offer_to_db(offer_data)

                st.success("Teklif PostgreSQL veritabanına başarıyla kaydedildi.")
                st.rerun()

        st.divider()

        st.write("### Bu Talebe Ait Teklifler")

        offers_df = load_supplier_offers_by_request_id(selected_request_id)

        if offers_df.empty:
            st.info("Bu talep için henüz teklif girilmedi.")
        else:
            offers_display = offers_df.rename(columns={
                "offer_id": "Teklif No",
                "supplier_name": "Tedarikçi",
                "supplier_contact": "Tedarikçi İletişim",
                "offer_unit_price": "Teklif Birim Fiyat",
                "currency": "Para Birimi",
                "exchange_rate": "Döviz Kuru",
                "offer_total_original": "Teklif Toplamı",
                "offer_total_tl": "Teklif TL Karşılığı",
                "delivery_days": "Teslim Süresi (Gün)",
                "payment_term": "Ödeme Şekli",
                "offer_note": "Teklif Notu",
                "is_selected": "Seçildi mi",
                "created_at": "Teklif Tarihi"
            })

            st.dataframe(offers_display, use_container_width=True)

            best_offer = offers_display.iloc[0]

            st.success(
                f"En düşük teklif: {best_offer['Tedarikçi']} - "
                f"{best_offer['Teklif TL Karşılığı']:,.2f} TL"
            )

elif menu == "Siparişe Dönüştür":
    st.subheader("Teklif Seç ve Siparişe Dönüştür")

    requests_with_offers_df = load_requests_with_offers_from_db()

    if requests_with_offers_df.empty:
        st.info("Siparişe dönüştürülebilecek teklifli talep bulunmuyor.")
    else:
        request_options = []

        for _, row in requests_with_offers_df.iterrows():
            option_text = (
                f"{row['request_id']} | "
                f"{row['department']} | "
                f"{row['item_name']} | "
                f"{row['total_amount_tl']:,.2f} TL"
            )
            request_options.append(option_text)

        selected_request_text = st.selectbox(
            "Siparişe Dönüştürülecek Talep Seç",
            request_options
        )

        selected_request_id = int(selected_request_text.split("|")[0].strip())

        selected_request = requests_with_offers_df[
            requests_with_offers_df["request_id"] == selected_request_id
        ].iloc[0]

        offers_df = load_order_offers_by_request_id(selected_request_id)

        st.write("### Talebe Ait Teklifler")

        if offers_df.empty:
            st.info("Bu talep için teklif bulunmuyor.")
        else:
            offers_display = offers_df.rename(columns={
                "offer_id": "Teklif No",
                "supplier_name": "Tedarikçi",
                "supplier_contact": "Tedarikçi İletişim",
                "offer_unit_price": "Teklif Birim Fiyat",
                "currency": "Para Birimi",
                "exchange_rate": "Döviz Kuru",
                "offer_total_original": "Teklif Toplamı",
                "offer_total_tl": "Teklif TL Karşılığı",
                "delivery_days": "Teslim Süresi (Gün)",
                "payment_term": "Ödeme Şekli",
                "offer_note": "Teklif Notu",
                "is_selected": "Seçildi mi",
                "created_at": "Teklif Tarihi"
            })

            st.dataframe(offers_display, use_container_width=True)

            st.divider()

            offer_options = []

            for _, row in offers_df.iterrows():
                option_text = (
                    f"{row['offer_id']} | "
                    f"{row['supplier_name']} | "
                    f"{row['offer_total_tl']:,.2f} TL | "
                    f"{row['delivery_days']} gün"
                )
                offer_options.append(option_text)

            selected_offer_text = st.selectbox(
                "Seçilecek Teklif",
                offer_options
            )

            selected_offer_id = int(selected_offer_text.split("|")[0].strip())

            selected_offer = offers_df[
                offers_df["offer_id"] == selected_offer_id
            ].iloc[0]

            st.write("### Seçilen Teklif Özeti")

            col1, col2 = st.columns(2)

            with col1:
                st.write(f"**Talep No:** {selected_request['request_id']}")
                st.write(f"**Departman:** {selected_request['department']}")
                st.write(f"**Ürün / Hizmet:** {selected_request['item_name']}")
                st.write(f"**Miktar:** {selected_request['quantity']} {selected_request['unit']}")

            with col2:
                st.write(f"**Tedarikçi:** {selected_offer['supplier_name']}")
                st.write(f"**Teklif Tutarı:** {selected_offer['offer_total_original']:,.2f} {selected_offer['currency']}")
                st.write(f"**TL Karşılığı:** {selected_offer['offer_total_tl']:,.2f} TL")
                st.write(f"**Teslim Süresi:** {selected_offer['delivery_days']} gün")

            expected_delivery_date = date.today() + timedelta(
                days=int(selected_offer["delivery_days"])
            )

            st.info(f"Beklenen Teslim Tarihi: {expected_delivery_date.strftime('%d.%m.%Y')}")

            order_note = st.text_area("Sipariş Notu")

            if st.button("Siparişe Dönüştür", type="primary"):
                order_data = {
                    "request_id": int(selected_request["request_id"]),
                    "offer_id": int(selected_offer["offer_id"]),
                    "supplier_name": selected_offer["supplier_name"],
                    "item_name": selected_request["item_name"],
                    "quantity": float(selected_request["quantity"]),
                    "unit": selected_request["unit"],
                    "order_amount_original": float(selected_offer["offer_total_original"]),
                    "currency": selected_offer["currency"],
                    "order_amount_tl": float(selected_offer["offer_total_tl"]),
                    "delivery_days": int(selected_offer["delivery_days"]),
                    "expected_delivery_date": expected_delivery_date,
                    "order_status": "Mal Kabul Bekliyor",
                    "order_note": order_note
                }

                create_purchase_order_from_offer(order_data)

                st.success("Seçilen teklif başarıyla siparişe dönüştürüldü.")
                st.rerun()

        st.divider()

        st.write("### Oluşturulan Satınalma Siparişleri")

        orders_df = load_purchase_orders_from_db()

        if orders_df.empty:
            st.info("Henüz satınalma siparişi bulunmuyor.")
        else:
            orders_display = orders_df.rename(columns={
                "order_id": "Sipariş No",
                "request_id": "Talep No",
                "offer_id": "Teklif No",
                "supplier_name": "Tedarikçi",
                "item_name": "Ürün / Hizmet",
                "quantity": "Miktar",
                "unit": "Birim",
                "order_amount_original": "Sipariş Tutarı",
                "currency": "Para Birimi",
                "order_amount_tl": "Sipariş TL Karşılığı",
                "delivery_days": "Teslim Süresi",
                "expected_delivery_date": "Beklenen Teslim Tarihi",
                "order_status": "Sipariş Durumu",
                "order_note": "Sipariş Notu",
                "created_at": "Sipariş Tarihi"
            })

            st.dataframe(orders_display, use_container_width=True)

elif menu == "Mal Kabul":
    st.subheader("Mal Kabul Ekranı")

    waiting_orders_df = load_waiting_receipt_orders_from_db()

    if waiting_orders_df.empty:
        st.info("Mal kabul bekleyen sipariş bulunmuyor.")
    else:
        order_options = []

        for _, row in waiting_orders_df.iterrows():
            option_text = (
                f"{row['order_id']} | "
                f"Talep:{row['request_id']} | "
                f"{row['supplier_name']} | "
                f"{row['item_name']} | "
                f"{row['order_amount_tl']:,.2f} TL"
            )
            order_options.append(option_text)

        selected_order_text = st.selectbox(
            "Mal Kabul Yapılacak Sipariş Seç",
            order_options
        )

        selected_order_id = int(selected_order_text.split("|")[0].strip())

        selected_order = waiting_orders_df[
            waiting_orders_df["order_id"] == selected_order_id
        ].iloc[0]

        st.write("### Sipariş Bilgisi")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Sipariş No:** {selected_order['order_id']}")
            st.write(f"**Talep No:** {selected_order['request_id']}")
            st.write(f"**Tedarikçi:** {selected_order['supplier_name']}")
            st.write(f"**Ürün / Hizmet:** {selected_order['item_name']}")
            st.write(f"**Sipariş Miktarı:** {selected_order['quantity']} {selected_order['unit']}")

        with col2:
            st.write(f"**Sipariş Tutarı:** {selected_order['order_amount_original']:,.2f} {selected_order['currency']}")
            st.write(f"**TL Karşılığı:** {selected_order['order_amount_tl']:,.2f} TL")
            st.write(f"**Beklenen Teslim Tarihi:** {selected_order['expected_delivery_date']}")
            st.write(f"**Sipariş Durumu:** {selected_order['order_status']}")

        st.divider()

        st.write("### Mal Kabul Bilgileri")

        received_quantity = st.number_input(
            "Teslim Alınan Miktar",
            min_value=0.0,
            step=1.0,
            value=float(selected_order["quantity"])
        )

        warehouse_user = st.text_input("Mal Kabul Yapan Depo Kullanıcısı")

        receipt_status = st.selectbox(
            "Mal Kabul Durumu",
            [
                "Tam Kabul",
                "Eksik Kabul",
                "Hasarlı Ürün",
                "Reddedildi"
            ]
        )

        receipt_note = st.text_area("Mal Kabul Notu")

        if st.button("Mal Kabulü Kaydet", type="primary"):
            if not warehouse_user or received_quantity <= 0:
                st.warning("Mal kabul yapan kullanıcı ve teslim alınan miktar zorunludur.")
            else:
                receipt_data = {
                    "order_id": int(selected_order["order_id"]),
                    "request_id": int(selected_order["request_id"]),
                    "supplier_name": selected_order["supplier_name"],
                    "item_name": selected_order["item_name"],
                    "ordered_quantity": float(selected_order["quantity"]),
                    "received_quantity": float(received_quantity),
                    "unit": selected_order["unit"],
                    "receipt_status": receipt_status,
                    "warehouse_user": warehouse_user,
                    "receipt_note": receipt_note
                }

                insert_goods_receipt_to_db(receipt_data)

                st.success("Mal kabul kaydı PostgreSQL veritabanına başarıyla kaydedildi.")
                st.success("Talep fatura kontrol sürecine aktarıldı.")
                st.rerun()

        st.divider()

        st.write("### Mal Kabul Kayıtları")

        receipts_df = load_goods_receipts_from_db()

        if receipts_df.empty:
            st.info("Henüz mal kabul kaydı bulunmuyor.")
        else:
            receipts_display = receipts_df.rename(columns={
                "receipt_id": "Mal Kabul No",
                "order_id": "Sipariş No",
                "request_id": "Talep No",
                "supplier_name": "Tedarikçi",
                "item_name": "Ürün / Hizmet",
                "ordered_quantity": "Sipariş Miktarı",
                "received_quantity": "Teslim Alınan Miktar",
                "unit": "Birim",
                "receipt_status": "Mal Kabul Durumu",
                "warehouse_user": "Depo Kullanıcısı",
                "receipt_note": "Mal Kabul Notu",
                "created_at": "Mal Kabul Tarihi"
            })

            st.dataframe(receipts_display, use_container_width=True)

elif menu == "Fatura Kontrolü":
    st.subheader("Fatura Kontrolü / Muhasebe Onayı")

    waiting_invoice_df = load_waiting_invoice_requests_from_db()

    if waiting_invoice_df.empty:
        st.info("Fatura kontrolü bekleyen talep bulunmuyor.")
    else:
        request_options = []

        for _, row in waiting_invoice_df.iterrows():
            option_text = (
                f"{row['request_id']} | "
                f"{row['department']} | "
                f"{row['item_name']} | "
                f"{row['supplier_name']} | "
                f"{row['order_amount_tl']:,.2f} TL"
            )
            request_options.append(option_text)

        selected_request_text = st.selectbox(
            "Fatura Kontrolü Yapılacak Talep Seç",
            request_options
        )

        selected_request_id = int(selected_request_text.split("|")[0].strip())

        selected_row = waiting_invoice_df[
            waiting_invoice_df["request_id"] == selected_request_id
        ].iloc[0]

        st.write("### Talep / Sipariş / Mal Kabul Özeti")

        col1, col2 = st.columns(2)

        with col1:
            st.write(f"**Talep No:** {selected_row['request_id']}")
            st.write(f"**Departman:** {selected_row['department']}")
            st.write(f"**Talep Eden:** {selected_row['requester_name']}")
            st.write(f"**Ürün / Hizmet:** {selected_row['item_name']}")
            st.write(f"**Kategori:** {selected_row['category']}")
            st.write(f"**Mevcut Durum:** {selected_row['status']}")

        with col2:
            st.write(f"**Sipariş No:** {selected_row['order_id']}")
            st.write(f"**Tedarikçi:** {selected_row['supplier_name']}")
            st.write(f"**Sipariş Tutarı:** {selected_row['order_amount_original']:,.2f} {selected_row['order_currency']}")
            st.write(f"**Sipariş TL Karşılığı:** {selected_row['order_amount_tl']:,.2f} TL")
            st.write(f"**Mal Kabul Durumu:** {selected_row['receipt_status']}")
            st.write(f"**Teslim Alınan Miktar:** {selected_row['received_quantity']} {selected_row['unit']}")

        st.divider()

        st.write("### Fatura Bilgileri")

        invoice_no = st.text_input("Fatura No")
        invoice_date = st.date_input("Fatura Tarihi", value=date.today())

        col3, col4 = st.columns(2)

        with col3:
            invoice_amount = st.number_input(
                "Fatura Tutarı",
                min_value=0.0,
                step=100.0
            )

            invoice_currency = st.selectbox(
                "Fatura Para Birimi",
                ["TL", "USD"]
            )

        with col4:
            invoice_exchange_rate = 1.0

            if invoice_currency == "USD":
                invoice_exchange_rate = st.number_input(
                    "Fatura Dolar Kuru (TL)",
                    min_value=0.01,
                    value=40.00,
                    step=0.10
                )

            accountant_name = st.text_input("Kontrol Eden Muhasebe / Finans Kullanıcısı")

        if invoice_currency == "USD":
            invoice_amount_tl = invoice_amount * invoice_exchange_rate
        else:
            invoice_amount_tl = invoice_amount

        order_amount_tl = float(selected_row["order_amount_tl"])
        amount_difference = invoice_amount_tl - order_amount_tl

        st.info(f"Fatura TL Karşılığı: {invoice_amount_tl:,.2f} TL")
        st.info(f"Sipariş TL Karşılığı: {order_amount_tl:,.2f} TL")

        if invoice_amount > 0:
            if abs(amount_difference) <= 1:
                st.success("Fatura tutarı sipariş tutarıyla uyumlu görünüyor.")
            elif amount_difference > 0:
                st.warning(f"Fatura tutarı siparişten {amount_difference:,.2f} TL daha yüksek.")
            else:
                st.warning(f"Fatura tutarı siparişten {abs(amount_difference):,.2f} TL daha düşük.")

        invoice_decision = st.radio(
            "Fatura Kontrol Kararı",
            ["Onaylandı", "Reddedildi"],
            horizontal=True
        )

        invoice_note = st.text_area("Fatura Kontrol Notu")

        if st.button("Fatura Kontrolünü Kaydet", type="primary"):
            if not invoice_no or not accountant_name or invoice_amount <= 0:
                st.warning("Fatura no, kontrol eden kişi ve fatura tutarı zorunludur.")
            else:
                invoice_data = {
                    "request_id": int(selected_row["request_id"]),
                    "order_id": int(selected_row["order_id"]),
                    "invoice_no": invoice_no,
                    "invoice_date": invoice_date,
                    "invoice_amount_original": float(invoice_amount),
                    "currency": invoice_currency,
                    "exchange_rate": float(invoice_exchange_rate),
                    "invoice_amount_tl": float(invoice_amount_tl),
                    "order_amount_tl": float(order_amount_tl),
                    "amount_difference": float(amount_difference),
                    "decision": invoice_decision,
                    "accountant_name": accountant_name,
                    "invoice_note": invoice_note
                }

                insert_invoice_control_to_db(invoice_data)

                if invoice_decision == "Onaylandı":
                    st.success("Fatura kontrolü onaylandı. Talep tamamlandı.")
                else:
                    st.warning("Fatura reddedildi. Talep inceleme sürecine alındı.")

                st.rerun()

        st.divider()

        st.write("### Fatura Kontrol Kayıtları")

        invoice_controls_df = load_invoice_controls_from_db()

        if invoice_controls_df.empty:
            st.info("Henüz fatura kontrol kaydı bulunmuyor.")
        else:
            invoice_controls_display = invoice_controls_df.rename(columns={
                "invoice_control_id": "Fatura Kontrol No",
                "request_id": "Talep No",
                "order_id": "Sipariş No",
                "invoice_no": "Fatura No",
                "invoice_date": "Fatura Tarihi",
                "invoice_amount_original": "Fatura Tutarı",
                "currency": "Para Birimi",
                "exchange_rate": "Döviz Kuru",
                "invoice_amount_tl": "Fatura TL Karşılığı",
                "order_amount_tl": "Sipariş TL Karşılığı",
                "amount_difference": "Fark",
                "decision": "Karar",
                "accountant_name": "Kontrol Eden",
                "invoice_note": "Not",
                "created_at": "Kontrol Tarihi"
            })

            st.dataframe(invoice_controls_display, use_container_width=True)

elif menu == "Dashboard":
    st.subheader("Satınalma Süreci Dashboard")

    df_requests = load_dashboard_requests_from_db()

    if df_requests.empty:
        st.info("Dashboard için henüz kayıtlı satınalma talebi bulunmuyor.")
    else:
        df_requests["total_amount_tl"] = pd.to_numeric(
            df_requests["total_amount_tl"],
            errors="coerce"
        ).fillna(0)

        total_requests = len(df_requests)
        completed_requests = len(df_requests[df_requests["status"] == "Tamamlandı"])
        waiting_approval = len(df_requests[df_requests["status"].str.contains("Onayı Bekliyor", na=False)])
        offer_collecting = len(df_requests[df_requests["status"] == "Teklif Toplanıyor"])
        waiting_receipt = len(df_requests[df_requests["status"] == "Mal Kabul Bekliyor"])
        waiting_invoice = len(df_requests[df_requests["status"] == "Fatura Kontrolü Bekliyor"])
        rejected_requests = len(df_requests[df_requests["status"].str.contains("Reddedildi", na=False)])
        delayed_requests = len(df_requests[df_requests["sla_status"] == "Gecikmiş"])
        total_amount = df_requests["total_amount_tl"].sum()

        st.write("### Genel KPI Özeti")

        col1, col2, col3, col4 = st.columns(4)

        col1.metric("Toplam Talep", total_requests)
        col2.metric("Tamamlanan", completed_requests)
        col3.metric("Onay Bekleyen", waiting_approval)
        col4.metric("Geciken Talep", delayed_requests)

        col5, col6, col7, col8 = st.columns(4)

        col5.metric("Teklif Toplanıyor", offer_collecting)
        col6.metric("Mal Kabul Bekleyen", waiting_receipt)
        col7.metric("Fatura Kontrolü Bekleyen", waiting_invoice)
        col8.metric("Toplam Talep Tutarı", f"{total_amount:,.2f} TL")

        st.divider()

        st.write("### Süreç Durum Dağılımı")

        status_summary = (
            df_requests
            .groupby("status")
            .size()
            .reset_index(name="Talep Sayısı")
        )

        st.bar_chart(status_summary.set_index("status"))

        st.divider()

        col_a, col_b = st.columns(2)

        with col_a:
            st.write("### Departman Bazlı Talep Sayısı")

            department_summary = (
                df_requests
                .groupby("department")
                .size()
                .reset_index(name="Talep Sayısı")
            )

            st.bar_chart(department_summary.set_index("department"))

            st.write("### Kategori Bazlı Talep Sayısı")

            category_summary = (
                df_requests
                .groupby("category")
                .size()
                .reset_index(name="Talep Sayısı")
            )

            st.bar_chart(category_summary.set_index("category"))

        with col_b:
            st.write("### Departman Bazlı Talep Tutarı")

            department_amount_summary = (
                df_requests
                .groupby("department")["total_amount_tl"]
                .sum()
                .reset_index()
            )

            st.bar_chart(department_amount_summary.set_index("department"))

            st.write("### Öncelik Bazlı Talep Sayısı")

            priority_summary = (
                df_requests
                .groupby("priority")
                .size()
                .reset_index(name="Talep Sayısı")
            )

            st.bar_chart(priority_summary.set_index("priority"))

        st.divider()

        st.write("### Geciken Talepler")

        delayed_df = df_requests[df_requests["sla_status"] == "Gecikmiş"]

        if delayed_df.empty:
            st.success("SLA süresi geçmiş açık talep bulunmuyor.")
        else:
            delayed_display = delayed_df.rename(columns={
                "request_id": "Talep No",
                "department": "Departman",
                "requester_name": "Talep Eden",
                "item_name": "Ürün / Hizmet",
                "category": "Kategori",
                "total_amount_tl": "Toplam TL",
                "priority": "Öncelik",
                "sla_due_at": "SLA Tarihi",
                "status": "Durum"
            })

            st.dataframe(
                delayed_display[
                    [
                        "Talep No",
                        "Departman",
                        "Talep Eden",
                        "Ürün / Hizmet",
                        "Kategori",
                        "Toplam TL",
                        "Öncelik",
                        "SLA Tarihi",
                        "Durum"
                    ]
                ],
                use_container_width=True
            )

        st.divider()

        st.write("### Sipariş ve Fatura Özeti")

        df_orders = load_dashboard_orders_from_db()
        df_invoices = load_dashboard_invoices_from_db()
        df_offers = load_dashboard_offers_from_db()

        order_total = 0
        invoice_total = 0
        selected_offer_count = 0

        if not df_orders.empty:
            df_orders["order_amount_tl"] = pd.to_numeric(
                df_orders["order_amount_tl"],
                errors="coerce"
            ).fillna(0)

            order_total = df_orders["order_amount_tl"].sum()

        if not df_invoices.empty:
            df_invoices["invoice_amount_tl"] = pd.to_numeric(
                df_invoices["invoice_amount_tl"],
                errors="coerce"
            ).fillna(0)

            invoice_total = df_invoices["invoice_amount_tl"].sum()

        if not df_offers.empty:
            selected_offer_count = len(df_offers[df_offers["is_selected"] == True])

        col9, col10, col11 = st.columns(3)

        col9.metric("Toplam Sipariş TL", f"{order_total:,.2f} TL")
        col10.metric("Toplam Fatura TL", f"{invoice_total:,.2f} TL")
        col11.metric("Seçilen Teklif Sayısı", selected_offer_count)

        st.divider()

        st.write("### Satınalma Siparişleri")

        if df_orders.empty:
            st.info("Henüz satınalma siparişi bulunmuyor.")
        else:
            orders_display = df_orders.rename(columns={
                "order_id": "Sipariş No",
                "request_id": "Talep No",
                "supplier_name": "Tedarikçi",
                "item_name": "Ürün / Hizmet",
                "quantity": "Miktar",
                "unit": "Birim",
                "order_amount_tl": "Sipariş TL",
                "expected_delivery_date": "Beklenen Teslim",
                "order_status": "Sipariş Durumu",
                "created_at": "Sipariş Tarihi"
            })

            st.dataframe(orders_display, use_container_width=True)

        st.write("### Fatura Kontrol Kayıtları")

        if df_invoices.empty:
            st.info("Henüz fatura kontrol kaydı bulunmuyor.")
        else:
            invoices_display = df_invoices.rename(columns={
                "invoice_control_id": "Fatura Kontrol No",
                "request_id": "Talep No",
                "order_id": "Sipariş No",
                "invoice_no": "Fatura No",
                "invoice_amount_tl": "Fatura TL",
                "order_amount_tl": "Sipariş TL",
                "amount_difference": "Fark",
                "decision": "Karar",
                "accountant_name": "Kontrol Eden",
                "created_at": "Kontrol Tarihi"
            })

            st.dataframe(invoices_display, use_container_width=True)

        st.divider()

        st.write("### CSV Çıktısı")

        export_df = df_requests.rename(columns={
            "request_id": "Talep No",
            "department": "Departman",
            "requester_name": "Talep Eden",
            "item_name": "Ürün / Hizmet",
            "category": "Kategori",
            "quantity": "Miktar",
            "unit": "Birim",
            "total_amount_tl": "Toplam TL",
            "urgency": "Aciliyet",
            "priority": "Öncelik",
            "approval_flow": "Onay Akışı",
            "status": "Durum",
            "sla_due_at": "SLA Tarihi",
            "created_at": "Oluşturulma Tarihi",
            "sla_status": "SLA Durumu"
        })

        csv_data = export_df.to_csv(index=False).encode("utf-8-sig")

        st.download_button(
            label="Satınalma Taleplerini CSV Olarak İndir",
            data=csv_data,
            file_name="satinalma_talepleri.csv",
            mime="text/csv"
        )
elif menu == "Admin Paneli":
    st.subheader("Admin Paneli - Kullanıcı ve Yetki Yönetimi")

    if not current_user_is_admin:
        st.warning("Bu sayfayı sadece admin kullanıcı kullanabilir.")
        st.stop()

    tab1, tab2, tab3 = st.tabs(
        [
            "Yeni Kullanıcı Ekle",
            "Yetki Güncelle",
            "Kullanıcı Listesi"
        ]
    )

    with tab1:
        st.write("### Yeni Kullanıcı Ekle")

        col1, col2 = st.columns(2)

        with col1:
            new_username = st.text_input("Kullanıcı Adı")
            new_password = st.text_input("Şifre", type="password")
            new_full_name = st.text_input("Ad Soyad")
            new_email = st.text_input("E-posta")

        with col2:
            new_department = st.selectbox(
                "Departman",
                [
                    "Üretim",
                    "Depo",
                    "Muhasebe",
                    "Satınalma",
                    "Kalite",
                    "Teknik Bakım",
                    "İnsan Kaynakları",
                    "Bilgi İşlem",
                    "Yönetim"
                ],
                key="new_department"
            )

            new_role = st.selectbox(
                "Rol",
                [
                    "Talep Eden Kullanıcı",
                    "Departman Yöneticisi",
                    "Satınalma",
                    "Finans",
                    "Depo",
                    "Genel Müdür / Yönetim",
                    "Admin"
                ],
                key="new_role"
            )

            new_is_admin = st.checkbox("Admin Yetkisi", value=False)
            new_is_active = st.checkbox("Aktif Kullanıcı", value=True)

        selectable_permissions = [
            menu_name for menu_name in ALL_MENUS
            if menu_name not in DEFAULT_OPEN_MENUS
        ]

        selected_permissions = st.multiselect(
            "Erişebileceği Menüleri Seç",
            selectable_permissions,
            default=[]
        )

        if new_is_admin:
            selected_permissions = selectable_permissions

        if st.button("Kullanıcıyı Kaydet", type="primary"):
            if not new_username or not new_password or not new_full_name:
                st.warning("Kullanıcı adı, şifre ve ad soyad alanları zorunludur.")
            else:
                user_data = {
                    "username": new_username,
                    "password": new_password,
                    "full_name": new_full_name,
                    "email": new_email,
                    "department": new_department,
                    "role": new_role,
                    "is_admin": new_is_admin,
                    "is_active": new_is_active
                }

                try:
                    insert_app_user_to_db(
                        user_data,
                        selected_permissions
                    )

                    st.success("Kullanıcı ve yetkileri başarıyla kaydedildi.")
                    st.rerun()

                except Exception as e:
                    st.error("Kullanıcı kaydedilirken hata oluştu.")
                    st.exception(e)

    with tab2:
        st.write("### Kullanıcı Yetkisi Güncelle")

        users_df = load_all_users_from_db()

        if users_df.empty:
            st.info("Kayıtlı kullanıcı bulunmuyor.")
        else:
            user_options = []

            for _, row in users_df.iterrows():
                option_text = (
                    f"{row['user_id']} | "
                    f"{row['username']} | "
                    f"{row['full_name']} | "
                    f"{row['role']}"
                )
                user_options.append(option_text)

            selected_user_text = st.selectbox(
                "Yetkisi Güncellenecek Kullanıcı",
                user_options
            )

            selected_user_id = int(selected_user_text.split("|")[0].strip())

            current_permissions = load_user_permissions(selected_user_id)

            selectable_permissions = [
                menu_name for menu_name in ALL_MENUS
                if menu_name not in DEFAULT_OPEN_MENUS
            ]

            updated_permissions = st.multiselect(
                "Menü Yetkileri",
                selectable_permissions,
                default=current_permissions
            )

            if st.button("Yetkileri Güncelle", type="primary"):
                update_user_permissions(
                    selected_user_id,
                    updated_permissions
                )

                st.success("Kullanıcı yetkileri güncellendi.")
                st.rerun()

    with tab3:
        st.write("### Kullanıcı Listesi")

        users_df = load_all_users_from_db()

        if users_df.empty:
            st.info("Kayıtlı kullanıcı bulunmuyor.")
        else:
            users_display = users_df.rename(columns={
                "user_id": "Kullanıcı No",
                "username": "Kullanıcı Adı",
                "full_name": "Ad Soyad",
                "email": "E-posta",
                "department": "Departman",
                "role": "Rol",
                "is_admin": "Admin mi",
                "is_active": "Aktif mi",
                "created_at": "Oluşturulma Tarihi"
            })

            st.dataframe(users_display, use_container_width=True)