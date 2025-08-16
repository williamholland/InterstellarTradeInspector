''' creates the data used IN a level '''

import sqlite3
from pathlib import Path
import csv

DB_PATH = Path("data/level1_example.sqlite")

VESSEL_CSV_PATH = Path("data/vessel.csv")
PASSENGER_CSV_PATH = Path("data/passenger.csv")
CARGO_CSV_PATH = Path("data/cargo.csv")
LOG_CSV_PATH = Path("data/log.csv")
PLANET_CSV_PATH = Path("data/planet.csv")

def create_table():
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Enable foreign key constraints
    cur.execute("PRAGMA foreign_keys = ON;")

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Planet (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            mass FLOAT,
            status VARCHAR
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Vessel (
            id INTEGER PRIMARY KEY,
            name VARCHAR,
            captain VARCHAR,
            type VARCHAR,
            flag INTEGER,
            FOREIGN KEY (flag) REFERENCES Planet(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Passenger (
            name VARCHAR PRIMARY KEY,
            type VARCHAR,
            nationality INTEGER,
            vessel INTEGER,
            FOREIGN KEY (nationality) REFERENCES Planet(id),
            FOREIGN KEY (vessel) REFERENCES Vessel(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Log (
            id INTEGER PRIMARY KEY,
            port INTEGER,
            arrival INTEGER,
            departure INTEGER,
            vessel INTEGER,
            FOREIGN KEY (port) REFERENCES Planet(id),
            FOREIGN KEY (vessel) REFERENCES Vessel(id)
        )
    """)

    cur.execute("""
        CREATE TABLE IF NOT EXISTS Cargo (
            id INTEGER PRIMARY KEY,
            description VARCHAR,
            category VARCHAR,
            weight FLOAT,
            hazardous BOOL,
            consignee VARCHAR,
            consignor VARCHAR,
            vessel INTEGER,
            FOREIGN KEY (vessel) REFERENCES Vessel(id)
        )
    """)

    conn.commit()
    conn.close()
    print(f"Level table created in {DB_PATH}")

def insert_from_csv():
    ''' reads all the CSVs and loads them into the tables '''
    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Planet
    with open(PLANET_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cur.executemany("""
            INSERT INTO Planet (id, name, mass, status)
            VALUES (:id, :name, :mass, :status)
        """, reader)

    # Vessel
    with open(VESSEL_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cur.executemany("""
            INSERT INTO Vessel (id, name, captain, type, flag)
            VALUES (:id, :name, :captain, :type, :flag)
        """, reader)

    # Passenger
    with open(PASSENGER_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cur.executemany("""
            INSERT INTO Passenger (name, type, nationality, vessel)
            VALUES (:name, :type, :nationality, :vessel)
        """, reader)

    # Log
    with open(LOG_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cur.executemany("""
            INSERT INTO Log (id, port, arrival, departure, vessel)
            VALUES (:id, :port, :arrival, :departure, :vessel)
        """, reader)

    # Cargo
    with open(CARGO_CSV_PATH, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        cur.executemany("""
            INSERT INTO Cargo (id, description, category, weight, hazardous, consignee, consignor, vessel)
            VALUES (:id, :description, :category, :weight, :hazardous, :consignee, :consignor, :vessel)
        """, reader)

    conn.commit()
    conn.close()
    print("CSV data inserted into database.")

if __name__ == "__main__":
    create_table()
    insert_from_csv()
