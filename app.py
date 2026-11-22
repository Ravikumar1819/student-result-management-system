import click
from flask import abort, g, render_template, session
from werkzeug.security import generate_password_hash
from common import create_base, data, db, install_auth, integer, login_required, text


def grade(score):
    return next(label for cutoff, label in [(90,"A+"),(80,"A"),(70,"B"),(60,"C"),(50,"D"),(0,"F")] if score >= cutoff)


def admin():
    if g.user["role"] != "admin":
        abort(403, "Administrator access required.")


def create_app(config=None):
    app = create_base(config)
    install_auth(app, roles=True)
    with app.app_context():
        db().executescript("""
        CREATE TABLE IF NOT EXISTS students(id INTEGER PRIMARY KEY, roll TEXT UNIQUE NOT NULL, name TEXT NOT NULL, user_id INTEGER UNIQUE REFERENCES users(id));
        CREATE TABLE IF NOT EXISTS exams(id INTEGER PRIMARY KEY, name TEXT NOT NULL, subject TEXT NOT NULL, UNIQUE(name,subject));
        CREATE TABLE IF NOT EXISTS results(student_id INTEGER REFERENCES students(id) ON DELETE CASCADE, exam_id INTEGER REFERENCES exams(id) ON DELETE CASCADE, score INTEGER NOT NULL CHECK(score BETWEEN 0 AND 100), PRIMARY KEY(student_id,exam_id));
        """)

    @app.cli.command("create-admin")
    @click.argument("username")
    @click.password_option(confirmation_prompt=True)
    def create_admin(username, password):
        if len(password) < 10:
            raise click.ClickException("Use at least 10 characters.")
        db().execute("INSERT INTO users(username,password,role) VALUES(?,?, 'admin')", (username, generate_password_hash(password)))
        db().commit()
        click.echo("Administrator created.")

    @app.get("/")
    def index():
        return render_template("index.html")

    @app.get("/api/records")
    @login_required
    def records():
        if g.user["role"] == "admin":
            students = db().execute("SELECT s.*, u.username FROM students s LEFT JOIN users u ON u.id=s.user_id ORDER BY s.roll").fetchall()
            users = db().execute("SELECT id,username FROM users WHERE role='student' ORDER BY username").fetchall()
        else:
            students = db().execute("SELECT * FROM students WHERE user_id=?", (session["user_id"],)).fetchall()
            users = []
        ids = [s["id"] for s in students]
        results = []
        if ids:
            results = db().execute(f"SELECT r.*, e.name AS exam, e.subject, s.name AS student FROM results r JOIN exams e ON e.id=r.exam_id JOIN students s ON s.id=r.student_id WHERE s.id IN ({','.join('?' for _ in ids)}) ORDER BY s.roll,e.name,e.subject", ids).fetchall()
        items = [dict(r, grade=grade(r["score"])) for r in results]
        return {"students": [dict(s) for s in students], "exams": [dict(e) for e in db().execute("SELECT * FROM exams ORDER BY name,subject")], "results": items, "users": [dict(u) for u in users]}

    @app.route("/api/students", methods=["POST"])
    @app.route("/api/students/<int:record_id>", methods=["PUT", "DELETE"])
    @login_required
    def students(record_id=None):
        from flask import request
        admin()
        if record_id and not db().execute("SELECT id FROM students WHERE id=?", (record_id,)).fetchone():
            abort(404, "Student not found.")
        if request.method == "DELETE":
            db().execute("DELETE FROM students WHERE id=?", (record_id,))
        else:
            p = data()
            uid = p.get("user_id")
            if uid is not None:
                integer(uid, "Account", 1, 2147483647)
                if not db().execute("SELECT id FROM users WHERE id=? AND role='student'", (uid,)).fetchone():
                    abort(400, "Choose a student account.")
            values = (text(p.get("roll"), "Roll number", 40), text(p.get("name"), "Name"), uid)
            if record_id:
                db().execute("UPDATE students SET roll=?,name=?,user_id=? WHERE id=?", (*values, record_id))
            else:
                db().execute("INSERT INTO students(roll,name,user_id) VALUES(?,?,?)", values)
        db().commit()
        return {"message": "Student record saved."}, 201 if request.method == "POST" else 200

    @app.route("/api/exams", methods=["POST"])
    @app.route("/api/exams/<int:record_id>", methods=["PUT", "DELETE"])
    @login_required
    def exams(record_id=None):
        from flask import request
        admin()
        if record_id and not db().execute("SELECT id FROM exams WHERE id=?", (record_id,)).fetchone():
            abort(404, "Examination not found.")
        if request.method == "DELETE":
            db().execute("DELETE FROM exams WHERE id=?", (record_id,))
        else:
            p = data()
            values = (text(p.get("name"), "Exam"), text(p.get("subject"), "Subject"))
            if record_id:
                db().execute("UPDATE exams SET name=?,subject=? WHERE id=?", (*values, record_id))
            else:
                db().execute("INSERT INTO exams(name,subject) VALUES(?,?)", values)
        db().commit()
        return {"message": "Examination saved."}, 201 if request.method == "POST" else 200

    @app.put("/api/results")
    @login_required
    def result():
        admin()
        p = data()
        sid = integer(p.get("student_id"), "Student", 1, 2147483647)
        eid = integer(p.get("exam_id"), "Exam", 1, 2147483647)
        score = integer(p.get("score"), "Score")
        db().execute("INSERT INTO results(student_id,exam_id,score) VALUES(?,?,?) ON CONFLICT(student_id,exam_id) DO UPDATE SET score=excluded.score", (sid,eid,score))
        db().commit()
        return {"message": "Result saved.", "grade": grade(score)}

    @app.delete("/api/results/<int:sid>/<int:eid>")
    @login_required
    def delete_result(sid,eid):
        admin()
        changed = db().execute("DELETE FROM results WHERE student_id=? AND exam_id=?", (sid,eid)).rowcount
        if not changed:
            abort(404, "Result not found.")
        db().commit()
        return {"message": "Result removed."}

    return app
