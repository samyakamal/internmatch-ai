import os
import re
import sqlite3
from functools import wraps
from pathlib import Path

from flask import Flask, render_template, request, redirect, url_for, session, flash
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from recommender import recommend_internships, extract_resume_text, SKILL_TERMS

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
UPLOAD_DIR.mkdir(exist_ok=True)
DB_PATH = BASE_DIR / "internmatch.db"
ALLOWED_EXTENSIONS = {"pdf", "docx", "txt"}

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "change-this-development-secret")
app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024  # 5 MB
app.config["UPLOAD_FOLDER"] = str(UPLOAD_DIR)

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

def init_db():
    with get_db() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );
        CREATE TABLE IF NOT EXISTS profiles (
            user_id INTEGER PRIMARY KEY,
            degree TEXT DEFAULT '',
            graduation_year TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            preferred_location TEXT DEFAULT 'Any',
            work_mode TEXT DEFAULT 'Any',
            resume_filename TEXT DEFAULT '',
            resume_text TEXT DEFAULT '',
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE TABLE IF NOT EXISTS saved_internships (
            user_id INTEGER NOT NULL,
            internship_id INTEGER NOT NULL,
            PRIMARY KEY(user_id, internship_id),
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        """)
        for internship in SEED_INTERNSHIPS:
            db.execute("""INSERT OR IGNORE INTO internships
                (id, title, company, description, skills, location, mode, duration, stipend, eligibility, apply_url)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""", internship)
        db.commit()

SEED_INTERNSHIPS = [
    (1, "Machine Learning Intern", "Nova Analytics", "Build predictive models, clean datasets, evaluate classifiers and collaborate on ML experiments.", "Python, machine learning, pandas, scikit-learn, statistics, SQL", "Bengaluru", "Hybrid", "3 months", "₹15,000/month", "Students with Python and ML fundamentals", "https://example.com/internships/ml"),
    (2, "NLP Research Intern", "LanguageLab", "Experiment with text classification, information retrieval, embeddings and natural language processing pipelines.", "Python, NLP, TF-IDF, scikit-learn, deep learning, research", "Remote", "Remote", "4 months", "₹18,000/month", "Students interested in NLP or applied research", "https://example.com/internships/nlp"),
    (3, "Data Analyst Intern", "MetricMint", "Analyze business data, create dashboards, write SQL queries and communicate insights with stakeholders.", "Python, SQL, Excel, pandas, statistics, data visualization", "Kolkata", "Hybrid", "3 months", "₹10,000/month", "Undergraduate students comfortable with data", "https://example.com/internships/data-analyst"),
    (4, "Backend Developer Intern", "StackSpring", "Build REST APIs, work with databases, write tests and maintain Python web services.", "Python, Flask, REST API, SQL, Git, testing", "Pune", "On-site", "6 months", "₹12,000/month", "Students with programming fundamentals", "https://example.com/internships/backend"),
    (5, "Computer Vision Intern", "VisionForge", "Prepare image datasets, train vision models and evaluate computer vision experiments.", "Python, OpenCV, deep learning, machine learning, NumPy, PyTorch", "Hyderabad", "Hybrid", "3 months", "₹16,000/month", "Students with Python and basic ML knowledge", "https://example.com/internships/cv"),
    (6, "AI Product Intern", "BrightAI", "Prototype AI features, evaluate model outputs, research user needs and document product experiments.", "Python, AI, machine learning, communication, research, SQL", "Remote", "Remote", "3 months", "₹14,000/month", "Students interested in applied AI", "https://example.com/internships/ai-product"),
    (7, "Frontend Developer Intern", "PixelPilot", "Create responsive interfaces, connect APIs and improve accessibility and user experience.", "HTML, CSS, JavaScript, React, Git, REST API", "Delhi", "On-site", "4 months", "₹11,000/month", "Students with web development fundamentals", "https://example.com/internships/frontend"),
    (8, "Data Science Intern", "InsightWorks", "Explore datasets, engineer features, build models and communicate analytical findings.", "Python, pandas, NumPy, machine learning, statistics, visualization", "Remote", "Remote", "5 months", "₹17,000/month", "Students studying computer science, statistics or related fields", "https://example.com/internships/data-science"),
    (9, "Cybersecurity Intern", "SafeStack", "Assist with security assessments, log analysis, vulnerability documentation and secure coding reviews.", "Networking, Linux, Python, cybersecurity, security testing", "Chennai", "Hybrid", "3 months", "₹13,000/month", "Students interested in information security", "https://example.com/internships/security"),
    (10, "Android Developer Intern", "PocketApps", "Develop Android features, integrate APIs and test mobile applications.", "Kotlin, Android, Jetpack Compose, REST API, Git", "Bengaluru", "Hybrid", "4 months", "₹12,000/month", "Students with Android development basics", "https://example.com/internships/android"),
]

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "info")
            return redirect(url_for("login"))
        return view(*args, **kwargs)
    return wrapped

def current_user():
    if "user_id" not in session:
        return None
    with get_db() as db:
        return db.execute("SELECT * FROM users WHERE id = ?", (session["user_id"],)).fetchone()

@app.route("/")
def index():
    if session.get("user_id"):
        return redirect(url_for("dashboard"))
    return render_template("landing.html")

@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        if not name or not email or len(password) < 8:
            flash("Enter your name and email, and use a password with at least 8 characters.", "error")
            return render_template("auth.html", mode="signup")
        try:
            with get_db() as db:
                cur = db.execute("INSERT INTO users(name, email, password_hash) VALUES (?, ?, ?)",
                                 (name, email, generate_password_hash(password)))
                db.execute("INSERT INTO profiles(user_id) VALUES (?)", (cur.lastrowid,))
                db.commit()
                session["user_id"] = cur.lastrowid
            flash("Account created! Complete your profile to get recommendations.", "success")
            return redirect(url_for("profile"))
        except sqlite3.IntegrityError:
            flash("That email already has an account. Try logging in.", "error")
    return render_template("auth.html", mode="signup")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        with get_db() as db:
            user = db.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("dashboard"))
        flash("Email or password is incorrect.", "error")
    return render_template("auth.html", mode="login")

@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    user = current_user()
    with get_db() as db:
        profile_row = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user["id"],)).fetchone()
    if request.method == "POST":
        degree = request.form.get("degree", "").strip()
        year = request.form.get("graduation_year", "").strip()
        skills = request.form.get("skills", "").strip()
        interests = request.form.get("interests", "").strip()
        location = request.form.get("preferred_location", "Any").strip()
        work_mode = request.form.get("work_mode", "Any").strip()
        resume_filename = profile_row["resume_filename"] or ""
        resume_text = profile_row["resume_text"] or ""
        upload = request.files.get("resume")
        if upload and upload.filename:
            filename = secure_filename(upload.filename)
            ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
            if ext not in ALLOWED_EXTENSIONS:
                flash("Upload a PDF, DOCX or TXT resume.", "error")
                return render_template("profile.html", user=user, profile=profile_row)
            stored = f"user_{user['id']}_{filename}"
            path = UPLOAD_DIR / stored
            upload.save(path)
            try:
                resume_text = extract_resume_text(path)
                resume_filename = filename
            except Exception:
                path.unlink(missing_ok=True)
                flash("We couldn't read that file. Please try another PDF, DOCX or TXT file.", "error")
                return render_template("profile.html", user=user, profile=profile_row)
        with get_db() as db:
            db.execute("""UPDATE profiles SET degree=?, graduation_year=?, skills=?, interests=?,
                preferred_location=?, work_mode=?, resume_filename=?, resume_text=? WHERE user_id=?""",
                (degree, year, skills, interests, location, work_mode, resume_filename, resume_text, user["id"]))
            db.commit()
        flash("Profile saved. Your recommendations are ready!", "success")
        return redirect(url_for("dashboard"))
    return render_template("profile.html", user=user, profile=profile_row)

@app.route("/dashboard")
@login_required
def dashboard():
    user = current_user()
    with get_db() as db:
        profile = db.execute("SELECT * FROM profiles WHERE user_id = ?", (user["id"],)).fetchone()
        internships = db.execute("SELECT * FROM internships").fetchall()
        saved = {r["internship_id"] for r in db.execute(
            "SELECT internship_id FROM saved_internships WHERE user_id = ?", (user["id"],)).fetchall()}
    query = " ".join([profile["skills"] or "", profile["interests"] or "", profile["resume_text"] or ""])
    recs = recommend_internships(query, profile["preferred_location"], profile["work_mode"], internships)
    return render_template("dashboard.html", user=user, profile=profile, recommendations=recs, saved=saved)

@app.route("/save/<int:internship_id>", methods=["POST"])
@login_required
def save_internship(internship_id):
    user_id = session["user_id"]
    with get_db() as db:
        exists = db.execute("SELECT id FROM internships WHERE id=?", (internship_id,)).fetchone()
        if not exists:
            flash("Internship not found.", "error")
            return redirect(url_for("dashboard"))
        saved = db.execute("SELECT 1 FROM saved_internships WHERE user_id=? AND internship_id=?",
                           (user_id, internship_id)).fetchone()
        if saved:
            db.execute("DELETE FROM saved_internships WHERE user_id=? AND internship_id=?", (user_id, internship_id))
            flash("Internship removed from saved items.", "info")
        else:
            db.execute("INSERT OR IGNORE INTO saved_internships(user_id, internship_id) VALUES (?, ?)",
                       (user_id, internship_id))
            flash("Internship saved.", "success")
        db.commit()
    return redirect(request.referrer or url_for("dashboard"))

@app.route("/saved")
@login_required
def saved():
    user = current_user()
    with get_db() as db:
        rows = db.execute("""SELECT i.* FROM internships i JOIN saved_internships s
            ON i.id=s.internship_id WHERE s.user_id=? ORDER BY i.title""", (user["id"],)).fetchall()
    return render_template("saved.html", user=user, internships=rows)

@app.errorhandler(413)
def too_large(_error):
    flash("That file is too large. Maximum resume size is 5 MB.", "error")
    return redirect(url_for("profile"))

# Keep demo seed data initialized after the table is created.
def ensure_internship_table():
    with get_db() as db:
        db.execute("""CREATE TABLE IF NOT EXISTS internships (
            id INTEGER PRIMARY KEY,
            title TEXT NOT NULL,
            company TEXT NOT NULL,
            description TEXT NOT NULL,
            skills TEXT NOT NULL,
            location TEXT NOT NULL,
            mode TEXT NOT NULL,
            duration TEXT NOT NULL,
            stipend TEXT NOT NULL,
            eligibility TEXT NOT NULL,
            apply_url TEXT NOT NULL
        )""")
        db.commit()

ensure_internship_table()
init_db()

if __name__ == "__main__":
    app.run(debug=True)
