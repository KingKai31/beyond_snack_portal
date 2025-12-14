from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import os
import sqlite3
from datetime import datetime
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = "beyond_snack_secret"

DB = "beyond.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# --------------------------------------------------
# DATABASE
# --------------------------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# --------------------------------------------------
# USERS & ROLES
# --------------------------------------------------
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

def role_required(*roles):
    def decorator(fn):
        def wrapper(*args, **kwargs):
            if session.get("role") in roles:
                return fn(*args, **kwargs)
            abort(403)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# --------------------------------------------------
# LOGIN
# --------------------------------------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")

        user = USERS.get(email)

        if user and user["password"] == password:
            session["email"] = email
            session["role"] = user["role"]
            return redirect(url_for("index"))

        flash("Invalid email or password", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# --------------------------------------------------
# MAIN MENU
# --------------------------------------------------
@app.route("/index")
@role_required("log", "quality", "manager")
def index():
    return render_template("index.html")

# --------------------------------------------------
# LEAK TEST
# --------------------------------------------------
@app.route("/leak", methods=["GET", "POST"])
@role_required("quality", "manager")
def leak_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO leak_tests
            (date, line, flavour, grammage, result, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            request.form["result"],
            None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Leak test submitted", "success")
    return render_template("form_leak.html")

# --------------------------------------------------
# OXYGEN TEST
# --------------------------------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@role_required("quality", "manager")
def oxygen_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO oxygen_tests
            (date, line, flavour, grammage, temperature, oxygen, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            float(request.form["temperature"]),
            float(request.form["oxygen"]),
            None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test submitted", "success")
    return render_template("form_oxygen.html")

# --------------------------------------------------
# BREAKAGE
# --------------------------------------------------
@app.route("/breakage", methods=["GET", "POST"])
@role_required("quality", "manager")
def breakage_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO breakage
            (date, line, product_code, good, broken, cluster, residue, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["product_code"],
            float(request.form["good"]),
            float(request.form["broken"]),
            float(request.form["cluster"]),
            float(request.form["residue"]),
            None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Breakage submitted", "success")
    return render_template("form_breakage.html")

# --------------------------------------------------
# PRODUCTION LOG
# --------------------------------------------------
@app.route("/log", methods=["GET", "POST"])
@role_required("log", "manager")
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
            request.form["line"],
            request.form["action"],
            request.form.get("stop_reason"),
            request.form.get("stop_other")
        ))
        conn.commit()
        conn.close()
        flash("Log entry saved", "success")
    return render_template("form_production.html")

# --------------------------------------------------
# DASHBOARD (MANAGER ONLY)
# --------------------------------------------------
@app.route("/dashboard")
@role_required("manager")
def dashboard():
    return render_template("dashboard.html")

# --------------------------------------------------
# REPORTS PAGE (MANAGER ONLY)
# --------------------------------------------------
@app.route("/reports")
@role_required("manager")
def reports():
    return render_template("reports.html")

# --------------------------------------------------
# EXPORTS
# --------------------------------------------------
def export_excel(name, df):
    df.to_excel(name, index=False)
    return send_file(name, as_attachment=True)

@app.route("/export/leak")
@role_required("manager")
def export_leak():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM leak_tests", conn)
    conn.close()
    return export_excel("leak_tests.xlsx", df)

@app.route("/export/oxygen")
@role_required("manager")
def export_oxygen():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM oxygen_tests", conn)
    conn.close()
    return export_excel("oxygen_tests.xlsx", df)

@app.route("/export/breakage")
@role_required("manager")
def export_breakage():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM breakage", conn)
    conn.close()
    return export_excel("breakage.xlsx", df)

@app.route("/export/log")
@role_required("manager")
def export_log():
    conn = get_db()
    df = pd.read_sql("SELECT * FROM production_log", conn)
    conn.close()
    return export_excel("production_log.xlsx", df)

# --------------------------------------------------
# RUN
# --------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
