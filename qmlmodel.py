import time
import numpy as np
import pandas as pd
import sqlite3
from sklearn.model_selection import train_test_split
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (
    accuracy_score, f1_score, roc_auc_score, classification_report, roc_curve, confusion_matrix
)
from imblearn.over_sampling import SMOTE
import pennylane as qml
from pennylane import numpy as pnp

from insertoperations import save_project_summary

def run_qml_model(project_name, include_confusion_matrix=False, progress_callback=None):
    import time
    conn = sqlite3.connect("database.db")
    query = """
        SELECT Time, V1, V2, V3, V4, V5, V6, V7, V8, V9,
               V10, V11, V12, V13, V14, V15, V16, V17,
               V18, V19, V20, V21, V22, V23, V24, V25,
               V26, V27, V28, Amount, Class
        FROM transactions
        WHERE project_name = ?
    """
    df = pd.read_sql_query(query, conn, params=(project_name,))
    conn.close()

    if df.empty:
        raise ValueError(f"No data found for project: {project_name}")

    X = df.drop("Class", axis=1).values
    y = df["Class"].values

    if len(np.unique(y)) > 1 and len(y) > 10:
        X_res, y_res = SMOTE(random_state=42).fit_resample(X, y)
    else:
        X_res, y_res = X, y

    X_scaled = StandardScaler().fit_transform(X_res)
    n_components = min(2, X_scaled.shape[1])
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X_scaled)

    X_train, X_test, y_train, y_test = train_test_split(
        X_pca, y_res, test_size=0.2, random_state=42, stratify=y_res
    )

    # ---------------- Quantum Circuit ---------------- #
    n_qubits = n_components
    dev = qml.device("lightning.qubit", wires=n_qubits)

    def feature_map(x):
        qml.AngleEmbedding(x, wires=range(n_qubits), rotation='Y')

    def variational_block(weights):
        for i in range(n_qubits):
            qml.Rot(*weights[i], wires=i)
        for i in range(n_qubits - 1):
            qml.CNOT(wires=[i, i + 1])

    @qml.qnode(dev)
    def quantum_circuit(x, weights):
        feature_map(x)
        variational_block(weights)
        return qml.expval(qml.PauliZ(0))

    weights = pnp.array(pnp.random.randn(n_qubits, 3), requires_grad=True)

    def predict(x, weights):
        x = pnp.array(x, requires_grad=False)  # ✅ FIX: Ensure compatibility
        return (quantum_circuit(x, weights) + 1) / 2

    def loss_fn(X, y, weights):
        preds = [predict(x, weights) for x in X]
        preds = pnp.clip(pnp.array(preds), 1e-6, 1 - 1e-6)
        return -pnp.mean(y * pnp.log(preds) + (1 - y) * pnp.log(1 - preds))

    # ---------------- Training ---------------- #
    opt = qml.GradientDescentOptimizer(stepsize=0.1)
    epochs = 10
    batch_size = min(64, len(X_train))

    loss_history, acc_history, f1_history, auc_history = [], [], [], []

    for epoch in range(1, epochs + 1):
        epoch_start = time.time()

        batch_size = min(batch_size, len(X_train))
        batch_idx = np.random.choice(len(X_train), batch_size, replace=False)
        X_batch, y_batch = X_train[batch_idx], y_train[batch_idx]

        weights, batch_loss = opt.step_and_cost(lambda w: loss_fn(X_batch, y_batch, w), weights)
        loss_history.append(float(batch_loss))

        y_val_probs = np.array([predict(x, weights) for x in X_test])
        y_val = (y_val_probs > 0.5).astype(int)

        acc_val = accuracy_score(y_test, y_val)
        f1_val = f1_score(y_test, y_val)
        auc_val = roc_auc_score(y_test, y_val_probs) if len(np.unique(y_test)) > 1 else 0.5

        acc_history.append(acc_val)
        f1_history.append(f1_val)
        auc_history.append(auc_val)

        if progress_callback:
            progress_callback("training_progress", {
                "project_name": project_name,
                "epoch": epoch,
                "total_epochs": epochs,
                "loss": float(batch_loss),
                "accuracy": float(acc_val),
                "f1": float(f1_val),
                "auc": float(auc_val),
                "progress": round((epoch / epochs) * 100, 2),
                "duration_sec": round(time.time() - epoch_start, 2)
            })

    # ---------------- Final Evaluation ---------------- #
    y_pred_probs = np.array([predict(x, weights) for x in X_test])
    y_pred = (y_pred_probs > 0.5).astype(int)

    acc = accuracy_score(y_test, y_pred)
    f1 = f1_score(y_test, y_pred)
    roc = roc_auc_score(y_test, y_pred_probs) if len(np.unique(y_test)) > 1 else 0.5
    fpr, tpr, _ = roc_curve(y_test, y_pred_probs) if len(np.unique(y_test)) > 1 else ([0, 1], [0, 1])

    cm = confusion_matrix(y_test, y_pred) if include_confusion_matrix else None

    if progress_callback:
        progress_callback("training_progress", {
            "project_name": project_name,
            "epoch": epochs,
            "total_epochs": epochs,
            "loss": float(loss_history[-1]),
            "progress": 100,
            "final": True,
            "accuracy": float(acc),
            "f1": float(f1),
            "auc": float(roc),
            "message": f"✅ Final Accuracy: {acc:.4f}, F1: {f1:.4f}, AUC: {roc:.4f}"
        })

    def downsample(arr, step=10):
        return arr[::step].tolist()

    results = {
        "summary": {
            "project": project_name,
            "total_samples": len(df),
            "train_size": len(X_train),
            "test_size": len(X_test),
            "accuracy": round(acc, 4),
            "f1_score": round(f1, 4),
            "roc_auc": round(roc, 4),
            "pca_variance": pca.explained_variance_ratio_.tolist()
        },
        "charts": {
            "loss_curve": loss_history,
            "accuracy_curve": acc_history,
            "f1_curve": f1_history,
            "auc_curve": auc_history,
            "roc_curve": {
                "fpr": downsample(fpr, 10),
                "tpr": downsample(tpr, 10),
            },
            **({"confusion_matrix": cm.tolist()} if include_confusion_matrix else {}),
        },
        "classification_report": classification_report(y_test, y_pred, output_dict=True)
    }

    fraud_count = sum(y)  # Count of frauds in original dataset

    save_project_summary(
        project_name=project_name,
        total_samples=len(df),
        fraud_count=fraud_count,
        accuracy=acc,
        f1_score=f1,
        auc=roc,
        status="Completed"
    )

    return results
