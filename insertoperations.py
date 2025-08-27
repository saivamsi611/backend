import sqlite3
import pandas as pd

import sqlite3
import pandas as pd
import os

def insert_csv_to_transactions_table(file_path, project_name):
    try:
        conn = sqlite3.connect("database.db")
        cursor = conn.cursor()

        required_columns = [
            "Time", "V1", "V2", "V3", "V4", "V5", "V6",
            "V7", "V8", "V9", "V10", "V11", "V12", "V13",
            "V14", "V15", "V16", "V17", "V18", "V19", "V20",
            "V21", "V22", "V23", "V24", "V25", "V26", "V27",
            "V28", "Amount", "Class"
        ]

        # Read CSV in chunks
        chunksize = 5000
        for chunk in pd.read_csv(file_path, chunksize=chunksize):
            # Check for missing columns in this chunk
            missing_cols = [col for col in required_columns if col not in chunk.columns]
            if missing_cols:
                raise ValueError(f"Missing columns in CSV chunk: {missing_cols}")

            # Prepare data safely
            data = []
            for _, row in chunk.iterrows():
                row_data = [row.get(col, None) for col in required_columns]  # safer
                data.append((project_name, *row_data))

            # Bulk insert
            cursor.executemany(
                f'''INSERT INTO transactions
                (project_name, {", ".join(required_columns)})
                VALUES ({",".join(["?"] * (len(required_columns) + 1))})''',
                data
            )
            conn.commit()

        conn.close()
        os.remove(file_path)

        return {"status": "success", "message": "CSV uploaded in chunks safely."}

    except Exception as e:
        return {"status": "error", "message": str(e)}


def save_project_summary(project_name, total_samples, fraud_count, accuracy, f1_score, auc, status="Completed"):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO project_summary (
                project_name, total_samples, fraud_count, accuracy, f1_score, auc, status
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(project_name) DO UPDATE SET
                total_samples=excluded.total_samples,
                fraud_count=excluded.fraud_count,
                accuracy=excluded.accuracy,
                f1_score=excluded.f1_score,
                auc=excluded.auc,
                status=excluded.status;
        """, (project_name, total_samples, fraud_count, accuracy, f1_score, auc, status))

        conn.commit()
        conn.close()
        print(f"📌 Project summary saved for: {project_name}")
    except Exception as e:
        print("❌ Error saving project summary:", e)
