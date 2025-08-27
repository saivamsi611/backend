import sqlite3
def resetpassword(email, new_password):
   try:
      conn = sqlite3.connect("database.db")
      cursor = conn.cursor()
      cursor.execute("UPDATE users SET password = ? WHERE email = ?", (new_password, email))
      conn.commit()
      conn.close()
      return {"status": "success"}
   except Exception as e:
      return {"status": "error", "message": str(e)}
