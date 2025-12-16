from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import sqlite3, os, io
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "beyond_snack_secret_key"

DB = "beyond.db"

# -----------------------------
# DATABASE
# -----------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    db = get_db()
    c = db.cursor()

    c.execute("""CREATE TABLE IF NOT EXISTS leak_tests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, line TEXT, flavour TEXT, grammage TEXT,
        pressure TEXT, result TEXT
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS oxygen_tests(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, line TEXT, flavour TEXT, grammage TEXT,
        temperature REAL, oxygen REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS breakage(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, line TEXT, product_code TEXT,
        good REAL, broken REAL, cluster REAL, residue REAL
    )""")

    c.execute("""CREATE TABLE IF NOT EXISTS production_log(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT, time TEXT, line TEXT,
        action TEXT, stop_reason TEXT
    )""")

    db.commit()
    db.close()

init_db()

# -----------------------------
# USERS
# -----------------------------
USERS = {
    "Linto@drjackfruit.com":  {"password": "DJF@123", "role": "log"},
    "qc@drjackfruit.com":     {"password": "DJF@123", "role": "quality"},
    "Rakesh@drjackfruit.com": {"password": "DJF@123", "role": "manager"},
}

def login_required(roles=None):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if "user" not in session:
                return redirect(url_for("login"))
            if roles and session.get("role") not in roles:
                abort(403)
            return fn(*args, **kwargs)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# -----------------------------
# LOGIN
# -----------------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = USERS.get(email)
        if user and user["password"] == password:
            session["user"] = email
            session["role"] = user["role"]
            return redirect(url_for("index"))

        flash("Invalid login", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# -----------------------------
# MAIN MENU
# -----------------------------
@app.route("/index")
@login_required()
def index():
    return render_template("index.html")

# -----------------------------
# PAGES
# -----------------------------
@app.route("/leak", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def leak_page():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO leak_tests VALUES (NULL,?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d"),
             request.form["line"], request.form["flavour"],
             request.form["grammage"], request.form["pressure"],
             request.form["result"])
        )
        db.commit()
        db.close()
    return render_template("form_leak.html")

@app.route("/oxygen", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def oxygen_page():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO oxygen_tests VALUES (NULL,?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d"),
             request.form["line"], request.form["flavour"],
             request.form["grammage"],
             float(request.form["temperature"]),
             float(request.form["oxygen"]))
        )
        db.commit()
        db.close()
    return render_template("form_oxygen.html")

@app.route("/breakage", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def breakage_page():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO breakage VALUES (NULL,?,?,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d"),
             request.form["line"], request.form["product_code"],
             float(request.form["good"]), float(request.form["broken"]),
             float(request.form["cluster"]), float(request.form["residue"]))
        )
        db.commit()
        db.close()
    return render_template("form_breakage.html")

@app.route("/log", methods=["GET", "POST"])
@login_required(["log", "manager"])
def log_page():
    if request.method == "POST":
        db = get_db()
        db.execute(
            "INSERT INTO production_log VALUES (NULL,?,?,?,?,?)",
            (datetime.now().strftime("%Y-%m-%d"),
             datetime.now().strftime("%H:%M:%S"),
             request.form["line"], request.form["action"],
             request.form.get("stop_reason", ""))
        )
        db.commit()
        db.close()
    return render_template("form_production.html")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
@login_required(["manager"])
def dashboard():
    return render_template("dashboard.html")

@app.route("/api/dashboard_data_v2", methods=["POST"])
@login_required(["manager"])
def dashboard_api():
    return {"kpi": {}, "leak": {}, "oxygen": {}, "breakage": {}, "stop": {}}

# -----------------------------
# EXPORTS
# -----------------------------
def export_excel(name, df):
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False)
    buffer.seek(0)
    return send_file(buffer, as_attachment=True, download_name=name)

@app.route("/export/leak")
@login_required(["manager"])
def export_leak():
    db = get_db()
    rows = db.execute("SELECT * FROM leak_tests").fetchall()
    db.close()
    return export_excel("leak_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/oxygen")
@login_required(["manager"])
def export_oxygen():
    db = get_db()
    rows = db.execute("SELECT * FROM oxygen_tests").fetchall()
    db.close()
    return export_excel("oxygen_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/breakage")
@login_required(["manager"])
def export_breakage():
    db = get_db()
    rows = db.execute("SELECT * FROM breakage").fetchall()
    db.close()
    return export_excel("breakage.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/log")
@login_required(["manager"])
def export_log():
    db = get_db()
    rows = db.execute("SELECT * FROM production_log").fetchall()
    db.close()
    return export_excel("production_log.xlsx", pd.DataFrame([dict(r) for r in rows]))

# -----------------------------
# RUN
# -----------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)


