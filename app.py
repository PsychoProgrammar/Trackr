from flask import Flask, flash, render_template, request, redirect, url_for, session, send_from_directory,jsonify
import psycopg2
import os
from flask_sqlalchemy import SQLAlchemy
import glob
from docx import Document
from PyPDF2 import PdfReader
from PyPDF2 import PdfFileReader
import fitz
import re
from flask_wtf import FlaskForm
from wtforms import RadioField, StringField, PasswordField, SubmitField, validators



# Flask app configuration
app = Flask(__name__)
# Configure your PostgreSQL database
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:root@localhost:8080/postgres'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['UPLOAD_FOLDER'] = 'uploads'

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

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.String(255), nullable=True)
    pdf_path = db.Column(db.String(255), nullable=False)
    approved = db.Column(db.Boolean, default=False)


class LoginForm(FlaskForm):
    username = StringField('Username', [validators.InputRequired()])
    password = PasswordField('Password', [validators.InputRequired()])
    #role = RadioField('Role', choices=[('manager', 'Manager'), ('employee', 'Employee')], validators=[validators.InputRequired()])
    submit = SubmitField('Login')

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
                return redirect(url_for('dashboard',username=username))
            
        else:
            #flash('Login unsuccessful. Please check your credentials.', 'danger')
            return redirect(url_for('login'))

    return render_template('login.html', form=form)

# Route for the dashboard
@app.route('/dashboard')
def dashboard():
    if 'username' in session:
        username = session['username']
        #role = session['role']
        return render_template('dashboard.html', username=username)
    else:
        return redirect(url_for('login'))

# Route for logout
@app.route('/logout')
def logout():
    session.pop('username', None)
    #session.pop('role', None)
    return redirect(url_for('login'))

@app.route('/add_post', methods=['POST','GET'])
def add_post():
    if request.method == 'POST':
        title = request.form['title']

        if 'pdf_file' not in request.files:
            return redirect(request.url)

        pdf_file = request.files['pdf_file']

        if pdf_file.filename == '':
            return redirect(request.url)

        pdf_path = os.path.join(app.config['UPLOAD_FOLDER'], pdf_file.filename)
        pdf_file.save(pdf_path)

        new_document = Document(title=title, pdf_path=pdf_path,approved=False)
        db.session.add(new_document)
        db.session.commit()

        return redirect(url_for('add_post'))
    return render_template('add_post.html')

@app.route('/process_document', methods=['POST'])
def process_document():
    option = request.form.get('option')

    if option == 'write':
        doc_title = request.form['doc_title']
        brief_description = request.form['brief_description']
        content = request.form['content']

        # Create a directory to store written documents if not exists
        write_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'written_documents')
        os.makedirs(write_dir, exist_ok=True)

        # Save the document as a text file
        file_path = os.path.join(write_dir, f"{doc_title}.txt")
        with open(file_path, 'w', encoding='utf-8') as file:
            file.write(f"Title: {doc_title}\n\nBrief Description: {brief_description}\n\nContent:\n{content}")

        # Save document information in the database
        new_document = Document(title=doc_title, description=brief_description, pdf_path=file_path, approved=False)
        db.session.add(new_document)
        db.session.commit()

    elif option == 'upload':
        file_title = request.form['file_title']
        brief_file_description = request.form['brief_file_description']
        file = request.files['file']

        # Create a directory to store uploaded files if not exists
        upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'uploaded_files')
        os.makedirs(upload_dir, exist_ok=True)

        # Save the uploaded file
        file_path = os.path.join(upload_dir, file.filename)
        file.save(file_path)

        # Save document information in the database
        new_document = Document(title=file_title, description=brief_file_description, pdf_path=file_path, approved=False)
        db.session.add(new_document)
        db.session.commit()

    return render_template('add_post.html', file_path=file_path)

def get_folder_content(path):
    content = []
    with os.scandir(path) as entries:
        for entry in entries:
            info = {
                'name': entry.name,
                'is_dir': entry.is_dir(),
                'path': entry.path.replace(os.sep, '/'),  # Replace backslashes with forward slashes
            }
            if entry.is_dir():
                info['content'] = get_folder_content(entry.path)
            content.append(info)
    return content

@app.route('/display_files', methods=['POST','GET'])
def display_files():
    directory = 'C:/Users/7000035122/Downloads/PF_SOCIALS/uploads'
    folder_content = get_folder_content(directory)
    if request.method == 'POST':
        query = request.form.get('search_query')
        results = search_documents(query)
        return render_template('display_files.html', folder_content=folder_content, get_folder_content=get_folder_content, query=query, results=results)
    return render_template('display_files.html', folder_content=folder_content, get_folder_content=get_folder_content, query='', results=[])

def split_string(value, separator):
    return value.split(separator)

app.jinja_env.filters['split'] = split_string

@app.route('/view/<path:filename>')
def view_file(filename):
    file_path = os.path.join(".", filename).replace(os.sep, '/') 
    return render_template('view_file.html', file_path=file_path)

@app.route('/files/<path:filename>')
def get_file(filename):
    parts = filename.split('/')
    undesired_parts = [0,1,2,3,4]
    remaining_parts = [part for index, part in enumerate(parts) if index not in undesired_parts]
    result = '/'.join(remaining_parts)
    return send_from_directory('uploads',result)



# Function to read text from different document types
def read_text(file_path):
    _, file_extension = os.path.splitext(file_path)
    if file_extension == '.pdf':
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            return ' '.join(page.extract_text() for page in pdf_reader.pages)
    elif file_extension == '.docx':
        doc = Document(file_path)
        return ' '.join(paragraph.text for paragraph in doc.paragraphs)
    elif file_extension == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='replace') as file:
            return file.read()
    else:
        return ''  # Unsupported file type

# Function to search documents by name and content
def search_documents(query):
    results = []
    allowed_extensions = ['.pdf', '.docx', '.txt']

    for root, dirs, files in os.walk('C:/Users/7000035122/Downloads/PF_SOCIALS/uploads'):
        for file in files:
            if file.lower().endswith(tuple(allowed_extensions)):
                file_path = os.path.join(root, file)

                if file.lower().endswith('.pdf'):
                    pdf_document = fitz.open(file_path)
                    for page_num in range(pdf_document.page_count):
                        page = pdf_document[page_num]
                        page_text = page.get_text()
                        if query and txt_content is not None and (query.lower() in page_text.lower() or query.lower() in file.lower()):
                            parts = re.split(r'[\\\/]', file_path)
                            undesired_parts = []
                            remaining_parts = [part for index, part in enumerate(parts) if index not in undesired_parts]
                            result = '/'.join(remaining_parts)
                            results.append(result)
                            break
                    pdf_document.close()
                

                elif file.lower().endswith('.docx'):
                    from zipfile import ZipFile, BadZipFile
                    import xml.etree.ElementTree as ET
                    try:
                        with ZipFile(file_path, 'r') as zip_file:
                            xml_content = zip_file.read('word/document.xml')

                        root = ET.fromstring(xml_content)
                        ns = {'w': 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'}
                        paragraphs = root.findall('.//w:p', namespaces=ns)

                        doc_text = '\n'.join([''.join([text.text for text in paragraph.findall('.//w:t', namespaces=ns)]) for paragraph in paragraphs])

                        if query.lower() in doc_text.lower() or query.lower() in file.lower():
                            parts = re.split(r'[\\\/]', file_path)
                            undesired_parts = []
                            remaining_parts = [part for index, part in enumerate(parts) if index not in undesired_parts]
                            result = '/'.join(remaining_parts)
                            results.append(result)

                    except BadZipFile:
                        print(f"Error reading {file_path}: Not a valid .docx file.")




                elif file.lower().endswith('.txt'):
                    with open(file_path, 'r', encoding='utf-8') as txt_file:
                        txt_content = txt_file.read()
                        if query and txt_content is not None and (query.lower() in txt_content.lower() or query.lower() in file.lower()):
                            parts = re.split(r'[\\\/]', file_path)
                            undesired_parts = []
                            remaining_parts = [part for index, part in enumerate(parts) if index not in undesired_parts]
                            result = '/'.join(remaining_parts)
                            results.append(result)


    return results

@app.route('/search', methods=['POST'])
def search():
    data = request.get_json()
    query = data.get('query', '')
    results = search_documents(query)
    return jsonify({'results': results})

@app.route('/admin_dashboard')
def admin_dashboard():
    # Fetch all documents awaiting approval
    pending_documents = Document.query.filter_by(approved=False).all()
    return render_template('admin_dashboard.html', pending_documents=pending_documents)

@app.route('/approve_document/<int:document_id>/<string:action>', methods=['GET', 'POST'])
def approve_document(document_id, action):
    document = Document.query.get_or_404(document_id)

    if action == 'approve':
        document.approved = True
        #flash('Document approved successfully.', 'success')
    elif action == 'reject':
        # Delete the document file if rejected
        os.remove(document.pdf_path)
        db.session.delete(document)
        #flash('Document rejected.', 'warning')

    db.session.commit()
    return redirect(url_for('admin_dashboard'))

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
                return redirect(url_for('dashboard', username=username))
                
            else:
                flash('New password and confirm password do not match', 'error')
        else:
            flash('Incorrect current password', 'error')

    return render_template('changepassword.html',username=username)


from flask import send_from_directory

# @app.route('/view_file/<filename>')
# def viewfile(filename):
#     parts = re.split(r'[\\\/]', filename)
#     undesired_parts = []
#     remaining_parts = [part for index, part in enumerate(parts) if index not in undesired_parts]
#     result = '/'.join(remaining_parts)
#     # Assuming you store your documents in a folder called 'uploads'
#     return send_from_directory('uploads', result)

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        app.run(debug=True)
