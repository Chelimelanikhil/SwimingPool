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
        country = request.form['country']  # New field for Country
        state = request.form['state']      # New field for State
        role = "User"

        # Check if the email already exists in the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cur.fetchone()
        
        if user:
            flash('Email is already registered. Please use a different email.', 'danger')
            cur.close()
            return render_template('register.html')

        # Hash the password before storing it
        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        # Insert the form data into the database, including Country and State
        cur.execute(""" 
            INSERT INTO Users (FirstName, LastName, Email, Password, Gender, DateOfBirth, MobileNo, Pincode, Address, Country, State, Role) 
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (first_name, last_name, email, hashed_password, gender, birth_date, mobile_no, pincode, address, country, state, role)
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
        cur.execute("SELECT * FROM Users WHERE email = ?", (email,))
        user = cur.fetchone()
        cur.close()

        # Check if the user exists
        if user:
            stored_hash = user[4]  # Assuming user[2] is the password column
            # Verify password
            if bcrypt.check_password_hash(stored_hash, password):  # Use check_password_hash directly
                session['loggedin'] = True
                session['id'] = user[0]  # Assuming user[0] is the ID column
                session['username'] = user[1]  # Assuming user[1] is the username column
                session['role'] = user[12]  # Assuming user[7] is the role column
                return redirect(url_for('dashboard'))  # Assuming you have a dashboard route
            else:
                flash('Incorrect email or password', 'danger')
        else:
            flash('User does not exist', 'danger')

    return render_template('login.html')

# def get_dashboard_data():
#     # Replace with your actual database connection and queries
#     data = {
#         'registered_users': 8282,  # Example data
#         'active_classes': 200,
#         'pending_orders': 32
#     }
#     return data

def get_dashboard_data():
    try:
        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Query to get the count of registered users
        cur.execute("SELECT COUNT(*) FROM Users")  # Assuming you have a Users table
        registered_users = cur.fetchone()[0]
        print(registered_users)

        # Query to get the count of active classes
        cur.execute("SELECT COUNT(*) FROM swimSchedules")  # Adjust based on your schema
        active_classes = cur.fetchone()[0]

        cur.execute("SELECT SUM(Amount) FROM Payments")  # Assuming the amount column is in the Payments table
        total_revenue = cur.fetchone()[0] or 0  # Use 0 if there are no payments

        
        # Close the cursor and connection
        cur.close()
        conn.close()

        # Return the data
        return {
            'registered_users': registered_users,
            'active_classes': active_classes,
            'total_revenue': total_revenue
            
        }

    except Exception as e:
        print("An error occurred while fetching dashboard data:", str(e))
        return {
            'registered_users': 0,
            'active_classes': 0,
            'total_revenue': 0
        }

@app.route('/Dashboard')
def Dashboard():
    # Call the function to get the dashboard data
    dashboard_data = get_dashboard_data()
    return render_template('Dashboard.html', data=dashboard_data)



# Dashboard route (protected)
@app.route('/dashboard')
def dashboard():
    if 'loggedin' in session:
        role = session.get('role')
        if role == 'Admin':
            return redirect(url_for('admin_dashboard'))
        elif role == 'User':
            return redirect(url_for('user_dashboard'))
    return redirect(url_for('login'))


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
    register_for = data.get('register_for')  # Get the register_for value from the request

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

        # Get the current date in the format 'YYYY-MM-DD'
        current_date = datetime.now().strftime('%Y-%m-%d')

        # Fetch fully booked days based on register_for, class_type, and the appropriate limit
        query = """
            SELECT schedule_date FROM swimSchedules
            WHERE class_type = ? 
              AND schedule_date >= ? 
              AND register_for = ?
            GROUP BY schedule_date
            HAVING COUNT(ID) >= ?
        """
        cursor.execute(query, (class_type, current_date, register_for, limit))
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

@app.route('/user_dashboard')
def user_dashboard():
    if 'loggedin' not in session:
        flash('You need to log in to access the dashboard.', 'danger')
        return redirect(url_for('login'))
    return render_template('user_dashboard.html')




@app.route('/admin_dashboard')
def admin_dashboard():
    if 'loggedin' in session and session.get('role') == 'Admin':
        return redirect(url_for('Dashboard'))
    else:
        flash('Access denied. Admins only.', 'danger')
        return redirect(url_for('dashboard'))





@app.route('/logout')
def logout():
    session.clear()  # Clear session data
    flash('You have been logged out.', 'info')
    return redirect(url_for('home'))


# @app.route('/profile')
# def profile():
#     return render_template('profilepage.html')

@app.route('/profile', methods=['GET'])
def get_user_profile():
    if 'loggedin' in session:
        userid = session['id']  # Get the UserID from the session

        try:
            # Connect to the database
            conn = pyodbc.connect(conn_str)
            cur = conn.cursor()

            # Fetch user details using the UserID from the session
            cur.execute("""
                SELECT FirstName, LastName, Email, Gender, DateOfBirth, MobileNo, Pincode, Address, Country, State, Role 
                FROM Users 
                WHERE UserID = ?
            """, (userid,))
            user = cur.fetchone()
            cur.close()

            # If user details are found, return them as a JSON response or render a template
            if user:
                user_details = {
                    'id': userid,
                    'FirstName': user[0],
                    'LastName': user[1],
                    'Email': user[2],
                    'Gender': user[3],
                    'DateOfBirth': str(user[4]),  # Convert date to string
                    'MobileNo': user[5],
                    'Pincode': user[6],
                    'Address': user[7],
                    'Country': user[8],  # New field for Country
                    'State': user[9]    # New field for State
                    
                }
                # Render the profile template or return user details in JSON format
                return render_template('profilepage.html', user=user_details)

            # If user details are not found, return an error
            else:
                flash('User not found', 'danger')
                return redirect(url_for('login'))

        except Exception as e:
            # Handle any database connection or execution errors
            return jsonify({'error': str(e)}), 500

    else:
        flash('Please log in to view your profile', 'warning')
        return redirect(url_for('login'))

    


@app.route('/swimschedule', methods=['GET'])
def get_swim_schedule():
    try:
        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Query to get all classes from swimSchedules
        cur.execute("SELECT * FROM swimSchedules")
        classes = cur.fetchall()

        # Close the cursor and connection
        cur.close()
        conn.close()

        # Process the results into a list of dictionaries
        schedule_list = []
        for row in classes:
            schedule_list.append({
                'register_for': row[1],         # Assuming column index 1 is register_for
                'age_group': row[2],            # Assuming column index 2 is age_group
                'level': row[3],                # Assuming column index 3 is level
                'class_type': row[4],           # Assuming column index 4 is class_type
                'schedule_date': row[5],        # Assuming column index 5 is schedule_date
                'time_slot': row[6],            # Assuming column index 6 is time_slot
                'registration_date': row[8]      # Assuming column index 8 is registration_date
            })

        # Return the JSON response
        return jsonify(schedule_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/registered_classes')
def registered_classes():
    user_id = session.get('id')  
    if not user_id:
        flash('Please log in to view your registered classes.', 'warning')
        return redirect(url_for('login'))

    try:
        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Query to get all registered classes for the specific user
        query = "SELECT * FROM swimSchedules WHERE UserID = ?"
        cur.execute(query, (user_id,))  # Ensure the tuple has a trailing comma

        classes = cur.fetchall()

        # Close the cursor and connection
        cur.close()
        conn.close()

        # Process the results into a list of dictionaries
        schedule_list = []
        for row in classes:
            schedule_list.append({
                'register_for': row[1],         # Adjust based on actual column indices
                'age_group': row[2],
                'level': row[3],
                'class_type': row[4],
                'schedule_date': row[5],
                'time_slot': row[6],
                'registration_date': row[8]
            })

        # Render the template with the classes data
        return render_template('registered_classes.html', classes=schedule_list)

    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
@app.route('/get_fee', methods=['POST'])
def get_fee():
    data = request.get_json()
    register_for = data.get('register_for')
    class_type = data.get('class_type')
    
    try:
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        
        query = """
            SELECT Fee
            FROM TimeSlots
            WHERE RegisteredFor = ? AND ClassType = ?
        """
        cur.execute(query, (register_for, class_type))
        fee_row = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if fee_row:
            fee_per_day = int(fee_row[0])
            return jsonify({'feePerDay': fee_per_day})
        else:
            return jsonify({'feePerDay': 0})  # Default case
    except Exception as e:
        return jsonify({'error': str(e)}), 500




    
@app.route('/view_all_user_classes', methods=['GET'])
def view_all_user_classes():
    try:
        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Query to fetch all classes, with LEVEL column escaped using brackets
        query = """
            SELECT register_for, age_group, [level], class_type, schedule_date, time_slot, registration_date
            FROM swimSchedules
        """
        cur.execute(query)

        # Fetch all results
        classes = cur.fetchall()

        # Process the results into a list of dictionaries
        class_list = []
        for row in classes:
            class_list.append({
                'register_for': row[0],
                'age_group': row[1],
                'level': row[2],  # Adjusted the index for each column
                'class_type': row[3],
                'schedule_date': row[4],
                'time_slot': row[5],
                'registration_date': row[6]
            })

        # Close the cursor and connection
        cur.close()
        conn.close()

        # Render the template with the class list
        return render_template('all_classes.html', classes=class_list)

    except Exception as e:
        return str(e), 500






@app.route('/approve_waitlist')
def approve_waitlist():
    return render_template('approve_waitlist.html')

@app.route('/respond_enquiry')
def respond_enquiry():
    return render_template('respond_enquiry.html')

@app.route('/update_view_schedule')
def update_view_schedule():
    return render_template('update_view_schedule.html')

# @app.route('/add_time_slot', methods=['GET', 'POST'])
# def add_time_slot():
#     if request.method == 'POST':
#         # Capture form data
#         time_slot = request.form['timeSlot']
#         fee = request.form['fee']

#         # Insert data into the TimeSlots table
#         conn = pyodbc.connect(conn_str)
#         cur = conn.cursor()
        
#         cur.execute("""
#             INSERT INTO TimeSlots (TimeSlot, Fee)
#             VALUES (?, ?)
#         """, (time_slot, fee))
        
#         # Commit transaction and close connection
#         conn.commit()
#         cur.close()

#         # Flash success message and redirect
#         flash('Time slot added successfully!', 'success')
#         return redirect(url_for('update_view_schedule'))
    
#     # Render the form
#     return render_template('update_view_schedule.html')

@app.route('/view_update_fee_structure')
def view_update_fee_structure():
    return render_template('view_update_fee_structure.html')

@app.route('/view_user_profiles', methods=['GET'])
def view_user_profiles():
    try:
        # Connect to the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()

        # Execute a query to get all users along with Country and State
        cur.execute("""
            SELECT UserID, FirstName, LastName, Email, Gender, DateOfBirth, 
                   MobileNo, Pincode, Address, Country, State, Role 
            FROM Users
        """)
        users = cur.fetchall()  # Fetch all results

        # Close the cursor and connection
        cur.close()
        conn.close()

        # Convert the results to a list of dictionaries for easy handling in templates
        user_list = []
        for user in users:
            user_list.append({
                'id': user.UserID,
                'first_name': user.FirstName,
                'last_name': user.LastName,
                'email': user.Email,
                'gender': user.Gender,
                'date_of_birth': user.DateOfBirth,
                'mobile_no': user.MobileNo,
                'pincode': user.Pincode,
                'address': user.Address,
                'country': user.Country,  # Added Country field
                'state': user.State,      # Added State field
                'role': user.Role
            })

        # Render a template to display the users
        return render_template('view_user_profiles.html', users=user_list)

    except Exception as e:
        # Handle any exceptions (e.g., log the error)
        print(f"An error occurred: {e}")
        flash('An error occurred while fetching user data.', 'danger')
        return redirect(url_for('dashboard'))  # Redirect to a safe page




@app.route('/edit_user/<int:user_id>', methods=['GET'])
def edit_user(user_id):
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    # Fetch the user data to prepopulate the form
    print(user_id)
    cur.execute("SELECT * FROM Users WHERE UserID = ?", (user_id,))
    user = cur.fetchone()
    cur.close()

    if user:
        return render_template('edit_user.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('users'))
    

@app.route('/edit_user_profile/<int:user_id>', methods=['GET'])
def edit_user_profile(user_id):
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    # Fetch the user data to prepopulate the form
    print(user_id)
    cur.execute("SELECT * FROM Users WHERE UserID = ?", (user_id,))
    user = cur.fetchone()
    cur.close()

    if user:
        return render_template('edit_user_profile.html', user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('users'))


@app.route('/delete_user/<int:user_id>', methods=['POST'])
def delete_user(user_id):
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()
    
    cur.execute("DELETE FROM Users WHERE UserID = ?", (user_id,))
    conn.commit()
    cur.close()
    
    flash('User deleted successfully!', 'success')
    return redirect(url_for('view_user_profiles'))



@app.route('/update_user/<int:user_id>', methods=['POST'])
def update_user(user_id):
    if request.method == 'POST':
        # Capture form data
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        gender = request.form['gender']
        birth_date = request.form['birthDate']
        mobile_no = request.form['mobileNo']
        pincode = request.form['pincode']
        address = request.form['address']
        country = request.form['country']  # New field
        state = request.form['state']      # New field

        # Connect to the database and update user data
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("""
            UPDATE Users 
            SET FirstName = ?, LastName = ?, Email = ?, Gender = ?, DateOfBirth = ?, 
                MobileNo = ?, Pincode = ?, Address = ?, Country = ?, State = ?
            WHERE UserID = ?
        """, (first_name, last_name, email, gender, birth_date, mobile_no, pincode, address, country, state, user_id))
        
        # Commit the transaction and close the connection
        conn.commit()
        cur.close()

        # Flash a success message and redirect to the user list
        flash('User updated successfully!', 'success')
        return redirect(url_for('view_user_profiles'))

    




@app.route('/update_user_profile/<int:user_id>', methods=['POST'])
def update_user_profile(user_id):
    if request.method == 'POST':
        # Capture form data
        first_name = request.form['firstName']
        last_name = request.form['lastName']
        email = request.form['email']
        gender = request.form['gender']
        birth_date = request.form['birthDate']
        mobile_no = request.form['mobileNo']
        pincode = request.form['pincode']
        address = request.form['address']
        country = request.form['country']  # Added country
        state = request.form['state']      # Added state

        # Debugging print statement
        print(f"Country: {country}, State: {state}")

        # Connect to the database and update user data
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        cur.execute("""
            UPDATE Users 
            SET FirstName = ?, LastName = ?, Email = ?, Gender = ?, DateOfBirth = ?, 
                MobileNo = ?, Pincode = ?, Address = ?, Country = ?, State = ?
            WHERE UserID = ?
        """, (first_name, last_name, email, gender, birth_date, mobile_no, pincode, address, country, state, user_id))
        
        # Commit the transaction and close the connection
        conn.commit()
        cur.close()

        flash('User updated successfully!', 'success')
        return redirect(url_for('get_user_profile'))



@app.route('/api/getTimeSlots', methods=['GET'])
def get_time_slots():
    # Connect to the database
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    # Query to fetch the time slots
    cur.execute("SELECT TimeSlot, ClassType, Fee, RegisteredFor FROM TimeSlots")
    time_slots = cur.fetchall()

    # Convert the fetched data to a list of dictionaries
    time_slots_list = [
        {
            "TimeSlot": row.TimeSlot,
            "ClassType": row.ClassType,
            "Fee": row.Fee,
            "RegisteredFor": row.RegisteredFor
        }
        for row in time_slots
    ]

    # Close the connection
    cur.close()
    conn.close()

    return jsonify(time_slots_list)



@app.route('/time_slots', methods=['GET'])
def time_slots():
    try:
        # Fetch all time slots from the database
        conn = pyodbc.connect(conn_str)
        cur = conn.cursor()
        
        query = "SELECT * FROM TimeSlots"
        cur.execute(query)
        slots = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return render_template('update_view_schedule.html', time_slots=slots)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/edit_time_slot/<int:slot_id>', methods=['GET', 'POST'])
def edit_time_slot(slot_id):
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()

    if request.method == 'POST':
        time_slot = request.form['timeSlot']
        fee = request.form['fee']
        class_type = request.form['classType']
        registered_for = request.form['registeredFor']

        # Update SQL command
        sql = """
        UPDATE TimeSlots
        SET TimeSlot = ?, Fee = ?, ClassType = ?, RegisteredFor = ?
        WHERE TimeSlotID = ?
        """
        try:
            cur.execute(sql, (time_slot, fee, class_type, registered_for, slot_id))
            conn.commit()
        except pyodbc.Error as e:
            print(f"Error during update: {e}")
            return "An error occurred while updating the time slot.", 500

        return redirect(url_for('time_slots'))  # Redirect to the time slots page after updating

    # Fetch current values for the time slot to be edited
    sql = "SELECT TimeSlotID, TimeSlot, Fee, ClassType, RegisteredFor FROM TimeSlots WHERE TimeSlotID = ?"
    try:
        cur.execute(sql, (slot_id,))
        slot = cur.fetchone()
    except pyodbc.Error as e:
        print(f"Error during fetch: {e}")
        return "An error occurred while retrieving the time slot.", 500

    cur.close()
    conn.close()

    if slot:
        return render_template('edit_time_slot.html', slot=slot)
    else:
        return "Time Slot not found", 404  # Handle case where the time slot does not exist



@app.route('/delete_time_slot/<int:slot_id>', methods=['POST'])
def delete_time_slot(slot_id):
    # Establish a connection to the MS Access database
    conn = pyodbc.connect(conn_str)
    cur = conn.cursor()
    
    try:
        # SQL command to delete the time slot with the given ID
        sql = "DELETE FROM TimeSlots WHERE TimeSlotID = ?"
        cur.execute(sql, (slot_id,))
        
        # Commit the transaction
        conn.commit()
    except Exception as e:
        # Handle any exceptions (optional)
        print(f"An error occurred: {e}")
    finally:
        # Close the cursor and connection
        cur.close()
        conn.close()

    # Redirect to the time slots page after deletion
    return redirect(url_for('time_slots'))



@app.route('/add_time_slot', methods=['GET', 'POST'])
def add_time_slot():
    if request.method == 'POST':
        # Logic to handle form submission and add new time slot to the database
        pass
    
    return render_template('add_time_slot.html')  # Create this HTML file for the form


import logging

# Set up logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/add_new_time_slot', methods=['GET', 'POST'])
def add_new_time_slot():
    logging.debug(f"Request method: {request.method}")
    
    if request.method == 'POST':
        time_slot = request.form['timeSlot']
        fee = request.form['fee']
        class_type = request.form['classType']
        registered_for = request.form['registeredFor']

        logging.debug(f"Inserting Time Slot: {time_slot}, Fee: {fee}, ClassType: {class_type}, RegisteredFor: {registered_for}")

        # Connect to the MS Access database
        conn = pyodbc.connect(conn_str)
        cursor = conn.cursor()
        
        try:
            # SQL query to insert a new time slot
            insert_query = """
            INSERT INTO TimeSlots (TimeSlot, Fee, ClassType, RegisteredFor)
            VALUES (?, ?, ?, ?)
            """
            cursor.execute(insert_query, (time_slot, fee, class_type, registered_for))
            conn.commit()  # Commit the transaction
            
            logging.debug("Insert successful!")  # Confirm successful insert
        except Exception as e:
            logging.error(f"Error occurred: {e}")  # Log the error message
        finally:
            cursor.close()  # Close the cursor
            conn.close()    # Close the connection

        return redirect(url_for('time_slots'))  # Redirect to the page where time slots are listed

    return render_template('add_time_slot.html')  # Render the form for GET requests




@app.route('/calender')
def calender():
    return render_template('calender.html')


# Run the app
if __name__ == '__main__':
    app.run(debug=True)
