

from datetime import datetime, timedelta, time
from decimal import Decimal
from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_wtf import FlaskForm
from sqlalchemy import Numeric, case, extract, literal_column
from wtforms import RadioField, StringField, PasswordField, SubmitField, validators
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import check_password_hash, generate_password_hash
from sqlalchemy import func
from threading import Thread
import time
from plyer import notification
import pytz

app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'  # Change this to a secure secret key
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


class User(db.Model):
    __tablename__ = 'flaskusers'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role=db.Column(db.String(20),nullable=False)
    email=db.Column(db.String(30),unique=True)
    manager_id =db.Column(db.Integer)
    manager_name=db.Column(db.String(20)) 


class Todo(db.Model):
    __tablename__ = 'todo'
    
    id = db.Column(db.Integer, nullable=False)
    task_id = db.Column(db.DECIMAL(precision=10, scale=2), primary_key=True)
    task_desc = db.Column(db.String(255), nullable=False)
    task_status=db.Column(db.String(20), nullable=False)
    due_date = db.Column(db.DateTime, nullable=False)
    time_left = db.Column(db.String(100))  # You may adjust the length as needed
    time_left_status = db.Column(db.String(50))
    
    
    def calculate_time_left(self):
        now = datetime.now(pytz.utc)
        local_tz = pytz.timezone("Asia/Kolkata")  # Replace with your desired time zone
        now_local = now.astimezone(local_tz)

        # Extract due date and time components
        due_date = self.due_date.date()
        due_time = self.due_date.time()

        # Combine due date and time
        due_datetime = datetime.combine(due_date, due_time)

        # Convert due_datetime to the local time zone
        due_datetime_local = local_tz.localize(due_datetime)

        if now_local > due_datetime_local:
        # Task is expired, set time_left to 0 and return without further calculation
            self.time_left = "0 days 0 hours 0 minutes 0 seconds"
            self.time_left_status = "Past Due"
            self.task_status = "expired"
        # Commit changes to the database
            db.session.commit()
            return self.time_left

        # Calculate the time left
        time_left = due_datetime_local - now_local

        # Calculate the remaining time in days, hours, minutes, and seconds
        self.days_left = time_left.days
        self.hours_left, remainder = divmod(time_left.seconds, 3600)
        self.minutes_left, self.seconds_left = divmod(remainder, 60)

        # Update time_left directly
        self.time_left = f"{self.days_left} days {self.hours_left} hours {self.minutes_left} minutes {self.seconds_left} seconds"

        # Commit changes to the database
        db.session.commit()

        return self.time_left

    def get_time_left_status(self):
        # Calculate time left using the calculate_time_left method
        time_left = self.calculate_time_left()

        # Extract days, hours, minutes, and seconds from the time_left string
        time_components = time_left.split()
        days_left = int(time_components[0])

        if days_left < 0:
            return "Past Due"
        elif days_left == 0:
            return "Less than 1 day"
        elif days_left < 7:
            return "Less than 7 days"
        else:
            return "More than 7 days"

    
    priority = db.Column(db.String(50), nullable=False)
    manager_id=db.Column(db.Integer,db.ForeignKey('flaskusers.manager_id'), nullable=False)
    comment=db.Column(db.String(255), nullable=False)
    subtasks = db.relationship('Subtask', backref=db.backref('todo', lazy=True))
    
    user = db.relationship('User', backref=db.backref('todo', lazy=True), lazy='joined')



   

class Subtask(db.Model):
    sid=db.Column(db.Integer,primary_key=True,autoincrement=True)
    #subtask_id = db.Column(db.String(10))
    title = db.Column(db.String(50), nullable=False)
    subtask_status=db.Column(db.String(20), nullable=False,default='pending')
    task_id = db.Column(db.Integer, db.ForeignKey('todo.task_id'), nullable=False)
    priority = db.Column(db.String(50), nullable=False)
    comments=db.Column(db.String(255), nullable=False)
    completed = db.Column(db.Boolean, default=False) 
    

class LoginForm(FlaskForm):
    username = StringField('Username', [validators.InputRequired()])
    password = PasswordField('Password', [validators.InputRequired()])
    #role = RadioField('Role', choices=[('manager', 'Manager'), ('employee', 'Employee')], validators=[validators.InputRequired()])
    submit = SubmitField('Login')





@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        #role=form.role.data
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            #flash('Login successful', 'success')
            if user.role=='employee':
                session['username'] = username
               # current_user = session.get('username')
                return redirect(url_for('employee',username=username))
            elif user.role=='manager':
                return redirect(url_for('manager'))
        else:
            flash('Login unsuccessful. Please check your credentials.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route('/changepassword<username>', methods=['GET', 'POST'])
def changepassword(username):
    if request.method == 'POST':
        old_password = request.form.get('old_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')

        #current_user = session.get('username')
        
        # Validate current password
        user = User.query.filter_by(username=username).first()

        if user and user.password == old_password:
            if new_password == confirm_password:
                # Update password
                user.password = new_password
                db.session.commit()
                flash('Password successfully changed', 'success')
                return redirect(url_for('employee', username=username))
                
            else:
                flash('New password and confirm password do not match', 'error')
        else:
            flash('Incorrect current password', 'error')

    return render_template('changepassword.html',username=username)

@app.route('/logout', methods=['POST'])
def logout():
    # Clear the session on logout
    session.pop('user', None)
    return redirect(url_for('home'))


@app.route('/')
def home():
    return render_template('home.html')


@app.route('/employee/<username>')
def employee(username):
    user = User.query.filter_by(username=username).first()

    if user:
        tasks_pending = Todo.query.filter_by(id=user.id, task_status='pending') \
            .order_by(func.coalesce(
                extract('days', Todo.due_date - func.current_timestamp()),
                0).asc()) \
            .all()

        for task in tasks_pending:
            task.calculate_time_left()  # Update time_left and its components directly
            task.time_left_status = task.get_time_left_status()

            # Check if the time_left_status is "Past Due" and update the task status
            #if task.time_left_status == "Past Due":
                #print(f"Task {task.task_id} is expired. Updating status...")
                #task.task_status = "expired"

        # Commit changes to the database
        db.session.commit()

    return render_template('employee.html', username=username, tasks=tasks_pending)




@app.route('/add_subtask/<username>/<task_id>', methods=['POST'])
def add_subtask(username, task_id):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(task_id=task_id, id=user.id).first()

    if user and task:
         # Count the existing subtasks for the given task
        #subtask_count=0
        #subtask_count = Subtask.query.filter_by(task_id=task.id).count()
        #print(subtask_count)
        # Increment the subtask_id based on the count
        #new_subtask_id = f"{task_id}.{subtask_count + 1}"

        # Create and add the new subtask
        subtask_title = request.form['subtask_title']
        priority = request.form['priority']
        subtask_status = 'pending'  # You may need to update this based on your logic

        # Check if the subtask is completed
        if subtask_status == 'completed':
            completed = True
        else:
            completed = False
        new_subtask = Subtask( title=subtask_title, todo=task,priority=priority, subtask_status=subtask_status, completed=completed)
        db.session.add(new_subtask)
        db.session.commit()

        return redirect(url_for('employee', username=username))
    else:
        return "User or task not found"



@app.route('/viewCompleted/<username>')
def viewCompleted(username):
    user = User.query.filter_by(username=username).first()
    if user:
        tasks_completed= Todo.query.filter_by(id=user.id,task_status='completed').all()
    return render_template('viewCompleted.html',username=username,tasks=tasks_completed)


@app.route('/viewExpired/<username>')
def viewExpired(username):
    user = User.query.filter_by(username=username).first()
    if user:
        tasks_expired= Todo.query.filter_by(id=user.id,task_status='expired').all()
    return render_template('viewExpired.html',username=username,tasks=tasks_expired)


@app.route('/update_comment/<username>/<int:task_id>', methods=['POST'])
def update_comment(username, task_id):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(task_id=task_id, id=user.id).first()

    if user and task:
        new_comment = request.form['comment']
        task.comment = new_comment
        db.session.commit()

        return redirect(url_for('employee', username=username))
    else:
        return "User or task not found"
    
@app.route('/edit_subtask_comment/<username>/<int:task_id>/<int:sid>', methods=['POST'])
def edit_subtask_comment(username, task_id, sid):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(task_id=task_id, id=user.id).first()
    subtask = Subtask.query.filter_by(sid=sid, task_id=task.task_id).first()

    if user and task and subtask:
        comment = request.form['comment']
        subtask.comments = comment
        db.session.commit()

        return redirect(url_for('employee', username=username))
    else:
        return "User or task not found" 
    

@app.route('/edit_subtask_title/<username>/<int:task_id>/<int:sid>', methods=['POST'])
def edit_subtask_title(username, task_id, sid):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(task_id=task_id, id=user.id).first()
    subtask = Subtask.query.filter_by(sid=sid, task_id=task.task_id).first()

    if user and task and subtask:
        title = request.form['title']
        subtask.title = title
        db.session.commit()

        return redirect(url_for('employee', username=username))
    else:
        return "User or task not found" 
    


from flask import jsonify


@app.route('/mark_subtask_completed/<username>/<int:task_id>/<int:sid>', methods=['POST'])
def mark_subtask_completed(username, task_id, sid):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(id=user.id, task_id=task_id).first()
    subtask = Subtask.query.filter_by(sid=sid, task_id=task.task_id).first()

    if user and task and subtask:
        # Update the subtask status to 'Completed' in the database
        subtask.subtask_status = 'completed'
        subtask.completed = True
        db.session.commit()

        # Check if all subtasks are completed
        all_subtasks_completed = all(subtask.subtask_status == 'completed' for subtask in task.subtasks)

        # If all subtasks are completed, update the main task status
        if all_subtasks_completed:
            task.task_status = 'completed'
            db.session.commit()

        # Return the updated subtask details as JSON
        return jsonify({
            'subtask_status': subtask.subtask_status,
            'completed': subtask.completed,
            'all_subtasks_completed': all_subtasks_completed,
            'main_task_status': task.task_status  # Include main task status in the response
        })

    return jsonify({'error': 'User, task, or subtask not found'})

# Add a new route to handle the task closure confirmation
@app.route('/confirm_close_task/<username>/<int:task_id>', methods=['POST'])
def confirm_close_task(username, task_id):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(id=user.id, task_id=task_id).first()

    if user and task:
        # Update the task status to 'Completed' in the database
        task.task_status = 'completed'
        db.session.commit()

        # Redirect to the employee page
        return redirect(url_for('employee', username=username))

    return jsonify({'error': 'User or task not found'})

@app.route('/delete_subtask/<username>/<int:task_id>/<int:sid>', methods=['POST'])
def delete_subtask(username, task_id, sid):
    user = User.query.filter_by(username=username).first()
    task = Todo.query.filter_by(task_id=task_id, id=user.id).first()
    subtask = Subtask.query.filter_by(sid=sid, task_id=task.task_id).first()

    if user and task and subtask:
        # Delete the subtask
        db.session.delete(subtask)
        db.session.commit()

    return redirect(url_for('employee', username=username))


       


from sqlalchemy import func

@app.route('/update_task/<username>/<int:task_id>', methods=['POST'])
def update_task_status(username, task_id):
    task = Todo.query.get(task_id)

    if task:
        if 'closeTask' in request.form:
            # Check if all subtasks are completed
            all_subtasks_completed = db.session.query(func.count(Subtask.sid)).filter_by(task_id=task_id, subtask_status='completed').scalar()

            if all_subtasks_completed == len(task.subtasks):
                # Update the task status to 'completed'
                task.task_status = 'completed'
                db.session.commit()
                flash('Main task closed successfully!', 'success')
            else:
                flash('Cannot close the main task. Some subtasks are not completed.', 'error')
        else:
            flash('Invalid request. The "closeTask" parameter is missing.', 'error')

    return redirect(url_for('employee', username=username))


@app.route('/get_task_info/<task_id>')
def get_task_info(task_id):
    task = Todo.query.filter_by(task_id=task_id).first()
    
    if task:
        task.calculate_time_left()
        return jsonify({
            'time_left': task.time_left,
            'time_left_status': task.get_time_left_status(),
            'task_status': task.task_status
        })
    else:
        return jsonify({'error': 'Task not found'}), 404

@app.route('/update_status/<task_id>', methods=['POST'])
def update_status(task_id):
    task = Todo.query.filter_by(task_id=task_id).first()

    if task:
        task.task_status = request.form.get('task_status', 'pending')
        db.session.commit()
        return jsonify({'success': True})
    else:
        return jsonify({'error': 'Task not found'}), 404




@app.route('/manager')
def manager():
    return render_template('manager.html')

if __name__ == '__main__':
    #with app.app_context():
        #db.create_all()
    app.run(debug=True)