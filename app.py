from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session, jsonify
import sqlite3, os, json
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "super_secret"

DB = "beyond.db"
UPLOAD_FOLDER = "static/uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------- DATABASE ----------------
def get_db():
    conn = sqlite3.connect(DB)
    conn.row_factory = sqlite3.Row
    return conn

def create_tables():
    conn = get_db()
    c = conn.cursor()

    c.execute("""
    CREATE TABLE IF NOT EXISTS leak_tests(
        id INTEGER PRIMARY KEY,
        date TEXT, line TEXT, flavour TEXT, grammage TEXT,
        pressure TEXT, result TEXT, photo TEXT, remarks TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS oxygen_tests(
        id INTEGER PRIMARY KEY,
        date TEXT, line TEXT, flavour TEXT, grammage TEXT,
        temperature REAL, oxygen REAL, photo TEXT, remarks TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS breakage(
        id INTEGER PRIMARY KEY,
        date TEXT, line TEXT, product_code TEXT,
        good REAL, broken REAL, cluster REAL, residue REAL,
        photo TEXT, remarks TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS production_log(
        id INTEGER PRIMARY KEY,
        date TEXT, time TEXT, line TEXT,
        action TEXT, stop_reason TEXT, stop_other TEXT
    )""")

    conn.commit()
    conn.close()

create_tables()

# ---------------- FILE SAVE ----------------
def save_file(file):
    if not file or not file.filename:
        return None
    name = datetime.now().strftime("%Y%m%d%H%M%S_") + file.filename
    path = os.path.join(UPLOAD_FOLDER, name)
    file.save(path)
    return path

# ---------------- AUTH ----------------
employee_pass = ["1111","2222","3333"]
boss_pass = ["9999","8888"]

def requires_role(allow_employee=False):
    def decorator(fn):
        def wrapper(*a, **kw):
            role = session.get("role")
            if role == "boss": return fn(*a, **kw)
            if allow_employee and role == "employee": return fn(*a, **kw)
            return abort(403)
        wrapper.__name__ = fn.__name__
        return wrapper
    return decorator

# ---------------- LOGIN ----------------
@app.route("/", methods=["GET","POST"])
@app.route("/login", methods=["GET","POST"])
def login():
    if request.method == "POST":
        code = request.form.get("passcode")
        if code in employee_pass:
            session["role"]="employee"; return redirect("/index")
        if code in boss_pass:
            session["role"]="boss"; return redirect("/index")
        flash("Invalid passcode","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

# ---------------- PAGES ----------------
@app.route("/index")
@requires_role(True)
def index(): return render_template("index.html")

@app.route("/leak", methods=["GET","POST"])
@requires_role(True)
def leak():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO leak_tests VALUES(NULL,?,?,?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            request.form["pressure"],
            request.form["result"],
            save_file(request.files.get("photo")),
            request.form.get("remarks")))
        conn.commit(); conn.close()
        flash("Leak test saved","success")
    return render_template("form_leak.html")

@app.route("/oxygen", methods=["GET","POST"])
@requires_role(True)
def oxygen():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO oxygen_tests VALUES(NULL,?,?,?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["flavour"],
            request.form["grammage"],
            float(request.form["temperature"]),
            float(request.form["oxygen"]),
            save_file(request.files.get("photo")),
            request.form.get("remarks")))
        conn.commit(); conn.close()
        flash("Oxygen test saved","success")
    return render_template("form_oxygen.html")

@app.route("/breakage", methods=["GET","POST"])
@requires_role(True)
def breakage():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO breakage VALUES(NULL,?,?,?,?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
            request.form["line"],
            request.form["product_code"],
            float(request.form["good"]),
            float(request.form["broken"]),
            float(request.form["cluster"]),
            float(request.form["residue"]),
            save_file(request.files.get("photo")),
            request.form.get("remarks")))
        conn.commit(); conn.close()
        flash("Breakage saved","success")
    return render_template("form_breakage.html")

@app.route("/log", methods=["GET","POST"])
@requires_role(True)
def log():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO production_log VALUES(NULL,?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
            datetime.now().strftime("%H:%M:%S"),
            request.form["line"],
            request.form["action"],
            request.form.get("stop_reason"),
            request.form.get("stop_other")))
        conn.commit(); conn.close()
        flash("Log saved","success")
    return render_template("form_production.html")

@app.route("/dashboard")
@requires_role(False)
def dashboard(): return render_template("dashboard.html")

@app.route("/reports")
@requires_role(False)
def reports(): return render_template("reports.html")

# ---------------- DASHBOARD API ----------------
@app.route("/api/dashboard_data_v2", methods=["POST"])
@requires_role(False)
def dashboard_api():
    conn=get_db()

    leak=conn.execute("SELECT date,result FROM leak_tests").fetchall()
    oxy=conn.execute("SELECT date,oxygen FROM oxygen_tests").fetchall()
    brk=conn.execute("SELECT broken FROM breakage").fetchall()
    stop=conn.execute("SELECT stop_reason,stop_other FROM production_log WHERE action='Stop'").fetchall()

    conn.close()

    pass_count=sum(1 for r in leak if r["result"]=="Pass")
    total=len(leak)

    stop_map={}
    for r in stop:
        reason=r["stop_other"] if r["stop_reason"]=="Other" else r["stop_reason"]
        stop_map[reason]=stop_map.get(reason,0)+1

    return jsonify({
        "kpi":{
            "pass_rate": round(pass_count/total*100,2) if total else 0,
            "avg_oxygen": round(sum(r["oxygen"] for r in oxy)/len(oxy),2) if oxy else "-",
            "avg_breakage": round(sum(r["broken"] for r in brk)/len(brk),2) if brk else "-",
            "top_stop": max(stop_map,key=stop_map.get) if stop_map else "-"
        },
        "leak":{
            "date":[r["date"] for r in leak],
            "pass":[1 if r["result"]=="Pass" else 0 for r in leak],
            "fail":[1 if r["result"]=="Fail" else 0 for r in leak]
        },
        "oxygen":{
            "date":[r["date"] for r in oxy],
            "oxygen":[r["oxygen"] for r in oxy]
        }
    })

# ---------------- EXPORTS ----------------
def export_excel(name, df):
    df.to_excel(name, index=False)
    return send_file(name, as_attachment=True, download_name=name)

@app.route("/export/leak_tests")
def export_leak():
    df=pd.read_sql("SELECT * FROM leak_tests", get_db())
    return export_excel("leak_tests.xlsx",df)

@app.route("/export/oxygen_tests")
def export_oxy():
    df=pd.read_sql("SELECT * FROM oxygen_tests", get_db())
    return export_excel("oxygen_tests.xlsx",df)

@app.route("/export/breakage")
def export_break():
    df=pd.read_sql("SELECT * FROM breakage", get_db())
    return export_excel("breakage.xlsx",df)

@app.route("/export/production_log")
def export_log():
    df=pd.read_sql("SELECT * FROM production_log", get_db())
    return export_excel("production_log.xlsx",df)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(host="0.0.0.0",port=8080,debug=True)
