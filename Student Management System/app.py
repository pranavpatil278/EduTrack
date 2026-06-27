from flask import Flask, render_template, request, redirect, flash
from datetime import date, datetime
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    logout_user,
    login_required
)
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash


app = Flask(__name__)

app.secret_key = "secret_key"

ADMIN_USERNAME = "admin"
ADMIN_PASSWORD = "admin@123"

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///database.db"

db = SQLAlchemy(app)


login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"


# ---------------- DATABASE ----------------

class Admin(UserMixin, db.Model):

    id = db.Column(
        db.Integer,
        primary_key=True
    )

    username = db.Column(
        db.String(100),
        unique=True,
        nullable=False
    )

    password = db.Column(
        db.String(200),
        nullable=False
    )



class Student(db.Model):

    id = db.Column(db.Integer, primary_key=True)

    name = db.Column(db.String(100))

    course = db.Column(db.String(100))

    joining_date = db.Column(db.Date)



class Attendance(db.Model):



    id = db.Column(

        db.Integer,

        primary_key=True

    )



    student_id = db.Column(

        db.Integer,

        db.ForeignKey('student.id')

    )



    attendance_date = db.Column(

        db.Date,

        default=date.today

    )



    status = db.Column(

        db.String(20)

    )

with app.app_context():
    db.create_all()



@login_manager.user_loader
def load_user(user_id):

    return Admin.query.get(int(user_id))



# ---------------- FIRST PAGE ----------------

@app.route("/")
def first_page():

    return redirect("/login")


# ---------------- LOGIN ----------------


@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        username = request.form["username"]
        password = request.form["password"]

        if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
            user = Admin(id=1, username=username)
            login_user(user)
            return redirect("/dashboard")

        flash("❌ Invalid username or password", "danger")
        return redirect("/login")

    return render_template("login.html")




# ---------------- DASHBOARD ----------------


@app.route("/dashboard")
@login_required
def dashboard():


    students = Student.query.all()


    return render_template(
        "index.html",
        students=students
    )


@app.route("/attendance")
@login_required
def attendance():

    students = Student.query.all()

    return render_template(
        "attendance.html",
        students=students,
        today=date.today().strftime("%Y-%m-%d")
    )

@app.route("/mark_attendance/<int:id>/<status>/<attendance_date>")
@login_required
def mark_attendance(id, status, attendance_date):

    attendance_date = datetime.strptime(
        attendance_date,
        "%Y-%m-%d"
    ).date()

    existing = Attendance.query.filter_by(
        student_id=id,
        attendance_date=attendance_date
    ).first()

    if existing:
        flash("Attendance already marked for this date!", "warning")
        return redirect("/attendance")

    attendance = Attendance(
        student_id=id,
        attendance_date=attendance_date,
        status=status
    )

    db.session.add(attendance)
    db.session.commit()

    flash("Attendance Marked Successfully!", "success")

    return redirect("/attendance")


@app.route("/attendance_report")

@login_required

def attendance_report():



    month = datetime.now().month

    year = datetime.now().year



    students = Student.query.all()



    report = []



    for student in students:



        records = Attendance.query.filter(

            Attendance.student_id == student.id,

            db.extract('month', Attendance.attendance_date) == month,

            db.extract('year', Attendance.attendance_date) == year

        ).all()



        total = len(records)



        present = sum(

            1 for record in records

            if record.status == "Present"

        )



        percentage = 0



        if total > 0:

            percentage = round((present / total) * 100, 2)



        report.append({

            "student": student,

            "total": total,

            "present": present,

            "percentage": percentage

        })



    return render_template(

        "attendance_report.html",

        report=report,

        month_name=datetime.now().strftime("%B"),

        year=year

    )
@app.route("/student_attendance/<int:id>")
@login_required
def student_attendance(id):

    student = Student.query.get_or_404(id)

    records = Attendance.query.filter_by(
        student_id=id
    ).order_by(
        Attendance.attendance_date.desc()
    ).all()

    return render_template(
        "student_attendance.html",
        student=student,
        records=records
    )

@app.route("/edit/<int:id>", methods=["GET", "POST"])
@login_required
def edit_student(id):

    student = Student.query.get_or_404(id)

    if request.method == "POST":

        try:
            joining_date = datetime.strptime(
                request.form["joining_date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash("Please select a valid joining date.", "danger")
            return redirect(f"/edit/{id}")

        student.name = request.form["name"]
        student.course = request.form["course"]
        student.joining_date = joining_date

        db.session.commit()

        flash("Student updated successfully!", "success")

        return redirect("/dashboard")

    return render_template(
        "edit_student.html",
        student=student
    )

@app.route("/attendance_history/<int:id>")
@login_required
def attendance_history(id):

    student = Student.query.get_or_404(id)

    prev_student = Student.query.filter(Student.id < id)\
    .order_by(Student.id.desc()).first()

    next_student = Student.query.filter(Student.id > id)\
    .order_by(Student.id.asc()).first()

    month = request.args.get("month", type=int)
    year = request.args.get("year", type=int)

    query = Attendance.query.filter_by(student_id=id)

    if month:
        query = query.filter(
            db.extract('month', Attendance.attendance_date) == month
        )

    if year:
        query = query.filter(
            db.extract('year', Attendance.attendance_date) == year
        )

    records = query.order_by(
        Attendance.attendance_date.desc()
    ).all()

    total = len(records)

    present = sum(
        1 for record in records
        if record.status == "Present"
    )

    absent = total - present

    percentage = 0

    if total > 0:
        percentage = round((present / total) * 100, 2)

    return render_template(
        "attendance_history.html",
        student=student,
        records=records,
        total=total,
        present=present,
        absent=absent,
        percentage=percentage,
        month=month,
        year=year,
        prev_student=prev_student,
        next_student=next_student
)

@app.route("/delete_attendance/<int:id>", methods=["POST"])
def delete_attendance(id):
    record = db.session.get(Attendance, id)

    if not record:
        flash("Record not found", "danger")
        return redirect("/dashboard")

    student_id = record.student_id

    db.session.delete(record)
    db.session.commit()

    return redirect(f"/attendance_history/{student_id}")

@app.route("/mark_bulk_attendance", methods=["POST"])
@login_required
def mark_bulk_attendance():

    present_students = request.form.getlist("present_students")

    attendance_date = datetime.strptime(
        request.form["attendance_date"],
        "%Y-%m-%d"
    ).date()

    students = Student.query.all()

    for student in students:

        status = "Present" if str(student.id) in present_students else "Absent"

        existing = Attendance.query.filter_by(
            student_id=student.id,
            attendance_date=attendance_date
        ).first()

        if not existing:
            db.session.add(Attendance(
                student_id=student.id,
                attendance_date=attendance_date,
                status=status
            ))

    db.session.commit()

    return redirect("/attendance")

@app.route("/logout")
@login_required
def logout():

    logout_user()

    return redirect("/login")





# ---------------- STUDENTS ----------------


@app.route("/add", methods=["GET","POST"])
@login_required
def add_student():

    if request.method == "POST":

        try:
            joining_date = datetime.strptime(
                request.form["joining_date"],
                "%Y-%m-%d"
            ).date()

        except ValueError:
            flash("Please select a valid joining date.", "danger")
            return redirect("/add")

        student = Student(
            name=request.form["name"],
            course=request.form["course"],
            joining_date=joining_date
        )

        db.session.add(student)
        db.session.commit()

        flash("Student Added Successfully!", "success")

        return redirect("/dashboard")

    return render_template("add_student.html")





@app.route("/delete/<int:id>")
@login_required
def delete_student(id):


    student = Student.query.get(id)


    db.session.delete(student)

    db.session.commit()


    return redirect("/dashboard")





if __name__ == "__main__":

    app.run(debug=True)