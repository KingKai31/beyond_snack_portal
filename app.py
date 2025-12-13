from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session, jsonify
import os
import sqlite3
from datetime import datetime
import pandas as pd
import json
import tempfile

app = Flask(__name__)
app.secret_key = "super_secret"

UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

DB = "beyond.db"


# -------------------------
# Database helpers
# -------------------------
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


# ensure tables exist
create_tables()


# -------------------------
# File save utility
# -------------------------
def save_file(file):
    if not file or not getattr(file, "filename", None):
        return None
    fname = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
    path = os.path.join(UPLOAD_FOLDER, fname)
    file.save(path)
    return path


# -------------------------
# Simple auth (passcodes)
# -------------------------
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


# -------------------------
# Auth routes
# -------------------------
@app.route("/", methods=["GET", "POST"])
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        code = request.form.get("passcode", "").strip()
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


@app.route("/index")
@requires_role(allow_employee=True)
def index():
    return render_template("index.html")


# -------------------------
# Leak test route
# -------------------------
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
            save_file(request.files.get("photo")) if request.files.get("photo") else None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Leak test submitted!", "success")
    return render_template("form_leak.html")


# -------------------------
# Oxygen test route
# -------------------------
@app.route("/oxygen", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def oxygen_page():
    if request.method == "POST":
        try:
            temp = float(request.form.get("temperature") or 0)
        except:
            temp = 0.0
        try:
            oxy = float(request.form.get("oxygen") or 0)
        except:
            oxy = 0.0

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
            save_file(request.files.get("photo")) if request.files.get("photo") else None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Oxygen test submitted!", "success")
    return render_template("form_oxygen.html")


# -------------------------
# Breakage route
# -------------------------
@app.route("/breakage", methods=["GET", "POST"])
@requires_role(allow_employee=True)
def breakage_page():
    if request.method == "POST":
        def to_float(v):
            try:
                return float(v or 0)
            except:
                return 0.0

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
            save_file(request.files.get("photo")) if request.files.get("photo") else None,
            request.form.get("remarks")
        ))
        conn.commit()
        conn.close()
        flash("Breakage analysis submitted!", "success")
    return render_template("form_breakage.html")


# -------------------------
# Production log route
# -------------------------
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
        flash("Log entry submitted!", "success")
    return render_template("form_production.html")


# -------------------------
# Dashboard page (renders template)
# -------------------------
@app.route("/dashboard")
@requires_role(allow_employee=False)
def dashboard():
    return render_template("dashboard.html")


# -------------------------
# Export helpers
# -------------------------
def rows_to_temp_xlsx(rows, filename):
    df = pd.DataFrame([dict(r) for r in rows])
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    df.to_excel(tmp.name, index=False)
    return tmp.name


@app.route("/export/leak_tests")
@requires_role(allow_employee=False)
def export_leak():
    conn = get_db()
    rows = conn.execute("SELECT date, line, flavour, grammage, result FROM leak_tests").fetchall()
    conn.close()
    tmp = rows_to_temp_xlsx(rows, "leak_tests.xlsx")
    return send_file(tmp, as_attachment=True, download_name="leak_tests.xlsx")


@app.route("/export/oxygen_tests")
@requires_role(allow_employee=False)
def export_oxygen():
    conn = get_db()
    rows = conn.execute("SELECT date, line, flavour, grammage, temperature, oxygen FROM oxygen_tests").fetchall()
    conn.close()
    tmp = rows_to_temp_xlsx(rows, "oxygen_tests.xlsx")
    return send_file(tmp, as_attachment=True, download_name="oxygen_tests.xlsx")


@app.route("/export/breakage")
@requires_role(allow_employee=False)
def export_breakage():
    conn = get_db()
    rows = conn.execute("SELECT date, line, product_code, good, broken, cluster, residue FROM breakage").fetchall()
    conn.close()
    tmp = rows_to_temp_xlsx(rows, "breakage.xlsx")
    return send_file(tmp, as_attachment=True, download_name="breakage.xlsx")


@app.route("/export/production_log")
@requires_role(allow_employee=False)
def export_production_log():
    conn = get_db()
    rows = conn.execute("SELECT date, time, line, action, stop_reason, stop_other FROM production_log").fetchall()
    conn.close()

    cleaned = []
    for r in rows:
        reason = r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        cleaned.append({
            "Date": r["date"],
            "Time": r["time"],
            "Line": r["line"],
            "Action": r["action"],
            "Stop Reason": reason
        })

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    pd.DataFrame(cleaned).to_excel(tmp.name, index=False)
    return send_file(tmp.name, as_attachment=True, download_name="production_log.xlsx")


# -------------------------
# Advanced Dashboard API (multi-select filters)
# -------------------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@requires_role(allow_employee=False)
def dashboard_data_v2():
    filters = request.get_json() or {}

    fromDate = filters.get("fromDate")
    toDate = filters.get("toDate")
    # Expect lists from frontend for these three fields (multi-select)
    lines = filters.get("line") or []        # list or empty
    flavours = filters.get("flavour") or [] # list or empty
    grammages = filters.get("grammage") or [] # list or empty
    product_code = filters.get("product_code") or None

    conn = get_db()

    # helper to add date filters
    def apply_date_filters(q, params, field="date"):
        if fromDate:
            q += f" AND {field} >= ?"
            params.append(fromDate)
        if toDate:
            q += f" AND {field} <= ?"
            params.append(toDate)
        return q, params

    # helper to add IN clause
    def add_in_clause(q, params, field, values):
        if values and len(values) > 0:
            placeholders = ",".join(["?"] * len(values))
            q += f" AND {field} IN ({placeholders})"
            params.extend(values)
        return q, params

    # ---------------------------
    # LEAK TESTS
    # ---------------------------
    leak_q = "SELECT date, result, flavour, grammage, line FROM leak_tests WHERE 1=1"
    leak_p = []
    leak_q, leak_p = apply_date_filters(leak_q, leak_p, "date")
    leak_q, leak_p = add_in_clause(leak_q, leak_p, "line", lines)
    leak_q, leak_p = add_in_clause(leak_q, leak_p, "flavour", flavours)
    leak_q, leak_p = add_in_clause(leak_q, leak_p, "grammage", grammages)

    leak_rows = conn.execute(leak_q, leak_p).fetchall()

    leak_group = {}
    for r in leak_rows:
        d = r["date"]
        leak_group.setdefault(d, {"Pass": 0, "Fail": 0})
        key = r["result"] if r["result"] in ("Pass", "Fail") else "Fail"
        leak_group[d][key] += 1

    leak_dates = sorted(leak_group.keys())
    leak_pass = [leak_group[d]["Pass"] for d in leak_dates]
    leak_fail = [leak_group[d]["Fail"] for d in leak_dates]
    total_tests = sum(leak_pass) + sum(leak_fail)
    pass_rate = round((sum(leak_pass) / total_tests) * 100, 2) if total_tests else 0

    # ---------------------------
    # OXYGEN TESTS
    # ---------------------------
    oxy_q = "SELECT date, oxygen, flavour, grammage, line FROM oxygen_tests WHERE 1=1"
    oxy_p = []
    oxy_q, oxy_p = apply_date_filters(oxy_q, oxy_p, "date")
    oxy_q, oxy_p = add_in_clause(oxy_q, oxy_p, "line", lines)
    oxy_q, oxy_p = add_in_clause(oxy_q, oxy_p, "flavour", flavours)
    oxy_q, oxy_p = add_in_clause(oxy_q, oxy_p, "grammage", grammages)

    oxy_rows = conn.execute(oxy_q, oxy_p).fetchall()
    oxy_dates = [r["date"] for r in oxy_rows]
    oxy_values = [r["oxygen"] for r in oxy_rows if r["oxygen"] is not None]
    avg_oxygen = round(sum(oxy_values) / len(oxy_values), 2) if oxy_values else "-"

    # ---------------------------
    # BREAKAGE
    # ---------------------------
    break_q = "SELECT date, product_code, good, broken, cluster, residue, line FROM breakage WHERE 1=1"
    break_p = []
    break_q, break_p = apply_date_filters(break_q, break_p, "date")
    break_q, break_p = add_in_clause(break_q, break_p, "line", lines)
    # breakage table does not have flavour/grammage columns in your schema,
    # so we don't filter by them here. We support product_code filter:
    if product_code:
        break_q += " AND product_code LIKE ?"; break_p.append(f"%{product_code}%")

    break_rows = conn.execute(break_q, break_p).fetchall()
    break_codes = [r["product_code"] for r in break_rows]
    good_list = [r["good"] for r in break_rows]
    broken_list = [r["broken"] for r in break_rows]
    cluster_list = [r["cluster"] for r in break_rows]
    residue_list = [r["residue"] for r in break_rows]
    avg_breakage = round(sum(broken_list) / len(broken_list), 2) if broken_list else "-"

    # ---------------------------
    # STOP REASONS
    # ---------------------------
    stop_q = "SELECT stop_reason, stop_other, line, date FROM production_log WHERE action='Stop' "
    stop_p = []
    stop_q, stop_p = apply_date_filters(stop_q, stop_p, "date")
    stop_q, stop_p = add_in_clause(stop_q, stop_p, "line", lines)

    stop_rows = conn.execute(stop_q, stop_p).fetchall()
    stop_count = {}
    for r in stop_rows:
        reason = r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"]
        if reason:
            stop_count[reason] = stop_count.get(reason, 0) + 1

    stop_labels = list(stop_count.keys())
    stop_values = list(stop_count.values())
    top_stop = stop_labels[stop_values.index(max(stop_values))] if stop_values else "-"

    # ---------------------------
    # RAW rows (for export)
    # ---------------------------
    raw = {
        "leak": [dict(r) for r in leak_rows],
        "oxygen": [dict(r) for r in oxy_rows],
        "breakage": [dict(r) for r in break_rows],
        "stop": [{"reason": (r["stop_other"] if r["stop_reason"] == "Other" else r["stop_reason"])} for r in stop_rows]
    }

    conn.close()

    result = {
        "kpi": {
            "pass_rate": pass_rate,
            "avg_oxygen": avg_oxygen,
            "avg_breakage": avg_breakage,
            "top_stop": top_stop
        },
        "leak": {"date": leak_dates, "pass": leak_pass, "fail": leak_fail},
        "oxygen": {"date": oxy_dates, "oxygen": oxy_values},
        "breakage": {"code": break_codes, "good": good_list, "broken": broken_list, "cluster": cluster_list, "residue": residue_list},
        "stop": {"label": stop_labels, "count": stop_values},
        "raw": raw
    }

    return jsonify(result)


# -------------------------
# Export filtered dashboard (combined workbook)
# -------------------------
@app.route("/export/dashboard_filtered")
@requires_role(allow_employee=False)
def export_dashboard_filtered():
    data_json = request.args.get("data")
    if not data_json:
        return "No data supplied", 400
    try:
        data = json.loads(data_json)
    except Exception as e:
        return f"Invalid data: {e}", 400

    leak_df = pd.DataFrame(data.get("raw", {}).get("leak", []))
    oxy_df = pd.DataFrame(data.get("raw", {}).get("oxygen", []))
    break_df = pd.DataFrame(data.get("raw", {}).get("breakage", []))
    stop_df = pd.DataFrame(data.get("raw", {}).get("stop", []))

    # drop private columns if present
    for df in (leak_df, oxy_df, break_df):
        for c in ["id", "photo", "remarks"]:
            if c in df.columns:
                df.drop(columns=[c], inplace=True, errors="ignore")

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    with pd.ExcelWriter(tmp.name) as writer:
        # ensure each sheet exists even if empty
        (leak_df if not leak_df.empty else pd.DataFrame()).to_excel(writer, sheet_name="Leak Tests", index=False)
        (oxy_df if not oxy_df.empty else pd.DataFrame()).to_excel(writer, sheet_name="Oxygen Tests", index=False)
        (break_df if not break_df.empty else pd.DataFrame()).to_excel(writer, sheet_name="Breakage", index=False)
        (stop_df if not stop_df.empty else pd.DataFrame()).to_excel(writer, sheet_name="Stop Reasons", index=False)

    return send_file(tmp.name, as_attachment=True, download_name="Filtered_Dashboard.xlsx")


# -------------------------
# Run server
# -------------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
