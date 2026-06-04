from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os
import pandas as pd

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
engine = create_engine(DATABASE_URL)

query = """
SELECT 
    request_id,
    department,
    requester_name,
    item_name,
    category,
    total_amount_tl,
    status,
    created_at
FROM purchase_requests
ORDER BY request_id DESC;
"""

try:
    df = pd.read_sql(query, engine)
    print(df)

except Exception as e:
    print("Veri okuma hatası:")
    print(e)