from flask import Flask, render_template, redirect, request, session, url_for, flash,jsonify
from flask_bcrypt import Bcrypt
import pyodbc
from datetime import datetime

app = Flask(__name__)
app.secret_key = 'your_secret_key'

# Database connection string for Microsoft Access
DB_PATH = r'C:\Users\brio support\Documents\Swiming.accdb'  # Make sure the path is correct
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

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        # Capture form data
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        password = request.form['password']
        gender = request.form['gender']
        birth_date = request.form['birthDate']
        mobile_no = request.form['mobileNo']
        pincode = request.form['pincode']
        address = request.form['address']

        # Check if the email already exists in the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT * FROM User WHERE email = ?", (email,))
        user = cur.fetchone()
        
        if user:
            flash('Email is already registered. Please use a different email.', 'danger')
            cur.close()
            return render_template('register.html')

        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert the form data into the database
        cur.execute(""" 
            INSERT INTO User (FirstName, LastName, Email, Password, Gender, DateOfBirth, MobileNo, Pincode, Address) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, email, hashed_password, gender, birth_date, mobile_no, pincode, address)
        )
        
        # Commit the transaction and close the connection
        conn.commit()
        cur.close()

        # Flash a success message and redirect to the login page
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))

    # Render the registration form
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT * FROM User WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()

        # Check if the user exists
        if user:
            stored_hash = user[2]  # Assuming user[2] is the password column
            # Verify password
            if bcrypt.check_password_hash(stored_hash, password):  # Use check_password_hash directly
                session['loggedin'] = True
                session['id'] = user[0]  # Assuming user[0] is the ID column
                session['username'] = user[1]  # Assuming user[1] is the username column
                session['role'] = user[7]  # Assuming user[7] is the role column
                return redirect(url_for('dashboard'))  # Assuming you have a dashboard route
            else:
                flash('Incorrect email or password', 'danger')
        else:
            flash('User does not exist', 'danger')

    return render_template('login.html')




@app.route('/registerswim', methods=['GET', 'POST'])
def registerswim():
    if 'loggedin' not in session:
        flash('You need to log in to register for swimming classes.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        username = session['username']  # Get username from session
        category = request.form.get('register_for')

        # Determine class level based on category
        if category == "children":
            class_level = request.form.get('age_group')  # Capture age group for children
        else:
            class_level = request.form.get('adult_level')  # Capture adult level

        group_type = request.form.get('class_type')
       
        registration_date = datetime.now().date()
        max_capacity = int(request.form.get('max_capacity', 0))  # Ensure this is an integer

        # Get selected schedule slots
        schedule_slots = request.form.getlist('schedule_slots')

        # Convert time to "8:00 AM - 9:00 AM" format
        def convert_time_slot(slot):
            if 'T' in slot:
                # Extract the time portion (08:00/09:00)
                times = slot.split('T')[1]
                start_time, end_time = times.split('/')
                return f"{convert_to_ampm(start_time)} - {convert_to_ampm(end_time)}"
            return slot

        # Function to convert 24-hour time to 12-hour AM/PM format
        def convert_to_ampm(time_str):
            # Convert "08:00" to "8:00 AM" and "17:00" to "5:00 PM"
            time_obj = datetime.strptime(time_str, "%H:%M")
            return time_obj.strftime("%I:%M %p").lstrip('0')  # Remove leading 0 from the hour

        # Extract dates and convert time slots
        dates_list = []
        formatted_slots = []

        for slot in schedule_slots:
            if 'T' in slot:
                # Extract the date part
                date_part = slot.split('T')[0]  # Extract the date part (2024-10-07)
                dates_list.append(date_part)

                # Convert the time portion to "8:00 AM - 9:00 AM"
                formatted_slot = f"{date_part} {convert_time_slot(slot)}"
                formatted_slots.append(formatted_slot)

        # Join the dates for storage in timings
        timings_str = ', '.join(dates_list) if dates_list else str(datetime.now().date())
        timings_slots = [convert_time_slot(slot) for slot in schedule_slots if 'T' in slot]
        timings = ', '.join(timings_slots) if timings_slots else 'None' 
        # Join the formatted schedule slots
        schedule_slots_str = ', '.join(formatted_slots) if formatted_slots else 'None'

        try:
            # Establish connection to the MS Access database
            conn = pyodbc.connect(conn_str)
            cur = conn.cursor()

            # SQL Insert Query for MS Access
            sql = '''
            INSERT INTO SwimSchedule 
            (Category, ClassLevel, GroupType, Instructor,ClassDate, RegistrationDate, Timings, MaxCapacity, ScheduleSlots)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            '''
            
            # Execute the insert statement
            cur.execute(sql, ( category, class_level, group_type, username,timings_str,registration_date , timings, max_capacity, schedule_slots_str))
        
            # Commit the transaction
            conn.commit()

            flash('Registration for swimming classes successful!', 'success')
        except Exception as e:
            print("An error occurred:", e)  # Log the error for debugging
            flash('There was an error registering for the class. Please try again.', 'danger')
        finally:
            # Close the cursor and connection
            cur.close()
            conn.close()

        # Redirect to a confirmation page
        return redirect(url_for('success'))

    return render_template('user_dashboard.html')  # Assuming this template exists





@app.route('/date_selection', methods=['POST'])
def date_selection():
    # You can access form data using request.form
    register_for = request.form.get('register_for')
    age_group = request.form.get('age_group')
    level = request.form.get('level')
    class_type = request.form.get('class_type')
    adultlevel = request.form.get('adult_level')

    # Conditional logic to use adultlevel if register_for is 'adult'
    if register_for == 'adult':
        level = adultlevel
        age_group='none'

    return render_template('slots.html', register_for=register_for, age_group=age_group, level=level, class_type=class_type)



@app.route('/save_schedule', methods=['POST'])
def save_schedule():
    data = request.json  # Get the JSON data from the request
    print(data)
    user_id = session['id']  # Get the user ID from the session
    register_for = data.get('register_for')
    age_group = data.get('age_group')
    level = data.get('level')
    class_type = data.get('class_type')
    selected_dates = data.get('selected_dates')
    selected_time_slot = data.get('selected_time_slot')
    registration_date = datetime.now().date()

    # Validate input data
    if not all([register_for, age_group, level, class_type, selected_dates, selected_time_slot]):
        return jsonify({"error": "All fields must be filled."}), 400

    # Insert into swimSchedule table
    try:
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # SQL Insert Query for MS Access (8 placeholders for 8 values, including registration_date)
        query = """
            INSERT INTO [swimSchedules] ([register_for], [age_group], [level], [class_type], [schedule_date], [time_slot], [UserID], [registration_date])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        
        for date in selected_dates:
            # 8 values to match the 8 placeholders, including registration_date
            values = (register_for, age_group, level, class_type, date, selected_time_slot, user_id, registration_date)
            cur.execute(query, values)  # Execute the query

        conn.commit()  # Commit the changes

    except Exception as e:
        print("An error occurred:", str(e))  # Log the error for debugging
        return jsonify({"error": str(e)}), 500

    finally:
        cur.close()  # Close the cursor
        conn.close()  # Close the connection

    return jsonify({"message": "Schedule saved successfully!"}), 201



@app.route('/get_fully_booked_days', methods=['GET', 'POST'])  # Accept both methods
def get_fully_booked_days():
    data = request.get_json()  # Get the JSON data from the request
    print(data)
    
    class_type = data.get('class_type')

    fully_booked_days = set()  # To avoid duplicate dates

    try:
        # Connect to the Access database
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()

        # Check if class_type is private or group and set the appropriate limit
        if class_type == 'private':
            limit = 1
        elif class_type == 'group':
            limit = 3
        else:
            return jsonify({"error": "Invalid class_type"}), 400

        # Fetch fully booked days based on register_for and class_type with the appropriate limit
        query = """
            SELECT schedule_date FROM swimSchedules
            WHERE class_type = ?
            GROUP BY schedule_date
            HAVING COUNT(ID) >= ?
        """
        cursor.execute(query, (class_type, limit))
        booked_days_rows = cursor.fetchall()

        # Add fully booked dates
        for row in booked_days_rows:
            fully_booked_days.add(row.schedule_date.strftime('%Y-%m-%d'))

        conn.close()

    except pyodbc.Error as e:
        return jsonify({"error": str(e)}), 500

    # Convert the set to a dictionary format for JSON response
    fully_booked_days_dict = {day: True for day in fully_booked_days}

    # Return fully booked days as JSON
    return jsonify(fully_booked_days_dict)


@app.route('/payment_page', methods=['GET'])
def payment_page():
    amount = request.args.get('amount', 0)  # Get amount from query parameters
    return render_template('payment.html', amount=amount)

@app.route('/process_payment', methods=['POST'])
def process_payment():
    user_id = session['id']  # Assuming user ID is stored in session
    amount = request.form['amount']
    card_number = request.form['card_number']
    card_holder_name = request.form['card_holder_name']
    expiration_date = request.form['expiration_date']
    cvv = request.form['cvv']
    PaymentDate=datetime.now().date()
    
    # Insert payment into the Payments table
    conn = pyodbc.connect(conn_str)
    cursor = conn.cursor()
    
    # Use question mark placeholders for Access SQL queries
    insert_payment = ("INSERT INTO Payments "
                      "(UserID, Amount, CardNumber, CardHolderName, ExpirationDate, CVV,PaymentDate) "
                      "VALUES (?, ?, ?, ?, ?, ?, ?)")
    
    payment_data = (user_id, amount, card_number, card_holder_name, expiration_date, cvv,PaymentDate)
    
    # Execute the query
    try:
        cursor.execute(insert_payment, payment_data)  # Pass payment_data as parameters
        conn.commit()  # Commit the transaction
    except pyodbc.Error as e:
        print("Error occurred while inserting payment:", e)
        return "Error processing payment", 500  # Return an error response
    finally:
        cursor.close()
        conn.close()
    
    return "Payment processed successfully", 200  # Optional: return a success message


@app.route('/registerclass')
def registerclass():
    return render_template('registerclass.html')

@app.route('/success_page')
def success_page():
    return render_template('success.html')

@app.route('/dashboard')
def dashboard():
    if 'loggedin' not in session:
        flash('You need to log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')

@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


@app.route('/profile')
def profile():
    return render_template('profilepage.html')

@app.route('/registered_classes')
def registered_classes():
    return render_template('registered_classes.html')

# Run the app
if __name__ == '__main__':
    app.run(debug=True)
