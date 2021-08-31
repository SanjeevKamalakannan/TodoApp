from flask import Flask, render_template, flash, redirect, url_for, session, request, logging
#from data import Articles
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, PasswordField, validators
from passlib.hash import sha256_crypt
from functools import wraps
from phe import paillier
from Crypto.Cipher import AES
import hashlib
from Crypto import Random
from base64 import b64encode, b64decode
import os, binascii
from backports.pbkdf2 import pbkdf2_hmac
import pickle
import os
app = Flask(__name__)

# Config MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'test123'
app.config['MYSQL_DB'] = 'flaskapp'
app.config['MYSQL_CURSORCLASS'] = 'DictCursor'
# init MYSQL
mysql = MySQL(app)

#Articles = Articles()

# Index
@app.route('/')
def index():
    return render_template('home.html')

# Register Form Class
class RegisterForm(Form):
    name = StringField('Name', [validators.Length(min=1, max=50)])
    username = StringField('Username', [validators.Length(min=4, max=25)])
    email = StringField('Email', [validators.Length(min=6, max=50)])
    password = PasswordField('Password', [
        validators.DataRequired(),
        validators.EqualTo('confirm', message='Passwords do not match')
    ])
    confirm = PasswordField('Confirm Password')


# User Register
@app.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm(request.form)
    if request.method == 'POST' and form.validate():
        name = form.name.data
        email = form.email.data
        username = form.username.data
        username = str(username)
        password = str(form.password.data)
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO todousers(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password ))
        mysql.connection.commit()
        cur.close()

        flash('You are now registered and can log in', 'success')

        return redirect(url_for('login'))
    return render_template('register.html', form=form)


# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # Get Form Fields
        username = request.form['username']
        password_candidate = request.form['password']
        # Create cursor
        cur = mysql.connection.cursor()

        # Get user by username
        result = cur.execute("SELECT * FROM todousers WHERE username = %s", [username])

        if result > 0:
            # Get stored hash
            data = cur.fetchone()
            password = data['password']
            
            # Compare Passwords
            if (password_candidate == password):
                session['logged_in'] = True
                session['username'] = username
                session['userid'] = data['id']
                session['password'] = password_candidate
                flash('You are now logged in', 'success')
                return redirect(url_for('dashboard'))
            else:
                error = 'Invalid login'
                return render_template('login.html', error=error)
            # Close connection
            cur.close()
        else:
            error = 'Username not found'
            return render_template('login.html', error=error)

    return render_template('login.html')

# Check if user logged in
def is_logged_in(f):
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'logged_in' in session:
            return f(*args, **kwargs)
        else:
            flash('Unauthorized, Please login', 'danger')
            return redirect(url_for('login'))
    return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
    session.clear()
    flash('You are now logged out', 'success')
    return redirect(url_for('login'))

@app.route('/todos')
def todos():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM todos wHERE userid = %s", [session['userid']])
    todos = cur.fetchall()
    if result > 0:
        return render_template('todos.html', todos=todos)
    else:
        msg = 'No Todos Found'
        return render_template('todos.html', msg=msg)
    # Close connection
    cur.close()
    
# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM todos wHERE userid = %s", [session['userid']])
    todos = cur.fetchall()
    if result > 0:
        return render_template('dashboard.html', todos=todos)
    else:
        msg = 'No Todos Found'
        return render_template('dashboard.html', msg=msg)
    cur.close()

class AddTodoForm(Form):
    todo = StringField('Your Todo :', [validators.Length(min=1, max=100)])

@app.route('/addtodo', methods=['GET', 'POST'])
@is_logged_in
def debit():
    form = AddTodoForm(request.form)
    if request.method == 'POST' and form.validate():
        todo = form.todo.data
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO todos(userid, todo) VALUES(%s, %s)", (session['userid'], todo ))
        mysql.connection.commit()
        cur.close()
        flash('Todo Added', 'success')
        return redirect(url_for('dashboard'))
        
    return render_template('addtodo.html', form=form)

@app.route('/delete_todo/<string:id>', methods=['POST'])
@is_logged_in
def delete_todo(id):
    print(id)
    cur = mysql.connection.cursor()
    cur.execute("DELETE FROM todos WHERE todoid = %s", [id])
    mysql.connection.commit()
    cur.close()
    flash('Todo Deleted', 'success')
    return redirect(url_for('dashboard'))

class EditTodoForm(Form):
    todo = StringField('Todo', [validators.Length(min=1, max=200)])

@app.route('/edit_todo/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_todo(id):
    cur = mysql.connection.cursor()
    result = cur.execute("SELECT * FROM todos WHERE todoid = %s and userid = %s", (id, session['userid']))

    todo = cur.fetchone()
    cur.close()
    form = EditTodoForm(request.form)
    form.todo.data = todo['todo']

    if request.method == 'POST' and form.validate():
        todo = request.form['todo']
        cur = mysql.connection.cursor()
        app.logger.info(todo)
        cur.execute ("UPDATE todos SET todo=%s WHERE todoid=%s and userid=%s",(todo, id, session['userid']))
        mysql.connection.commit()
        cur.close()
        flash('Todo Updated', 'success')

        return redirect(url_for('dashboard'))

    return render_template('edit_article.html', form=form)

if __name__ == '__main__':
    app.secret_key='secret123'
    app.run(debug=True)
