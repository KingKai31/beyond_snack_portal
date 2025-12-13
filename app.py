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

    c.execute("""
        CREATE TABLE IF NOT EXISTS leak_tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            line TEXT,
            flavour TEXT,
            grammage TEXT,
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
# HOME PAGE
# ---------------------------------------------------------
@app.route("/index")
@requires_role(allow_employee=True)
def index():
    return render_template("index.html")


# ---------------------------------------------------------
# LEAK TEST FORM
# ---------------------------------------------------------
@app.route("/leak", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def leak_page():
    if request.method == "POST":
        conn = get_db()
        conn.execute("""
            INSERT INTO leak_tests
            (date, line, flavour, grammage, result, photo, remarks)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            datetime.now().strftime("%Y-%m-%d"),
            request.form.get("line"),
            request.form.get("flavour"),
            request.form.get("grammage"),
            request.form.get("result"),
            save_file(request.files.get("photo")),
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Leak test submitted!", "success")
    return render_template("form_leak.html")


# ---------------------------------------------------------
# OXYGEN FORM
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
# BREAKAGE FORM
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
# DASHBOARD PAGE
# ---------------------------------------------------------
@app.route("/dashboard")
@requires_role(allow_employee=False)
def dashboard():
    return render_template("dashboard.html")


# ---------------------------------------------------------
# EXPORT ROUTES (FIXED FOR MOBILE)
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
    rows = conn.execute("SELECT date,line,flavour,grammage,result FROM leak_tests").fetchall()
    conn.close()
    df = pd.DataFrame([dict(r) for r in rows])
    return export_excel("leak_tests.xlsx", df)


@app.route("/export/oxygen_tests")
@requires_role(allow_employee=False)
def export_oxy():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,line,flavour,grammage,temperature,oxygen FROM oxygen_tests"
    ).fetchall()
    conn.close()
    df = pd.DataFrame([dict(r) for r in rows])
    return export_excel("oxygen_tests.xlsx", df)


@app.route("/export/breakage")
@requires_role(allow_employee=False)
def export_breakage():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,line,product_code,good,broken,cluster,residue FROM breakage"
    ).fetchall()
    conn.close()
    df = pd.DataFrame([dict(r) for r in rows])
    return export_excel("breakage.xlsx", df)


@app.route("/export/production_log")
@requires_role(allow_employee=False)
def export_prod():
    conn = get_db()
    rows = conn.execute(
        "SELECT date,time,line,action,stop_reason,stop_other FROM production_log"
    ).fetchall()
    conn.close()

    cleaned = []
    for r in rows:
        cleaned.append({
            "Date": r["date"],
            "Time": r["time"],
            "Line": r["line"],
            "Action": r["action"],
            "Stop Reason":
                r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        })

    df = pd.DataFrame(cleaned)
    return export_excel("production_log.xlsx", df)


# ---------------------------------------------------------
# ADVANCED DASHBOARD API (JSON FIXED)
# ---------------------------------------------------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@requires_role(allow_employee=False)
def dashboard_data_v2():

    filters = request.get_json() or {}

    fromDate = filters.get("fromDate")
    toDate = filters.get("toDate")
    line = filters.get("line") or []
    flavour = filters.get("flavour") or []
    grammage = filters.get("grammage") or []
    product_code = filters.get("product_code")

    conn = get_db()

    # Helper: Add IN clause
    def add_in(q, p, field, values):
        if values:
            q += f" AND {field} IN ({','.join(['?'] * len(values))})"
            p.extend(values)
        return q, p

    # ---------------- LEAK TEST ----------------
    q = "SELECT date,result,line,flavour,grammage FROM leak_tests WHERE 1=1"
    p = []
    if fromDate:
        q += " AND date >= ?"; p.append(fromDate)
    if toDate:
        q += " AND date <= ?"; p.append(toDate)

    q, p = add_in(q, p, "line", line)
    q, p = add_in(q, p, "flavour", flavour)
    q, p = add_in(q, p, "grammage", grammage)

    leak_rows = conn.execute(q, p).fetchall()

    leak_group = {}
    for r in leak_rows:
        d = r["date"]
        leak_group.setdefault(d, {"Pass": 0, "Fail": 0})
        leak_group[d][r["result"]] += 1

    leak_data = {"date": [], "pass": [], "fail": []}
    for d in sorted(leak_group.keys()):
        leak_data["date"].append(d)
        leak_data["pass"].append(leak_group[d]["Pass"])
        leak_data["fail"].append(leak_group[d]["Fail"])

    total_tests = sum(v["Pass"] + v["Fail"] for v in leak_group.values())
    pass_rate = round(sum(v["Pass"] for v in leak_group.values()) / total_tests * 100, 2) if total_tests else 0

    # ---------------- OXYGEN ----------------
    q = "SELECT date,oxygen,line,flavour,grammage FROM oxygen_tests WHERE 1=1"
    p = []
    if fromDate:
        q += " AND date >= ?"; p.append(fromDate)
    if toDate:
        q += " AND date <= ?"; p.append(toDate)
    q, p = add_in(q, p, "line", line)
    q, p = add_in(q, p, "flavour", flavour)
    q, p = add_in(q, p, "grammage", grammage)

    oxy_rows = conn.execute(q, p).fetchall()

    oxy_data = {
        "date": [r["date"] for r in oxy_rows],
        "oxygen": [r["oxygen"] for r in oxy_rows]
    }
    avg_oxygen = round(sum(r["oxygen"] for r in oxy_rows) / len(oxy_rows), 2) if oxy_rows else "-"

    # ---------------- BREAKAGE ----------------
    q = "SELECT date,product_code,good,broken,cluster,residue,line FROM breakage WHERE 1=1"
    p = []
    if fromDate:
        q += " AND date >= ?"; p.append(fromDate)
    if toDate:
        q += " AND date <= ?"; p.append(toDate)
    if product_code:
        q += " AND product_code = ?"; p.append(product_code)

    break_rows = conn.execute(q, p).fetchall()

    break_data = {
        "code": [r["product_code"] for r in break_rows],
        "good": [r["good"] for r in break_rows],
        "broken": [r["broken"] for r in break_rows],
        "cluster": [r["cluster"] for r in break_rows],
        "residue": [r["residue"] for r in break_rows]
    }
    avg_break = round(sum(r["broken"] for r in break_rows) / len(break_rows), 2) if break_rows else "-"

    # ---------------- STOP REASONS ----------------
    q = "SELECT stop_reason, stop_other FROM production_log WHERE action='Stop'"
    p = []
    if fromDate:
        q += " AND date >= ?"; p.append(fromDate)
    if toDate:
        q += " AND date <= ?"; p.append(toDate)

    stop_rows = conn.execute(q, p).fetchall()

    stop_count = {}
    for r in stop_rows:
        reason = r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        stop_count[reason] = stop_count.get(reason, 0) + 1

    stop_labels = list(stop_count.keys())
    stop_values = list(stop_count.values())

    top_stop = stop_labels[stop_values.index(max(stop_values))] if stop_values else "-"

    # RAW DATA (for filtered export)
    raw = {
        "leak": [dict(r) for r in leak_rows],
        "oxygen": [dict(r) for r in oxy_rows],
        "breakage": [dict(r) for r in break_rows],
        "stop": [{"reason": r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]} for r in stop_rows]
    }

    conn.close()

    return {
        "kpi": {
            "pass_rate": pass_rate,
            "avg_oxygen": avg_oxygen,
            "avg_breakage": avg_break,
            "top_stop": top_stop
        },
        "leak": leak_data,
        "oxygen": oxy_data,
        "breakage": break_data,
        "stop": {"label": stop_labels, "count": stop_values},
        "raw": raw
    }


# ---------------------------------------------------------
# FILTERED COMPLETE EXPORT (MULTI-SHEET EXCEL)
# ---------------------------------------------------------
@app.route("/export/dashboard_filtered")
@requires_role(allow_employee=False)
def export_dashboard_filtered():
    data_json = request.args.get("data")
    if not data_json:
        return "Missing data", 400

    try:
        data = json.loads(data_json)
    except:
        return "Invalid JSON", 400

    filename = "Filtered_Dashboard.xlsx"

    leak_df = pd.DataFrame(data["raw"]["leak"])
    oxy_df = pd.DataFrame(data["raw"]["oxygen"])
    brk_df = pd.DataFrame(data["raw"]["breakage"])
    stop_df = pd.DataFrame(data["raw"]["stop"])

    with pd.ExcelWriter(filename) as writer:
        leak_df.to_excel(writer, sheet_name="Leak Tests", index=False)
        oxy_df.to_excel(writer, sheet_name="Oxygen Tests", index=False)
        brk_df.to_excel(writer, sheet_name="Breakage", index=False)
        stop_df.to_excel(writer, sheet_name="Stop Reasons", index=False)

    return send_file(
        filename,
        as_attachment=True,
        download_name=filename,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    )


# ---------------------------------------------------------
# RUN SERVER
# ---------------------------------------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", debug=True, port=8080)

