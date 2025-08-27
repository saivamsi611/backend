import sqlite3

from flask import jsonify
def login_user(email,password):
    try:
        cann=sqlite3.connect('database.db')
        cursor=cann.cursor()
        cursor.execute("SELECT * FROM users WHERE email=? AND password=?", (email, password))
        user = cursor.fetchone()
        cann.close()
        if user:
            return (jsonify({"message": "Login successful!"}), 200)
        else:
            return (jsonify({"message": "Invalid email or password!"}), 401)
    except Exception as e:
        print("Error logging in user:", e)
        return (jsonify({"message": "Login failed!"}), 500)
    


def user_signup(username,email,password):
    try:
        conn = sqlite3.connect('database.db')
        cursor = conn.cursor()
        cursor.execute("INSERT INTO users (username, email, password) VALUES (?, ?, ?)", (username, email, password))
        conn.commit()
        conn.close()
        return {"status": "success", "message": "User created successfully!"}, 201
    except Exception as e:
        print("Error signing up user:", e)
        return ({"message": "User creation failed!"},500)