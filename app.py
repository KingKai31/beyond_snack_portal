from flask import Flask, render_template, request, redirect, url_for, flash, send_file, session, abort
import sqlite3
import os
from datetime import datetime
import pandas as pd

# --------------------
# APP SETUP
# --------------------
app = Flask(__name__)
app.secret_key = "beyond_snack_secret"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "beyond.db")
UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------
# USERS & ROLES
# --------------------
USERS = {
    "Linto@drjackfruit.com":  {"password": "DJF@123", "role": "log"},
    "qc@drjackfruit.com":     {"password": "DJF@123", "role": "quality"},
    "Rakesh@drjackfruit.com": {"password": "DJF@123", "role": "manager"},
}

# --------------------
# DATABASE
# --------------------
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS leak_tests (
        id INTEGER PRIMARY KEY,
        date TEXT,
        line TEXT,
        flavour TEXT,
        grammage TEXT,
        pressure TEXT,
        result TEXT
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS oxygen_tests (
        id INTEGER PRIMARY KEY,
        date TEXT,
        line TEXT,
        flavour TEXT,
        grammage TEXT,
        temperature REAL,
        oxygen REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS breakage (
        id INTEGER PRIMARY KEY,
        date TEXT,
        line TEXT,
        product_code TEXT,
        broken REAL
    )
    """)

    c.execute("""
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY,
        date TEXT,
        time TEXT,
        line TEXT,
        action TEXT,
        reason TEXT
    )
    """)

    conn.commit()
    conn.close()

init_db()

# --------------------
# AUTH DECORATOR
# --------------------
def login_required(roles=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user_id" not in session:
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# --------------------
# LOGIN
# --------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user_id = request.form["id"]
        password = request.form["password"]

        user = USERS.get(user_id)
        if user and user["password"] == password:
           session["user_id"] = user_id
           session["role"] = user["role"]
           return redirect(url_for("index"))

        flash("Invalid login", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------
# MAIN MENU
# --------------------
@app.route("/index")
@login_required(["log", "quality", "manager"])
def index():
    return render_template("index.html")

# --------------------
# LEAK TEST
# --------------------
@app.route("/leak", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def leak():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO leak_tests (date,line,flavour,grammage,pressure,result)
        VALUES (?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            request.form["pressure"],
            request.form["result"]
        ))
        conn.commit()
        conn.close()
        flash("Leak test saved", "success")
    return render_template("form_leak.html")

# --------------------
# OXYGEN TEST
# --------------------
@app.route("/oxygen", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def oxygen():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO oxygen_tests (date,line,flavour,grammage,temperature,oxygen)
        VALUES (?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            float(request.form["temperature"]),
            float(request.form["oxygen"])
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test saved", "success")
    return render_template("form_oxygen.html")

# --------------------
# BREAKAGE
# --------------------
@app.route("/breakage", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def breakage():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO breakage (date,line,product_code,broken)
        VALUES (?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["product_code"],
            float(request.form["broken"])
        ))
        conn.commit()
        conn.close()
        flash("Breakage saved", "success")
    return render_template("form_breakage.html")

# --------------------
# PRODUCTION LOG
# --------------------
@app.route("/log", methods=["GET", "POST"])
@login_required(["log", "manager"])
def log():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO production_log (date,time,line,action,reason)
        VALUES (?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M"),
            request.form["line"],
            request.form["action"],
            request.form.get("reason")
        ))
        conn.commit()
        conn.close()
        flash("Log saved", "success")
    return render_template("form_production.html")

# --------------------
# REPORTS
# --------------------
@app.route("/reports")
@login_required(["manager"])
def reports():
    return render_template("reports.html")

# --------------------
# EXPORTS
# --------------------
@app.route("/export/leak")
@login_required(["manager"])
def export_leak():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM leak_tests", conn)
    conn.close()
    file = "leak.xlsx"
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)

@app.route("/export/oxygen")
@login_required(["manager"])
def export_oxygen():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM oxygen_tests", conn)
    conn.close()
    file = "oxygen.xlsx"
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)

@app.route("/export/log")
@login_required(["manager"])
def export_log():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM production_log", conn)
    conn.close()
    file = "log.xlsx"
    df.to_excel(file, index=False)
    return send_file(file, as_attachment=True)

# --------------------
# ERRORS
# --------------------
@app.errorhandler(403)
def forbidden(e):
    return "Access denied", 403

@app.errorhandler(500)
def server_error(e):
    return "Server error. Check logs.", 500

# --------------------
# RUN
# --------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)

