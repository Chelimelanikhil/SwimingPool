from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_mysqldb import MySQL
from flask_bcrypt import Bcrypt
import MySQLdb.cursors

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Configure MySQL
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Nani@1234'
app.config['MYSQL_DB'] = 'Swimingpoll'

# Initialize MySQL and Bcrypt
mysql = MySQL(app)
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
        role = request.form.get('role', 'user')  # Default to 'user'

        # Check if the email already exists
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user:
            flash('Email is already registered. Please use a different email.', 'danger')
            return render_template('register.html')

        # Hash the password
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert the data into the database
        cur = mysql.connection.cursor()
        cur.execute("INSERT INTO users (username, email, password, age, phone, gender, address, role) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)", 
                    (username, email, hashed_password, age, phone, gender, address, role))
        mysql.connection.commit()
        cur.close()

        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))

    return render_template('register.html')

# Login route
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Check if the user exists
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and bcrypt.check_password_hash(user['password'], password):
            session['loggedin'] = True
            session['id'] = user['id']
            session['username'] = user['username']
            session['role'] = user['role']  # Store the user role
            flash('Login successful!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Incorrect email or password', 'danger')
    
    return render_template('login.html')

# Role-based route for Admin
@app.route('/admin_dashboard')
def admin_dashboard():
    if 'loggedin' in session and session.get('role') == 'admin':
        return render_template('admin_dashboard.html')
    else:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))

# Role-based route for User
@app.route('/user_dashboard', methods=['GET', 'POST'])
def user_dashboard():
    if 'loggedin' in session:
        if request.method == 'POST':
            # Handle registration
            user_id = session['id']
            class_type = request.form['class_type']
            timing = request.form['timing']
            fee = request.form['fee']
            age_group = request.form.get('age_group')
            level = request.form.get('level')
            
            # Find class ID based on the selection
            cur = mysql.connection.cursor()
            cur.execute("SELECT id FROM classes WHERE class_type = %s AND timing = %s AND fee = %s AND age_group = %s AND level = %s",
                        (class_type, timing, fee, age_group, level))
            class_id = cur.fetchone()
            cur.close()

            if class_id:
                # Register the user for the class
                cur = mysql.connection.cursor()
                cur.execute("INSERT INTO registrations (user_id, class_id) VALUES (%s, %s)", (user_id, class_id['id']))
                mysql.connection.commit()
                cur.close()
                
                flash('Registered successfully!', 'success')
            else:
                flash('Class not found.', 'danger')
        
        # Fetch registered classes for the user
        cur = mysql.connection.cursor()
        cur.execute("""
            SELECT c.class_type, c.timing, c.fee, c.age_group, c.level
            FROM registrations r
            JOIN classes c ON r.class_id = c.id
            WHERE r.user_id = %s
        """, (session['id'],))
        registered_classes = cur.fetchall()
        cur.close()

        return render_template('user_dashboard.html', registered_classes=registered_classes)
    return redirect(url_for('login'))

# Route to fetch class options (could be in a separate route or function)
@app.route('/class_options', methods=['GET'])
def class_options():
    cur = mysql.connection.cursor()
    cur.execute("SELECT DISTINCT class_type FROM classes")
    class_types = cur.fetchall()
    cur.execute("SELECT DISTINCT timing FROM classes")
    timings = cur.fetchall()
    cur.execute("SELECT DISTINCT fee FROM classes")
    fees = cur.fetchall()
    cur.close()
    return render_template('class_options.html', class_types=class_types, timings=timings, fees=fees)


# Dashboard route (protected)
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        role = session.get('role')
        if role == 'admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'user':
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


@app.route('/Dashboard')
def Dashboard():
    return render_template('Dashboard.html')

@app.route('/approve_waitlist')
def approve_waitlist():
    return render_template('approve_waitlist.html')

@app.route('/respond_enquiry')
def respond_enquiry():
    return render_template('respond_enquiry.html')

@app.route('/update_view_schedule')
def update_view_schedule():
    return render_template('update_view_schedule.html')



@app.route('/view_update_fee_structure')
def view_update_fee_structure():
    return render_template('view_update_fee_structure.html')


@app.route('/view_user_profiles')
def view_user_profiles():
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users")
        users = cur.fetchall()
        cur.close()
        return render_template('view_user_profiles.html', users=users)
    else:
        flash('Please log in to view user profiles.', 'warning')
        return redirect(url_for('login'))


@app.route('/user_profile/<int:user_id>')
def view_user_profile(user_id):
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()
        if user:
            return render_template('view_user_profile.html', user=user)
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('view_user_profiles'))
    else:
        flash('Please log in to view user profiles.', 'warning')
        return redirect(url_for('login'))

@app.route('/edit_user_profile/<int:user_id>', methods=['GET', 'POST'])
def edit_user_profile(user_id):
    if 'loggedin' in session:
        if request.method == 'POST':
            username = request.form['username']
            email = request.form['email']
            # Update other fields if necessary

            cur = mysql.connection.cursor()
            cur.execute("""
                UPDATE users
                SET username = %s, email = %s
                WHERE id = %s
            """, (username, email, user_id))
            mysql.connection.commit()
            cur.close()

            flash('Profile updated successfully!', 'success')
            return redirect(url_for('view_user_profile', user_id=user_id))

        # Fetch user profile for editing
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        user = cur.fetchone()
        cur.close()

        if user:
            return render_template('edit_user_profile.html', user=user)
        else:
            flash('User not found.', 'danger')
            return redirect(url_for('view_user_profiles'))
    else:
        flash('Please log in to edit user profiles.', 'warning')
        return redirect(url_for('login'))


@app.route('/view_all_user_classes')
def view_all_user_classes():
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM classes")  # Adjust the table name and fields as necessary
        user_classes = cur.fetchall()
        cur.close()
        return render_template('view_all_user_classes.html', user_classes=user_classes)
    else:
        flash('Please log in to view user classes.', 'warning')
        return redirect(url_for('login'))



@app.route('/user_class/<int:class_id>')
def view_user_class(class_id):
    if 'loggedin' in session:
        cur = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cur.execute("SELECT * FROM classes WHERE class_id = %s", (class_id,))
        user_class = cur.fetchone()
        cur.close()
        if user_class:
            return render_template('view_user_class.html', user_class=user_class)
        else:
            flash('Class not found.', 'danger')
            return redirect(url_for('view_all_user_classes'))
    else:
        flash('Please log in to view class details.', 'warning')
        return redirect(url_for('login'))



# Logout route
@app.route('/logout')
def logout():
    # Clear session
    session.pop('loggedin', None)
    session.pop('id', None)
    session.pop('username', None)
    
    # Clear any existing flash messages
    session.pop('_flashes', None)
    
    # Flash a message and redirect to login
    #flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


if __name__ == '__main__':
    app.run(debug=True)
