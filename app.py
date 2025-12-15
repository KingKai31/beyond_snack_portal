from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import sqlite3
import os
from datetime import datetime
import pandas as pd

# -------------------------------------------------
# APP SETUP
# -------------------------------------------------
app = Flask(__name__)
app.secret_key = "beyond_snack_secret_key"

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB = os.path.join(BASE_DIR, "beyond.db")

UPLOAD_FOLDER = os.path.join(BASE_DIR, "static", "uploads")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------------------------
# USERS & ROLES
# -------------------------------------------------
USERS = {
    "Linto@drjackfruit.com": {
        "password": "DJF@123",
        "role": "log"
    },
    "qc@drjackfruit.com": {
        "password": "DJF@123",
        "role": "quality"
    },
    "Rakesh@drjackfruit.com": {
        "password": "DJF@123",
        "role": "manager"
    }
}

# -------------------------------------------------
# DATABASE
# -------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    cur = conn.cursor()

    cur.execute("""
    CREATE TABLE IF NOT EXISTS leak_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        line TEXT,
        flavour TEXT,
        grammage TEXT,
        pressure TEXT,
        result TEXT,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS oxygen_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        line TEXT,
        flavour TEXT,
        grammage TEXT,
        temperature REAL,
        oxygen REAL,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS breakage (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        line TEXT,
        product_code TEXT,
        good REAL,
        broken REAL,
        cluster REAL,
        residue REAL,
        remarks TEXT
    )
    """)

    cur.execute("""
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        line TEXT,
        action TEXT,
        stop_reason TEXT
    )
    """)

    conn.commit()
    conn.close()


init_db()

# -------------------------------------------------
# AUTH DECORATOR
# -------------------------------------------------
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

# -------------------------------------------------
# LOGIN / LOGOUT
# -------------------------------------------------
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

# -------------------------------------------------
# MAIN MENU
# -------------------------------------------------
@app.route("/index")
@login_required(roles=["log", "quality", "manager"])
def index():
    return render_template("index.html")

# -------------------------------------------------
# LEAK TEST
# -------------------------------------------------
@app.route("/leak", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def leak_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO leak_tests (date,line,flavour,grammage,pressure,result,remarks)
        VALUES (?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            request.form["pressure"],
            request.form["result"],
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Leak test saved", "success")

    return render_template("form_leak.html")

# -------------------------------------------------
# OXYGEN TEST
# -------------------------------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def oxygen_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO oxygen_tests (date,line,flavour,grammage,temperature,oxygen,remarks)
        VALUES (?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            float(request.form["temperature"]),
            float(request.form["oxygen"]),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test saved", "success")

    return render_template("form_oxygen.html")

# -------------------------------------------------
# BREAKAGE
# -------------------------------------------------
@app.route("/breakage", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def breakage_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO breakage (date,line,product_code,good,broken,cluster,residue,remarks)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["product_code"],
            float(request.form["good"]),
            float(request.form["broken"]),
            float(request.form["cluster"]),
            float(request.form["residue"]),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Breakage saved", "success")

    return render_template("form_breakage.html")

# -------------------------------------------------
# PRODUCTION LOG
# -------------------------------------------------
@app.route("/log", methods=["GET", "POST"])
@login_required(roles=["log", "manager"])
def log():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO production_log (date,time,line,action,stop_reason)
        VALUES (?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            request.form["line"],
            request.form["action"],
            request.form.get("stop_reason")
        ))
        conn.commit()
        conn.close()
        flash("Log saved", "success")

    return render_template("form_production.html")

# -------------------------------------------------
# DASHBOARD
# -------------------------------------------------
@app.route("/dashboard")
@login_required(roles=["manager"])
def dashboard():
    return render_template("dashboard.html")

# -------------------------------------------------
# REPORTS
# -------------------------------------------------
@app.route("/reports")
@login_required(roles=["manager"])
def reports():
    return render_template("reports.html")

# -------------------------------------------------
# EXPORTS
# -------------------------------------------------
def export_excel(filename, df):
    df.to_excel(filename, index=False)
    return send_file(filename, as_attachment=True)


@app.route("/export/leak")
@login_required(roles=["manager"])
def export_leak():
    conn = get_db()
    rows = conn.execute("SELECT * FROM leak_tests").fetchall()
    conn.close()
    return export_excel("leak_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/oxygen")
@login_required(roles=["manager"])
def export_oxygen():
    conn = get_db()
    rows = conn.execute("SELECT * FROM oxygen_tests").fetchall()
    conn.close()
    return export_excel("oxygen_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/breakage")
@login_required(roles=["manager"])
def export_breakage():
    conn = get_db()
    rows = conn.execute("SELECT * FROM breakage").fetchall()
    conn.close()
    return export_excel("breakage.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/log")
@login_required(roles=["manager"])
def export_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM production_log").fetchall()
    conn.close()
    return export_excel("production_log.xlsx", pd.DataFrame([dict(r) for r in rows]))

# -------------------------------------------------
# RUN
# -------------------------------------------------
if __name__ == "__main__":
    app.run(debug=True)
