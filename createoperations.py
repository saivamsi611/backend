import datetime
import sqlite3
from datetime import date 
from flask import jsonify
import sqlite3
def createtable():
    try:
        conn=sqlite3.connect('database.db')
        cursor=conn.cursor()
        cursor.execute('''CREATE TABLE IF NOT EXISTS users
                        (id INTEGER PRIMARY KEY AUTOINCREMENT,
                        username TEXT NOT NULL,
                        email TEXT NOT NULL,
                        password TEXT NOT NULL
                    )''')
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error creating table:", e)
        

def create_csv_table():
    try:
        conn=sqlite3.connect('database.db')
        cursor=conn.cursor()
        cursor.execute("""
CREATE TABLE  IF NOT EXISTS transactions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    project_name text,    -- new column to identify project
    Time REAL,
    V1 REAL,
    V2 REAL,
    V3 REAL,
    V4 REAL,
    V5 REAL,
    V6 REAL,
    V7 REAL,
    V8 REAL,
    V9 REAL,
    V10 REAL,
    V11 REAL,
    V12 REAL,
    V13 REAL,
    V14 REAL,
    V15 REAL,
    V16 REAL,
    V17 REAL,
    V18 REAL,
    V19 REAL,
    V20 REAL,
    V21 REAL,
    V22 REAL,
    V23 REAL,
    V24 REAL,
    V25 REAL,
    V26 REAL,
    V27 REAL,
    V28 REAL,
    Amount REAL,
    Class INTEGER
    );

""")
        conn.commit()
        conn.close()
    except Exception as e:
        print("Error creating table:", e)
def create_project_summary_table():
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS project_summary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_name TEXT UNIQUE NOT NULL,
                total_samples INTEGER,
                fraud_count INTEGER,
                accuracy REAL,
                f1_score REAL,
                auc REAL,
                status TEXT DEFAULT 'Idle',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        conn.commit()
        conn.close()
        print("✅ project_summary table created or already exists.")
    except Exception as e:
        print("❌ Error creating project_summary table:", e)
