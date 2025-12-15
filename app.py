from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import sqlite3
import os
from datetime import datetime
import pandas as pd
import io

app = Flask(__name__)
app.secret_key = "beyond_snack_secret_key"

DB = "beyond.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

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
# USERS / ROLES
# -----------------------------
USERS = {
    "Linto@drjackfruit.com":   {"password": "DJF@123", "role": "log"},
    "qc@drjackfruit.com":      {"password": "DJF@123", "role": "quality"},
    "Rakesh@drjackfruit.com":  {"password": "DJF@123", "role": "manager"},
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
# LEAK TEST
# -----------------------------
@app.route("/leak", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def leak_page():
    if request.method == "POST":
        db = get_db()
        db.execute("""
            INSERT INTO leak_tests
            (date,line,flavour,grammage,pressure,result)
            VALUES (?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            request.form.get("pressure"),
            request.form.get("result")
        ))
        db.commit()
        db.close()
        flash("Leak test saved", "success")

    return render_template("form_leak.html")

# -----------------------------
# OXYGEN TEST
# -----------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def oxygen_page():
    if request.method == "POST":
        db = get_db()
        db.execute("""
            INSERT INTO oxygen_tests
            (date,line,flavour,grammage,temperature,oxygen)
            VALUES (?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            float(request.form.get("temperature")),
            float(request.form.get("oxygen"))
        ))
        db.commit()
        db.close()
        flash("Oxygen test saved", "success")

    return render_template("form_oxygen.html")

# -----------------------------
# BREAKAGE
# -----------------------------
@app.route("/breakage", methods=["GET", "POST"])
@login_required(["quality", "manager"])
def breakage_page():
    if request.method == "POST":
        db = get_db()
        db.execute("""
            INSERT INTO breakage
            (date,line,product_code,good,broken,cluster,residue)
            VALUES (?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("product_code"),
            float(request.form.get("good")),
            float(request.form.get("broken")),
            float(request.form.get("cluster")),
            float(request.form.get("residue"))
        ))
        db.commit()
        db.close()
        flash("Breakage saved", "success")

    return render_template("form_breakage.html")

# -----------------------------
# PRODUCTION LOG
# -----------------------------
@app.route("/log", methods=["GET", "POST"])
@login_required(["log", "manager"])
def log_page():
    if request.method == "POST":
        db = get_db()
        db.execute("""
            INSERT INTO production_log
            (date,time,line,action,stop_reason)
            VALUES (?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            request.form.get("line"),
            request.form.get("action"),
            request.form.get("stop_reason", "")
        ))
        db.commit()
        db.close()
        flash("Log entry saved", "success")

    return render_template("form_production.html")

# -----------------------------
# DASHBOARD
# -----------------------------
@app.route("/dashboard")
@login_required(["manager"])
def dashboard():
    return render_template("dashboard.html")

# -----------------------------
# DASHBOARD API (THIS WAS MISSING)
# -----------------------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@login_required(["manager"])
def dashboard_api():
    db = get_db()

    leak = db.execute("SELECT result FROM leak_tests").fetchall()
    oxy = db.execute("SELECT oxygen FROM oxygen_tests").fetchall()
    brk = db.execute("SELECT broken FROM breakage").fetchall()
    stop = db.execute("SELECT stop_reason FROM production_log WHERE action='STOP'").fetchall()

    db.close()

    pass_count = sum(1 for r in leak if r["result"] == "Pass")
    total = len(leak) if leak else 1

    return {
        "kpi": {
            "pass_rate": round(pass_count / total * 100, 2),
            "avg_oxygen": round(sum(r["oxygen"] for r in oxy) / len(oxy), 2) if oxy else "-",
            "avg_breakage": round(sum(r["broken"] for r in brk) / len(brk), 2) if brk else "-",
            "top_stop": stop[0]["stop_reason"] if stop else "-"
        },
        "leak": {"date": [], "pass": [], "fail": []},
        "oxygen": {"date": [], "oxygen": []},
        "breakage": {"code": [], "broken": []},
        "stop": {"label": [], "count": []}
    }

# -----------------------------
# REPORTS PAGE
# -----------------------------
@app.route("/reports")
@login_required(["manager"])
def reports():
    return render_template("reports.html")

# -----------------------------
# EXPORT HELPERS
# -----------------------------
def export_excel(filename, df):
    output = io.BytesIO()
    df.to_excel(output, index=False)
    output.seek(0)

    return send_file(
        output,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


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
    app.run(host="0.0.0.0", port=8080)

