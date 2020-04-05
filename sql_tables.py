import sqlite3
import pandas as pd

connection = sqlite3.connect('database.db')
cursor = connection.cursor()


cursor.execute("DROP TABLE IF EXISTS qr_codes")

cursor.execute("""
CREATE TABLE qr_codes(
    code_id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    message TEXT NOT NULL,
    qr_url TEXT,
    file_name TEXT,
    qr_file TEXT,
    view_count INTEGER,
    date_created date default current_date
    );
""")

# cursor.execute("""
# INSERT INTO qr_codes( file_id,qr_url, title,message)
# VALUES (99999,"test.test/?id=test","Test Title","test test test test")
# """)

# cursor.execute("DELETE FROM qr_codes;")

# print(pd.read_sql_query("SELECT * FROM qr_codes",connection))

connection.commit()
connection.close()
