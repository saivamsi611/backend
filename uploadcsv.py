import pandas as pd
import sqlite3
from datetime import date

def upload_csv_to_db(csv_file_obj, project_name):
    try:
        df = pd.read_csv(csv_file_obj)  # Read from file object

        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        for index, row in df.iterrows():
            cursor.execute("""
                INSERT INTO transactions 
                (projectname, Time, V1, V2, V3, V4, V5, V6, V7, V8, V9, V10, V11, V12, V13, V14, V15, V16, V17, V18, V19, V20, V21, V22, V23, V24, V25, V26, V27, V28, Amount, Class)
                VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                project_name, row['Time'], row['V1'], row['V2'], row['V3'], row['V4'], row['V5'],
                row['V6'], row['V7'], row['V8'], row['V9'], row['V10'], row['V11'], row['V12'],
                row['V13'], row['V14'], row['V15'], row['V16'], row['V17'], row['V18'], row['V19'],
                row['V20'], row['V21'], row['V22'], row['V23'], row['V24'], row['V25'], row['V26'],
                row['V27'], row['V28'], row['Amount'], row['Class']
            ))

        conn.commit()
        conn.close()

        return {
            "project_name": project_name,
            "date": str(date.today()),
            "status": "success",
            "message": "CSV uploaded and data inserted successfully."
        }, 201

    except Exception as e:
        return {
            "status": "error",
            "message": str(e)
        }, 500
