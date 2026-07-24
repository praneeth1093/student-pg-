from flask import Flask, render_template, request, session, redirect, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os

app = Flask(__name__)
app.secret_key = "studentpg123"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Praneeth@1093'
app.config['MYSQL_DB'] = 'student_pg'

mysql = MySQL(app)

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM students WHERE email=%s AND password=%s",
            (email, password)
        )

        user = cur.fetchone()

        cur.close()

        if user:

            session["student"] = email

            return redirect("/dashboard")

        else:

            return "Invalid Email or Password"

    return render_template("login.html")

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        # Check if email already exists
        cur.execute("SELECT * FROM students WHERE email=%s", (email,))
        existing_user = cur.fetchone()

        if existing_user:
            cur.close()
            return "Email already registered. Please login."

        # Insert new student
        cur.execute(
            "INSERT INTO students(name, email, password) VALUES(%s, %s, %s)",
            (name, email, password)
        )

        mysql.connection.commit()
        cur.close()

        return redirect("/login")

    return render_template("register.html")

@app.route("/dashboard")
def dashboard():

    if "student" not in session:
        return redirect("/login")

    return render_template("dashboard.html")



@app.route("/pg/<int:pg_id>")
def pg_details(pg_id):

    cur = mysql.connection.cursor()

    cur.execute("SELECT * FROM pg_details WHERE id=%s", (pg_id,))

    pg = cur.fetchone()

    cur.close()

    return render_template("pg_details.html", pg=pg)

@app.route("/add_pg", methods=["GET", "POST"])
def add_pg():

    if request.method == "POST":

        pg_name = request.form["pg_name"]
        location = request.form["location"]
        rent = request.form["rent"]
        gender = request.form["gender"]
        description = request.form["description"]

        # Get uploaded image
        image = request.files["image"]

        # Create a safe filename
        filename = secure_filename(image.filename)

        # Save image in uploads folder
        image.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))

        # Save data to database
        cur = mysql.connection.cursor()

        cur.execute("""
            INSERT INTO pg_details
            (owner_id, pg_name, location, rent, gender, description, image)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """, (1, pg_name, location, rent, gender, description, filename))

        mysql.connection.commit()
        cur.close()

        return "PG Added Successfully!"

    return render_template("add_pg.html")


@app.route("/book/<int:pg_id>")
def book_pg(pg_id):

    if "student" not in session:
        return redirect("/login")

    student_email = session["student"]

    cur = mysql.connection.cursor()

    cur.execute("""
        INSERT INTO bookings(student_email, pg_id)
        VALUES(%s, %s)
    """, (student_email, pg_id))

    mysql.connection.commit()

    cur.close()

    return "🎉 Booking Successful!"

@app.route("/uploads/<filename>")
def uploaded_file(filename):
    return send_from_directory(app.config["UPLOAD_FOLDER"], filename)

@app.route("/student_dashboard")
def student_dashboard():

    if "student" not in session:
        return redirect("/login")

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT pg_details.pg_name,
               pg_details.location,
               pg_details.rent
        FROM bookings
        JOIN pg_details
        ON bookings.pg_id = pg_details.id
        WHERE bookings.student_email=%s
    """, (session["student"],))

    bookings = cur.fetchall()

    cur.close()

    return render_template(
        "student_dashboard.html",
        bookings=bookings
    )

@app.route("/owner_register", methods=["GET", "POST"])
def owner_register():

    if request.method == "POST":

        name = request.form["name"]
        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute(
            "INSERT INTO owners(name, email, password) VALUES(%s,%s,%s)",
            (name, email, password)
        )

        mysql.connection.commit()
        cur.close()

        return redirect("/owner_login")

    return render_template("owner_register.html")

@app.route("/owner_login", methods=["GET", "POST"])
def owner_login():

    if request.method == "POST":

        email = request.form["email"]
        password = request.form["password"]

        cur = mysql.connection.cursor()

        cur.execute(
            "SELECT * FROM owners WHERE email=%s AND password=%s",
            (email, password)
        )

        owner = cur.fetchone()

        cur.close()

        if owner:
            session["owner"] = owner[0]   # Store owner ID
            return redirect("/owner_dashboard")

        return "Invalid Email or Password"

    return render_template("owner_login.html")

@app.route("/owner_dashboard")
def owner_dashboard():

    if "owner" not in session:
        return redirect("/owner_login")

    cur = mysql.connection.cursor()

    cur.execute(
    "SELECT id, pg_name, location, rent FROM pg_details WHERE owner_id=%s",
    (session["owner"],)
    )
    

    pgs = cur.fetchall()

    cur.close()

    return render_template("owner_dashboard.html", pgs=pgs)


@app.route("/delete_pg/<int:pg_id>")
def delete_pg(pg_id):

    if "owner" not in session:
        return redirect("/owner_login")

    cur = mysql.connection.cursor()

    cur.execute(
        "DELETE FROM pg_details WHERE id=%s AND owner_id=%s",
        (pg_id, session["owner"])
    )

    mysql.connection.commit()
    cur.close()

    return redirect("/owner_dashboard") 

@app.route("/pgs")
def pg_list():

    location = request.args.get("location")

    cur = mysql.connection.cursor()

    if location:
        cur.execute(
            "SELECT * FROM pg_details WHERE location LIKE %s",
            ("%" + location + "%",)
        )
    else:
        cur.execute("SELECT * FROM pg_details")

    pgs = cur.fetchall()

    cur.close()

    return render_template("pg_list.html", pgs=pgs)

if __name__ == "__main__":
    app.run(debug=True)