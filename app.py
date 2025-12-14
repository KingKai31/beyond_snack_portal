from flask import Flask, render_template, request, redirect, url_for, flash, send_file, abort, session
import os, sqlite3
from datetime import datetime
import pandas as pd

app = Flask(__name__)
app.secret_key = "super_secret"

DB = "beyond.db"

# ---------------- DB ----------------
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
        pressure TEXT,
        result TEXT
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS oxygen_tests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        line TEXT,
        flavour TEXT,
        grammage TEXT,
        temperature REAL,
        oxygen REAL
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
        residue REAL
    )""")

    c.execute("""
    CREATE TABLE IF NOT EXISTS production_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT,
        time TEXT,
        line TEXT,
        action TEXT,
        stop_reason TEXT
    )""")

    conn.commit()
    conn.close()

create_tables()

# ---------------- AUTH ----------------
employee_pass = ["1111","2222","3333"]
boss_pass = ["9999","8888"]

def requires_role(emp=False):
    def deco(fn):
        def wrap(*a,**k):
            r=session.get("role")
            if r=="boss" or (emp and r=="employee"):
                return fn(*a,**k)
            return abort(403)
        wrap.__name__=fn.__name__
        return wrap
    return deco

@app.route("/",methods=["GET","POST"])
def login():
    if request.method=="POST":
        c=request.form["passcode"]
        if c in employee_pass:
            session["role"]="employee"
            return redirect("/index")
        if c in boss_pass:
            session["role"]="boss"
            return redirect("/index")
        flash("Invalid passcode","danger")
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/")

# ---------------- HOME ----------------
@app.route("/index")
@requires_role(emp=True)
def index():
    return render_template("index.html")

# ---------------- FORMS ----------------
@app.route("/leak",methods=["GET","POST"])
@requires_role(emp=True)
def leak():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO leak_tests (date,line,flavour,grammage,pressure,result)
        VALUES (?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
             request.form["line"],
             request.form["flavour"],
             request.form["grammage"],
             request.form["pressure"],
             request.form["result"]))
        conn.commit(); conn.close()
        flash("Leak Test Submitted","success")
    return render_template("form_leak.html")

@app.route("/oxygen",methods=["GET","POST"])
@requires_role(emp=True)
def oxygen():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO oxygen_tests
        (date,line,flavour,grammage,temperature,oxygen)
        VALUES (?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
             request.form["line"],
             request.form["flavour"],
             request.form["grammage"],
             float(request.form["temperature"]),
             float(request.form["oxygen"])))
        conn.commit(); conn.close()
        flash("Oxygen Test Submitted","success")
    return render_template("form_oxygen.html")

@app.route("/breakage",methods=["GET","POST"])
@requires_role(emp=True)
def breakage():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO breakage
        (date,line,product_code,good,broken,cluster,residue)
        VALUES (?,?,?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
             request.form["line"],
             request.form["product_code"],
             float(request.form["good"]),
             float(request.form["broken"]),
             float(request.form["cluster"]),
             float(request.form["residue"])))
        conn.commit(); conn.close()
        flash("Breakage Submitted","success")
    return render_template("form_breakage.html")

@app.route("/log",methods=["GET","POST"])
@requires_role(emp=True)
def log():
    if request.method=="POST":
        conn=get_db()
        conn.execute("""
        INSERT INTO production_log
        (date,time,line,action,stop_reason)
        VALUES (?,?,?,?,?)
        """,(datetime.now().strftime("%Y-%m-%d"),
             datetime.now().strftime("%H:%M:%S"),
             request.form["line"],
             request.form["action"],
             request.form.get("stop_reason")))
        conn.commit(); conn.close()
        flash("Log Submitted","success")
    return render_template("form_production.html")

# ---------------- DASHBOARD ----------------
@app.route("/dashboard")
@requires_role()
def dashboard():
    return render_template("dashboard.html")

# ---------------- REPORTS ----------------
@app.route("/reports")
@requires_role()
def reports():
    return render_template("reports.html")

def export_xlsx(name, df):
    df.to_excel(name,index=False)
    return send_file(name,as_attachment=True)

@app.route("/export/leak")
@requires_role()
def exp_leak():
    df=pd.read_sql("SELECT * FROM leak_tests",get_db())
    return export_xlsx("leak.xlsx",df)

@app.route("/export/oxygen")
@requires_role()
def exp_oxy():
    df=pd.read_sql("SELECT * FROM oxygen_tests",get_db())
    return export_xlsx("oxygen.xlsx",df)

@app.route("/export/breakage")
@requires_role()
def exp_break():
    df=pd.read_sql("SELECT * FROM breakage",get_db())
    return export_xlsx("breakage.xlsx",df)

@app.route("/export/log")
@requires_role()
def exp_log():
    df=pd.read_sql("SELECT * FROM production_log",get_db())
    return export_xlsx("log.xlsx",df)

if __name__=="__main__":
    app.run(debug=True,port=8080)
