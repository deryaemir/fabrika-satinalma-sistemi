from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

engine = create_engine(DATABASE_URL)

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

try:
    with engine.begin() as connection:
        connection.execute(text(create_purchase_requests_table))

    print("purchase_requests tablosu başarıyla oluşturuldu.")

except Exception as e:
    print("Tablo oluşturma hatası:")
    print(e)