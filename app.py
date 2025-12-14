from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import os
import sqlite3
from datetime import datetime
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = "super_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB = "beyond.db"

# ---------------------------------------------------------
# DATABASE CONNECTION & CREATION
# ---------------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables():
    conn = get_db()
    c = conn.cursor()

    # LEAK TEST (pressure added)
    c.execute("""
        CREATE TABLE IF NOT EXISTS leak_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            line TEXT,
            flavour TEXT,
            grammage TEXT,
            pressure TEXT,
            result TEXT,
            photo TEXT,
            remarks TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS oxygen_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            line TEXT,
            flavour TEXT,
            grammage TEXT,
            temperature REAL,
            oxygen REAL,
            photo TEXT,
            remarks TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS breakage (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            line TEXT,
            product_code TEXT,
            good REAL,
            broken REAL,
            cluster REAL,
            residue REAL,
            photo TEXT,
            remarks TEXT
        )
    """)

    c.execute("""
        CREATE TABLE IF NOT EXISTS production_log (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            time TEXT,
            line TEXT,
            action TEXT,
            stop_reason TEXT,
            stop_other TEXT
        )
    """)

    conn.commit()
    conn.close()


create_tables()

# ---------------------------------------------------------
# FILE SAVING UTILITY
# ---------------------------------------------------------
def save_file(file):
    if not file or not file.filename:
        return None
    name = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
    file.save(os.path.join(UPLOAD_FOLDER, name))
    return f"{UPLOAD_FOLDER}/{name}"

# ---------------------------------------------------------
# AUTHENTICATION
# ---------------------------------------------------------
employee_pass = ["1111", "2222", "3333"]
boss_pass = ["9999", "8888"]


def requires_role(allow_employee=False):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            role = session.get("role")
            if role == "boss":
                return fn(*args, **kwargs)
            if allow_employee and role == "employee":
                return fn(*args, **kwargs)
            return abort(403)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# ---------------------------------------------------------
# LOGIN
# ---------------------------------------------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("passcode")

        if code in employee_pass:
            session["role"] = "employee"
            return redirect(url_for("index"))

        if code in boss_pass:
            session["role"] = "boss"
            return redirect(url_for("index"))

        flash("Invalid passcode", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ---------------------------------------------------------
# HOME
# ---------------------------------------------------------
@app.route("/index")
@requires_role(allow_employee=True)
def index():
    return render_template("index.html")

# ---------------------------------------------------------
# LEAK TEST
# ---------------------------------------------------------
@app.route("/leak", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def leak_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO leak_tests
            (date, line, flavour, grammage, pressure, result, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            request.form.get("pressure"),
            request.form.get("result"),
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Leak test submitted!", "success")
    return render_template("form_leak.html")

# ---------------------------------------------------------
# OXYGEN TEST
# ---------------------------------------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def oxygen_page():
    if request.method == "POST":
        try:
            temp = float(request.form.get("temperature") or 0)
        except:
            temp = 0
        try:
            oxy = float(request.form.get("oxygen") or 0)
        except:
            oxy = 0

        conn = get_db()
        conn.execute("""
            INSERT INTO oxygen_tests
            (date, line, flavour, grammage, temperature, oxygen, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            temp,
            oxy,
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test submitted!", "success")
    return render_template("form_oxygen.html")

# ---------------------------------------------------------
# BREAKAGE
# ---------------------------------------------------------
@app.route("/breakage", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def breakage_page():
    def to_float(x):
        try:
            return float(x or 0)
        except:
            return 0.0

    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO breakage
            (date, line, product_code, good, broken, cluster, residue, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("product_code"),
            to_float(request.form.get("good")),
            to_float(request.form.get("broken")),
            to_float(request.form.get("cluster")),
            to_float(request.form.get("residue")),
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Breakage data submitted!", "success")
    return render_template("form_breakage.html")

# ---------------------------------------------------------
# PRODUCTION LOG
# ---------------------------------------------------------
@app.route("/log", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def log_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO production_log
            (date, time, line, action, stop_reason, stop_other)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            request.form.get("line"),
            request.form.get("action"),
            request.form.get("stop_reason"),
            request.form.get("stop_other")
        ))
        conn.commit()
        conn.close()
        flash("Log submitted!", "success")
    return render_template("form_production.html")

# ---------------------------------------------------------
# EXPORT (MOBILE SAFE)
# ---------------------------------------------------------
def export_excel(filename, df):
    df.to_excel(filename, index=False)
    return send_file(
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/export/leak_tests")
@requires_role(allow_employee=False)
def export_leak():
    conn = get_db()
    rows = conn.execute("""
        SELECT date,line,flavour,grammage,pressure,result
        FROM leak_tests
    """).fetchall()
    conn.close()
    df = pd.DataFrame([dict(r) for r in rows])
    return export_excel("leak_tests.xlsx", df)

# ---------------------------------------------------------
# RUN
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8080)
