''' creates the data for the level METADATA '''

import sqlite3
from pathlib import Path
import csv

DB_PATH = Path("data/level_meta.sqlite")
CSV_PATH = Path("data/level_meta.csv")

def create_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Level (
            id INTEGER PRIMARY KEY,
            title VARCHAR,
            pretext TEXT,
            posttext TEXT,
            solution_sql TEXT,
            solved BOOLEAN
        )
    """)

    conn.commit()
    conn.close()
    print(f"Level table created in {DB_PATH}")

def insert_from_csv():
    if not CSV_PATH.exists():
        print(f"CSV file not found: {CSV_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    with open(CSV_PATH, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        rows = [
            (
                int(row["id"]),
                row["title"],
                row["pretext"],
                row["posttext"],
                row["solution_sql"],
                row.get("solved", "0") in ("1", "true", "True")
            )
            for row in reader
        ]

    cur.executemany("""
        INSERT OR REPLACE INTO Level
        (id, title, pretext, posttext, solution_sql, solved)
        VALUES (?, ?, ?, ?, ?, ?)
    """, rows)

    conn.commit()
    conn.close()
    print(f"Inserted {len(rows)} rows from {CSV_PATH} into {DB_PATH}")

if __name__ == "__main__":
    create_table()
    insert_from_csv()
