from flask import Flask, render_template, request, jsonify, redirect, session, url_for
from flask_sqlalchemy import SQLAlchemy
from functools import wraps
from uuid import uuid4 as genuuid
import re as regex
import hashlib

app = Flask(__name__)
app.secret_key = "TESTING_TESTING_123"
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.sqlite'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class User(db.Model):
    __tablename__ = 'users'
    uuid = db.Column(db.String, primary_key=True)
    username = db.Column(db.String, nullable=False)
    password = db.Column(db.String, nullable=False)

class Teacher(db.Model):
    __tablename__ = 'teachers'
    uuid = db.Column(db.String, primary_key=True)
    school = db.Column(db.String, nullable=False)
    name = db.Column(db.String, nullable=False)

class Rating(db.Model):
    __tablename__ = 'ratings'
    user_uuid = db.Column(db.String, db.ForeignKey('users.uuid'), nullable=False)
    teacher_uuid = db.Column(db.String, db.ForeignKey('teachers.uuid'), nullable=False)
    rating = db.Column(db.Integer, primary_key=True)

with app.app_context():
    db.create_all()

#region Decorators

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not loggedIn():
            return redirect(url_for('log_in'))
        return f(*args, **kwargs)
    return decorated_function

#endregion

#region Helpers

def toHash(password):
    hash_object = hashlib.sha256()
    hash_object.update(password.encode())
    return hash_object.hexdigest()

def userId():
    try:
        return session["id"]
    except:
        return None

def averageList(list, decimals=-1):
    result = 0
    for item in list:
        result += item
    return (result / len(list)) if decimals == -1 else round(result / len(list), decimals)

def loggedIn():
    try:
        return "id" in session and User.query.filter_by(uuid=str(userId())).first() is not None
    except:
        return False

def isEmptyOrWhitespace(str):
    return str == None or str == "" or str.isspace()

def hasNumber(password):
    return bool(regex.search(r"\d", password))

def hasSpecial(password):
    return bool(regex.search(r"[!@#$%^&*(),.?\":{}|<>]", password))

#endregion

#region User Mgmt

@app.route("/register/", methods=["GET", "POST"])
def register():
    if not request.method == "POST":
        return render_template("register.html", page="Register")

    try:
        username = request.form.get('username')
        password = request.form.get('password')
    except:
        return f"""Fields not filled"""
    
    if len(password) < 8 or not hasNumber(password) or not hasSpecial(password):
        return f"""Pasword be at least 8 characters and have at least one number and special character"""
    
    password = toHash(password)

    if User.query.filter_by(username=username).first() is not None:
        return f"""User exists"""
    
    user_id = str(genuuid())

    new_user = User(uuid=user_id, username=username, password=password)
    db.session.add(new_user)
    db.session.commit()

    return redirect(url_for('log_in'))

@app.route("/log-in/", methods=["GET", "POST"])
def log_in():
    if not request.method == "POST":
        return render_template("login.html", page="Log in")

    try:
        username = request.form.get('username')
        password = toHash(request.form.get('password'))
    except:
        return f"""Fields not filled"""
    
    user = User.query.filter_by(username=username).first()

    if user is None:
        return f"""Doesnt exist"""
    
    if user.password == password:
        session["id"] = user.uuid
        return redirect(url_for('main'))

    return f"""Password doesnt match"""

@app.route("/log-out/", methods=["GET"])
def log_out():
    try:
        del session["id"]
    except KeyError:
        return f"""Not logged in"""
    
    return redirect(url_for('log_in'))

#endregion

#region Teacher Mgmt

@app.route("/add-teacher/", methods=["GET", "POST"])
@login_required
def add_teacher():
    if not request.method == "POST":
        return render_template("add_teacher.html", page="Add teacher")
    
    try:
        name = request.form.get("name")
        school = request.form.get("school")
    except:
        return f"""Fields not filled"""
    
    if Teacher.query.filter_by(name=name).first() is not None:
        return f"""Teacher already exists"""
    
    teach_id = str(genuuid())

    new_teacher = Teacher(uuid=teach_id, school=school, name=name)
    db.session.add(new_teacher)
    db.session.commit()

    return redirect(url_for('leaderboard'))

@app.route("/rate-teacher/", methods=["GET", "POST"])
@login_required
def rate_teacher():
    if not request.method == "POST":
        teachers = Teacher.query.order_by(Teacher.name).all()
        return render_template("rate_teacher.html", page="Rate teacher", teachers=teachers)
    
    try:
        uuid = request.form.get("uuid")
        rating = int(request.form.get("rating"))
    except:
        return f"""Fields not filled"""
    
    teacher = Teacher.query.filter_by(uuid=uuid).first()

    if teacher is None:
        return f"""Teacher doesnt exist"""

    new_rating = Rating(user_uuid=userId(), teacher_uuid=uuid, rating=rating)
    db.session.add(new_rating)
    db.session.commit()

    return redirect(url_for('leaderboard'))

#endregion

@app.route("/", methods=["GET"])
def main():
    return render_template("home.html", page="Home")

@app.route("/leaderboard/", methods=["GET"])
def leaderboard():
    teachers = Teacher.query.all()
    teacher_ratings = []

    for teacher in teachers:
        ratings = [rating.rating for rating in Rating.query.filter_by(teacher_uuid=teacher.uuid).all()]
        average_rating = str(averageList(ratings, 2)) if ratings else "?"
        teacher_ratings.append({
            "name": teacher.name,
            "school": teacher.school,
            "rating": average_rating
        })

    teacher_ratings.sort(key=lambda x: x["rating"], reverse=True)
    top_10_teachers = teacher_ratings[:10]
    
    return render_template("leaderboard.html", page="Leaderboard", teacher_ratings=top_10_teachers)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000, threaded=True, debug=True)