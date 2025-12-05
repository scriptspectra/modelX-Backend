from app.db import engine
from sqlalchemy import text

def check_table(table_name: str):
    with engine.connect() as conn:
        # check table existence in pg_tables
        res = conn.execute(
            text("SELECT schemaname, tablename FROM pg_tables WHERE tablename = :t"),
            {"t": table_name}
        ).fetchall()
        if not res:
            print(f"table '{table_name}' does NOT exist in this database (search_path shown below)")
            # show search_path
            sp = conn.execute("SHOW search_path").fetchone()
            print("search_path:", sp)
            return False

        print(f"table '{table_name}' exists in schemas:")
        for row in res:
            print("  -", row)

        # list constraints for the table
        try:
            q = text("""
            SELECT conname, pg_get_constraintdef(c.oid) as def
            FROM pg_constraint c
            JOIN pg_class t ON t.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = t.relnamespace
            WHERE t.relname = :t;
            """)
            cons = conn.execute(q, {"t": table_name}).fetchall()
            print(f"constraints for '{table_name}':")
            if not cons:
                print("  (no constraints found)")
            for c in cons:
                print("  -", c[0], ":", c[1])
        except Exception as e:
            print("error listing constraints:", e)

        return True

if __name__ == '__main__':
    print('Checking tables...')
    check_table('newsitem')
    check_table('currency_rates')
    print('Done')
