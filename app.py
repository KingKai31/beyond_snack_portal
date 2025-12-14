from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import os
import sqlite3
from datetime import datetime
import pandas as pd
import json

app = Flask(__name__)
app.secret_key = "beyond_snack_secret_key"

# -------------------------------
# FILES & DATABASE
# -------------------------------
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
DB = "beyond.db"


# -------------------------------
# DATABASE CONNECTION
# -------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn


# -------------------------------
# CREATE TABLES
# -------------------------------
def create_tables():
    conn = get_db()
    c = conn.cursor()

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
    )""")

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
    )""")

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
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        line TEXT,
        action TEXT,
        stop_reason TEXT,
        stop_other TEXT
    )""")

    conn.commit()
    conn.close()


create_tables()


# -------------------------------
# FILE UPLOAD
# -------------------------------
def save_file(file):
    if not file or not file.filename:
        return None
    name = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    return path


# -------------------------------
# USERS & ROLES
# -------------------------------
USERS = {
    "Linto@drjackfruit.com": {"password": "DJF@123", "role": "log"},
    "qc@drjackfruit.com": {"password": "DJF@123", "role": "quality"},
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


# -------------------------------
# LOGIN / LOGOUT
# -------------------------------
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

        flash("Invalid email or password", "danger")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# -------------------------------
# MAIN MENU
# -------------------------------
@app.route("/index")
@login_required(roles=["log", "quality", "manager"])
def index():
    return render_template("index.html")


# -------------------------------
# LEAK TEST
# -------------------------------
@app.route("/leak", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def leak_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO leak_tests
        (date,line,flavour,grammage,pressure,result,photo,remarks)
        VALUES (?,?,?,?,?,?,?,?)
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
        flash("Leak test submitted", "success")
    return render_template("form_leak.html")


# -------------------------------
# OXYGEN TEST
# -------------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def oxygen_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO oxygen_tests
        (date,line,flavour,grammage,temperature,oxygen,photo,remarks)
        VALUES (?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            float(request.form.get("temperature")),
            float(request.form.get("oxygen")),
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test submitted", "success")
    return render_template("form_oxygen.html")


# -------------------------------
# BREAKAGE
# -------------------------------
@app.route("/breakage", methods=["GET", "POST"])
@login_required(roles=["quality", "manager"])
def breakage_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO breakage
        (date,line,product_code,good,broken,cluster,residue,photo,remarks)
        VALUES (?,?,?,?,?,?,?,?,?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("product_code"),
            float(request.form.get("good")),
            float(request.form.get("broken")),
            float(request.form.get("cluster")),
            float(request.form.get("residue")),
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Breakage submitted", "success")
    return render_template("form_breakage.html")


# -------------------------------
# PRODUCTION LOG
# -------------------------------
@app.route("/log", methods=["GET", "POST"])
@login_required(roles=["log", "manager"])
def log_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
        INSERT INTO production_log
        (date,time,line,action,stop_reason,stop_other)
        VALUES (?,?,?,?,?,?)
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
        flash("Log entry saved", "success")
    return render_template("form_production.html")


# -------------------------------
# DASHBOARD
# -------------------------------
@app.route("/dashboard")
@login_required(roles=["manager"])
def dashboard():
    return render_template("dashboard.html")


# -------------------------------
# REPORTS PAGE
# -------------------------------
@app.route("/reports")
@login_required(roles=["manager"])
def reports():
    return render_template("reports.html")


# -------------------------------
# EXPORT HELP
# -------------------------------
def export_excel(name, df):
    df.to_excel(name, index=False)
    return send_file(
        name,
        as_attachment=True,
        download_name=name,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


@app.route("/export/leak")
@login_required(roles=["manager"])
def export_leak():
    conn = get_db()
    rows = conn.execute("SELECT date,line,flavour,grammage,pressure,result FROM leak_tests").fetchall()
    conn.close()
    return export_excel("leak_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/oxygen")
@login_required(roles=["manager"])
def export_oxygen():
    conn = get_db()
    rows = conn.execute("SELECT date,line,flavour,grammage,temperature,oxygen FROM oxygen_tests").fetchall()
    conn.close()
    return export_excel("oxygen_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/breakage")
@login_required(roles=["manager"])
def export_breakage():
    conn = get_db()
    rows = conn.execute("SELECT date,line,product_code,good,broken,cluster,residue FROM breakage").fetchall()
    conn.close()
    return export_excel("breakage.xlsx", pd.DataFrame([dict(r) for r in rows]))


@app.route("/export/log")
@login_required(roles=["manager"])
def export_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM production_log").fetchall()
    conn.close()

    cleaned = []
    for r in rows:
        cleaned.append({
            "Date": r["date"],
            "Time": r["time"],
            "Line": r["line"],
            "Action": r["action"],
            "Stop Reason": r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        })

    return export_excel("production_log.xlsx", pd.DataFrame(cleaned))


# -------------------------------
# DASHBOARD API
# -------------------------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@login_required(roles=["manager"])
def dashboard_data_v2():
    conn = get_db()

    leak = conn.execute("SELECT date,result FROM leak_tests").fetchall()
    oxy = conn.execute("SELECT date,oxygen FROM oxygen_tests").fetchall()
    brk = conn.execute("SELECT product_code,broken FROM breakage").fetchall()
    stop = conn.execute("SELECT stop_reason,stop_other FROM production_log WHERE action='Stop'").fetchall()

    conn.close()

    leak_group = {}
    for r in leak:
        leak_group.setdefault(r["date"], {"Pass": 0, "Fail": 0})
        leak_group[r["date"]][r["result"]] += 1

    stop_count = {}
    for r in stop:
        reason = r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        stop_count[reason] = stop_count.get(reason, 0) + 1

    return {
        "kpi": {
            "pass_rate": round(
                sum(v["Pass"] for v in leak_group.values()) /
                max(sum(v["Pass"] + v["Fail"] for v in leak_group.values()), 1) * 100, 2
            ),
            "avg_oxygen": round(sum(r["oxygen"] for r in oxy) / max(len(oxy), 1), 2),
            "avg_breakage": round(sum(r["broken"] for r in brk) / max(len(brk), 1), 2),
            "top_stop": max(stop_count, key=stop_count.get) if stop_count else "-"
        },
        "leak": {
            "date": list(leak_group.keys()),
            "pass": [v["Pass"] for v in leak_group.values()],
            "fail": [v["Fail"] for v in leak_group.values()]
        },
        "oxygen": {
            "date": [r["date"] for r in oxy],
            "oxygen": [r["oxygen"] for r in oxy]
        },
        "breakage": {
            "code": [r["product_code"] for r in brk],
            "broken": [r["broken"] for r in brk]
        },
        "stop": {
            "label": list(stop_count.keys()),
            "count": list(stop_count.values())
        }
    }


# -------------------------------
# RUN
# -------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
