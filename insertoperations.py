import sqlite3
import pandas as pd

def insert_csv_to_transactions_table(csv_file_path,project_name):
    conn = sqlite3.connect("database.db")
    cursor = conn.cursor()

    df = pd.read_csv(csv_file_path)
    required_columns = ['Time'] + [f'V{i}' for i in range(1, 29)] + ['Amount', 'Class']
    missing_cols = [col for col in required_columns if col not in df.columns]

    if missing_cols:
        raise ValueError(f"Missing columns in CSV: {missing_cols}")

    for _, row in df.iterrows():
        cursor.execute('''
            INSERT INTO transactions (project_name,
                Time, V1, V2, V3, V4, V5, V6, V7, V8,
                V9, V10, V11, V12, V13, V14, V15, V16, V17, V18,
                V19, V20, V21, V22, V23, V24, V25, V26, V27, V28,
                Amount, Class
            ) VALUES (?,?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (project_name, *[row[col] for col in required_columns]))

    conn.commit()
    conn.close()
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
