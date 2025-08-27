import sqlite3
import tempfile
from flask import Flask, jsonify, request
from flask_cors import CORS
from createoperations import create_csv_table, create_project_summary_table, createtable
from auth import login_user, user_signup
from forgot_passward import resetpassword
from werkzeug.security import generate_password_hash
import random, string, os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from datetime import datetime
from insertoperations import insert_csv_to_transactions_table
from qmlmodel import run_qml_model

from flask_socketio import SocketIO
import threading
import eventlet
eventlet.monkey_patch()

# Initialize Flask app and load environment variables
app = Flask(__name__)
load_dotenv()

# --- CORS Setup ---
# Allow only your frontend origin, enable credentials for cookies if needed
CORS(app, resources={r"/*": {"origins": ["http://localhost:5173"]}}, supports_credentials=True)

# Add CORS headers on all responses explicitly (helps with some edge cases)
@app.after_request
def add_cors_headers(response):
    response.headers.add("Access-Control-Allow-Origin", "http://localhost:5173")
    response.headers.add("Access-Control-Allow-Headers", "Content-Type,Authorization")
    response.headers.add("Access-Control-Allow-Methods", "GET,POST,OPTIONS")
    response.headers.add("Access-Control-Allow-Credentials", "true")
    return response

# Initialize SocketIO with eventlet support and CORS allowed origins
socketio = SocketIO(app, cors_allowed_origins=["http://localhost:5173"], async_mode="eventlet")

# Store task results in memory
task_results = {}

# ---------------- Utils ---------------- #
def generate_temp_password(length=10):
    chars = string.ascii_letters + string.digits
    return ''.join(random.choice(chars) for _ in range(length))

def send_email(to_email, temp_password):
    from_email = os.getenv("SENDGRID_FROM_EMAIL")
    api_key = os.getenv("SENDGRID_API_KEY")

    if not from_email or not api_key:
        print("❌ Missing SENDGRID_FROM_EMAIL or SENDGRID_API_KEY in .env file.")
        return

    try:
        message = Mail(
            from_email=from_email,
            to_emails=to_email,
            subject="🔐 Your Temporary Password",
            plain_text_content=f"Hello,\n\nYour temporary password is: {temp_password}\n\nRegards,\nSecurity Team"
        )
        sg = SendGridAPIClient(api_key)
        sg.send(message)
        print("✅ Email sent successfully!")
    except Exception as e:
        print("❌ Error sending email:", e)

# ---------------- Routes ---------------- #

@app.route("/")
def hello():
    return "Hello, World!"

@app.route("/health", methods=["GET"])
def health_check():
    return jsonify({"status": "OK"}), 200


@app.route("/signup", methods=["POST"])
def signup():
    try:
        name = request.form.get("name")
        email = request.form.get("email")
        password = request.form.get("password")

        # Basic validation
        if not all([name, email, password]):
            return jsonify({"status": "error", "message": "All fields are required."}), 400

        # Call your user signup function
        result, code = user_signup(name, email, password)

        # Ensure result is a dict, else wrap it
        if not isinstance(result, dict):
            result = {"status": "success", "message": "Signup successful!"}
            code = 201

        return jsonify(result), code

    except Exception as e:
        # Catch unexpected errors and return JSON response
        return jsonify({"status": "error", "message": str(e)}), 500


def login():
    email = request.form.get("email")
    password = request.form.get("password")

    if not all([email, password]):
        return jsonify({"status": "error", "message": "Email and password are required."}), 400

    result, code = login_user(email, password)
    return jsonify(result), code

@app.route("/forget_password", methods=["POST"])
def forget_user_password():
    email = request.form.get("email")
    if not email:
        return jsonify({"status": "error", "message": "Email is required."}), 400

    temp_password = generate_temp_password()
    hashed_password = generate_password_hash(temp_password)
    result, code = resetpassword(email, hashed_password)

    if result.get("status") == "success":
        send_email(email, temp_password)
    return jsonify(result), code

@app.route("/upload_csv", methods=["POST"])
def upload_csv_simple():
    try:
        project_name = request.form.get("project_name")
        if not project_name:
            return jsonify({"status": "error", "message": "Project name is required."}), 400

        if "file" not in request.files:
            return jsonify({"status": "error", "message": "No file uploaded"}), 400

        file = request.files["file"]
        if file.filename == "":
            return jsonify({"status": "error", "message": "Empty filename"}), 400

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        print(f"Saved temp file at {tmp_path}")

        insert_csv_to_transactions_table(tmp_path, project_name)
        os.remove(tmp_path)

        return jsonify({"status": "success", "message": "CSV data inserted into transactions table"}), 200

    except Exception as e:
        print("Error in upload_csv_simple:", e)
        return jsonify({"status": "error", "message": str(e)}), 500

# ---------------- Training Task (Threaded) ---------------- #
def background_train(project_name):
    try:
        def progress_callback(event, data):
            print(f"[{event}] {data}")
            socketio.emit(event, {"project_name": project_name, **data})

        results = run_qml_model(
            project_name,
            include_confusion_matrix=True,
            progress_callback=progress_callback
        )
        task_results[project_name] = results
        socketio.emit("training_complete", {
            "project_name": project_name,
            "status": "success",
            "results": results
        })

    except Exception as e:
        task_results[project_name] = {"status": "error", "message": str(e)}
        socketio.emit("training_error", {
            "project_name": project_name,
            "status": "error",
            "message": str(e)
        })

@app.route("/train", methods=["GET"])
def train():
    try:
        project_name = request.args.get("project_name")
        if not project_name:
            return jsonify({"status": "error", "message": "Project name is required"}), 400

        # start training thread (no task_id)
        thread = threading.Thread(target=background_train, args=(project_name,))
        thread.start()

        return jsonify({
            "status": "success",
            "message": f"Training started for {project_name}"
        }), 202

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

@app.route("/task/<project_name>", methods=["GET"])
def get_task_result(project_name):
    result = task_results.get(project_name)
    if result:
        return jsonify({"project_name": project_name, "status": "done", "result": result})
    else:
        return jsonify({"project_name": project_name, "status": "pending"})

@socketio.on("connect")
def on_connect():
    print("✅ Socket.IO: Client connected")

@socketio.on("disconnect")
def on_disconnect():
    print("❌ Socket.IO: Client disconnected")

@socketio.on("start_training")
def handle_start_training(data):
    project_name = data.get("project_name")
    if not project_name:
        socketio.emit("training_error", {
            "status": "error",
            "message": "Missing project_name"
        })
        return

    print(f"🎬 Starting training for project: {project_name}")

    thread = threading.Thread(target=background_train, args=(project_name,))
    thread.start()

@app.route("/projects", methods=["GET"])
def get_all_projects():
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM project_summary ORDER BY created_at DESC")
        rows = cursor.fetchall()
        conn.close()

        projects = [dict(row) for row in rows]
        return jsonify({"status": "success", "projects": projects}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500
    

@app.route("/view-users", methods=["GET"])
def view_users():
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM users")
        rows = cursor.fetchall()
        conn.close()

        users = [dict(row) for row in rows]
        return jsonify({"status": "success", "users": users}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500



@app.route("/view_transactions", methods=["GET"])
def view_transactions():
    try:
        conn = sqlite3.connect("database.db")
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # Fetch all rows from transactions table
        cursor.execute("SELECT * FROM transactions")
        rows = cursor.fetchall()
        conn.close()

        transactions = [dict(row) for row in rows]
        return jsonify({"status": "success", "transactions": transactions}), 200

    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500

# ------------- Initialization outside __main__ ------------- #
# This ensures DB tables are ready on import (for Gunicorn)
create_csv_table()
createtable()
create_project_summary_table()

# ------------- Run server if executed directly ------------- #
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    socketio.run(app, host="0.0.0.0", port=port)
