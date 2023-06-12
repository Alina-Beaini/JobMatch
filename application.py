import os

from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request, session
from flask_session import Session
from tempfile import mkdtemp
from werkzeug.exceptions import default_exceptions, HTTPException, InternalServerError
from werkzeug.security import check_password_hash, generate_password_hash

from helpers import apology, login_required

# import sqlalchemy



# Configure application
app = Flask(__name__)

# Ensure templates are auto-reloaded
app.config["TEMPLATES_AUTO_RELOAD"] = True


# Ensure responses aren't cached
@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response




# Configure session to use filesystem (instead of signed cookies)
app.config["SESSION_FILE_DIR"] = mkdtemp()
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_TYPE"] = "filesystem"
Session(app)

# Configure CS50 Library to use SQLite database
db = SQL("sqlite:///jobmatch.db")


@app.route("/", methods=["GET", "POST"])
@login_required
def index():
    if request.method == "GET":

        if db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"] == 'employer':
            hiring = db.execute("SELECT * FROM hiring WHERE userid = ?", session["user_id"])
            return render_template("employer.html", hiring=hiring)
        else:
            seeking = db.execute("SELECT * FROM seeking WHERE userid = ?", session["user_id"])
            return render_template("employee.html", seeking=seeking)

    if request.method == "POST":
        if db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"] == 'employer':
            if not request.form.get("job"):
                jobs = db.execute("SELECT job FROM jobs ORDER BY job")
                majors = db.execute("SELECT major FROM majors ORDER BY major")
                return render_template("addjob.html", jobs=jobs, majors=majors)

            else:
            # add them to table hiring, and send them back to / via get --> employer (display).
                job = request.form.get("job")
                major = request.form.get("major")
                years = request.form.get("years")

                db.execute("INSERT INTO hiring (userid, position, major, years) VALUES (?,?,?,?)", session["user_id"], job, major, years)
                return redirect('/')

        else:
            if not request.form.get("job"):
                jobs = db.execute("SELECT job FROM jobs")
                return render_template("addjob2.html", jobs=jobs)
            else:
                job = request.form.get("job")
                years = request.form.get("years")

                db.execute("INSERT INTO seeking (userid, position, years) VALUES (?,?,?)", session["user_id"], job, years)
                return redirect('/')

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    Type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    if Type == 'employer':
        info = db.execute("SELECT * FROM employers WHERE userid = ?", session["user_id"])
        return render_template("employerprofile.html", info=info[0])
    else:
        info = db.execute("SELECT * FROM employees WHERE userid = ?", session["user_id"])
        return render_template("employeeprofile.html", info=info[0])
    return apology("TODO")


@app.route("/readmore", methods=["POST"])
@login_required
def readmore():
    nameid = request.form.get("nameid")
    Type = db.execute("SELECT type FROM users WHERE id = ?", nameid)[0]["type"]

    if Type == 'employee':
        info = db.execute("SELECT * FROM employees WHERE userid = ?", nameid)[0]
    else:
        info = db.execute("SELECT * FROM employers WHERE userid = ?", nameid)[0]

    return render_template("userprofile.html", Type=Type, info=info)

    return apology("TO DO")

@app.route("/match")
@login_required
def match():
    Type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    # First, matches from the point of view of employer.
    if Type == 'employer':
        jobs = db.execute("SELECT position FROM hiring WHERE userid = ?", session["user_id"])
        positions = []
        for job in jobs:
            positions.append(job["position"])
    # TO FIX THINGS: USE ID NOT USERID?
        matchseeking = db.execute("SELECT * FROM seeking WHERE position IN (?)", positions)
        ids = []
        id_years = {}
        info = {}
        id_job = {}
        for row in matchseeking:
            if row["years"] >= db.execute("SELECT years FROM hiring WHERE position = ? AND userid = ?", row["position"], session["user_id"])[0]["years"] and (db.execute("SELECT major FROM hiring WHERE userid = ? AND position = ?", session["user_id"], row["position"])[0]["major"] == db.execute("SELECT major FROM employees WHERE userid = ?", row["userid"])[0]["major"] or not db.execute("SELECT major FROM employees WHERE userid = ?", row["userid"])[0]["major"] or db.execute("SELECT major FROM hiring WHERE userid = ? AND position = ?", session["user_id"], row["position"])[0]["major"] == 'No major'):
                ids.append(row["userid"])
                id_years[row["userid"]] = row["years"]
                id_job[row["userid"]] = row["position"]
                info[row["userid"]] = db.execute("SELECT * FROM employees WHERE userid = ?", row["userid"])[0]

        for position in positions:
            major = db.execute("SELECT major FROM hiring WHERE userid = ? AND position = ?", session["user_id"], position)[0]["major"]
            employees = db.execute("SELECT * FROM employees WHERE major = ?", major)
            for employee in employees:
                if employee["years"] >= db.execute("SELECT years FROM hiring WHERE userid = ? AND position = ?", session["user_id"], position)[0]["years"]:
                    if employee["userid"] not in ids:

                        ids.append(employee["userid"])
                        id_years[employee["userid"]] = employee["years"]
                        id_job[employee["userid"]] = position
                        info[employee["userid"]] = db.execute("SELECT * FROM employees WHERE userid = ?", employee["userid"])[0]

        # info = db.execute("SELECT  * FROM employees WHERE userid IN (?)", ids)
        # Majors = db.execute("SELECT major FROM hiring WHERE userid = ?", session["user_id"])
        # majors = []
        # for major in Majors:
        #     majors.append(major["major"])
        # matchmajors = db.execute("SELECT * FROM employees WHERE major IN (?)", majors)

        # for row in matchmajors:
        #     if (row["userid"] not in ids) and (row["years"] >= db.execute("SELECT years FROM hiring WHERE userid = ? AND major = ?", session["user_id"], row["major"])[0]["years"]) :
        #         ids.append(row["userid"])
        #         id_years[row["userid"]] = row["years"]
        #         info[row["userid"]] = db.execute("SELECT  * FROM employees WHERE userid = ?", row["userid"])[0]

        return render_template("matches.html", Type=Type, id_job=id_job, info=info, id_years=id_years, ids=ids, positions=positions)

    else: # Now, pt of view of employee..
        jobs = db.execute("SELECT position FROM seeking WHERE userid = ?", session["user_id"])
        positions = []
        for job in jobs:
            positions.append(job["position"])

        matchhiring = db.execute("SELECT * FROM hiring WHERE position IN (?)", positions)

        Major = db.execute("SELECT major FROM employees WHERE userid = ?", session["user_id"])[0]["major"]
        ids = []
        id_years = {}
        info = {}
        id_job = {}

        matchmajors = db.execute("SELECT * FROM hiring WHERE major = ?", Major)

        for row in matchhiring:
            if row["years"] <= db.execute("SELECT years FROM seeking WHERE position = ? AND userid = ?", row["position"], session["user_id"])[0]["years"] and (row["major"] == 'No major' or row["major"] == Major):
                ids.append(row["userid"])
                id_years[row["userid"]] = row["years"]
                id_job[row["userid"]] = row["position"]
                info[row["userid"]] = db.execute("SELECT  * FROM employers WHERE userid = ?", row["userid"])[0]

        matchmajors = db.execute("SELECT * FROM hiring WHERE major = ?", Major)

        majorids = []
        majorid_years = {}
        majorinfo = {}
        majorid_job = {}
        for row in matchmajors:
            if (row["years"] <= db.execute("SELECT years FROM employees WHERE userid = ?", session["user_id"])[0]["years"]):
                majorids.append(row["userid"])
                majorid_years[row["userid"]] = row["years"]
                majorinfo[row["userid"]] = db.execute("SELECT  * FROM employers WHERE userid = ?", row["userid"])[0]
                majorid_job[row["userid"]] = row["position"]



        return render_template("matches.html", majorinfo=majorinfo, majorid_job=majorid_job,  majorids=majorids, majorid_years=majorid_years, info=info, Type=Type, ids=ids, id_job=id_job, id_years=id_years, positions=positions, matchmajors=matchmajors)


@app.route("/edit", methods=["GET", "POST"])
@login_required
def edit():

    Type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]

    if request.method == "GET":
        majors = db.execute("SELECT major FROM majors")
        return render_template("editprofile.html", Type=Type, majors=majors)

    if request.method == "POST":
        if Type == 'employer':
            company = request.form.get("company")
            name = request.form.get("name")
            email = request.form.get("email")
            phone = request.form.get("phone")
            location = request.form.get("location")

            if company:
                db.execute("UPDATE employers SET company = ? WHERE userid = ?", company, session["user_id"])
            if name:
                db.execute("UPDATE employers SET name = ? WHERE userid = ?", name, session["user_id"])
            if email:
                db.execute("UPDATE employers SET email = ? WHERE userid = ?", email, session["user_id"])
            if phone:
                db.execute("UPDATE employers SET phone = ? WHERE userid = ?", phone, session["user_id"])
            if location:
                db.execute("UPDATE employers SET location = ? WHERE userid = ?", location, session["user_id"])

            return redirect("/profile")

        else:
            name = request.form.get("name")
            degree = request.form.get("degree")
            major = request.form.get("major")
            years = request.form.get("years")
            email = request.form.get("email")
            phone = request.form.get("phone")
            address = request.form.get("address")


            if name:
                db.execute("UPDATE employees SET name = ? WHERE userid = ?", name, session["user_id"])
            if degree:
                db.execute("UPDATE employees SET degree = ? WHERE userid = ?", degree, session["user_id"])
            if major:
                db.execute("UPDATE employees SET major = ? WHERE userid = ?", major, session["user_id"])

            if years:
                db.execute("UPDATE employees SET years = ? WHERE userid = ?", years, session["user_id"])
            if email:
                db.execute("UPDATE employees SET email = ? WHERE userid = ?", email, session["user_id"])
            if phone:
                db.execute("UPDATE employees SET phone = ? WHERE userid = ?", phone, session["user_id"])
            if address:
                db.execute("UPDATE employees SET address = ? WHERE userid = ?", address, session["user_id"])

            return redirect("/profile")
    return apology("TBD")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Log user in"""

    # Forget any user_id
    session.clear()

    # User reached route via POST (as by submitting a form via POST)
    if request.method == "POST":

        # Ensure username was submitted
        if not request.form.get("username"):
            return apology("must provide username", 403)

        # Ensure password was submitted
        elif not request.form.get("password"):
            return apology("must provide password", 403)

        # Query database for username
        rows = db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username"))

        # Ensure username exists and password is correct
        if len(rows) != 1 or not check_password_hash(rows[0]["hash"], request.form.get("password")):
            return apology("invalid username and/or password", 403)

        # Remember which user has logged in
        session["user_id"] = rows[0]["id"]

        # Redirect user to home page
        return redirect("/")

    # User reached route via GET (as by clicking a link or via redirect)
    else:
        return render_template("login.html")


@app.route("/deletejob", methods=["POST"])
@login_required
def deletejob():
    Type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    if Type == 'employer':
        position = request.form.get("delete")
        db.execute("DELETE FROM hiring WHERE userid = ? AND position = ?", session["user_id"], position)
        # alert('DELETE FROM hiring WHERE id='+ids)


    else:
        position = request.form.get("delete")
        db.execute("DELETE FROM seeking WHERE userid = ? AND position = ?", session["user_id"], position)

    return redirect("/")

@app.route("/editjob", methods=["POST"])
@login_required
def editjob():
    Type = db.execute("SELECT type FROM users WHERE id = ?", session["user_id"])[0]["type"]
    majors = db.execute("SELECT major FROM majors")
    position = request.form.get("position")
    if position:
        return render_template("editjob.html", majors=majors, Type=Type, position=position)

    if Type == 'employee':
        years = request.form.get("years")
        position = request.form.get("job")

        if years:
            db.execute("UPDATE seeking SET years = ? WHERE userid = ? AND position = ?", years, session["user_id"], position)

    else:
        years = request.form.get("years")
        position = request.form.get("job")
        major = request.form.get("major")


        if years:
            db.execute("UPDATE hiring SET years = ? WHERE userid = ? AND position = ?", years, session["user_id"], position)
        if major:
            db.execute("UPDATE hiring SET major = ? WHERE userid = ? AND position = ?", major, session["user_id"], position)

    return redirect("/")

@app.route("/logout")
def logout():
    """Log user out"""

    # Forget any user_id
    session.clear()

    # Redirect user to login form
    return redirect("/")


@app.route("/register", methods=["GET", "POST"])
def register():
    """Register user"""
    if request.method == "GET":
        return render_template("register.html")

    if request.method == "POST":
        if not request.form.get("username"):
            return apology("must provide username", 400)
        if db.execute("SELECT * FROM users WHERE username = ?", request.form.get("username")):
            return apology("username already exists", 400)

        if request.form.get("password") != request.form.get("confirmation"):
            return apology("password does not match", 400)
        if not request.form.get("password"):
            return apology("must provide password", 400)
        if not request.form.get("type"):
            return apology("must specify what you're registering as", 400)
        username = request.form.get("username")
        password = generate_password_hash(request.form.get("password"))
        types = request.form.get("type")
        db.execute("INSERT INTO users (username,hash,type) VALUES (?,?,?)", username, password, types)

        session["username"] = username

        if types == 'employer':
            return render_template("iemployer.html", username=session["username"])
        else:
            majors = db.execute("SELECT major FROM majors ORDER BY major")
            return render_template("iemployee.html", majors=majors, username=session["username"])

        return apology("??")


@app.route("/employercont", methods=["POST"])
def employercont():
    username = session["username"]
    if db.execute("SELECT type FROM users WHERE username = ?", username)[0]["type"] == 'employee':
        return apology("not username for an employer")

    userid = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
    company = request.form.get("company")
    name = request.form.get("name")
    email = request.form.get("email")
    location = request.form.get("location")
    phone = request.form.get("phone")

    db.execute("INSERT INTO employers (userid,company,name,email,location,phone) VALUES (?,?,?,?,?,?)", userid, company, name, email, location, phone)

    return redirect("/login")

@app.route("/employeecont", methods=["POST"])
def employeecont():
    username = session["username"]
    if db.execute("SELECT type FROM users WHERE username = ?", username)[0]["type"] == 'employer':
        return apology("not username for an employee")

    userid = db.execute("SELECT id FROM users WHERE username = ?", username)[0]["id"]
    name = request.form.get("name")
    email = request.form.get("email")
    address = request.form.get("address")
    phone = request.form.get("phone")
    degree = request.form.get("degree")
    major = request.form.get("major")
    years = request.form.get("years")

    if not years:
        years = 0

    if not major:
        major = 'No major'


    db.execute("INSERT INTO employees (userid,name,email,address,phone, degree, major, years) VALUES (?,?,?,?,?,?,?,?)", userid, name, email, address, phone, degree, major, years)

    return redirect("/login")



def errorhandler(e):
    """Handle error"""
    if not isinstance(e, HTTPException):
        e = InternalServerError()
    return apology(e.name, e.code)


# Listen for errors
for code in default_exceptions:
    app.errorhandler(code)(errorhandler)
