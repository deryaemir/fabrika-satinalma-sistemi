from sqlalchemy import create_engine, text
from dotenv import load_dotenv
from datetime import datetime, timedelta, date
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

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

data = {
    "department": "Üretim",
    "requester_name": "Derya",
    "item_name": "Pet Preform",
    "category": "Hammadde",
    "quantity": 1000,
    "unit": "Adet",
    "estimated_unit_price": 8,
    "currency": "TL",
    "exchange_rate": 1,
    "total_amount_original": 8000,
    "total_amount_tl": 8000,
    "urgency": "Yüksek",
    "priority": "Yüksek",
    "approval_flow": "2 Seviye Onay - Departman Yöneticisi + Satınalma",
    "required_approval_count": 2,
    "current_approval_step": 1,
    "next_approval_role": "Departman Yöneticisi",
    "sla_due_at": datetime.now() + timedelta(days=3),
    "required_date": date.today() + timedelta(days=7),
    "status": "Departman Yöneticisi Onayı Bekliyor",
    "description": "Test satınalma talebi"
}

try:
    with engine.begin() as connection:
        connection.execute(text(insert_query), data)

    print("Test satınalma talebi başarıyla PostgreSQL'e kaydedildi.")

except Exception as e:
    print("Kayıt ekleme hatası:")
    print(e)