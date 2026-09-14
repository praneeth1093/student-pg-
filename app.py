from flask import Flask, render_template, request, session, redirect, send_from_directory
from flask_mysqldb import MySQL
from werkzeug.utils import secure_filename
import os
import boto3
from dotenv import load_dotenv

app = Flask(__name__)
load_dotenv()
app.secret_key = "studentpg123"

UPLOAD_FOLDER = "uploads"
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

app.config['MYSQL_HOST'] = os.getenv("MYSQL_HOST")
app.config['MYSQL_USER'] = os.getenv("MYSQL_USER")
app.config['MYSQL_PASSWORD'] = os.getenv("MYSQL_PASSWORD")
app.config['MYSQL_DB'] = os.getenv("MYSQL_DB")

mysql = MySQL(app)
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY_ID")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_ACCESS_KEY")
AWS_REGION = os.getenv("AWS_REGION")
AWS_BUCKET = os.getenv("AWS_BUCKET_NAME")

s3 = boto3.client(
    "s3",
    aws_access_key_id=AWS_ACCESS_KEY,
    aws_secret_access_key=AWS_SECRET_KEY,
    region_name=AWS_REGION
)
@app.route("/")
def home():
    return render_template("home.html")

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
@app.route("/pg/<int:id>")
def pg_details(id):

    cur = mysql.connection.cursor()

    cur.execute("""
        SELECT *
        FROM pg_details
        WHERE id=%s
    """, (id,))
    pg = cur.fetchone()

    cur.execute("""
        SELECT image_url
        FROM pg_images
        WHERE pg_id=%s
    """, (id,))
    images = cur.fetchall()

    print("PG ID:", id)
    print("Images:", images)

    cur.close()

    return render_template(
        "pg_details.html",
        pg=pg,
        images=images
    )

@app.route("/add_pg", methods=["GET", "POST"])
def add_pg():

    if request.method == "POST":

        pg_name = request.form["pg_name"]
        location = request.form["location"]
        rent = request.form["rent"]
        total_rooms = request.form["total_rooms"]
        available_rooms = total_rooms
        gender = request.form["gender"]
        description = request.form["description"]

        # Get all uploaded images
        images = request.files.getlist("images")

        print("===================================")
        print("Number of images selected:", len(images))
        for img in images:
            print("Selected Image:", img.filename)
        print("===================================")

        cur = mysql.connection.cursor()

        # Insert PG details
        cur.execute("""
            INSERT INTO pg_details
            (owner_id, pg_name, location, rent, gender, description, total_rooms, available_rooms)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (
            1,
            pg_name,
            location,
            rent,
            gender,
            description,
            total_rooms,
            available_rooms
        ))

        mysql.connection.commit()

        # Get the newly inserted PG ID
        pg_id = cur.lastrowid

        # Upload every image to S3
        for image in images:

            if image.filename == "":
                print("Skipped empty image")
                continue

            filename = secure_filename(image.filename)

            print("Uploading:", filename)

            s3.upload_fileobj(
                image,
                AWS_BUCKET,
                filename,
                ExtraArgs={"ContentType": image.content_type}
            )

            image_url = f"https://{AWS_BUCKET}.s3.{AWS_REGION}.amazonaws.com/{filename}"

            print("Image URL:", image_url)

            cur.execute("""
                INSERT INTO pg_images (pg_id, image_url)
                VALUES (%s, %s)
            """, (pg_id, image_url))

            print("Inserted into pg_images table")

        mysql.connection.commit()
        cur.close()

        print("All images uploaded successfully!")

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

    location = request.args.get("location", "")
    gender = request.args.get("gender", "")
    rent = request.args.get("rent", "")

    cur = mysql.connection.cursor()

    query = """
    SELECT
        pg_details.*,
        (
            SELECT image_url
            FROM pg_images
            WHERE pg_images.pg_id = pg_details.id
            LIMIT 1
        ) AS image_url
    FROM pg_details
    WHERE 1=1
    """

    values = []

    if location:
        query += " AND location LIKE %s"
        values.append("%" + location + "%")

    if gender:
        query += " AND gender=%s"
        values.append(gender)

    if rent:
        query += " AND rent<=%s"
        values.append(rent)

    cur.execute(query, tuple(values))

    pgs = cur.fetchall()

    print("========== PG LIST ==========")
    for pg in pgs:
        print(pg)

    cur.close()

    return render_template("pg_list.html", pgs=pgs)

@app.route("/edit_pg/<int:pg_id>", methods=["GET", "POST"])
def edit_pg(pg_id):

    if "owner" not in session:
        return redirect("/owner_login")

    cur = mysql.connection.cursor()

    if request.method == "POST":

        pg_name = request.form["pg_name"]
        location = request.form["location"]
        rent = request.form["rent"]
        gender = request.form["gender"]
        description = request.form["description"]

        cur.execute("""
            UPDATE pg_details
            SET
                pg_name=%s,
                location=%s,
                rent=%s,
                gender=%s,
                description=%s
            WHERE id=%s AND owner_id=%s
        """, (
            pg_name,
            location,
            rent,
            gender,
            description,
            pg_id,
            session["owner"]
        ))

        mysql.connection.commit()
        cur.close()

        return redirect("/owner_dashboard")

    cur.execute(
        "SELECT * FROM pg_details WHERE id=%s AND owner_id=%s",
        (pg_id, session["owner"])
    )

    pg = cur.fetchone()

    cur.close()

    return render_template("edit_pg.html", pg=pg)
@app.route("/explore")
def explore_pgs():
    return render_template("explore_pgs.html")

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)