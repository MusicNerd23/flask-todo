from flask import Flask, render_template, request, redirect, url_for, flash
import sqlite3
from datetime import datetime

app = Flask(__name__)
app.config["SECRET_KEY"] = "dev"  # needed for flash messages; replace in prod

DB_FILE = "tasks.db"

def get_db():
    """
    Open a SQLite connection to our tasks.db and return it.
    row_factory makes rows behave like dicts (row['title']).
    """
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """
    Create the tasks table if it doesn't exist.
    Columns:
      - id: primary key (auto)
      - title: required text
      - done: 0/1 flag (default 0)
      - due: optional YYYY-MM-DD text
      - notes: optional text
      - created_at: ISO timestamp
    """
    with get_db() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                done INTEGER NOT NULL DEFAULT 0,
                due TEXT,
                notes TEXT,
                created_at TEXT NOT NULL
            );
        """)

# Initialize the DB once at startup (Flask 3.x-compatible)
with app.app_context():
    init_db()


@app.get("/")
def index():
    """
    READ: list all tasks.
    - Fetch rows ordered by 'done' then id.
    - Render the list with an Add form.
    """
    with get_db() as conn:
        tasks = conn.execute(
            "SELECT id, title, done, due, notes, created_at FROM tasks ORDER BY done, id"
        ).fetchall()
    # Reformat due dates to MM-DD-YYYY for display
    formatted_tasks = []
    for t in tasks:
        t = dict(t)
        if t.get("due"):
            try:
                dt = datetime.strptime(t["due"], "%Y-%m-%d")
                t["due"] = dt.strftime("%m-%d-%Y")
            except ValueError:
                pass
        formatted_tasks.append(t)
    tasks = formatted_tasks
    return render_template("index.html", tasks=tasks)

@app.post("/add")
def add():
    """
    CREATE: insert a new task from form fields.
    - Validates non-empty title.
    - Inserts with done=0 and current UTC timestamp.
    """
    title = request.form.get("title", "").strip()
    if not title:
        flash("Title is required.")
        return redirect(url_for("index"))

    due = request.form.get("due", "").strip()
    notes = request.form.get("notes", "").strip()

    with get_db() as conn:
        conn.execute(
            "INSERT INTO tasks (title, done, due, notes, created_at) VALUES (?, 0, ?, ?, ?)",
            (title, due, notes, datetime.utcnow().isoformat(timespec="seconds")),
        )
    return redirect(url_for("index"))

@app.post("/toggle/<int:task_id>")
def toggle(task_id: int):
    """
    UPDATE: flip the 'done' flag for a task.
    - Reads current value (0/1), toggles it, saves.
    """
    with get_db() as conn:
        row = conn.execute("SELECT done FROM tasks WHERE id = ?", (task_id,)).fetchone()
        if row is not None:
            new_done = 0 if row["done"] else 1
            conn.execute("UPDATE tasks SET done = ? WHERE id = ?", (new_done, task_id))
    return redirect(url_for("index"))

@app.get("/edit/<int:task_id>")
def edit(task_id: int):
    """
    READ (single): fetch a task and show the edit form.
    """
    with get_db() as conn:
        task = conn.execute("SELECT * FROM tasks WHERE id = ?", (task_id,)).fetchone()
    if task is None:
        flash("Task not found.")
        return redirect(url_for("index"))
    return render_template("edit.html", task=task)

@app.post("/edit/<int:task_id>")
def edit_post(task_id: int):
    """
    UPDATE: persist changes from the edit form.
    - Title required; due/notes optional.
    """
    title = request.form.get("title", "").strip()
    due = request.form.get("due", "").strip()
    notes = request.form.get("notes", "").strip()

    if not title:
        flash("Title is required.")
        return redirect(url_for("edit", task_id=task_id))

    with get_db() as conn:
        conn.execute(
            "UPDATE tasks SET title = ?, due = ?, notes = ? WHERE id = ?",
            (title, due, notes, task_id),
        )
    return redirect(url_for("index"))

@app.post("/delete/<int:task_id>")
def delete(task_id: int):
    """
    DELETE: remove a task by id.
    """
    with get_db() as conn:
        conn.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    return redirect(url_for("index"))

if __name__ == "__main__":
    # Dev server. Use gunicorn/uvicorn for production.
    app.run(debug=True)