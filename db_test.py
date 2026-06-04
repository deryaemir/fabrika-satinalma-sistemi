from sqlalchemy import create_engine, text
from dotenv import load_dotenv
import os

load_dotenv()

database_url = os.getenv("DATABASE_URL")

engine = create_engine(database_url)

try:
    with engine.connect() as connection:
        result = connection.execute(text("SELECT 1"))
        print("PostgreSQL bağlantısı başarılı.")
        print("Test sonucu:", result.scalar())

except Exception as e:
    print("Bağlantı hatası:")
    print(e)