import base64
from datetime import datetime,timedelta
from functools import wraps
import time
from flask import Flask, jsonify, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
import os
import fitz
from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import FlaskForm
from flask_login import LoginManager, UserMixin, login_user, login_required, current_user, logout_user
from wtforms import BooleanField, MultipleFileField, StringField, TextAreaField, FileField, SubmitField
from wtforms.validators import DataRequired
from flask import Flask, render_template, redirect, request, session, url_for, flash
from flask_wtf import FlaskForm
from sqlalchemy import Numeric, case, extract, literal_column
from flask import current_app
from werkzeug.utils import secure_filename
from wtforms import RadioField, StringField, PasswordField, SubmitField, validators
from wtforms.validators import InputRequired
import pytz
app = Flask(__name__)

# Configure your PostgreSQL database
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost:5432/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'  # Create an 'uploads' folder in your project directory

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
     

    # Add a method to get the user's questions and answers
    def get_user_questions(self):
        return Question.query.filter_by(user_id=self.id).all()

    def get_user_answers(self):
        return Answer.query.filter_by(user_id=self.id).all()


class Question(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    image_data = db.Column(db.ARRAY(db.String), nullable=True)  # Array to store multiple images
    user_id = db.Column(db.Integer, db.ForeignKey('flaskusers.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('questions', lazy=True))
    answers = db.relationship('Answer', backref='question', lazy=True)
    

class Answer(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('flaskusers.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('answers', lazy=True))
    question_id = db.Column(db.Integer, db.ForeignKey('question.id'), nullable=False)
    edited = db.Column(db.Boolean, default=False)
    edited_at = db.Column(db.DateTime, nullable=True)

class Reply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    answer_id = db.Column(db.Integer, db.ForeignKey('answer.id'), nullable=False)
    answer = db.relationship('Answer', backref=db.backref('replies', lazy=True))
    user_id = db.Column(db.Integer, db.ForeignKey('flaskusers.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('replies', lazy=True))
    #created_at = db.Column(db.DateTime, default=datetime.utcnow)
    

class LoginForm(FlaskForm):
    username = StringField('Username', [validators.InputRequired()])
    password = PasswordField('Password', [validators.InputRequired()])
    #role = RadioField('Role', choices=[('manager', 'Manager'), ('employee', 'Employee')], validators=[validators.InputRequired()])
    submit = SubmitField('Login')

from flask_wtf.file import FileField, FileAllowed

class QuestionForm(FlaskForm):
    title = StringField('Title', validators=[InputRequired()])
    content = TextAreaField('Content', validators=[InputRequired()])
    images = FileField('Upload Images', validators=[FileAllowed(['jpg', 'jpeg', 'png', 'gif'])])
    submit = SubmitField('Ask Question')

from flask_wtf import FlaskForm
from wtforms import TextAreaField, SubmitField
from wtforms.validators import InputRequired

class AnswerForm(FlaskForm):
    content = TextAreaField('Your Answer', validators=[InputRequired()])
    submit = SubmitField('Post Answer')
    edited = BooleanField('edited', default=False)

class ReplyForm(FlaskForm):
    content = TextAreaField('Reply', render_kw={'rows': 3})
    submit = SubmitField('Submit Reply')

# Dummy data to simulate admin login
admin_credentials = {'username': 'admin', 'password': 'admin123'}

@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data
        password = form.password.data

        if username == admin_credentials['username'] and password == admin_credentials['password']:
            return redirect(url_for('admin_dashboard'))
        #role=form.role.data
        user = User.query.filter_by(username=username).first()

        if user and user.password == password:
            #flash('Login successful', 'success')
            
                session['username'] = username
               # current_user = session.get('username')
                return redirect(url_for('index',username=username))
            
        else:
            flash('Login unsuccessful. Please check your credentials.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

@app.route("/<username>")
def index(username):
    user = User.query.filter_by(username=username).first()
    if user:
        questions = Question.query.all()
        return render_template("index.html", questions=questions, user=user)
    else:
        flash('User not found.', 'danger')
        return redirect(url_for('login'))
    


@app.route('/ask', methods=['GET', 'POST'])
def ask_question():
    form = QuestionForm()
    user = User.query.filter_by(username=session['username']).first()
    if form.validate_on_submit():
        title = form.title.data
        content = form.content.data
        images = request.files.getlist('images')

        # Process and store the images
        image_data = []

        for image_file in images:
            if image_file:
                image_data.append(base64.b64encode(image_file.read()).decode('utf-8'))
            else:
                image_data.append(None)
        question = Question(title=title, content=content, user=user, image_data=image_data)
        db.session.add(question)
        db.session.commit()
        

        #flash('Question posted successfully!', 'success')
        return redirect(url_for('index', username=session['username']))

    return render_template('ask.html', form=form,user=user)

@app.route('/answer/<int:question_id>', methods=['GET', 'POST'])
def answer_question(question_id):
    form = AnswerForm()
    question = Question.query.get_or_404(question_id)  # Use get_or_404 to handle not found cases
    user = User.query.filter_by(username=session['username']).first()
    if form.validate_on_submit():
        content = form.content.data
        # user = User.query.filter_by(username=session['username']).first()
        
        answer = Answer(content=content, user=user, question=question)
        db.session.add(answer)
        db.session.commit()

        #flash('Answer posted successfully!', 'success')
        return redirect(url_for('question_detail', question_id=question_id))
    
    

    return render_template('answer.html', form=form, question=question,user=user)



@app.route("/question/<int:question_id>", methods=['GET', 'POST'])
def question_detail(question_id):
    question = Question.query.get_or_404(question_id)
    #answers = Answer.query.filter_by(question_id=question_id).all()
    user = User.query.filter_by(username=session.get('username')).first()
    num_answers = len(list(question.answers))
    

    reply_form = ReplyForm()

    if request.method == 'POST' and reply_form.validate_on_submit():
    # Retrieve 'answer_id' from the form
        answer_id = request.form.get('answer_id')
        print(f"Answer ID: {answer_id}")

        if not answer_id:
            flash('Answer ID not provided', 'error')
            return redirect(url_for('question_detail', question_id=question_id))

        answer = Answer.query.get_or_404(answer_id)

        # Check if the reply content is not empty
        if not reply_form.content.data.strip():
            #flash('Reply content cannot be empty', 'error')
            return redirect(url_for('question_detail', question_id=question_id))

        new_reply = Reply(content=reply_form.content.data, answer=answer, user=user)
        db.session.add(new_reply)
        db.session.commit()
    
        #flash('Reply submitted successfully', 'success')
        return redirect(url_for('question_detail', question_id=question_id))
    
    for answer in question.answers:
        if answer.edited_at:
            print(f"Original edited_at (UTC): {answer.edited_at}")

        # Add 5.5 hours to the edited_at timestamp
            answer.edited_at_local = answer.edited_at + timedelta(hours=5.5)

            print(f"Edited edited_at (IST): {answer.edited_at_local.strftime('%Y-%m-%d %H:%M')}")
        
    return render_template("question_detail.html", question=question, user=user,num_answers=num_answers,reply_form=reply_form)





@app.route('/edit-answer/<int:answer_id>', methods=['GET', 'POST'])
def edit_answer(answer_id):
    answer = Answer.query.get_or_404(answer_id)
    form = AnswerForm(obj=answer)
    user = User.query.filter_by(username=session['username']).first()

    if form.validate_on_submit():
        answer.original_content = answer.content  # Save the original content
        answer.content = form.content.data
        answer.edited = True
        answer.edited_at = datetime.utcnow()
        db.session.commit()

        # Redirect to question detail page after editing the answer
        return redirect(url_for('question_detail', question_id=answer.question.id))

    return render_template('edit_answer.html', form=form, question=answer.question, user=user, answer=answer)





@app.route('/logout')
def logout():
    # Clear the session on logout
    session.pop('user', None)
    return redirect(url_for('login'))


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
