from app.db import engine
from sqlalchemy import text

sql = "SELECT setval(pg_get_serial_sequence('currency_rates','id'), COALESCE((SELECT MAX(id) FROM currency_rates), 1));"
with engine.connect() as conn:
    conn.execute(text(sql))
    conn.commit()

print('Sequence fix executed.')
