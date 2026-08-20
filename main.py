import psycopg2
from flask import Flask, render_template, url_for, session, flash, redirect
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Email
from flask_bootstrap import Bootstrap5
from flask_login import logout_user, login_user, current_user, LoginManager, login_required, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = 'VerySecretPasswordOfArnavSomanI@gmail.comWHoisaCoderSetsAPaasswordCRSFTokenForWebsiteTaskEasy2026'
Bootstrap5(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

DSN = "postgresql://posts_fuui_user:D9VjVBMC5qvlIzx2t7rAv1KC4aFfjp0V@dpg-d9li63u7bikc7393dhp0-a.oregon-postgres.render.com/posts_fuui"
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
        return User(id=user_data[0], username=user_data[1], email=user_data[2])
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

def init_db():
    conn = psycopg2.connect(DSN)
    cur = conn.cursor()
    cur.execute("DROP TABLE IF EXISTS users CASCADE;")
    cur.execute("""
        CREATE TABLE users (
            id SERIAL PRIMARY KEY, 
            username VARCHAR(150) NOT NULL, 
            email VARCHAR(150) NOT NULL UNIQUE, 
            code TEXT NOT NULL
        )
    """)
    conn.commit()
    cur.close()
    conn.close()

@app.route('/')
def main():
    return render_template("index.html")

@app.route('/home')
@login_required
def home():
    return render_template('home.html', user=current_user.username)

@app.route('/register', methods=['POST', 'GET'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        email = form.email.data
        password = form.password.data

        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        conn = psycopg2.connect(DSN)
        cur = conn.cursor()

        try:
            cur.execute(
                "INSERT INTO users (username, email, code) VALUES (%s, %s, %s) RETURNING id",
                (name, email, hashed_password)
            )
            user_id = cur.fetchone()[0]
            conn.commit()
            cur.close()
            conn.close()

            userobj = User(id=user_id, username=name, email=email)
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

        if user_data and check_password_hash(user_data[3], password):
            userobj = User(id=user_data[0], username=user_data[1], email=user_data[2])
            login_user(userobj)
            session['user_name'] = user_data[1]
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
