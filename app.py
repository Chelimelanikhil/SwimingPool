from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_bcrypt import Bcrypt
import pyodbc

# pip install Flask Flask-Bcrypt pyodbc

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection string for Microsoft Access
DB_PATH = r'C:\Users\brio support\Documents\demo.accdb'  # Make sure the path is correct
conn_str = (
    r'DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};'  
    r'DBQ=' + DB_PATH + ';'
)

# Initialize bcrypt for password hashing
bcrypt = Bcrypt(app)

# Home route
@app.route('/')
def home():
    return render_template('home.html')

# Registration route
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']
        age = request.form['age']
        phone = request.form['phone']
        gender = request.form['gender']
        address = request.form['address']
        role = request.form.get('role', 'user')  # Default role is 'user'

        # Check if the email already exists
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        if user:
            flash('Email is already registered. Please use a different email.', 'danger')
            cur.close()
            return render_template('register.html')

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert the user data into the database
        cur.execute("""
            INSERT INTO users (username, email, password, age, phone, gender, address, role) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (username, email, hashed_password, age, phone, gender, address, role)
        )
        conn.commit()
        cur.close()

        
        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()

        # Check if the user exists and the password is correct
        if user and bcrypt.check_password_hash(user[3], password):  # user[3] is the password column in the database
            session['loggedin'] = True
            session['id'] = user[0]  # Assuming user[0] is the ID column
            session['username'] = user[1]  # Assuming user[1] is the username column
            session['role'] = user[7]  # Assuming user[7] is the role column
           
            return redirect(url_for('dashboard'))  # Assuming you have a dashboard route
        else:
            flash('Incorrect email or password', 'danger')

    return render_template('login.html')

# Placeholder for the dashboard
@app.route('/dashboard')
def dashboard():
    return render_template('user_dashboard.html')
  

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
