import os
import datetime
from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from functools import wraps
import mysql.connector
import sqlite3

app = Flask(__name__)
app.secret_key = 'cloud_budget_secret_key_13579' # Secure key for sessions

@app.template_filter('format_currency')
def format_currency(value):
    try:
        return f"{float(value):,.2f}"
    except (ValueError, TypeError):
        return "0.00"

# Database helper to run queries across either MySQL or SQLite
class Database:
    def __init__(self):
        self.db_type = 'sqlite'
        self.conn = None
        self.sqlite_path = os.path.join(os.path.dirname(__file__), 'cloud_budget.db')
        
        # Try connecting to MySQL
        try:
            # First connect without database to create it if not exists
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password=""
            )
            cursor = self.conn.cursor()
            cursor.execute("CREATE DATABASE IF NOT EXISTS cloud_budget_db")
            cursor.close()
            self.conn.close()
            
            # Now connect to the database
            self.conn = mysql.connector.connect(
                host="localhost",
                user="root",
                password="",
                database="cloud_budget_db"
            )
            self.db_type = 'mysql'
            print("Successfully connected to MySQL database: 'cloud_budget_db'")
        except Exception as e:
            print(f"MySQL connection failed: {e}. Falling back to local SQLite database.")
            self.conn = sqlite3.connect(self.sqlite_path)
            self.db_type = 'sqlite'
        
        self.init_db()

    def init_db(self):
        # Create tables depending on the DB type
        cursor = self.get_cursor()
        if self.db_type == 'mysql':
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(100) NOT NULL UNIQUE,
                email VARCHAR(150) NOT NULL UNIQUE,
                password VARCHAR(255) NOT NULL
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                budget_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                monthly_limit DECIMAL(10, 2) NOT NULL DEFAULT 0.00,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_costs (
                cost_id INT AUTO_INCREMENT PRIMARY KEY,
                user_id INT NOT NULL,
                service_name VARCHAR(100) NOT NULL,
                amount DECIMAL(10, 2) NOT NULL,
                usage_date DATE NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """)
        else:
            # SQLite
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                email TEXT NOT NULL UNIQUE,
                password TEXT NOT NULL
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS budget (
                budget_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                monthly_limit REAL NOT NULL DEFAULT 0.00,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS cloud_costs (
                cost_id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                service_name TEXT NOT NULL,
                amount REAL NOT NULL,
                usage_date TEXT NOT NULL,
                FOREIGN KEY (user_id) REFERENCES users(user_id) ON DELETE CASCADE
            )
            """)
        self.commit()
        cursor.close()

    def get_connection(self):
        if self.db_type == 'mysql':
            try:
                self.conn.ping(reconnect=True, attempts=3, delay=1)
                return self.conn
            except Exception:
                self.conn = mysql.connector.connect(
                    host="localhost",
                    user="root",
                    password="",
                    database="cloud_budget_db"
                )
                return self.conn
        else:
            # SQLite connection open-per-thread safety
            return sqlite3.connect(self.sqlite_path)

    def get_cursor(self, connection=None):
        if connection is None:
            connection = self.get_connection()
        if self.db_type == 'mysql':
            return connection.cursor(dictionary=True)
        else:
            connection.row_factory = sqlite3.Row
            return connection.cursor()

    def commit(self, connection=None):
        if self.db_type == 'mysql':
            if connection:
                connection.commit()
            elif self.conn:
                self.conn.commit()
        else:
            if connection:
                connection.commit()

    def execute_query(self, query, params=(), fetch='all'):
        conn = self.get_connection()
        cursor = self.get_cursor(conn)
        try:
            if self.db_type == 'sqlite':
                query = query.replace('%s', '?')
            cursor.execute(query, params)
            if fetch == 'all':
                result = cursor.fetchall()
                if self.db_type == 'sqlite' and result:
                    result = [dict(row) for row in result]
                elif not result:
                    result = []
            elif fetch == 'one':
                result = cursor.fetchone()
                if self.db_type == 'sqlite' and result:
                    result = dict(result)
            else:
                self.commit(conn)
                result = cursor.lastrowid
            return result
        finally:
            cursor.close()
            if self.db_type == 'sqlite':
                conn.close()

# Initialize DB
db = Database()

# Login Required Decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'danger')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# --- Authentication Routes ---

@app.route('/register', methods=['GET', 'POST'])
def register():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        email = request.form.get('email', '').strip()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        if not username or not email or not password:
            flash('All fields are required.', 'danger')
            return render_template('register.html')
            
        if password != confirm_password:
            flash('Passwords do not match.', 'danger')
            return render_template('register.html')
            
        # Check if username or email already exists
        existing = db.execute_query(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (username, email),
            fetch='one'
        )
        if existing:
            flash('Username or Email already registered.', 'danger')
            return render_template('register.html')
            
        hashed_password = generate_password_hash(password)
        db.execute_query(
            "INSERT INTO users (username, email, password) VALUES (%s, %s, %s)",
            (username, email, hashed_password),
            fetch='lastrowid'
        )
        flash('Registration successful! Please login.', 'success')
        return redirect(url_for('login'))
        
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
        
    if request.method == 'POST':
        username_or_email = request.form.get('username_or_email', '').strip()
        password = request.form.get('password', '')
        
        if not username_or_email or not password:
            flash('Please fill in all fields.', 'danger')
            return render_template('login.html')
            
        # Query user
        user = db.execute_query(
            "SELECT * FROM users WHERE username = %s OR email = %s",
            (username_or_email, username_or_email),
            fetch='one'
        )
        
        if user and check_password_hash(user['password'], password):
            session['user_id'] = user['user_id']
            session['username'] = user['username']
            flash(f"Welcome back, {user['username']}!", 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username/email or password.', 'danger')
            return render_template('login.html')
            
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

# --- Main Dashboard ---

@app.route('/')
@app.route('/dashboard')
@login_required
def dashboard():
    user_id = session['user_id']
    
    # 1. Fetch Budget
    budget_row = db.execute_query(
        "SELECT monthly_limit FROM budget WHERE user_id = %s",
        (user_id,),
        fetch='one'
    )
    budget = float(budget_row['monthly_limit']) if budget_row else 0.0
    
    # 2. Fetch Expenses
    expenses = db.execute_query(
        "SELECT * FROM cloud_costs WHERE user_id = %s ORDER BY usage_date DESC",
        (user_id,)
    )
    
    # 3. Calculate Aggregates
    total_spent = sum(float(exp['amount']) for exp in expenses)
    remaining_budget = budget - total_spent
    
    # 4. Determine Alert Levels and Budget Status
    utilization = (total_spent / budget * 100) if budget > 0 else 0.0
    
    # Default Level Statuses
    # 80% -> Warning
    # 90% -> Critical
    # 100% -> Budget Exceeded
    if budget <= 0:
        status_text = "No Budget Set"
        status_level = "secondary"
        alert_msg = "Please set a monthly budget to enable cost tracking alerts."
    elif utilization >= 100:
        status_text = "Budget Exceeded"
        status_level = "danger"
        alert_msg = f"Alert: Monthly budget exceeded! You have overspent by ₹{abs(remaining_budget):,.2f} ({utilization:.1f}% used)."
    elif utilization >= 90:
        status_text = "Critical"
        status_level = "warning-orange" # Custom styling
        alert_msg = f"Critical Warning: You have consumed {utilization:.1f}% of your budget! Only ₹{remaining_budget:,.2f} remaining."
    elif utilization >= 80:
        status_text = "Warning"
        status_level = "warning"
        alert_msg = f"Warning: You have consumed {utilization:.1f}% of your budget. ₹{remaining_budget:,.2f} remaining."
    else:
        status_text = "Normal"
        status_level = "success"
        alert_msg = f"Good news! Your spending is under control at {utilization:.1f}% of your budget."
        
    # 5. Service-wise Grouping (Pie Chart Data)
    service_totals = {}
    for exp in expenses:
        svc = exp['service_name']
        service_totals[svc] = service_totals.get(svc, 0.0) + float(exp['amount'])
        
    pie_labels = list(service_totals.keys())
    pie_values = list(service_totals.values())
    
    # 6. Monthly Spending Trend (Line Chart Data)
    monthly_totals = {}
    for exp in expenses:
        dt = exp['usage_date']
        if isinstance(dt, str):
            try:
                date_obj = datetime.datetime.strptime(dt.split(' ')[0], '%Y-%m-%d').date()
            except ValueError:
                date_obj = datetime.datetime.strptime(dt, '%Y-%m-%d').date()
        else:
            date_obj = dt
        month_key = date_obj.strftime('%b %Y')
        monthly_totals[month_key] = monthly_totals.get(month_key, 0.0) + float(exp['amount'])
        
    # Sort chronological
    sorted_months = sorted(
        monthly_totals.keys(),
        key=lambda x: datetime.datetime.strptime(x, '%b %Y')
    )
    line_labels = sorted_months
    line_values = [monthly_totals[m] for m in sorted_months]
    
    # 7. Report Statistics
    highest_cost_service = "N/A"
    highest_cost_amount = 0.0
    if service_totals:
        highest_cost_service = max(service_totals, key=service_totals.get)
        highest_cost_amount = service_totals[highest_cost_service]
        
    reports = {
        'total_expenses': total_spent,
        'highest_cost_service': highest_cost_service,
        'highest_cost_amount': highest_cost_amount,
        'budget_utilization': utilization,
        'monthly_report': [{'month': m, 'amount': monthly_totals[m]} for m in reversed(sorted_months)]
    }

    # Format values for template display
    formatted_budget = f"₹{budget:,.2f}"
    formatted_spent = f"₹{total_spent:,.2f}"
    formatted_remaining = f"₹{remaining_budget:,.2f}"
    
    return render_template(
        'dashboard.html',
        budget=formatted_budget,
        raw_budget=budget,
        spent=formatted_spent,
        raw_spent=total_spent,
        remaining=formatted_remaining,
        raw_remaining=remaining_budget,
        status_text=status_text,
        status_level=status_level,
        alert_msg=alert_msg,
        recent_expenses=expenses[:5],
        pie_labels=pie_labels,
        pie_values=pie_values,
        line_labels=line_labels,
        line_values=line_values,
        reports=reports
    )

# --- Budget Management ---

@app.route('/budget', methods=['GET', 'POST'])
@login_required
def manage_budget():
    user_id = session['user_id']
    
    if request.method == 'POST':
        action = request.form.get('action')
        
        if action == 'delete':
            db.execute_query(
                "DELETE FROM budget WHERE user_id = %s",
                (user_id,),
                fetch='commit'
            )
            flash('Monthly budget cleared successfully.', 'success')
            return redirect(url_for('dashboard'))
            
        monthly_limit = request.form.get('monthly_limit', '').strip()
        if not monthly_limit:
            flash('Budget amount cannot be empty.', 'danger')
            return redirect(url_for('manage_budget'))
            
        try:
            limit = float(monthly_limit)
            if limit < 0:
                raise ValueError("Limit must be positive.")
        except ValueError:
            flash('Please enter a valid positive number for the budget.', 'danger')
            return redirect(url_for('manage_budget'))
            
        # Check if budget already exists
        existing = db.execute_query(
            "SELECT * FROM budget WHERE user_id = %s",
            (user_id,),
            fetch='one'
        )
        if existing:
            db.execute_query(
                "UPDATE budget SET monthly_limit = %s WHERE user_id = %s",
                (limit, user_id),
                fetch='commit'
            )
            flash('Monthly budget updated successfully!', 'success')
        else:
            db.execute_query(
                "INSERT INTO budget (user_id, monthly_limit) VALUES (%s, %s)",
                (user_id, limit),
                fetch='lastrowid'
            )
            flash('Monthly budget set successfully!', 'success')
            
        return redirect(url_for('dashboard'))
        
    budget_row = db.execute_query(
        "SELECT monthly_limit FROM budget WHERE user_id = %s",
        (user_id,),
        fetch='one'
    )
    current_limit = float(budget_row['monthly_limit']) if budget_row else 0.0
    return render_template('budget.html', current_limit=current_limit)

# --- Expense Management ---

@app.route('/expenses', methods=['GET', 'POST'])
@login_required
def expenses():
    user_id = session['user_id']
    
    if request.method == 'POST':
        service_name = request.form.get('service_name', '').strip()
        custom_service = request.form.get('custom_service', '').strip()
        amount = request.form.get('amount', '').strip()
        usage_date = request.form.get('usage_date', '').strip()
        
        # Resolve service name if 'Other' custom option is selected
        if service_name == 'Other' and custom_service:
            service_name = custom_service
        elif service_name == 'Other':
            service_name = 'Other Expense'
            
        if not service_name or not amount or not usage_date:
            flash('All fields are required to log an expense.', 'danger')
            return redirect(url_for('expenses'))
            
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            flash('Please enter a valid positive number for amount.', 'danger')
            return redirect(url_for('expenses'))
            
        db.execute_query(
            "INSERT INTO cloud_costs (user_id, service_name, amount, usage_date) VALUES (%s, %s, %s, %s)",
            (user_id, service_name, amount_val, usage_date),
            fetch='lastrowid'
        )
        flash(f'Expense for {service_name} logged successfully!', 'success')
        return redirect(url_for('dashboard'))
        
    expenses_list = db.execute_query(
        "SELECT * FROM cloud_costs WHERE user_id = %s ORDER BY usage_date DESC",
        (user_id,)
    )
    today = datetime.date.today().strftime('%Y-%m-%d')
    return render_template('expenses.html', expenses=expenses_list, today=today)

@app.route('/expenses/edit/<int:cost_id>', methods=['GET', 'POST'])
@login_required
def edit_expense(cost_id):
    user_id = session['user_id']
    
    expense = db.execute_query(
        "SELECT * FROM cloud_costs WHERE cost_id = %s AND user_id = %s",
        (cost_id, user_id),
        fetch='one'
    )
    if not expense:
        flash('Expense not found or unauthorized access.', 'danger')
        return redirect(url_for('expenses'))
        
    if request.method == 'POST':
        service_name = request.form.get('service_name', '').strip()
        custom_service = request.form.get('custom_service', '').strip()
        amount = request.form.get('amount', '').strip()
        usage_date = request.form.get('usage_date', '').strip()
        
        if service_name == 'Other' and custom_service:
            service_name = custom_service
        elif service_name == 'Other':
            service_name = 'Other Expense'
            
        if not service_name or not amount or not usage_date:
            flash('All fields are required.', 'danger')
            return redirect(url_for('edit_expense', cost_id=cost_id))
            
        try:
            amount_val = float(amount)
            if amount_val <= 0:
                raise ValueError("Amount must be positive.")
        except ValueError:
            flash('Please enter a valid positive number for amount.', 'danger')
            return redirect(url_for('edit_expense', cost_id=cost_id))
            
        db.execute_query(
            "UPDATE cloud_costs SET service_name = %s, amount = %s, usage_date = %s WHERE cost_id = %s AND user_id = %s",
            (service_name, amount_val, usage_date, cost_id, user_id),
            fetch='commit'
        )
        flash('Expense updated successfully!', 'success')
        return redirect(url_for('expenses'))
        
    # Standard cloud services to populate dropdown
    common_services = ['EC2 / Compute', 'S3 / Storage', 'RDS / Database', 'VPC / Networking', 'Lambda / Serverless']
    is_custom = expense['service_name'] not in common_services
    
    return render_template(
        'expenses_edit.html',
        expense=expense,
        common_services=common_services,
        is_custom=is_custom
    )

@app.route('/expenses/delete/<int:cost_id>', methods=['POST'])
@login_required
def delete_expense(cost_id):
    user_id = session['user_id']
    
    # Verify owner
    expense = db.execute_query(
        "SELECT * FROM cloud_costs WHERE cost_id = %s AND user_id = %s",
        (cost_id, user_id),
        fetch='one'
    )
    if not expense:
        flash('Expense not found or unauthorized access.', 'danger')
        return redirect(url_for('expenses'))
        
    db.execute_query(
        "DELETE FROM cloud_costs WHERE cost_id = %s AND user_id = %s",
        (cost_id, user_id),
        fetch='commit'
    )
    flash('Expense deleted successfully.', 'success')
    return redirect(url_for('expenses'))

if __name__ == '__main__':
    app.run(debug=True)
