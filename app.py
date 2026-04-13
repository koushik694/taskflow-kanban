import bcrypt
from flask import Flask, render_template, request, redirect, session, jsonify
from db import get_connection

app = Flask(__name__)
app.secret_key = "secret123"


# ---------------- HOME ----------------
@app.route('/')
def home():
    return render_template('signup.html')


# ---------------- SIGNUP ----------------
@app.route('/signup', methods=['POST'])
def signup():
    conn = get_connection()
    cur = conn.cursor()

    try:
        hashed_password = bcrypt.hashpw(
            request.form['password'].encode('utf-8'),
            bcrypt.gensalt()
        )

        cur.execute(
            "INSERT INTO users (first_name, last_name, email, role, password) VALUES (%s, %s, %s, %s, %s)",
            (
                request.form['first_name'],
                request.form['last_name'],
                request.form['email'],
                request.form['role'],
                hashed_password.decode('utf-8')
            )
        )

        conn.commit()

    except Exception as e:
        conn.rollback()
        return "Email already exists or error occurred"

    finally:
        cur.close()
        conn.close()

    return redirect('/login')


# ---------------- LOGIN PAGE ----------------
@app.route('/login')
def login_page():
    return render_template('login.html')


# ---------------- LOGIN ----------------
@app.route('/login', methods=['POST'])
def login():
    conn = get_connection()
    cur = conn.cursor()

    cur.execute("SELECT * FROM users WHERE email=%s", (request.form['email'],))
    user = cur.fetchone()

    cur.close()
    conn.close()

    if user and bcrypt.checkpw(
        request.form['password'].encode('utf-8'),
        user[5].encode('utf-8')
    ):
        session['user_id'] = user[0]

        # ✅ Admin safe check
        if len(user) > 6:
            session['is_admin'] = user[6]
        else:
            session['is_admin'] = False

        return redirect('/dashboard')   # 🔥 UPDATED

    else:
        return "Invalid credentials"


# ---------------- DASHBOARD ----------------
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    # Get user tasks summary
    if session.get('is_admin'):
        cur.execute("SELECT * FROM tasks")
    else:
        cur.execute("SELECT * FROM tasks WHERE user_id=%s", (session['user_id'],))

    tasks = cur.fetchall()

    # 📊 Stats for dashboard cards
    total = len(tasks)
    done = len([t for t in tasks if t[2] == 'done'])
    active = len([t for t in tasks if t[2] == 'inprogress'])

    cur.close()
    conn.close()

    return render_template(
        'dashboard.html',
        total=total,
        done=done,
        active=active
    )


# ---------------- KANBAN ----------------
@app.route('/kanban')
def kanban():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    if session.get('is_admin'):
        cur.execute("SELECT * FROM tasks")
    else:
        cur.execute(
            "SELECT * FROM tasks WHERE user_id=%s",
            (session['user_id'],)
        )

    tasks = cur.fetchall()

    # 📊 Pie chart
    todo = len([t for t in tasks if t[2] == 'todo'])
    inprogress = len([t for t in tasks if t[2] == 'inprogress'])
    done = len([t for t in tasks if t[2] == 'done'])

    cur.close()
    conn.close()

    return render_template(
        'kanban.html',
        tasks=tasks,
        is_admin=session.get('is_admin', False),
        todo=todo,
        inprogress=inprogress,
        done=done
    )


# ---------------- ADD TASK ----------------
@app.route('/add_task', methods=['POST'])
def add_task():
    if 'user_id' not in session:
        return redirect('/login')

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "INSERT INTO tasks (title, status, user_id) VALUES (%s, %s, %s)",
        (request.form['title'], 'todo', session['user_id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return redirect('/kanban')


# ---------------- UPDATE STATUS ----------------
@app.route('/update_status', methods=['POST'])
def update_status():
    data = request.get_json()

    conn = get_connection()
    cur = conn.cursor()

    cur.execute(
        "UPDATE tasks SET status=%s WHERE id=%s",
        (data['status'], data['id'])
    )

    conn.commit()
    cur.close()
    conn.close()

    return jsonify({"message": "updated"})


# ---------------- DELETE TASK ----------------
@app.route('/delete_task/<int:id>')
def delete_task(id):
    if not session.get('is_admin'):
        return "Unauthorized"

    conn = get_connection()
    cur = conn.cursor()

    cur.execute("DELETE FROM tasks WHERE id=%s", (id,))
    conn.commit()

    cur.close()
    conn.close()

    return redirect('/kanban')


# ---------------- LOGOUT ----------------
@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')


# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(debug=True)