from sqlalchemy import text
from app.database.session import engine
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_name FROM information_schema.tables WHERE table_schema='public';"))
    for r in res:
        print(r[0])
