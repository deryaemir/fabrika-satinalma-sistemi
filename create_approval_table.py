from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

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

try:
    with engine.begin() as connection:
        connection.execute(text(create_approval_history_table))

    print("approval_history tablosu başarıyla oluşturuldu.")

except Exception as e:
    print("Tablo oluşturma hatası:")
    print(e)