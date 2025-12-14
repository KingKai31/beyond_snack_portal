from flask import (
    Flask, render_template, request, redirect,
    url_for, flash, send_file, abort, session
)
import os
import sqlite3
from datetime import datetime
import pandas as pd
import tempfile

app = Flask(__name__)
app.secret_key = "beyond_snack_secret_key"

DB = "beyond.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# -------------------------------
# USERS & ROLES
# -------------------------------
USERS = {
    "Linto@drjackfruit.com": {"password": "DJF@123", "role": "log"},
    "qc@drjackfruit.com": {"password": "DJF@123", "role": "quality"},
    "Rakesh@drjackfruit.com": {"password": "DJF@123", "role": "manager"},
}

# -------------------------------
# DB
# -------------------------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

# -------------------------------
# AUTH
# -------------------------------
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
# LOGIN
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
# MENU
# -------------------------------
@app.route("/index")
@login_required(["log", "quality", "manager"])
def index():
    return render_template("index.html")

# -------------------------------
# DASHBOARD & REPORTS
# -------------------------------
@app.route("/dashboard")
@login_required(["manager"])
def dashboard():
    return render_template("dashboard.html")

@app.route("/reports")
@login_required(["manager"])
def reports():
    return render_template("reports.html")

# -------------------------------
# SAFE EXCEL EXPORT (FIX)
# -------------------------------
def export_excel_safe(filename, df):
    temp_dir = tempfile.gettempdir()
    file_path = os.path.join(temp_dir, filename)
    df.to_excel(file_path, index=False)

    return send_file(
        file_path,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )

# -------------------------------
# EXPORT ROUTES (MATCH TEMPLATE)
# -------------------------------
@app.route("/export/leak")
@login_required(["manager"])
def export_leak():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,line,flavour,grammage,pressure,result FROM leak_tests"
    ).fetchall()
    conn.close()
    return export_excel_safe("leak_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/oxygen")
@login_required(["manager"])
def export_oxygen():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,line,flavour,grammage,temperature,oxygen FROM oxygen_tests"
    ).fetchall()
    conn.close()
    return export_excel_safe("oxygen_tests.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/breakage")
@login_required(["manager"])
def export_breakage():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,line,product_code,good,broken,cluster,residue FROM breakage"
    ).fetchall()
    conn.close()
    return export_excel_safe("breakage.xlsx", pd.DataFrame([dict(r) for r in rows]))

@app.route("/export/log")
@login_required(["manager"])
def export_log():
    conn = get_db()
    rows = conn.execute("SELECT * FROM production_log").fetchall()
    conn.close()

    cleaned = [{
        "Date": r["date"],
        "Time": r["time"],
        "Line": r["line"],
        "Action": r["action"],
        "Stop Reason": r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
    } for r in rows]

    return export_excel_safe("production_log.xlsx", pd.DataFrame(cleaned))

# -------------------------------
# DASHBOARD API (UNCHANGED LOGIC)
# -------------------------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@login_required(["manager"])
def dashboard_data_v2():
    conn = get_db()

    leak = conn.execute("SELECT date,result FROM leak_tests").fetchall()
    oxy = conn.execute("SELECT date,oxygen FROM oxygen_tests").fetchall()
    brk = conn.execute("SELECT product_code,broken FROM breakage").fetchall()
    stop = conn.execute(
        "SELECT stop_reason,stop_other FROM production_log WHERE action='Stop'"
    ).fetchall()

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
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
