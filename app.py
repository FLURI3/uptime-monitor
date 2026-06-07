import sqlite3
from flask import Flask, render_template, request, redirect, jsonify

DB_PATH = "monitor.db"
app = Flask(__name__, template_folder="templates", static_folder="static")

def query(sql, params=(), commit=False):
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute(sql, params)
    if commit:
        conn.commit()
        conn.close()
        return
    rows = cur.fetchall()
    conn.close()
    return rows

@app.route("/")
def index():
    sites = query("SELECT id, name, url, timeout FROM sites")
    data = []
    for s in sites:
        row = query("SELECT last_status, last_ts FROM site_state WHERE site_id = ?", (s[0],))
        last = row[0] if row else (None, None)
        data.append({
            "id": s[0], "name": s[1], "url": s[2],
            "timeout": s[3], "status": last[0], "ts": last[1]
        })
    return render_template("index.html", sites=data)

@app.route("/add", methods=["POST"])
def add():
    name = request.form["name"]
    url = request.form["url"]
    timeout = int(request.form.get("timeout", 10))
    query("INSERT INTO sites (name, url, timeout) VALUES (?, ?, ?)", (name, url, timeout), commit=True)
    return redirect("/")

@app.route("/delete/<int:sid>")
def delete(sid):
    query("DELETE FROM sites WHERE id = ?", (sid,), commit=True)
    query("DELETE FROM site_state WHERE site_id = ?", (sid,), commit=True)
    return redirect("/")

@app.route("/history/<int:sid>")
def history(sid):
    rows = query("SELECT timestamp, status, rtt_ms FROM checks WHERE site_id = ? ORDER BY timestamp DESC LIMIT 300", (sid,))
    return jsonify([{"ts": r[0], "status": r[1], "rtt": r[2]} for r in rows])

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8000)
