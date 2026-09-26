from sqlalchemy import text
from app.database.session import engine

with engine.connect() as conn:
    conn.execute(text("DROP SCHEMA public CASCADE;"))
    conn.execute(text("CREATE SCHEMA public;"))
    conn.execute(text("GRANT ALL ON SCHEMA public TO public;"))
    conn.commit()

print("Schema dropped and recreated")
