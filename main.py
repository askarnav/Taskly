import os
import psycopg2
from flask import Flask, render_template, url_for, session, flash, redirect, request
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email
from flask_bootstrap import Bootstrap5
from flask_login import logout_user, login_user, current_user, LoginManager, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
bootstrap = Bootstrap5(app)

app.secret_key = 'MyVerySecretKeyForTaskly2026Andialsousethiskeyforblogman-759jandistudeinclass7cintheyar2026pleasedonotsharethissecretkeywithanyoneintheworlthankyou'
app.config['WTF_CSRF_ENABLED'] = False
DSN = 'postgresql://posts_fuui_user:D9VjVBMC5qvlIzx2t7rAv1KC4aFfjp0V@://render.com'


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'


class User(UserMixin):
    def __init__(self, id, username, email):
        self.id = id
        self.username = username
        self.email = email


@login_manager.user_loader
def load_user(user_id):
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT id, username, email FROM users WHERE id = %s", (int(user_id),))
    user_data = cur.fetchone()
    cur.close()
    conn.close()
    if user_data:
        from operator import itemgetter
        get_id, get_user, get_email = itemgetter(0, 1, 2)(user_data)
        return User(id=str(get_id), username=get_user, email=get_email)
    return None




class RegisterForm(FlaskForm):
    name = StringField('Enter your name', [DataRequired()])
    email = StringField('Enter your e-mail', [DataRequired(), Email()])
    password = PasswordField('Set a password', [DataRequired()])
    submit = SubmitField('Create Account')


class LoginForm(FlaskForm):
    email = StringField('Enter your e-mail', [DataRequired(), Email()])
    password = PasswordField('Enter your password', [DataRequired()])
    submit = SubmitField('Login')


class TaskForm(FlaskForm):
    task = StringField('Add a task', [DataRequired()])
    submit = SubmitField('Add task')


def init_db():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY, 
            username VARCHAR(150) NOT NULL, 
            email VARCHAR(150) NOT NULL UNIQUE, 
            code TEXT NOT NULL
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS tasks (
            id SERIAL PRIMARY KEY,
            title TEXT NOT NULL,
            status VARCHAR(50) DEFAULT 'Pending',
            user_id INTEGER NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
        )
    """)
    conn.commit()
    cur.close()
    conn.close()


@app.route('/')
def main():
    return render_template("index.html")


@app.route('/home', methods=['POST', 'GET'])
@login_required
def home():
    form = TaskForm()
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    if form.validate_on_submit():
        task = form.task.data
        cur.execute(
            "INSERT INTO tasks (title, user_id) VALUES (%s, %s)",
            (task, int(current_user.id))
        )
        conn.commit()
        cur.close()
        conn.close()
        return redirect(url_for('home'))

    cur.execute("SELECT id, title, status FROM tasks WHERE user_id = %s ORDER BY id DESC", (int(current_user.id),))
    user_tasks = cur.fetchall()
    cur.close()
    conn.close()
    return render_template('home.html', user=current_user.username, form=form, tasks=user_tasks)


@app.route('/task/toggle/<int:task_id>', methods=['POST'])
@login_required
def toggle_task(task_id):
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("SELECT status FROM tasks WHERE id = %s AND user_id = %s", (task_id, int(current_user.id)))
    task = cur.fetchone()
    if task:
        new_status = 'Completed' if task[0] == 'Pending' else 'Pending'
        cur.execute("UPDATE tasks SET status = %s WHERE id = %s", (new_status, task_id))
        conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))


@app.route('/task/delete/<int:task_id>', methods=['POST'])
@login_required
def delete_task(task_id):
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("DELETE FROM tasks WHERE id = %s AND user_id = %s", (task_id, int(current_user.id)))
    conn.commit()
    cur.close()
    conn.close()
    return redirect(url_for('home'))


@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data
        hashed_password = generate_password_hash(password)
        conn = psycopg2.connect(DSN)
        cur = conn.cursor()
        try:
            cur.execute(
                "INSERT INTO users (username, email, code) VALUES (%s, %s, %s) RETURNING id",
                (name, email, hashed_password)
            )
            row = cur.fetchone()
            if row:
                from operator import itemgetter
                user_id = itemgetter(0)(row)
            else:
                user_id = None

            conn.commit()
            cur.close()
            conn.close()
            if user_id:
                userobj = User(id=str(user_id), username=name, email=email)
                login_user(userobj)
                return redirect(url_for('home'))
        except psycopg2.errors.UniqueViolation:
            conn.rollback()
            cur.close()
            conn.close()
            flash('User already exists with this email!')
            return redirect(url_for('register'))
    return render_template('register.html', form=form)


@app.route('/login', methods=['POST', 'GET'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        email = form.email.data
        password = form.password.data
        conn = psycopg2.connect(DSN)
        cur = conn.cursor()
        cur.execute('SELECT id, username, email, code FROM users WHERE email = %s', (email,))
        user_data = cur.fetchone()
        cur.close()
        conn.close()
        if user_data:
            from operator import itemgetter
            get_id, get_user, get_email, get_code = itemgetter(0, 1, 2, 3)(user_data)
            if check_password_hash(get_code, password):
                userobj = User(id=str(get_id), username=get_user, email=get_email)
                login_user(userobj)
                session['user_name'] = get_user
                return redirect(url_for('home'))
        flash('Invalid email or password!')
        return redirect(url_for('login'))
    return render_template('login.html', form=form)



@app.route('/logout')
@login_required
def logout():
    logout_user()
    session.clear()
    flash('You have been logged out.')
    return redirect(url_for('main'))


if __name__ == '__main__':
    init_db()
    app.run(debug=True)
